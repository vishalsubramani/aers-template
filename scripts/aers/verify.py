from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .contracts import load_bundle
from .git import export_commit, head_sha, is_clean, rev_parse
from .scope import classify_path, evaluate_scope
from .util import atomic_write_json, hash_object, load_json, redact, sha256_bytes, utc_now


def _network_prefix() -> tuple[list[str], str]:
    if os.environ.get("AERS_NETWORK_ISOLATED") == "1":
        return [], "external_enforced"
    if shutil.which("unshare"):
        probe = subprocess.run(["unshare", "-Urn", "true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if probe.returncode == 0:
            return ["unshare", "-Urn", "--"], "linux_user_network_namespace"
    return [], "unavailable"


def _scrubbed_env(home: Path) -> dict[str, str]:
    allowed = {"PATH", "LANG", "LC_ALL", "TZ", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"}
    env = {key:value for key,value in os.environ.items() if key in allowed}
    env.update({"HOME":str(home),"CI":"1","AERS_VERIFICATION":"author","GIT_CONFIG_NOSYSTEM":"1",
                "http_proxy":"","https_proxy":"","HTTP_PROXY":"","HTTPS_PROXY":"","ALL_PROXY":"","NO_PROXY":"*"})
    return env


def author_verify(repo: Path, feature_id: str, task_id: str, base_ref: str, output: Path, degraded: bool = False) -> dict[str, Any]:
    base_sha = rev_parse(repo, base_ref)
    candidate_sha = head_sha(repo)
    bundle = load_bundle(repo, feature_id, task_id, ref=base_sha)
    scope = evaluate_scope(repo, feature_id, task_id, base_sha, contract_ref=base_sha)
    integrity: dict[str, Any] = {"clean_candidate":is_clean(repo),"scope_passed":scope.passed,"network_mode":None,
                                 "clean_export":False,"contract_ref":base_sha,"contract_hashes":scope.contract_hashes}
    commands: list[dict[str, Any]] = []
    fatal: list[str] = []
    if not integrity["clean_candidate"]:
        fatal.append("Candidate worktree is dirty; verification must bind to an exact commit")
    if not scope.passed:
        fatal.append("Scope/protected-path/budget gate failed")
    prefix, network_mode = _network_prefix()
    integrity["network_mode"] = network_mode
    if network_mode == "unavailable" and not degraded:
        fatal.append("Network isolation could not be proven; fail closed or explicitly request degraded local evidence")

    if not fatal or degraded:
        with tempfile.TemporaryDirectory(prefix="aers-export-") as temp:
            export_root = Path(temp) / "source"
            export_commit(repo, candidate_sha, export_root)
            integrity["clean_export"] = True
            home = Path(temp) / "home"; home.mkdir()
            env = _scrubbed_env(home)
            for spec in bundle.task["commands"]:
                if spec.get("network", "deny") != "deny":
                    commands.append({"name":spec["name"],"argv":spec["argv"],"status":"not_run","reason":"allowlisted network commands require trusted infrastructure"})
                    fatal.append(f"Command requires allowlisted network: {spec['name']}")
                    continue
                argv = [*prefix, *spec["argv"]] if network_mode != "unavailable" else list(spec["argv"])
                start = time.monotonic()
                try:
                    proc = subprocess.run(argv, cwd=export_root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          timeout=spec["timeout_seconds"])
                    status = "pass" if proc.returncode == 0 else "fail"
                    if proc.returncode != 0:
                        fatal.append(f"Command failed: {spec['name']}")
                    commands.append({"name":spec["name"],"argv":spec["argv"],"executed_argv":argv,"status":status,
                                     "returncode":proc.returncode,"duration_seconds":round(time.monotonic()-start,3),
                                     "stdout":redact(proc.stdout),"stderr":redact(proc.stderr)})
                except subprocess.TimeoutExpired as exc:
                    fatal.append(f"Command timed out: {spec['name']}")
                    commands.append({"name":spec["name"],"argv":spec["argv"],"status":"timeout","duration_seconds":round(time.monotonic()-start,3),
                                     "stdout":redact(exc.stdout or ""),"stderr":redact(exc.stderr or "")})

    differential: list[dict[str, Any]] = []
    task_diff = bundle.task.get("differential")
    if task_diff and not fatal:
        policy = load_json(repo / ".agents/policies/protected-paths.json")
        test_paths = [p for p in scope.changed_paths if "test" in classify_path(p, policy)]
        if test_paths:
            with tempfile.TemporaryDirectory(prefix="aers-diffbase-") as base_temp:
                base_root = Path(base_temp) / "base"
                export_commit(repo, base_sha, base_root)
                cand_temp = tempfile.TemporaryDirectory(prefix="aers-diffcand-")
                cand_root = Path(cand_temp.name) / "cand"
                export_commit(repo, candidate_sha, cand_root)
                home2 = Path(base_temp) / "home"; home2.mkdir()
                env2 = _scrubbed_env(home2)
                prefix2, _mode2 = _network_prefix()
                for test_path in test_paths:
                    source_file = cand_root / test_path
                    if not source_file.exists():
                        continue
                    target = base_root / test_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source_file.read_bytes())
                    argv = [token.replace("{file}", test_path) for token in task_diff["argv_template"]]
                    argv = [*prefix2, *argv] if _mode2 != "unavailable" else argv
                    try:
                        proc = subprocess.run(argv, cwd=base_root, env=env2, text=True,
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                              timeout=task_diff.get("timeout_seconds", 120))
                        passes_on_base = proc.returncode == 0
                        entry = {"file": test_path, "fails_on_base": not passes_on_base,
                                 "executed_argv": argv, "returncode": proc.returncode,
                                 "stdout_tail": redact(proc.stdout[-1500:]), "stderr_tail": redact(proc.stderr[-1500:])}
                    except subprocess.TimeoutExpired:
                        passes_on_base = False
                        entry = {"file": test_path, "fails_on_base": True, "executed_argv": argv, "returncode": "timeout"}
                    differential.append(entry)
                    if passes_on_base:
                        fatal.append(f"DIFFERENTIAL_TEST_PASSES_ON_BASE: {test_path} does not discriminate the new behavior")
                cand_temp.cleanup()
        integrity["differential"] = differential

    if fatal:
        verdict = "DEGRADED" if degraded and all(c.get("status") in {"pass"} for c in commands) and scope.passed and integrity["clean_candidate"] else "AUTHOR_FAILED"
    else:
        verdict = "AUTHOR_READY"
    report = {"schema_version":1,"generated_at":utc_now(),"verdict":verdict,"base_sha":base_sha,"candidate_sha":candidate_sha,
              "feature_id":feature_id,"task_id":task_id,"integrity":integrity,"scope":scope.to_dict(),"commands":commands,
              "fatal_reasons":fatal,"statement":"This author-side report cannot issue VERIFIED."}
    report["report_hash"] = hash_object(report)
    atomic_write_json(output, report)
    return report

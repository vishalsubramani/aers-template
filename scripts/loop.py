#!/usr/bin/env python3
"""Fresh-process, single-writer AERS task loop.

The loop creates candidates only. It never pushes, merges, releases, accesses private tests,
or issues VERIFIED. Run it inside an independently configured sandbox.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aers.audit import audit_candidate
from aers.config import load_config
from aers.context import build_context_packet
from aers.contracts import load_bundle
from aers.git import changed_paths, diff_text, head_sha, rev_parse, run_git
from aers.ledger import ALLOWED_TASK_TRANSITIONS, Ledger
from aers.scope import evaluate_scope
from aers.util import atomic_write_json, atomic_write_text, hash_object, load_json, redact, utc_now
from aers.verify import author_verify


def parse_command_env(name: str) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        raise ValueError(f"{name} must be a JSON array of argv tokens; shell strings are forbidden")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} is not valid JSON: {exc}") from exc
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
        raise ValueError(f"{name} must be a non-empty JSON string array")
    return value


def render_argv(template: list[str], values: dict[str, str]) -> list[str]:
    rendered=[]
    for token in template:
        for key,value in values.items():
            token=token.replace("{"+key+"}",value)
        rendered.append(token)
    return rendered


def dependencies_ready(ledger: Ledger, feature_id: str, task: dict) -> tuple[bool, list[str]]:
    blocked=[]
    for dep in task["depends_on"]:
        status=ledger.task(feature_id,dep)["status"]
        if status not in {"author_ready","verified","merged","released"}:
            blocked.append(f"{dep}:{status}")
    return not blocked, blocked


def validate_reviewer(path: Path, feature_id: str, task_id: str, candidate_sha: str, required_acceptance: list[str]) -> dict:
    if not path.exists():
        raise ValueError("Reviewer did not create its required JSON report")
    value=load_json(path)
    required=["schema_version","feature_id","task_id","candidate_sha","verdict","findings","acceptance_reviewed"]
    missing=[x for x in required if x not in value]
    if missing:
        raise ValueError(f"Reviewer report missing fields: {missing}")
    if value["schema_version"]!=1 or value["feature_id"]!=feature_id or value["task_id"]!=task_id or value["candidate_sha"]!=candidate_sha:
        raise ValueError("Reviewer report identity does not bind to the candidate")
    if value["verdict"] not in {"pass","fail","needs_review"}:
        raise ValueError("Reviewer verdict is invalid")
    if set(required_acceptance)-set(value["acceptance_reviewed"]):
        raise ValueError("Reviewer did not review all task acceptance criteria")
    if not isinstance(value["findings"],list):
        raise ValueError("Reviewer findings must be an array")
    return value


def validate_llm_audit(path: Path, feature_id: str, task_id: str, candidate_sha: str) -> dict:
    if not path.exists():
        raise ValueError("LLM auditor did not create its required JSON report")
    value=load_json(path)
    required=["schema_version","feature_id","task_id","candidate_sha","verdict","findings"]
    missing=[x for x in required if x not in value]
    if missing:
        raise ValueError(f"LLM audit report missing fields: {missing}")
    if value["schema_version"]!=1 or value["feature_id"]!=feature_id or value["task_id"]!=task_id or value["candidate_sha"]!=candidate_sha:
        raise ValueError("LLM audit report identity does not bind to the candidate")
    if value["verdict"] not in {"pass","needs_work","security_stop"}:
        raise ValueError("LLM audit verdict is invalid")
    if not isinstance(value["findings"],list):
        raise ValueError("LLM audit findings must be an array")
    return value


def failure_count(ledger: Ledger, feature_id: str, task_id: str, fingerprint: str) -> int:
    with ledger.connect() as conn:
        row=conn.execute("SELECT COUNT(*) AS n FROM runs WHERE feature_id=? AND task_id=? AND failure_fingerprint=?",
                         (feature_id,task_id,fingerprint)).fetchone()
        return int(row["n"])


def cleanup_failed(source_repo: Path, worktree: Path, branch: str) -> None:
    if worktree.exists():
        run_git(worktree,["reset","--hard","HEAD"],check=False)
        run_git(worktree,["clean","-fd"],check=False)
    run_git(source_repo,["worktree","remove","--force",str(worktree)],check=False)
    run_git(source_repo,["branch","-D",branch],check=False)


def make_prompt(bundle, context_path: Path, run_id: str, trajectory: Path, output: Path) -> None:
    task=bundle.task
    criteria={c["id"]:c for c in bundle.feature["acceptance_criteria"]}
    lines=[
      "# AERS bounded implementation task", "", f"Run: `{run_id}`", f"Feature: `{bundle.feature['feature_id']}`", f"Task: `{task['id']}`",
      f"Role: `{task['role']}`", "", "## Context packet", "", context_path.read_text(encoding="utf-8"), "", "## Immutable authority",
      f"Write scope: {task['write_scope']}", f"Budgets: {task['budget']}", "Do not edit the contract, task graph, tests (unless test_author), hooks, policies, evals, workflows, or verifier.",
      "Do not commit, push, merge, or change permissions. The orchestrator owns candidate commits.", "", "## Acceptance"
    ]
    for cid in task["acceptance"]:
        lines.append(f"- {cid}: {criteria[cid]['statement']}")
    lines += ["", "## Execution", "1. Inspect primary evidence and form falsifiable hypotheses.", "2. Implement the smallest coherent change inside scope.",
              "3. Run targeted author-visible checks without weakening them.", "4. Leave the worktree uncommitted for the orchestrator.",
              f"5. Append normalized, redacted JSONL trajectory events to `{trajectory}` when your runtime supports it.",
              "6. Safe-stop on ambiguity, integrity failure, permission need, repeated failure, or budget pressure."]
    atomic_write_text(output,"\n".join(lines)+"\n")


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature",required=True);parser.add_argument("--task",required=True)
    parser.add_argument("--contract-ref",default="HEAD",help="Approved commit containing immutable feature/task contracts")
    parser.add_argument("--owner",default=f"orchestrator-{os.getpid()}")
    args=parser.parse_args(argv)
    cfg=load_config(); source=cfg.repo; contract_sha=rev_parse(source,args.contract_ref)
    mission=source/"MISSION.md"
    if mission.exists() and "<!-- PLACEHOLDER" in mission.read_text(encoding="utf-8",errors="replace"):
        print("SAFE_STOP: MISSION.md is still the unfilled placeholder; a human must state the repository's mission before autonomous work",file=sys.stderr);return 2
    bundle=load_bundle(source,args.feature,args.task,ref=contract_sha)
    if bundle.feature["risk_tier"]=="R3":
        print("SAFE_STOP: R3 tasks cannot produce autonomous candidates",file=sys.stderr);return 2
    ledger=Ledger(cfg.state_dir/"ledger.sqlite3")
    ledger.register(bundle.feature,bundle.tasks_doc,contract_sha)
    ready,blocked=dependencies_ready(ledger,args.feature,bundle.task)
    if not ready:
        print(f"SAFE_STOP: dependencies not ready: {blocked}",file=sys.stderr);return 2
    current=ledger.task(args.feature,args.task)
    if current["attempts"] >= bundle.task["budget"]["max_attempts"]:
        print("SAFE_STOP: attempt budget exhausted",file=sys.stderr);return 2
    run_id=ledger.start_run(args.feature,args.task,args.owner)
    branch=f"aers/{args.feature.lower()}/{args.task.lower()}-{run_id[-8:].lower()}"
    worktree_root=Path(os.environ.get("AERS_WORKTREE_DIR", str(cfg.repo.parent / f".{cfg.repo.name}-aers-worktrees")))
    worktree=worktree_root/run_id
    evidence=cfg.evidence_dir/run_id; evidence.mkdir(parents=True,exist_ok=True)
    trajectory=evidence/"trajectory.jsonl"
    atomic_write_text(trajectory,json.dumps({"timestamp":utc_now(),"run_id":run_id,"event_type":"state","result":"run_started","redacted":True})+"\n")
    try:
        run_git(source,["worktree","add","-b",branch,str(worktree),contract_sha])
        ledger.transition(args.feature,args.task,"implementing",run_id,{"worktree":str(worktree),"branch":branch})
        context_path=evidence/"context.md"; build_context_packet(source,args.feature,args.task,contract_sha,context_path)
        prompt_path=evidence/"prompt.md"; make_prompt(bundle,context_path,run_id,trajectory,prompt_path)
        agent_template=parse_command_env("AERS_AGENT_CMD_JSON")
        agent_argv=render_argv(agent_template,{"prompt_file":str(prompt_path),"worktree":str(worktree),"trajectory":str(trajectory),"run_id":run_id})
        env={**os.environ,"AERS_FEATURE_ID":args.feature,"AERS_TASK_ID":args.task,"AERS_BASE_SHA":contract_sha,
             "AERS_RUN_ID":run_id,"AERS_TRAJECTORY_PATH":str(trajectory),"AERS_STATE_DIR":str(cfg.state_dir),"AERS_EVIDENCE_DIR":str(cfg.evidence_dir)}
        proc=subprocess.run(agent_argv,cwd=worktree,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                            timeout=bundle.task["budget"]["max_seconds"])
        atomic_write_text(evidence/"agent.stdout.txt",redact(proc.stdout));atomic_write_text(evidence/"agent.stderr.txt",redact(proc.stderr))
        with trajectory.open("a",encoding="utf-8") as tf:
            tf.write(json.dumps({"timestamp":utc_now(),"run_id":run_id,"event_type":"model","result":"agent_process_finished","redacted":True,"attributes":{"returncode":proc.returncode}})+"\n")
        if proc.returncode!=0:
            raise RuntimeError(f"agent process exited {proc.returncode}")
        scope=evaluate_scope(worktree,args.feature,args.task,contract_sha,contract_ref=contract_sha)
        atomic_write_json(evidence/"scope.json",scope.to_dict())
        if not scope.changed_paths:
            raise RuntimeError("agent produced no changed files")
        if not scope.passed:
            raise RuntimeError("scope gate failed: "+json.dumps(scope.findings,sort_keys=True))
        ledger.transition(args.feature,args.task,"scope_passed",run_id)
        run_git(worktree,["config","user.name","AERS Orchestrator"]);run_git(worktree,["config","user.email","aers-orchestrator@invalid.local"])
        run_git(worktree,["add","--",*scope.changed_paths])
        staged=run_git(worktree,["diff","--cached","--name-only"]).stdout.splitlines()
        if sorted(staged)!=sorted(scope.changed_paths):
            raise RuntimeError("staged path set differs from approved changed path set")
        run_git(worktree,["commit","-m",f"{args.feature} {args.task}: {bundle.task['title']}"])
        candidate=head_sha(worktree);ledger.set_candidate(args.feature,args.task,candidate,run_id)
        ledger.transition(args.feature,args.task,"candidate_committed",run_id,{"candidate_sha":candidate})
        ledger.transition(args.feature,args.task,"author_verifying",run_id)
        author_path=evidence/"author-report.json"
        author=author_verify(worktree,args.feature,args.task,contract_sha,author_path,degraded=False)
        if author["verdict"]!="AUTHOR_READY":
            reasons="; ".join(author.get("fatal_reasons") or [])
            raise RuntimeError("author verification did not produce AUTHOR_READY"+(f": {reasons}" if reasons else ""))
        ledger.transition(args.feature,args.task,"auditing",run_id)
        audit_path=evidence/"audit-report.json"
        audit=audit_candidate(worktree,args.feature,args.task,contract_sha,run_id,trajectory,audit_path)
        if audit["verdict"]!="pass":
            raise RuntimeError(f"deterministic audit verdict is {audit['verdict']}")
        llm_audit_raw=os.environ.get("AERS_AUDITOR_CMD_JSON")
        if llm_audit_raw:
            auditor_template=parse_command_env("AERS_AUDITOR_CMD_JSON")
            auditor_prompt=evidence/"llm-audit-prompt.md"
            auditor_output=evidence/"llm-audit-report.json"
            role_text=(cfg.repo/".claude/agents/auditor.md").read_text(encoding="utf-8")
            atomic_write_text(auditor_prompt,
              role_text+"\n\n---\n"
              f"Run: {run_id}\nFeature: {args.feature}\nTask: {args.task}\nBase: {contract_sha}\nCandidate: {candidate}\n"
              f"Evidence to read: {context_path}, {author_path}, {audit_path}, the Git diff `git diff {contract_sha}..{candidate}`, "
              f"and the trajectory at {trajectory}.\n"
              f"Write STRICT schema-valid JSON to {auditor_output} with schema_version=1, feature_id, task_id, candidate_sha, "
              "verdict (pass|needs_work|security_stop), findings, confidence. You cannot issue VERIFIED and must not edit the worktree.\n")
            auditor_argv=render_argv(auditor_template,{"audit_prompt":str(auditor_prompt),"output":str(auditor_output),
                                                       "worktree":str(worktree),"candidate_sha":candidate,"run_id":run_id})
            audit_proc=subprocess.run(auditor_argv,cwd=worktree,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                      timeout=min(900,bundle.task["budget"]["max_seconds"]))
            atomic_write_text(evidence/"llm-auditor.stdout.txt",redact(audit_proc.stdout))
            atomic_write_text(evidence/"llm-auditor.stderr.txt",redact(audit_proc.stderr))
            if audit_proc.returncode!=0:
                raise RuntimeError(f"LLM auditor process exited {audit_proc.returncode}")
            llm_report=validate_llm_audit(auditor_output,args.feature,args.task,candidate)
            if llm_report["verdict"]!="pass":
                raise RuntimeError(f"LLM audit verdict is {llm_report['verdict']}")
        ledger.transition(args.feature,args.task,"reviewing",run_id)
        reviewer_template=parse_command_env("AERS_REVIEWER_CMD_JSON")
        reviewer_prompt=evidence/"reviewer-prompt.md"
        atomic_write_text(reviewer_prompt,
          f"Review candidate {candidate} for {args.feature}/{args.task} against original contracts at {contract_sha}.\n"
          f"Read {context_path}, {author_path}, {audit_path}, and the Git diff. Flag only evidence-backed correctness, scope, security, operability, or requirement gaps.\n"
          f"Write schema-valid JSON to {evidence/'reviewer-report.json'} with schema_version=1, feature_id, task_id, candidate_sha, verdict, findings, acceptance_reviewed.\n"
          "You cannot issue VERIFIED and must not edit the worktree.\n")
        reviewer_output=evidence/"reviewer-report.json"
        reviewer_argv=render_argv(reviewer_template,{"review_prompt":str(reviewer_prompt),"output":str(reviewer_output),"worktree":str(worktree),"candidate_sha":candidate,"run_id":run_id})
        review_proc=subprocess.run(reviewer_argv,cwd=worktree,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   timeout=min(900,bundle.task["budget"]["max_seconds"]))
        atomic_write_text(evidence/"reviewer.stdout.txt",redact(review_proc.stdout));atomic_write_text(evidence/"reviewer.stderr.txt",redact(review_proc.stderr))
        if review_proc.returncode!=0:
            raise RuntimeError(f"reviewer process exited {review_proc.returncode}")
        review=validate_reviewer(reviewer_output,args.feature,args.task,candidate,bundle.task["acceptance"])
        if review["verdict"]!="pass":
            raise RuntimeError(f"reviewer verdict is {review['verdict']}")
        ledger.transition(args.feature,args.task,"author_ready",run_id,{"candidate_sha":candidate,"author_report_hash":author["report_hash"],"audit_hash":audit["evidence_hash"]})
        ledger.finish_run(run_id,"author_ready",str(evidence))
        summary={"verdict":"AUTHOR_READY","run_id":run_id,"feature_id":args.feature,"task_id":args.task,"base_sha":contract_sha,
                 "candidate_sha":candidate,"branch":branch,"worktree":str(worktree),"evidence":str(evidence),
                 "statement":"External verifier attestation is still required; no push/merge/release was performed."}
        atomic_write_json(evidence/"summary.json",summary);print(json.dumps(summary,indent=2));return 0
    except Exception as exc:
        fingerprint=hash_object({"type":type(exc).__name__,"message":str(exc)})
        try:
            if worktree.exists():
                atomic_write_text(evidence/"failed-attempt.patch", diff_text(worktree, contract_sha))
        except Exception:
            pass
        try:
            task_state=ledger.task(args.feature,args.task)["status"]
            if "failed" in ALLOWED_TASK_TRANSITIONS.get(task_state,set()):
                ledger.transition(args.feature,args.task,"failed",run_id,{"error":str(exc),"fingerprint":fingerprint})
        except Exception:
            pass
        ledger.finish_run(run_id,"failed",str(evidence),fingerprint)
        atomic_write_json(evidence/"failure.json",{"run_id":run_id,"error":type(exc).__name__,"message":str(exc),"fingerprint":fingerprint})
        repeated=failure_count(ledger,args.feature,args.task,fingerprint)
        cleanup_failed(source,worktree,branch)
        if repeated>=2:
            try:
                task_state=ledger.task(args.feature,args.task)["status"]
                if "safe_stopped" in ALLOWED_TASK_TRANSITIONS.get(task_state,set()):
                    ledger.transition(args.feature,args.task,"safe_stopped",run_id,{"fingerprint":fingerprint,"reason":"repeated failure fingerprint"})
            except Exception:
                pass
            print(f"SAFE_STOP: repeated failure fingerprint {fingerprint}: {exc}",file=sys.stderr)
        else:
            print(f"FAILED ATTEMPT (rolled back): {exc}",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())

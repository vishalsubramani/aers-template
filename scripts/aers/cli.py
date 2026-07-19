"""argparse command surface for the AERS control plane (`python3 scripts/aers.py --help`)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .audit import audit_candidate
from .config import load_config
from .context import build_context_packet
from .contracts import feature_paths, load_bundle, validate_feature, validate_tasks
from .evals import run_public
from .feature import init_feature
from .git import head_sha, rev_parse
from .hooks import pre_tool_guard, task_completed_gate
from .ledger import Ledger
from .lint import lint_repo
from .memory import promote, propose
from .repo_map import generate
from .scope import evaluate_scope
from .util import atomic_write_json, load_json, utc_now
from .verify import author_verify


def _json(value):
    print(json.dumps(value, indent=2, sort_keys=False))


def _ledger(cfg):
    return Ledger(cfg.state_dir / "ledger.sqlite3")


def build_parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(prog="aers",description="AERS verified-autonomy control plane")
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("lint")
    i=sub.add_parser("init-feature");i.add_argument("feature_id");i.add_argument("--title",required=True);i.add_argument("--mode",choices=["S0","S1","S2"],default="S1");i.add_argument("--risk",choices=["R0","R1","R2","R3"],default="R2")
    sub.add_parser("ledger-init")
    r=sub.add_parser("register");r.add_argument("--feature",required=True);r.add_argument("--ref",default="HEAD")
    s=sub.add_parser("ledger-show");s.add_argument("--feature")
    rq=sub.add_parser("requeue");rq.add_argument("--feature",required=True);rq.add_argument("--task",required=True);rq.add_argument("--reason",required=True,help="Human-stated reason (e.g. stale stack); recorded on the event chain")
    c=sub.add_parser("context-pack");c.add_argument("--feature",required=True);c.add_argument("--task",required=True);c.add_argument("--base");c.add_argument("--output")
    sc=sub.add_parser("scope-check");sc.add_argument("--feature",required=True);sc.add_argument("--task",required=True);sc.add_argument("--base",required=True);sc.add_argument("--contract-ref",help="Ref for immutable contracts when it differs from --base (stacked tasks)");sc.add_argument("--output")
    v=sub.add_parser("author-verify");v.add_argument("--feature",required=True);v.add_argument("--task",required=True);v.add_argument("--base",required=True);v.add_argument("--contract-ref",help="Ref for immutable contracts when it differs from --base (stacked tasks)");v.add_argument("--output");v.add_argument("--degraded",action="store_true")
    a=sub.add_parser("audit");a.add_argument("--feature",required=True);a.add_argument("--task",required=True);a.add_argument("--base",required=True);a.add_argument("--contract-ref",help="Ref for immutable contracts when it differs from --base (stacked tasks)");a.add_argument("--run-id",default="RUN-LOCAL");a.add_argument("--trajectory");a.add_argument("--output")
    sub.add_parser("eval-public")
    rm=sub.add_parser("repo-map");rm.add_argument("--output")
    mp=sub.add_parser("memory-propose");mp.add_argument("--statement",required=True);mp.add_argument("--scope",action="append",default=[]);mp.add_argument("--provenance",action="append",required=True);mp.add_argument("--review-by",required=True);mp.add_argument("--link",action="append",default=[],help="ID of a related memory record; retrieval follows links one hop")
    pr=sub.add_parser("memory-promote");pr.add_argument("record");pr.add_argument("--validation",action="append",required=True)
    h=sub.add_parser("hook");h.add_argument("hook_name",choices=["pre-tool","task-completed"])
    return p


def main(argv: list[str] | None=None) -> int:
    args=build_parser().parse_args(argv)
    try:
        cfg=load_config()
        if args.command=="lint":
            report=lint_repo(cfg.repo);_json(report);return 0 if report["passed"] else 1
        if args.command=="init-feature":
            path=init_feature(cfg.repo,args.feature_id,args.title,args.mode,args.risk);_json({"created":str(path)});return 0
        if args.command=="ledger-init":
            ledger=_ledger(cfg);_json({"ledger":str(ledger.path)});return 0
        if args.command=="register":
            ref=rev_parse(cfg.repo,args.ref)
            fp,tp=feature_paths(args.feature)
            import json as _j
            from .git import read_file_at_ref
            feature=_j.loads(read_file_at_ref(cfg.repo,ref,fp))
            tasks=_j.loads(read_file_at_ref(cfg.repo,ref,tp))
            _ledger(cfg).register(feature,tasks,ref);_json({"registered":args.feature,"base_sha":ref});return 0
        if args.command=="ledger-show":
            ledger=_ledger(cfg)
            view=ledger.view(args.feature)
            if args.feature:
                view["stale_stacks"]=ledger.stale_stacks(args.feature)
            _json(view)
            return 0
        if args.command=="context-pack":
            base=args.base or load_json(cfg.feature_root/args.feature/"feature.contract.json")["base_ref"]
            output=Path(args.output) if args.output else cfg.state_dir/"context"/f"{args.feature}-{args.task}.md"
            _json(build_context_packet(cfg.repo,args.feature,args.task,base,output))
            return 0
        if args.command=="scope-check":
            report=evaluate_scope(cfg.repo,args.feature,args.task,args.base,contract_ref=args.contract_ref or args.base)
            if args.output: atomic_write_json(Path(args.output),report.to_dict())
            _json(report.to_dict())
            return 0 if report.passed else 1
        if args.command=="author-verify":
            output=Path(args.output) if args.output else cfg.evidence_dir/f"author-{args.feature}-{args.task}-{head_sha(cfg.repo)[:12]}.json"
            report=author_verify(cfg.repo,args.feature,args.task,args.base,output,args.degraded,contract_ref=args.contract_ref);_json({"report":str(output),**report});return 0 if report["verdict"]=="AUTHOR_READY" else 1
        if args.command=="audit":
            output=Path(args.output) if args.output else cfg.evidence_dir/f"audit-{args.feature}-{args.task}-{head_sha(cfg.repo)[:12]}.json"
            report=audit_candidate(cfg.repo,args.feature,args.task,args.base,args.run_id,Path(args.trajectory) if args.trajectory else None,output,contract_ref=args.contract_ref);_json({"report":str(output),**report});return 0 if report["verdict"]=="pass" else 1
        if args.command=="eval-public":
            report=run_public(cfg.repo);_json(report);return 0 if report["passed"] else 1
        if args.command=="repo-map":
            output=Path(args.output) if args.output else cfg.repo/".agents/context/repo-map.generated.md";_json(generate(cfg.repo,output));return 0
        if args.command=="requeue":
            _ledger(cfg).requeue(args.feature,args.task,args.reason)
            _json({"requeued":f"{args.feature}/{args.task}","reason":args.reason})
            return 0
        if args.command=="memory-propose":
            path=propose(cfg.repo,args.statement,args.scope,args.provenance,args.review_by,links=args.link)
            _json({"proposal":str(path)})
            return 0
        if args.command=="memory-promote":
            path=promote(cfg.repo,Path(args.record),args.validation);_json({"active":str(path)});return 0
        if args.command=="hook":
            if args.hook_name=="pre-tool":
                payload=json.load(sys.stdin)
                return pre_tool_guard(payload)
            return task_completed_gate()
        raise ValueError(f"Unhandled command: {args.command}")
    except Exception as exc:
        _json({"error":type(exc).__name__,"message":str(exc)});return 2

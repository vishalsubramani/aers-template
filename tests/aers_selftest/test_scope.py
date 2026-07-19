import json, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from aers.scope import matches, classify_path, evaluate_scope

class ScopeTests(unittest.TestCase):
    def test_globs_and_colocated_tests(self):
        self.assertTrue(matches("src/x.py", ["src/**"]))
        policy=json.loads((Path(__file__).resolve().parents[2]/".agents/policies/protected-paths.json").read_text())
        self.assertIn("test", classify_path("src/foo_test.go", policy))
        self.assertIn("test", classify_path("lib/foo.spec.ts", policy))
        self.assertIn("protected", classify_path(".claude/hooks/pre-tool.py", policy))

    def test_integrated_scope_blocks_test(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            subprocess.run(["git","init","-q",str(repo)],check=True)
            subprocess.run(["git","-C",str(repo),"config","user.email","t@example.invalid"],check=True)
            subprocess.run(["git","-C",str(repo),"config","user.name","Test"],check=True)
            (repo/".agents/policies").mkdir(parents=True);(repo/".specify/specs/FEAT-X").mkdir(parents=True);(repo/"src").mkdir()
            policy=json.loads((Path(__file__).resolve().parents[2]/".agents/policies/protected-paths.json").read_text())
            (repo/".agents/policies/protected-paths.json").write_text(json.dumps(policy))
            feature={"schema_version":1,"feature_id":"FEAT-X","title":"x feature","spec_mode":"S1","risk_tier":"R1","status":"approved","base_ref":"HEAD","acceptance_criteria":[{"id":"AC-001","statement":"works","evidence":["test"]}],"contracts":[],"quality":{"security":[],"reliability":[],"observability":[]},"rollout":{"strategy":"flag","rollback":"disable"}}
            tasks={"schema_version":1,"feature_id":"FEAT-X","tasks":[{"id":"T-001","title":"code","role":"implementer","depends_on":[],"write_scope":["src/**"],"acceptance":["AC-001"],"commands":[],"budget":{"max_attempts":2,"max_files":5,"max_lines":100,"max_seconds":60}}]}
            (repo/".specify/specs/FEAT-X/feature.contract.json").write_text(json.dumps(feature));(repo/".specify/specs/FEAT-X/tasks.json").write_text(json.dumps(tasks));(repo/"src/x.py").write_text("x=1\n")
            subprocess.run(["git","-C",str(repo),"add","."],check=True);subprocess.run(["git","-C",str(repo),"commit","-qm","base"],check=True)
            base=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
            (repo/"src/foo_test.go").write_text("package x\n")
            report=evaluate_scope(repo,"FEAT-X","T-001",base,contract_ref=base)
            self.assertFalse(report.passed)
            self.assertTrue(any(f["code"]=="IMPLEMENTER_EDITED_TEST" for f in report.findings))

if __name__ == "__main__": unittest.main()

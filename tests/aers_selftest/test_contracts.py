import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"scripts"))
from aers.contracts import validate_feature, validate_tasks

class ContractTests(unittest.TestCase):
    def feature(self):
        return {"schema_version":1,"feature_id":"FEAT-X","title":"valid title","spec_mode":"S1","risk_tier":"R1","status":"approved","base_ref":"HEAD","acceptance_criteria":[{"id":"AC-001","statement":"works","evidence":["test"]}],"contracts":[],"quality":{"security":[],"reliability":[],"observability":[]},"rollout":{"strategy":"flag","rollback":"disable"}}
    def task(self,id,deps):
        return {"id":id,"title":"task","role":"implementer","depends_on":deps,"write_scope":["src/**"],"acceptance":["AC-001"],"commands":[],"budget":{"max_attempts":2,"max_files":5,"max_lines":100,"max_seconds":60}}
    def test_valid(self):
        f=self.feature();validate_feature(f);validate_tasks({"schema_version":1,"feature_id":"FEAT-X","tasks":[self.task("T-001",[])]},f)
    def test_cycle_rejected(self):
        f=self.feature();tasks={"schema_version":1,"feature_id":"FEAT-X","tasks":[self.task("T-001",["T-002"]),self.task("T-002",["T-001"])]}
        with self.assertRaises(ValueError):validate_tasks(tasks,f)

if __name__ == "__main__": unittest.main()

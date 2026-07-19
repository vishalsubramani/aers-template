import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
from aers.ledger import Ledger

class LedgerTests(unittest.TestCase):
    def feature(self):return {"schema_version":1,"feature_id":"FEAT-X","title":"valid title","spec_mode":"S1","risk_tier":"R1","status":"approved","base_ref":"abc","acceptance_criteria":[{"id":"AC-001","statement":"works","evidence":["test"]}],"contracts":[],"quality":{"security":[],"reliability":[],"observability":[]},"rollout":{"strategy":"flag","rollback":"disable"}}
    def tasks(self):return {"schema_version":1,"feature_id":"FEAT-X","tasks":[{"id":"T-001","title":"task","role":"implementer","depends_on":[],"write_scope":["src/**"],"acceptance":["AC-001"],"commands":[],"budget":{"max_attempts":2,"max_files":5,"max_lines":100,"max_seconds":60}}]}
    def test_chain_and_immutable_registration(self):
        with tempfile.TemporaryDirectory() as td:
            l=Ledger(Path(td)/"ledger.db");l.register(self.feature(),self.tasks(),"a"*40);run=l.start_run("FEAT-X","T-001","owner")
            l.transition("FEAT-X","T-001","implementing",run);self.assertTrue(l.verify_chain(run))
            with l.connect() as c:c.execute("UPDATE events SET payload_json='{}' WHERE run_id=? AND sequence=1",(run,))
            self.assertFalse(l.verify_chain(run))

    def test_register_refuses_unapproved_contract(self):
        with tempfile.TemporaryDirectory() as td:
            l=Ledger(Path(td)/"ledger.db")
            draft=self.feature();draft["status"]="draft"
            with self.assertRaisesRegex(ValueError,"approved"):l.register(draft,self.tasks(),"a"*40)
            unowned=self.feature();unowned["owner"]="REPLACE_WITH_OWNER"
            with self.assertRaisesRegex(ValueError,"REPLACE_WITH_OWNER"):l.register(unowned,self.tasks(),"a"*40)

if __name__ == "__main__":unittest.main()

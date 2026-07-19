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

    def two_task_docs(self):
        tasks=self.tasks()
        second=dict(tasks["tasks"][0]);second=dict(second,id="T-002",depends_on=["T-001"])
        tasks["tasks"]=[tasks["tasks"][0],second]
        return tasks

    def walk(self,l,task_id,payload=None):
        run=l.start_run("FEAT-X",task_id,"owner")
        for state in ("implementing","scope_passed","candidate_committed","author_verifying","auditing","reviewing"):
            l.transition("FEAT-X",task_id,state,run)
        l.set_candidate("FEAT-X",task_id,"c"*39+task_id[-1],run)
        l.transition("FEAT-X",task_id,"author_ready",run,payload or {})
        return run

    def test_lease_is_atomic_compare_and_set(self):
        with tempfile.TemporaryDirectory() as td:
            l=Ledger(Path(td)/"ledger.db");l.register(self.feature(),self.tasks(),"a"*40)
            l.start_run("FEAT-X","T-001","owner-1")
            with self.assertRaisesRegex(ValueError,"cannot be leased"):
                l.start_run("FEAT-X","T-001","owner-2")

    def test_stale_stack_detection_and_requeue(self):
        with tempfile.TemporaryDirectory() as td:
            l=Ledger(Path(td)/"ledger.db");l.register(self.feature(),self.two_task_docs(),"a"*40)
            self.walk(l,"T-001")
            t1_candidate=l.task("FEAT-X","T-001")["candidate_sha"]
            self.walk(l,"T-002",{"integrated":[f"T-001:{t1_candidate}"],"start_sha":t1_candidate})
            self.assertEqual(l.stale_stacks("FEAT-X"),[])
            l.requeue("FEAT-X","T-001","withdrawn by human")
            self.assertIsNone(l.task("FEAT-X","T-001")["candidate_sha"])
            stale=l.stale_stacks("FEAT-X")
            self.assertEqual(len(stale),1)
            self.assertEqual(stale[0]["task_id"],"T-002")
            self.assertEqual(stale[0]["dependency"],"T-001")
            l.requeue("FEAT-X","T-002","stale stack")
            self.assertEqual(l.stale_stacks("FEAT-X"),[])

    def test_requeue_requires_reason_and_prior_run(self):
        with tempfile.TemporaryDirectory() as td:
            l=Ledger(Path(td)/"ledger.db");l.register(self.feature(),self.tasks(),"a"*40)
            with self.assertRaisesRegex(ValueError,"reason"):l.requeue("FEAT-X","T-001","  ")
            with self.assertRaisesRegex(ValueError,"No prior run"):l.requeue("FEAT-X","T-001","stale")

    def test_force_reclaims_orphaned_in_flight_task(self):
        with tempfile.TemporaryDirectory() as td:
            l=Ledger(Path(td)/"ledger.db");l.register(self.feature(),self.tasks(),"a"*40)
            run=l.start_run("FEAT-X","T-001","owner")
            l.transition("FEAT-X","T-001","implementing",run)  # process now "dies" here
            # Without force, implementing -> pending is not a legal transition.
            with self.assertRaises(ValueError):l.requeue("FEAT-X","T-001","stuck")
            l.requeue("FEAT-X","T-001","orphaned by crash",force=True)
            self.assertEqual(l.task("FEAT-X","T-001")["status"],"pending")
            self.assertTrue(l.verify_chain(run))  # forced reset is journaled, chain intact

    def test_requeue_resets_attempts_so_task_can_rerun(self):
        with tempfile.TemporaryDirectory() as td:
            tasks=self.tasks();tasks["tasks"][0]["budget"]["max_attempts"]=1
            l=Ledger(Path(td)/"ledger.db");l.register(self.feature(),tasks,"a"*40)
            self.walk(l,"T-001")  # reaches author_ready at attempts=1 (the cap)
            self.assertEqual(l.task("FEAT-X","T-001")["attempts"],1)
            l.requeue("FEAT-X","T-001","withdrawn")
            task=l.task("FEAT-X","T-001")
            self.assertEqual(task["status"],"pending")
            self.assertEqual(task["attempts"],0)  # fresh authorization — not stranded at the cap

    def test_force_recovers_safe_stopped(self):
        with tempfile.TemporaryDirectory() as td:
            l=Ledger(Path(td)/"ledger.db");l.register(self.feature(),self.tasks(),"a"*40)
            run=l.start_run("FEAT-X","T-001","owner")
            l.transition("FEAT-X","T-001","safe_stopped",run)
            with self.assertRaises(ValueError):l.requeue("FEAT-X","T-001","resume")  # not without force
            l.requeue("FEAT-X","T-001","human resumed after review",force=True)
            self.assertEqual(l.task("FEAT-X","T-001")["status"],"pending")

if __name__ == "__main__":unittest.main()

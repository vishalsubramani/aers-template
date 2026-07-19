import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
from aers.audit import audit_text_for_eval
class AuditTests(unittest.TestCase):
    def test_tampering_needs_review(self):self.assertEqual(audit_text_for_eval("def pytest_collection_modifyitems(items): items.clear()"),"needs_review")
    def test_secret_fails(self):self.assertEqual(audit_text_for_eval("x='ghp_abcdefghijklmnopqrstuvwxyz123456'"),"fail")
    def test_normal_passes(self):self.assertEqual(audit_text_for_eval("def add(a,b): return a+b"),"pass")
if __name__ == "__main__":unittest.main()

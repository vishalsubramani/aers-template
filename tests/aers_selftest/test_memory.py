import os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
from aers.memory import propose,promote
from aers.util import atomic_write_json
class MemoryTests(unittest.TestCase):
    def test_promotion_requires_curator_and_two_runs(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);(repo/".agents/memory/quarantine").mkdir(parents=True);(repo/".agents/memory/active").mkdir(parents=True);atomic_write_json(repo/".agents/memory/index.json",{"schema_version":1,"active_records":[]})
            p=propose(repo,"Use idempotent writes",["src/**"],["RUN-1"],"2099-01-01T00:00:00Z")
            os.environ.pop("AERS_CURATOR_ID",None)
            with self.assertRaises(ValueError):promote(repo,p,["RUN-1","RUN-2"])
            os.environ["AERS_CURATOR_ID"]="curator-test"
            with self.assertRaises(ValueError):promote(repo,p,["RUN-1"])
            active=promote(repo,p,["RUN-1","RUN-2"]);self.assertTrue(active.exists())
            os.environ.pop("AERS_CURATOR_ID",None)
if __name__ == "__main__":unittest.main()

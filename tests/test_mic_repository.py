import unittest
from mic.repository import MicRepository,READ_FACTUAL_SQL,INSERT_RUN_SQL,INSERT_OBSERVATION_SQL

class Fake:
    def __init__(self): self.calls=[]
    def query(self,*x): self.calls.append(x);return []
    def execute(self,*x): self.calls.append(x)

class RepositoryTests(unittest.TestCase):
    def test_read_contract_only_evt007_results(self): self.assertIn("FROM gsb.evt007_results",READ_FACTUAL_SQL)
    def test_t18_no_legacy_writes(self):
        sql=(INSERT_RUN_SQL+INSERT_OBSERVATION_SQL).lower()
        for table in ("evt007_results","evt007_collection_runs","evt007_raw_pages","evt007_item_identity","evt007_item_identity_observations"):
            self.assertNotIn("insert into gsb."+table,sql)
    def test_distinct_read_write_sides(self):
        r,w=Fake(),Fake();repo=MicRepository(r,w);repo.read_factual();repo.insert_run({});repo.insert_observation({})
        self.assertEqual((len(r.calls),len(w.calls)),(1,2))

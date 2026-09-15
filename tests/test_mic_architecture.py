import ast,re,socket,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
class ArchitectureTests(unittest.TestCase):
    def test_t17_no_frozen_imports(self):
        for path in (ROOT/"mic").glob("*.py"):
            tree=ast.parse(path.read_text())
            imports=[]
            for n in ast.walk(tree):
                if isinstance(n,ast.Import): imports += [x.name for x in n.names]
                elif isinstance(n,ast.ImportFrom): imports.append(n.module or "")
            self.assertFalse(any(x.split('.')[0] in {"coletor","motor","monitor"} for x in imports))
    def test_t19_migration_allowlist(self):
        sql=next((ROOT/"supabase/migrations").glob("*mic*.sql")).read_text().lower()
        tables=re.findall(r"create\s+table\s+([\w.]+)",sql)
        self.assertEqual(tables,["gsb.mic_runs","gsb.mic_identity_observations"])
        for banned in (" drop "," truncate "," delete ","create view","create function","create trigger"):
            self.assertNotIn(banned," "+sql)
        self.assertNotRegex(sql,r"alter\s+table\s+gsb\.evt007_")
    def test_t20_no_real_network(self):
        source="".join(p.read_text() for p in (ROOT/"mic").glob("*.py"))
        for name in ("urllib","httpx","requests","socket"):
            self.assertNotRegex(source,rf"(^|\n)\s*(from|import)\s+{name}\b")
    def test_t21_no_real_database(self):
        source="".join(p.read_text() for p in (ROOT/"mic").glob("*.py"))
        for name in ("psycopg","supabase","DATABASE_URL"):
            self.assertNotIn(name,source)

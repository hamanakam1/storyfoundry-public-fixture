import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from generate import build, csv_value, write_dataset
from import_preview import prepare
from validate import validate_directory, validate_tables

class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.config={'company_name':'Fixture Studio','company_expansion':'Fictional test company','scenario':'SYNTHETIC service company','anchor_date':'2026-10-28','history_start':'2024-10-29','seed':42,'customers':5,'leads':25,'talent':20,'staff':10,'future_meetings':4,'currency':'USD','synthetic':True}
        self.shapes={'shapes':[{'title':'Fictional reviewer','skills':['review','writing'],'count':10},{'title':'Fictional analyst','skills':['analysis'],'count':10}]}
        self.tables,self.meta=build(self.config,self.shapes)
    def errors(self):return validate_tables(self.tables,self.config)
    def test_consistent_history_and_paid_customer_chain(self):self.assertEqual(self.errors(),[])
    def test_replay_is_byte_identical(self):
        other,meta=build(self.config,self.shapes);self.assertEqual((other,meta),(self.tables,self.meta))
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';b=Path(d)/'b';write_dataset(self.tables,self.meta,a);write_dataset(other,meta,b)
            self.assertEqual((a/'manifest.json').read_bytes(),(b/'manifest.json').read_bytes())
    def test_distinct_seed_has_distinct_external_id_namespace(self):
        cfg={**self.config,'seed':43};tables,_=build(cfg,self.shapes)
        self.assertFalse({r['id'] for r in tables['leads']} & {r['id'] for r in self.tables['leads']})
    def test_dangling_owner_rejected(self):
        self.tables['leads'][0]['owner_id']='unknown';self.assertTrue(any('dangling' in x for x in self.errors()))
    def test_invoice_imbalance_rejected(self):
        self.tables['invoices'][0]['balance_cents']+=1;self.assertIn('invoice balance mismatch',self.errors())
    def test_future_posted_payment_rejected(self):
        self.tables['payments'][0]['paid_on']='2027-01-01';self.assertTrue(any('outside history' in x for x in self.errors()))
    def test_future_generic_timestamp_rejected(self):
        self.tables['tasks'][0]['completed_at']='2027-01-01T12:00:00Z';self.assertTrue(any('outside history' in x for x in self.errors()))
    def test_real_contact_endpoint_rejected(self):
        self.tables['contacts'][0]['email']='person@real-domain.com';self.assertTrue(any('non-reserved' in x for x in self.errors()))
    def test_embedded_invalid_domain_and_real_phone_rejected(self):
        self.tables['accounts'][0]['website']='https://real-domain.com/path/example.invalid'
        self.tables['accounts'][0]['phone']='+1-212-555-0100'
        self.assertEqual(sum('non-reserved contact endpoint' in e for e in self.errors()),2)
    def test_missing_synthetic_marker_rejected(self):
        self.tables['tasks'][0]['synthetic']=False;self.assertTrue(any('missing synthetic' in x for x in self.errors()))
    def test_cycle_rejected(self):
        row=copy.deepcopy(self.tables['task_dependencies'][0]);row['id']='new-cycle';row['task_id'],row['depends_on_task_id']=row['depends_on_task_id'],row['task_id'];self.tables['task_dependencies'].append(row)
        self.assertIn('task dependency cycle',self.errors())
    def test_meeting_contact_must_match_account(self):
        self.tables['meetings'][0]['contact_id']=self.tables['contacts'][-1]['id'];self.assertIn('meeting contact belongs to different account',self.errors())
    def test_paying_customer_requires_payment(self):
        cid=self.tables['customers'][0]['id'];self.tables['payments']=[r for r in self.tables['payments'] if r['customer_id']!=cid]
        self.assertIn('customer without a posted synthetic payment',self.errors())
    def test_shape_population_exact(self):
        with self.assertRaises(ValueError):build({**self.config,'talent':21},self.shapes)
    def test_unique_fictional_people_and_normalized_skills(self):
        names=[r['display_name'] for r in self.tables['talent']];self.assertEqual(len(set(names)),20)
        self.assertEqual(len(self.tables['talent_skills']),30)
    def test_nonempty_unowned_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'human.txt').write_text('preserve')
            with self.assertRaises(ValueError):write_dataset(self.tables,self.meta,Path(d))
            self.assertEqual((Path(d)/'human.txt').read_text(),'preserve')
    def test_csv_formula_injection_escaped(self):
        for value in ['=HYPERLINK("https://example.invalid")','+1-202-555-0100','-danger','@cmd']:
            self.assertTrue(csv_value(value).startswith("'"))
    def test_missing_identifier_is_structured_failure(self):
        del self.tables['leads'][0]['id'];self.assertTrue(any('missing stable ID' in x for x in self.errors()))
    def test_directory_validation_reports_missing_csv_and_json(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=root/'data';profiles=root/'profiles.json'
            profiles.write_text(json.dumps(self.shapes));write_dataset(self.tables,self.meta,data)
            self.assertEqual(validate_directory(data,profiles)['errors'],[])
            (data/'csv'/'leads.csv').unlink()
            (data/'json'/'tasks.jsonl').unlink()
            errors=validate_directory(data,profiles)['errors']
            self.assertTrue(any('missing CSV: leads' in e for e in errors))
            self.assertTrue(any('JSON domains mismatch' in e for e in errors))
            self.assertTrue(any('manifest inventory mismatch' in e for e in errors))
    def test_directory_validation_rejects_unlisted_file_and_manifest_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=root/'data';profiles=root/'profiles.json'
            profiles.write_text(json.dumps(self.shapes));write_dataset(self.tables,self.meta,data)
            (data/'extra.txt').write_text('unexpected')
            self.assertTrue(any('manifest inventory mismatch' in e for e in validate_directory(data,profiles)['errors']))
            manifest=json.loads((data/'manifest.json').read_text())
            manifest['files'][0]['path']='../outside.txt'
            (data/'manifest.json').write_text(json.dumps(manifest))
            self.assertTrue(any('invalid or duplicate manifest path' in e for e in validate_directory(data,profiles)['errors']))
    def test_import_preview_preserves_unowned_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);output=root/'output';output.mkdir()
            (output/'human.txt').write_text('preserve')
            with self.assertRaisesRegex(ValueError,'unowned preview'):
                prepare(Path(__file__).parent/'data',output)
            self.assertEqual((output/'human.txt').read_text(),'preserve')
if __name__=='__main__':unittest.main()

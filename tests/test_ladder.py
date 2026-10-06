import tempfile
import unittest
from pathlib import Path
from ladder.core import *

class LadderTests(unittest.TestCase):
    def test_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            rows = [{'scene_id':f's{i%3}', 'episode_id':str(i//3),'instruction':{'text':str(i)}} for i in range(30)]
            for name, episodes in [('source',rows),('p1',rows[:3]),('p2',rows[:9])]:
                write(p/(name+'.json.gz'),{'episodes':episodes,'instruction_vocab':{'words':['test']}})
            kwargs = dict(source_path=p/'source.json.gz', parent100=p/'p1.json.gz',parent500=p/'p2.json.gz',expected_sha=sha(p/'source.json.gz'),counts=(3,9,15),check_parent_hash=False)
            generate(out=p/'a',**kwargs)
            generate(out=p/'b',**kwargs)
            plan = read(p/'a/generation_plan.json')
            self.assertEqual(plan['source_dataset'], 'source.json.gz')
            self.assertEqual([x['path'] for x in plan['parent_datasets']], ['p1.json.gz', 'p2.json.gz'])
            self.assertNotIn(str(p), plan['source_dataset'])
            with self.assertRaises(ValueError): generate(out=p/'leak', source_label=str(p/'source.json.gz'), **kwargs)
            self.assertEqual(sha(p/'a/random15_v1.json.gz'),sha(p/'b/random15_v1.json.gz'))
            a,b,c = [set(index(read(p/f'a/random{n}_v1.json.gz')['episodes'])) for n in (3,9,15)]
            self.assertTrue(a < b < c)
            self.assertEqual(len(c),15)
            kwargs['expected_sha']='invalid'
            with self.assertRaises(ValueError): generate(out=p/'c',**kwargs)

    def test_duplicate_and_content(self):
        row={'scene_id':'a','episode_id':'1'}
        with self.assertRaises(ValueError): index([row,row])
        self.assertEqual(len(index([row,{**row,'scene_id':'b'}])),2)
        with self.assertRaises(ValueError): validate_subset(index([row]),[{**row,'instruction':'changed'}])

    def test_pairing_and_report(self):
        rows=[{'scene_id':'a','episode_id':str(i),'sr':i,'spl':i,'os':i,'ne':1,'steps':2} for i in (0,1)]
        candidate=[{**r,'sr':1-r['sr']} for r in rows]
        m={f:'locked' for f in LOCK_FIELDS}
        left,right=pairing(rows,candidate,rows,m,m)
        result=report({'all':set(left)},left,right)['all']
        self.assertEqual((result['gain'],result['loss'],result['net_gain']),(1,1,0))
        with self.assertRaises(ValueError): pairing(rows,candidate,rows,m,{**m,'model':'other'})

    def test_cache_rejects_incomplete(self):
        with self.assertRaises(ValueError): cache_audit([{'request':{}}])

if __name__ == '__main__': unittest.main()

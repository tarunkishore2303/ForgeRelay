import importlib.util
import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'skills'/'local-ollama-delegate'/'scripts'
sys.path.insert(0,str(SCRIPTS))
import delegate as runner
import economics

class RunnerTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'test-data'; parent.mkdir(exist_ok=True)
        self.folder=parent/('test-'+uuid4().hex); self.folder.mkdir()
        self.project=self.folder/'project'; self.project.mkdir()
        for name in ['app','tests']:
            (self.project/name).mkdir(); (self.project/name/'__init__.py').write_text('')
        (self.project/'app'/'source.py').write_text('def existing():\n    return 1\n')
        (self.project/'tests'/'test_feature.py').write_text('import unittest\nfrom app.value import answer\nclass Feature(unittest.TestCase):\n    def test_answer(self): self.assertEqual(answer(),42)\n')
        self.task={'id':'small-helper','kind':'helper','scope':'unit','goal':'Implement answer() returning 42',
                   'target':'app/value.py','context':[{'path':'app/source.py'}],'snapshot_paths':['app','tests'],
                   'constraints':['One helper only'],'acceptance':['Returns 42','Takes no arguments'],
                   'baseline_commands':[['python','-B','-c','from app.source import existing; assert existing()==1']],
                   'test_commands':[['python','-B','-m','unittest','discover','-s','tests','-v']]}
        self.task_path=self.folder/'task.json'; runner.write_json(self.task_path,self.task)
        self.settings=runner.config(); self.answers=['def answer():\n    return 42\n']; self.requests=[]

    def tearDown(self):
        target=self.folder.resolve(); parent=(ROOT/'test-data').resolve()
        if target.parent!=parent or not target.name.startswith('test-'):raise RuntimeError('Refusing unsafe test cleanup')
        shutil.rmtree(target)

    def fake_call(self,settings,path,payload=None):
        if path=='/api/tags':return {'models':[{'name':settings['model'],'digest':'test-digest','details':{'context_length':32768}}]}
        if path=='/api/ps':return {'models':[{'name':settings['model'],'context_length':settings['num_ctx']}]}
        self.requests.append(payload)
        return {'response':self.answers.pop(0),'done':True,'done_reason':'stop','prompt_eval_count':100,'eval_count':10}

    def start(self):
        with patch.object(runner,'call',side_effect=self.fake_call):
            result=runner.start_run(self.task_path,self.project,self.settings)
        return Path(result['run']),result

    def test_successful_review_verify_apply_and_backup(self):
        target=self.project/'app'/'value.py'; target.write_text('def answer():\n    return 12\n')
        folder,result=self.start()
        self.assertEqual(result['status'],'ready_for_review'); self.assertIn('12',target.read_text())
        self.assertEqual(runner.verify(folder)['status'],'verified')
        runner.finish(folder,'accepted','Independent feature assertion passed')
        runner.apply(folder)
        self.assertIn('42',target.read_text()); self.assertIn('12',(folder/'target-before-apply.py').read_text())
        self.assertIsNone(runner.report(self.project)['net_primary_usage_saved'])

    def test_baseline_failure_sends_no_generation_request(self):
        self.task['baseline_commands']=[['python','-c','raise SystemExit(1)']]
        runner.write_json(self.task_path,self.task)
        folder,result=self.start()
        self.assertEqual(result['status'],'blocked_before_generation')
        self.assertEqual(self.requests,[]); self.assertFalse((folder/'response.json').exists())

    def test_path_and_symlink_scope(self):
        for name in ['../escape.py','C:/escape.py','app/../../escape.py','.git/config','.local-delegation/meta.json']:
            with self.subTest(name=name),self.assertRaises(ValueError):runner.contained(self.project,name)
        # A mocked resolution checks the symlink invariant without Windows link privileges.
        with patch.object(Path,'resolve',side_effect=[self.folder/'outside.py',self.project]):
            with self.assertRaises(ValueError):runner.contained(self.project,'app/link.py')

    def test_stale_project_refuses_apply(self):
        folder,result=self.start(); runner.verify(folder); runner.finish(folder,'accepted','Checked')
        (self.project/'app'/'source.py').write_text('def existing():\n    return 2\n')
        with self.assertRaisesRegex(ValueError,'Baseline changed'):runner.apply(folder)
        self.assertFalse((self.project/'app'/'value.py').exists())

    def test_post_verification_edit_requires_reverification(self):
        folder,result=self.start(); runner.verify(folder)
        (folder/'candidate'/'app'/'value.py').write_text('def answer():\n    return 0\n')
        with self.assertRaises(ValueError):runner.finish(folder,'accepted','Checked')

    def test_master_changes_are_recorded_honestly(self):
        self.answers=['def answer():\n    return 0\n']
        folder,result=self.start(); self.assertEqual(runner.verify(folder)['status'],'needs_repair')
        (folder/'candidate'/'app'/'value.py').write_text('def answer():\n    return 42\n')
        self.assertEqual(runner.verify(folder)['status'],'verified')
        with self.assertRaises(ValueError):runner.finish(folder,'accepted','Checked')
        runner.finish(folder,'accepted_with_changes','Master corrected return value')
        self.assertEqual(runner.report(self.project)['outcomes']['accepted_with_changes'],1)

    def test_one_repair_then_fallback(self):
        self.answers=['def answer():\n    return 0\n','def answer():\n    return 1\n']
        folder,result=self.start(); runner.verify(folder)
        feedback=self.folder/'errors.txt'; feedback.write_text('Expected 42, got 0.')
        with patch.object(runner,'call',side_effect=self.fake_call):repair=runner.repair(folder,feedback)
        second=Path(repair['run']); self.assertNotEqual(folder,second)
        runner.verify(second)
        with self.assertRaisesRegex(ValueError,'budget exhausted'):runner.repair(second,feedback)
        runner.finish(second,'rejected','Primary agent will implement')
        self.assertEqual(runner.report(self.project)['attempts'],2)

    def test_snapshot_side_effect_blocks_acceptance(self):
        folder,result=self.start(); runner.verify(folder)
        (folder/'candidate'/'app'/'source.py').write_text('def existing():\n    return 999\n')
        self.assertEqual(runner.verify(folder)['status'],'needs_repair')
        with self.assertRaises(ValueError):runner.finish(folder,'accepted','Should not pass')

    def test_truncated_or_invalid_response_cannot_stage(self):
        with self.assertRaises(ValueError):runner.normalize_answer('def answer():\n return 42',self.settings,'length')
        with self.assertRaises(SyntaxError):runner.normalize_answer('Here is the answer',self.settings,'stop')
        self.assertEqual(runner.normalize_answer('```python\ndef answer():\n    return 42\n```',self.settings,'stop'),'def answer():\n    return 42\n')

    def test_frozen_source_survives_project_change(self):
        folder,result=self.start()
        (self.project/'app'/'source.py').write_text('def existing():\n    return 999\n')
        prompt,count=runner.build_prompt(self.task,folder/'snapshot')
        self.assertIn('return 1',prompt); self.assertNotIn('return 999',prompt)

class EconomicsTests(unittest.TestCase):
    def scenario(self,**changes):
        return dict(delegatable_share=.2,success_rate=.8,overhead_ratio=.3,baseline_usage_units=100,**changes)

    def test_conditional_savings_and_fixed_fee(self):
        result=economics.estimate(self.scenario())
        self.assertEqual(result['expected_usage_reduction_percent'],10)
        self.assertEqual(result['fixed_subscription_fee_reduction'],0)

    def test_failures_increase_primary_usage(self):
        scenario=self.scenario(); scenario['success_rate']=0
        result=economics.estimate(scenario)
        self.assertEqual(result['expected_hybrid_primary_usage_units'],106)

    def test_rejects_invalid_measurements_and_rates(self):
        for p in [-1,1.1,float('nan')]:
            scenario=self.scenario(); scenario['success_rate']=p
            with self.assertRaises(ValueError):economics.estimate(scenario)
        with self.assertRaises(ValueError):economics.compare({'both_builds_passed':False})

    def test_electricity_units(self):
        self.assertAlmostEqual(economics.energy_cost(100,600,8),.1333333333)

    def test_entered_measurement_keeps_cash_and_usage_separate(self):
        data={'same_task_and_acceptance':True,'both_builds_passed':True,'comparable_usage_conditions':True,
              'primary_only_usage_units':100,'hybrid_primary_usage_units':90,'usage_unit':'dashboard points',
              'primary_only_wall_minutes':10,'hybrid_wall_minutes':12,'currency':'INR'}
        result=economics.compare(data)
        self.assertEqual(result['primary_usage_reduction_percent'],10)
        self.assertEqual(result['cash_difference_after_estimated_electricity'],0)
        self.assertEqual(result['wall_minutes_difference'],-2)

if __name__=='__main__':unittest.main()

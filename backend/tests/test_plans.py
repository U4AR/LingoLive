import copy,json,unittest
from dataclasses import replace
from unittest.mock import patch
import httpx
from backend.app import TeachRequest,GoogleProvider,validate_lesson
from backend.fast_lessons import merge
from test_app import INPUT,EXAMPLE,CONFIG
from test_parallel import responses

PLAN={'intent':'Reach the railway station by cab, maybe stop for tea first.','steps':[{'label':'Get a cab','optional':False,'state':'pending'},{'label':'Tea stop','optional':True,'state':'pending'},{'label':'Railway station','optional':False,'state':'pending'}],'current_step':0}
class PlanValidationTests(unittest.TestCase):
 def test_plan_and_active_step_are_bounded_and_do_not_accept_coordinates(self):
  self.assertEqual(3,len(TeachRequest.model_validate({**INPUT,'task_plan':PLAN}).task_plan.steps))
  for plan in [{**PLAN,'steps':PLAN['steps']*3},{**PLAN,'current_step':4},{**PLAN,'current_step':None},{**PLAN,'latitude':12.97},{**PLAN,'intent':'x'*601}]:
   with self.assertRaises(ValueError):TeachRequest.model_validate({**INPUT,'task_plan':plan})
 def test_a_done_step_cannot_be_current_and_narrative_only_plan_is_valid(self):
  p=copy.deepcopy(PLAN);p['steps'][0]['state']='done'
  with self.assertRaises(ValueError):TeachRequest.model_validate({**INPUT,'task_plan':p})
  self.assertEqual([],TeachRequest.model_validate({**INPUT,'task_plan':{'intent':'Station after tea'}}).task_plan.steps)
 def test_known_language_expression_keeps_source_detection_honest_and_all_target_words(self):
  source,replies=responses();source.update(contains_learning_language=False,words=[],reply_mode='express')
  lesson=validate_lesson(merge(source,replies,'I need a cab.'),'I need a cab.')
  self.assertFalse(lesson['contains_learning_language']);self.assertEqual([],lesson['words']);self.assertEqual(3,len(lesson['replies']))
 def test_express_mode_rejects_partial_target_phrases_or_invented_source_words(self):
  d=copy.deepcopy(EXAMPLE['lesson']);d.update(contains_learning_language=False,reply_mode='express',words=[]);d['replies'].pop()
  with self.assertRaises(ValueError):validate_lesson(d,'English')
  d['replies']=EXAMPLE['lesson']['replies'];d['words']=EXAMPLE['lesson']['words']
  with self.assertRaises(ValueError):validate_lesson(d,'English')
 def test_explicit_say_this_can_override_no_learning_language_without_extra_calls(self):
  source,replies=responses();source.update(contains_learning_language=False,words=[])
  self.assertEqual('express',merge(source,replies,'My own words',force_express=True)['reply_mode'])

class PlannedProviderTests(unittest.IsolatedAsyncioTestCase):
 async def test_known_language_routing_does_not_depend_on_a_correct_model_mode_estimate(self):
  original=httpx.AsyncClient;source,replies=responses();source.update(detected_language='en-US',contains_learning_language=False,words=[],reply_mode='respond')
  for strategy in ('single','parallel'):
   def handler(request):
    b=json.loads(request.content)
    if strategy=='single':
     d=copy.deepcopy(EXAMPLE['lesson']);d.update(detected_language='en-US',contains_learning_language=False,words=[],reply_mode='respond')
    else:d=replies if 'replies' in b['generationConfig']['responseJsonSchema']['properties'] else source
    return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(d)}]}}]})
   def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
   model=GoogleProvider(replace(CONFIG,lesson_strategy=strategy));self.addAsyncCleanup(model.aclose)
   with patch('backend.app.httpx.AsyncClient',side_effect=client):lesson=await model.teach(TeachRequest.model_validate({**INPUT,'text':'Could we stop for tea first?'}))
   self.assertEqual('express',lesson['reply_mode']);self.assertEqual(3,len(lesson['replies']));self.assertFalse(lesson['contains_learning_language'])
 async def test_both_existing_parallel_calls_receive_plan_current_stage_and_expression_mode(self):
  original=httpx.AsyncClient;seen=[];source,replies=responses();source.update(contains_learning_language=False,words=[],reply_mode='express',suggested_plan_steps=[{'label':'Must not replace the explicit steps','optional':False}])
  def handler(request):
   body=json.loads(request.content);seen.append(body);d=replies if 'replies' in body['generationConfig']['responseJsonSchema']['properties'] else source
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(d)}]}}]})
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  model=GoogleProvider(replace(CONFIG,lesson_strategy='parallel'));self.addAsyncCleanup(model.aclose)
  with patch('backend.app.httpx.AsyncClient',side_effect=client):lesson=await model.teach(TeachRequest.model_validate({**INPUT,'text':'Please stop for tea first.','task_plan':PLAN,'assistance_mode':'say_this'}))
  self.assertEqual(2,len(seen));self.assertEqual(3,len(lesson['replies']));self.assertNotIn('suggested_plan_steps',lesson)
  for b in seen:
   d=json.loads(b['contents'][0]['parts'][0]['text']);self.assertEqual(PLAN,d['task_plan']);self.assertEqual('say_this',d['assistance_mode'])

import copy,json,unittest
from dataclasses import replace
from unittest.mock import patch
import httpx
from backend.app import TeachRequest,GoogleProvider,validate_lesson
from test_app import INPUT,EXAMPLE,CONFIG
from test_parallel import responses

MEMORY={'kind':'activity','text':'Usually takes the metro from Indiranagar','status':'possible','setting':'travelling','observations':2}
CANDIDATE={'kind':'activity','topic':'commute','text':MEMORY['text'],'evidence':EXAMPLE['text'],'setting':'travelling','duration':'routine'}

class MemoryValidationTests(unittest.TestCase):
 def test_personal_context_is_bounded_and_cannot_hold_sensor_or_secret_fields(self):
  request=TeachRequest.model_validate({**INPUT,'personal_memories':[MEMORY],'learn_personal_memory':True})
  self.assertEqual('possible',request.personal_memories[0].status)
  for value in ([MEMORY]*6,[{**MEMORY,'text':'x'*161}],[{**MEMORY,'status':'certain'}],[{**MEMORY,'latitude':12.97}],[{**MEMORY,'observations':0}]):
   with self.assertRaises(ValueError):TeachRequest.model_validate({**INPUT,'personal_memories':value})
 def test_memory_proposals_require_current_verbatim_evidence(self):
  value=copy.deepcopy(EXAMPLE['lesson']);value['memory_candidates']=[{**CANDIDATE,'evidence':'Not spoken'}]
  self.assertEqual([],validate_lesson(value,EXAMPLE['text'])['memory_candidates'])
  value['memory_candidates']=[CANDIDATE]*3
  with self.assertRaises(ValueError):validate_lesson(value,EXAMPLE['text'])
 def test_old_saved_lessons_and_requests_remain_compatible(self):
  self.assertNotIn('memory_candidates',validate_lesson(EXAMPLE['lesson'],EXAMPLE['text']))
  self.assertFalse(TeachRequest.model_validate(INPUT).learn_personal_memory)

class MemoryProviderTests(unittest.IsolatedAsyncioTestCase):
 async def run_lesson(self,learn=True,speaker='user',evidence=None):
  original=httpx.AsyncClient;received=[];source,replies=responses();source.update(current_speaker=speaker,speaker_confidence='high',memory_candidates=[{**CANDIDATE,'evidence':evidence or CANDIDATE['evidence']}])
  def handler(request):
   body=json.loads(request.content);received.append(body)
   result=replies if 'replies' in body['generationConfig']['responseJsonSchema']['properties'] else source
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(result)}]}}]})
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  model=GoogleProvider(replace(CONFIG,lesson_strategy='parallel',flash_model='gemini-3.1-flash-lite'));self.addAsyncCleanup(model.aclose)
  with patch('backend.app.httpx.AsyncClient',side_effect=client):result=await model.teach(TeachRequest.model_validate({**INPUT,'personal_memories':[MEMORY],'learn_personal_memory':learn}))
  self.assertEqual(2,len(received),'Memory must not introduce a third generation')
  for body in received:
   data=json.loads(body['contents'][0]['parts'][0]['text']);self.assertEqual([MEMORY],data['personal_memories']);self.assertIn('possible',body['systemInstruction']['parts'][0]['text'])
  return result
 async def test_existing_parallel_calls_both_receive_memory_and_source_can_propose_updates(self):
  result=await self.run_lesson();self.assertEqual([CANDIDATE],result['memory_candidates'])
 async def test_memory_disabled_does_not_return_learning_candidates(self):
  self.assertNotIn('memory_candidates',await self.run_lesson(learn=False))
 async def test_other_speakers_and_invented_evidence_do_not_become_personal_memory(self):
  self.assertEqual([], (await self.run_lesson(speaker='other'))['memory_candidates'])
  self.assertEqual([], (await self.run_lesson(evidence='Invented'))['memory_candidates'])

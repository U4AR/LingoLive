import copy,json,unittest
from dataclasses import replace
from unittest.mock import patch
import httpx
from backend.app import TeachRequest,GoogleProvider,validate_lesson
from test_app import INPUT,EXAMPLE,CONFIG
from test_parallel import responses

CONTEXT={'label':'Tea stall','fact':'Usually orders ginger tea here','status':'possible'}
CANDIDATE={'label':'Tea stall','fact':CONTEXT['fact'],'evidence':EXAMPLE['text']}

class PlaceValidationTests(unittest.TestCase):
 def test_place_context_caps_notes_and_rejects_coordinates_or_unbounded_fields(self):
  self.assertEqual(1,len(TeachRequest.model_validate({**INPUT,'place_context':[CONTEXT]}).place_context))
  for value in ([CONTEXT]*3,[{**CONTEXT,'latitude':12.97}],[{**CONTEXT,'fact':'x'*161}],[{**CONTEXT,'label':'x'*61}]):
   with self.assertRaises(ValueError):TeachRequest.model_validate({**INPUT,'place_context':value})
 def test_place_candidate_requires_bounded_verbatim_evidence(self):
  d=copy.deepcopy(EXAMPLE['lesson']);d['place_candidates']=[{**CANDIDATE,'evidence':'Not spoken here'}]
  self.assertEqual([],validate_lesson(d,EXAMPLE['text'])['place_candidates'])
  d['place_candidates']=[CANDIDATE]*2
  with self.assertRaises(ValueError):validate_lesson(d,EXAMPLE['text'])

class PlaceProviderTests(unittest.IsolatedAsyncioTestCase):
 async def run_lesson(self,enabled=True,speaker='user',confidence='high',hint='auto'):
  original=httpx.AsyncClient;seen=[];source,replies=responses();source.update(current_speaker=speaker,speaker_confidence=confidence,place_candidates=[CANDIDATE])
  def handler(request):
   body=json.loads(request.content);seen.append(body);d=replies if 'replies' in body['generationConfig']['responseJsonSchema']['properties'] else source
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(d)}]}}]})
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  provider=GoogleProvider(replace(CONFIG,lesson_strategy='parallel'));self.addAsyncCleanup(provider.aclose)
  with patch('backend.app.httpx.AsyncClient',side_effect=client):result=await provider.teach(TeachRequest.model_validate({**INPUT,'place_context':[CONTEXT],'learn_place_memory':enabled,'current_speaker_hint':hint}))
  self.assertEqual(2,len(seen));self.assertEqual(4096,sum(b['generationConfig']['maxOutputTokens'] for b in seen))
  for b in seen:self.assertEqual([CONTEXT],json.loads(b['contents'][0]['parts'][0]['text'])['place_context'])
  return result
 async def test_place_learning_uses_existing_source_call_and_both_branches_receive_returned_context(self):
  self.assertEqual([CANDIDATE],(await self.run_lesson())['place_candidates'])
 async def test_disabled_or_other_speaker_cannot_request_a_place_save(self):
  self.assertNotIn('place_candidates',await self.run_lesson(enabled=False));self.assertEqual([],(await self.run_lesson(speaker='other'))['place_candidates'])
 async def test_uncertain_estimates_require_explicit_own_words_confirmation(self):
  self.assertEqual([],(await self.run_lesson(confidence='medium'))['place_candidates']);self.assertEqual([CANDIDATE],(await self.run_lesson(confidence='medium',hint='user'))['place_candidates'])

import asyncio,copy,json,unittest
from dataclasses import replace
from unittest.mock import AsyncMock,patch
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.app import Config,GoogleProvider,TeachRequest,create_app,validate_lesson
from backend.fast_lessons import expand_words,merge
from test_app import EXAMPLE,INPUT,TOKEN,AUTH,CONFIG,FakeProvider

def responses():
 def rows(words):return [[w['text'],w['reading'],w['meaning']] for w in words if w['is_word']]
 source={k:copy.deepcopy(v) for k,v in EXAMPLE['lesson'].items() if k not in ('replies','tip')};source['words']=rows(source['words'])
 replies={'replies':[{'label':r['label'],'text':''.join(w['text'] for w in r['words']),'translation':r['translation'],'words':rows(r['words'])} for r in EXAMPLE['lesson']['replies']]}
 return source,replies

class ParallelWordsTests(unittest.TestCase):
 def test_reconstructs_exact_unicode_punctuation_spaces_and_repeated_words(self):
  text='  café, café！ ';words=expand_words([['café','','coffee'],['café','','coffee']],text)
  self.assertEqual(text,''.join(w['text'] for w in words));self.assertEqual(['café','café'],[w['reading'] for w in words if w['is_word']])
 def test_missing_changed_reordered_or_undefined_words_fail(self):
  for rows,text in [([['Hello','Hello','greeting']],'Hello world'),([['你好','','hello']],'你好'),([['changed','changed','meaning']],'original'),([['world','','world'],['Hello','','hello']],'Hello world'),([['hello','','']],'hello')]:
   with self.assertRaises(ValueError):expand_words(rows,text)
 def test_punctuation_rows_are_ignored_and_original_punctuation_is_restored(self):
  result=expand_words([['Hello','','hello'],['!','','']],'Hello!')
  self.assertEqual('Hello!',''.join(w['text'] for w in result));self.assertFalse(result[-1]['is_word'])
 def test_merge_keeps_three_fully_defined_replies_and_no_source_mutation(self):
  source,replies=responses();saved=copy.deepcopy(source);lesson=validate_lesson(merge(source,replies,EXAMPLE['text']),EXAMPLE['text'])
  self.assertEqual(source,saved);self.assertEqual(3,len(lesson['replies']));self.assertEqual('',lesson['tip'])
 def test_non_learning_phrase_is_authoritative_even_if_reply_branch_disagrees(self):
  source,replies=responses();source.update(contains_learning_language=False,words=[])
  lesson=merge(source,replies,'Hello');self.assertEqual([],lesson['words']);self.assertEqual([],lesson['replies'])
 def test_missing_reply_or_word_is_not_hidden_by_parallel_merge(self):
  source,replies=responses();replies['replies'].pop()
  with self.assertRaises(ValueError):merge(source,replies,EXAMPLE['text'])

class ParallelProviderTests(unittest.IsolatedAsyncioTestCase):
 async def test_both_branches_overlap_share_context_and_split_the_output_cap(self):
  original=httpx.AsyncClient;received=[];ready=asyncio.Event();source,replies=responses()
  async def handler(request):
   body=json.loads(request.content);received.append(body)
   if len(received)==2:ready.set()
   await asyncio.wait_for(ready.wait(),.5)
   is_reply='replies' in body['generationConfig']['responseJsonSchema']['properties']
   value=replies if is_reply else source
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(value)}]}}]})
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  config=replace(CONFIG,flash_model='gemini-3.1-flash-lite',lesson_strategy='parallel',max_output_tokens=4095)
  model=GoogleProvider(config);self.addAsyncCleanup(model.aclose)
  with patch('backend.app.httpx.AsyncClient',side_effect=client):
   lesson=await model.teach(TeachRequest.model_validate({**INPUT,'user_goal':'Order coffee','recent_turns':[{'speaker':'user','text':'I want coffee.'}]}))
  self.assertEqual(2,len(received));self.assertEqual(4095,sum(b['generationConfig']['maxOutputTokens'] for b in received))
  self.assertTrue(all(b['generationConfig']['thinkingConfig']=={'thinkingLevel':'minimal'} for b in received));self.assertEqual(3,len(lesson['replies']))
  for body in received:
   data=json.loads(body['contents'][0]['parts'][0]['text']);self.assertEqual('Order coffee',data['user_goal']);self.assertEqual('user',data['recent_turns'][0]['speaker']);self.assertIn('untrusted',body['systemInstruction']['parts'][0]['text'])
 async def test_branch_failure_cancels_sibling_without_a_third_paid_request(self):
  original=httpx.AsyncClient;seen=[];arrived=asyncio.Event();cancelled=asyncio.Event()
  async def handler(request):
   body=json.loads(request.content);seen.append(body)
   if len(seen)==2:arrived.set()
   await arrived.wait()
   if 'replies' not in body['generationConfig']['responseJsonSchema']['properties']:return httpx.Response(403,json={})
   try:await asyncio.Event().wait()
   except asyncio.CancelledError:cancelled.set();raise
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  model=GoogleProvider(replace(CONFIG,lesson_strategy='parallel'));self.addAsyncCleanup(model.aclose)
  with patch('backend.app.httpx.AsyncClient',side_effect=client):
   with self.assertRaises(HTTPException) as e:await model.teach(TeachRequest.model_validate(INPUT))
  self.assertEqual(502,e.exception.status_code);self.assertEqual(2,len(seen));self.assertTrue(cancelled.is_set())
 async def test_vertex_parallel_requests_use_only_cloud_identity(self):
  original=httpx.AsyncClient;seen=[];source,replies=responses()
  def handler(request):
   seen.append(request);body=json.loads(request.content);value=replies if 'replies' in body['generationConfig']['responseJsonSchema']['properties'] else source
   self.assertEqual('Bearer test-only-cloud-token',request.headers['authorization']);self.assertNotIn('x-goog-api-key',request.headers)
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(value)}]}}]})
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  provider=GoogleProvider(replace(CONFIG,provider='vertex',project='locateassist',lesson_strategy='parallel'))
  self.addAsyncCleanup(provider.aclose)
  with patch.object(provider,'_vertex_token',new=AsyncMock(return_value='test-only-cloud-token')),patch('backend.app.httpx.AsyncClient',side_effect=client):await provider.teach(TeachRequest.model_validate(INPUT))
  self.assertEqual(2,len(seen))

 async def test_parallel_connections_are_reused_then_closed_explicitly(self):
  original=httpx.AsyncClient;created=[];source,replies=responses()
  def handler(request):
   body=json.loads(request.content);value=replies if 'replies' in body['generationConfig']['responseJsonSchema']['properties'] else source
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(value)}]}}]})
  def client(**kwargs):
   value=original(transport=httpx.MockTransport(handler),**kwargs);created.append(value);return value
  provider=GoogleProvider(replace(CONFIG,lesson_strategy='parallel'));self.addAsyncCleanup(provider.aclose)
  with patch('backend.app.httpx.AsyncClient',side_effect=client):
   await provider.teach(TeachRequest.model_validate(INPUT));await provider.teach(TeachRequest.model_validate(INPUT))
  self.assertEqual(1,len(created));self.assertFalse(created[0].is_closed)
  await provider.aclose();self.assertTrue(created[0].is_closed)
 async def test_optional_audio_goes_only_to_source_and_stale_location_goes_to_neither(self):
  from test_signals import wav_data
  original=httpx.AsyncClient;seen=[];source,replies=responses()
  def handler(request):
   body=json.loads(request.content);seen.append(body);value=replies if 'replies' in body['generationConfig']['responseJsonSchema']['properties'] else source
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(value)}]}}]})
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  provider=GoogleProvider(replace(CONFIG,lesson_strategy='parallel'));self.addAsyncCleanup(provider.aclose)
  value=TeachRequest.model_validate({**INPUT,'audio_context':{'data':wav_data(.1)},'location_context':{'latitude':12.97,'longitude':77.59,'accuracy_m':1000.0,'captured_at':1}})
  with patch('backend.app.httpx.AsyncClient',side_effect=client):await provider.teach(value)
  self.assertEqual([1,2],sorted(len(b['contents'][0]['parts']) for b in seen))
  for b in seen:self.assertNotIn('location_context',json.loads(b['contents'][0]['parts'][0]['text']))

class ParallelGuardTests(unittest.TestCase):
 def test_two_model_calls_count_twice_against_existing_rate_and_usage_allowances(self):
  for limit in ('lessons_per_hour','requests_per_minute'):
   config=replace(CONFIG,lesson_strategy='parallel',**{limit:2});provider=FakeProvider()
   with TestClient(create_app(config,provider)) as client:
    self.assertEqual(200,client.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
    self.assertEqual(429,client.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
   self.assertEqual(1,len(provider.requests))
 def test_personal_and_host_parallel_allowances_stay_separate(self):
  provider=FakeProvider();personal=FakeProvider();config=replace(CONFIG,lesson_strategy='parallel',lessons_per_hour=2)
  with TestClient(create_app(config,provider,key_provider_factory=lambda _:personal)) as client:
   client.post('/v1/session',json={'mode':'api_key','api_key':'test-only-key-parallel-12345'},headers={'Origin':'http://testserver'})
   self.assertEqual(200,client.post('/v1/teach',json=INPUT,headers={'Origin':'http://testserver'}).status_code)
   self.assertEqual(429,client.post('/v1/teach',json=INPUT,headers={'Origin':'http://testserver'}).status_code)
   self.assertEqual(200,client.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
  self.assertEqual(1,len(provider.requests));self.assertEqual(1,len(personal.requests))

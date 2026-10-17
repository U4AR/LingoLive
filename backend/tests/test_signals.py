import base64,copy,io,json,time,unittest,wave
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from backend.app import AudioContext,GoogleProvider,TeachRequest,create_app
from test_app import AUTH,CONFIG,EXAMPLE,INPUT,FakeProvider

def wav_data(seconds=.1,channels=1,rate=16000):
 out=io.BytesIO()
 with wave.open(out,'wb') as wav:
  wav.setnchannels(channels);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(bytes(int(seconds*rate)*channels*2))
 return base64.b64encode(out.getvalue()).decode()

class SignalTests(unittest.TestCase):
 def test_audio_allows_at_most_four_seconds_of_mono_pcm_wav(self):
  AudioContext(data=wav_data(4))
  for fields in [{'data':wav_data(4.01)},{'data':wav_data(1,2)},{'data':wav_data(1,rate=8000)},{'data':base64.b64encode(bytes(100)).decode()},{'data':'!'*100},{'data':wav_data(1),'mime_type':'audio/mp3'}]:
   with self.assertRaises(ValueError):AudioContext(**fields)
 def test_audio_and_location_do_not_bypass_signin(self):
  provider=FakeProvider();c=TestClient(create_app(CONFIG,provider))
  self.assertEqual(401,c.post('/v1/teach',json={**INPUT,'audio_context':{'data':wav_data(1)}}).status_code);self.assertEqual([],provider.requests)
 def test_notes_prior_suggestions_and_seen_vocabulary_are_bounded(self):
  provider=FakeProvider();c=TestClient(create_app(CONFIG,provider))
  for values in [{'memory_notes':'x'*801},{'previous_replies':[{'text':'a','translation':'a'}]*4},{'previously_seen_words':[{'text':'a','meaning':'a'}]*13},{'setting':'definitely-in-a-specific-house'},{'location_context':{'latitude':91.0,'longitude':0.0,'accuracy_m':1000.0,'captured_at':1}}]:
   self.assertEqual(422,c.post('/v1/teach',json={**INPUT,**values},headers=AUTH).status_code)
  self.assertEqual([],provider.requests)
 def test_location_is_rounded_before_the_model_receives_it(self):
  value=TeachRequest.model_validate({**INPUT,'location_context':{'latitude':12.971598,'longitude':77.594566,'accuracy_m':1000.0,'captured_at':int(time.time())}})
  self.assertEqual(12.97,value.location_context.latitude);self.assertEqual(77.59,value.location_context.longitude)

class SignalContractTests(unittest.IsolatedAsyncioTestCase):
 async def test_audio_is_inline_media_not_base64_text_and_stale_location_is_discarded(self):
  original=httpx.AsyncClient;seen=[];audio=wav_data(1)
  def handler(request):
   body=json.loads(request.content);seen.append(body);parts=body['contents'][0]['parts'];data=json.loads(parts[0]['text'])
   self.assertNotIn('audio_context',data);self.assertNotIn('location_context',data)
   self.assertEqual('Beginner; use polite short replies.',data['memory_notes'])
   self.assertEqual({'mimeType':'audio/wav','data':audio},parts[1]['inlineData'])
   self.assertEqual(4096,body['generationConfig']['maxOutputTokens'])
   result=copy.deepcopy(EXAMPLE['lesson']);result.update(context_summary='Possibly at a cafe.',inferred_setting='cafe',context_confidence='low')
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(result)}]}}]})
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  request=TeachRequest.model_validate({**INPUT,'memory_notes':'Beginner; use polite short replies.','audio_context':{'data':audio},'location_context':{'latitude':12.97,'longitude':77.59,'accuracy_m':1000.0,'captured_at':int(time.time())-301}})
  with patch('backend.app.httpx.AsyncClient',side_effect=client):result=await GoogleProvider(CONFIG).teach(request)
  self.assertEqual('low',result['context_confidence']);self.assertEqual(1,len(seen))
 async def test_no_goal_or_sensors_still_sends_conversation_and_prior_reply_context(self):
  original=httpx.AsyncClient;seen=[]
  def handler(request):
   body=json.loads(request.content);parts=body['contents'][0]['parts'];self.assertEqual(1,len(parts));data=json.loads(parts[0]['text']);seen.append(data)
   self.assertEqual('Tea please',data['previous_replies'][0]['translation']);self.assertEqual('unattributed',data['recent_turns'][0]['speaker'])
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(EXAMPLE['lesson'])}]}}]})
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  request=TeachRequest.model_validate({**INPUT,'previous_reply_source':'Would you like a drink?','previous_replies':[{'text':'お茶をください。','translation':'Tea please'}],'recent_turns':[{'speaker':'unattributed','text':'At a cafe'}]})
  with patch('backend.app.httpx.AsyncClient',side_effect=client):await GoogleProvider(CONFIG).teach(request)
  self.assertNotIn('user_goal',seen[0])

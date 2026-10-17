import asyncio,base64,copy,json,unittest
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from backend.app import Config,create_app,validate_audio,validate_lesson,setup_message,Window,GoogleProvider,TeachRequest

ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=json.loads((ROOT/'web/example.json').read_text())
TOKEN='test-only-access-token-never-a-production-secret'
AUTH={'Authorization':'Bearer '+TOKEN}
CONFIG=Config('test-only-not-a-real-google-key',TOKEN)
INPUT={'text':EXAMPLE['text'],'known_code':'en-US','known_name':'English','learning_code':'ja-JP','learning_name':'Japanese'}

class FakeUpstream:
    def __init__(self):self.sent=[];self.queue=asyncio.Queue()
    async def send(self,text):
        value=json.loads(text);self.sent.append(value)
        if 'setup' in value:await self.queue.put(json.dumps({'setupComplete':{}}))
        else:await self.queue.put(json.dumps({'serverContent':{'inputTranscription':{'text':EXAMPLE['text']}}}))
    def __aiter__(self):return self
    async def __anext__(self):return await self.queue.get()
class FakeProvider:
    def __init__(self):self.requests=[];self.socket=None;self.invalid=False
    async def teach(self,value):
        self.requests.append(value.model_dump(exclude_defaults=True));result=copy.deepcopy(EXAMPLE['lesson'])
        if self.invalid:result['words'][0]['text']='changed'
        return result
    @asynccontextmanager
    async def live(self):self.socket=FakeUpstream();yield self.socket

class ApiTests(unittest.TestCase):
    def setUp(self):self.provider=FakeProvider();self.client=TestClient(create_app(CONFIG,self.provider))
    def test_health_and_unconfigured_service_require_real_runtime_setup(self):
        with TestClient(create_app(Config(),self.provider)) as c:
            self.assertFalse(c.get('/health').json()['configured'])
            self.assertEqual(503,c.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
    def test_authentication_precedes_any_model_call(self):
        self.assertEqual(401,self.client.post('/v1/teach',json=INPUT).status_code)
        self.assertEqual(401,self.client.post('/v1/teach',json=INPUT,headers={'Authorization':'Bearer wrong'}).status_code)
        self.assertEqual([],self.provider.requests)
    def test_valid_learning_response_keeps_full_source_and_definitions(self):
        r=self.client.post('/v1/teach',json=INPUT,headers=AUTH);self.assertEqual(200,r.status_code)
        lesson=r.json();self.assertEqual(EXAMPLE['text'],''.join(w['text'] for w in lesson['words']));self.assertEqual(3,len(lesson['replies']))
        self.assertEqual(INPUT,self.provider.requests[0])
    def test_validation_rejects_same_language_blank_and_oversized_text(self):
        for fields in [{'learning_code':'en-IN'},{'text':' '},{'text':'x'*1001}]:
            r=self.client.post('/v1/teach',json=dict(INPUT,**fields),headers=AUTH);self.assertEqual(422,r.status_code)
        self.assertEqual([],self.provider.requests)
    def test_rewritten_or_undefined_words_do_not_become_lessons(self):
        self.provider.invalid=True;self.assertEqual(502,self.client.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
        bad=copy.deepcopy(EXAMPLE['lesson']);bad['words'][0]['is_word']=False
        with self.assertRaises(ValueError):validate_lesson(bad,EXAMPLE['text'])
    def test_rate_limit_does_not_call_google_again(self):
        with TestClient(create_app(Config(CONFIG.api_key,TOKEN,requests_per_minute=1),self.provider)) as c:
            self.assertEqual(200,c.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
            r=c.post('/v1/teach',json=INPUT,headers=AUTH);self.assertEqual(429,r.status_code);self.assertEqual('15',r.headers['Retry-After'])
        self.assertEqual(1,len(self.provider.requests))
    def test_websocket_relay_requires_auth_controls_model_and_forwards_pcm_and_final(self):
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect('/v1/listen'):pass
        with self.client.websocket_connect('/v1/listen',headers=AUTH) as ws:
            ws.send_json({'setup':{'model':'models/untrusted-other-model'}})
            self.assertIn('setupComplete',ws.receive_json())
            frame={'realtimeInput':{'audio':{'mimeType':'audio/pcm;rate=16000','data':base64.b64encode(bytes(3200)).decode()}}}
            ws.send_json(frame)
            self.assertEqual(EXAMPLE['text'],ws.receive_json()['serverContent']['inputTranscription']['text'])
            self.assertEqual(setup_message(CONFIG.transcribe_model),self.provider.socket.sent[0]);self.assertEqual(frame,self.provider.socket.sent[1])
    def test_only_bounded_even_sized_pcm_or_stream_end_is_allowed(self):
        validate_audio({'realtimeInput':{'audioStreamEnd':True}})
        for value in [{'clientContent':{}},{'realtimeInput':{'audio':{'data':'invalid%','mimeType':'audio/pcm;rate=16000'}}},{'realtimeInput':{'audio':{'data':base64.b64encode(bytes(6402)).decode(),'mimeType':'audio/pcm;rate=16000'}}}]:
            with self.assertRaises(ValueError):validate_audio(value)
    def test_window_reopens_after_rolling_minute(self):
        with patch('backend.app.time.monotonic',side_effect=[0,1,61]):
            w=Window(1);self.assertTrue(w.allow());self.assertFalse(w.allow());self.assertTrue(w.allow())

class GoogleContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_google_flash_request_contract_and_validated_response(self):
        original=httpx.AsyncClient;received=[]
        def handler(request):
            received.append(request);payload=json.loads(request.content)
            self.assertEqual('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent',str(request.url))
            self.assertEqual(CONFIG.api_key,request.headers['x-goog-api-key'])
            self.assertEqual(INPUT,json.loads(payload['contents'][0]['parts'][0]['text']))
            self.assertEqual('application/json',payload['generationConfig']['responseMimeType'])
            self.assertEqual(4096,payload['generationConfig']['maxOutputTokens'])
            self.assertIn('words',payload['generationConfig']['responseJsonSchema']['properties'])
            return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'thought':True,'text':'ignore this thought'},{'text':json.dumps(EXAMPLE['lesson'])}]}}]})
        def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
        with patch('backend.app.httpx.AsyncClient',side_effect=client):
            result=await GoogleProvider(CONFIG).teach(TeachRequest.model_validate(INPUT))
        self.assertEqual(EXAMPLE['lesson'],result);self.assertEqual(1,len(received))
    async def test_upstream_errors_do_not_expose_keys_and_truncated_lessons_fail(self):
        original=httpx.AsyncClient
        for code,payload in [(403,{'error':{'message':CONFIG.api_key}}),(200,{'candidates':[{'finishReason':'MAX_TOKENS'}]}),(402,{'error':{'message':CONFIG.api_key}})]:
            def handler(request):return httpx.Response(code,json=payload)
            def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
            with patch('backend.app.httpx.AsyncClient',side_effect=client):
                with self.assertRaises(HTTPException) as failure:await GoogleProvider(CONFIG).teach(TeachRequest.model_validate(INPUT))
            self.assertEqual(503 if code==402 else 502,failure.exception.status_code);self.assertNotIn(CONFIG.api_key,str(failure.exception.detail))
            if code==402:self.assertIn('billing',failure.exception.detail)

if __name__=='__main__':unittest.main()

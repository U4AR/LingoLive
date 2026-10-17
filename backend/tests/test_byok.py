"""Personal-key billing isolation, credential lifetime, auth and real provider transport."""
import base64,json,time,unittest
from dataclasses import replace
from unittest.mock import patch
from contextlib import asynccontextmanager
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from backend.app import Config,COOKIE,SESSION_SECONDS,GoogleProvider,TeachRequest,create_app
from test_app import CONFIG,TOKEN,INPUT,EXAMPLE,FakeProvider
ORIGIN={'Origin':'http://testserver'}
KEY1='test-personal-google-key-one-12345'
KEY2='test-personal-google-key-two-12345'

class PersonalKeyTests(unittest.TestCase):
    def setUp(self):self.host=FakeProvider();self.personal=[]
    def factory(self,config):
        provider=FakeProvider();provider.config=config;self.personal.append(provider);return provider
    def app(self,config=CONFIG):return create_app(config,self.host,key_provider_factory=self.factory)
    def login(self,c,key=KEY1):return c.post('/v1/session',json={'mode':'api_key','api_key':key},headers=ORIGIN)
    def test_options_offer_both_modes_and_personal_keys_without_host_billing_setup(self):
        with TestClient(self.app(Config())) as c:
            data=c.get('/v1/auth/config').json();self.assertFalse(data['access_code_available']);self.assertTrue(data['api_key_available'])
            self.assertEqual(200,self.login(c).status_code)
            self.assertEqual(200,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
            self.assertEqual([],self.host.requests)
    def test_key_routes_to_its_provider_and_cookie_and_responses_never_contain_the_key(self):
        config=replace(CONFIG,provider='vertex',project='test-project-123')
        with TestClient(self.app(config)) as c:
            response=self.login(c);self.assertEqual(200,response.status_code)
            self.assertEqual('api_key',response.json()['mode']);self.assertNotIn(KEY1,response.text+str(response.headers))
            self.assertIn('HttpOnly',response.headers['set-cookie']);self.assertIn('SameSite=strict',response.headers['set-cookie'])
            self.assertEqual('api_key',c.get('/v1/session').json()['mode'])
            self.assertEqual(200,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
            self.assertEqual(KEY1,self.personal[0].config.api_key);self.assertEqual('gemini',self.personal[0].config.provider)
            self.assertEqual('',self.personal[0].config.project);self.assertEqual('',self.personal[0].config.access_token)
            self.assertEqual(1,len(self.personal[0].requests));self.assertEqual([],self.host.requests)
    def test_keys_are_isolated_between_clients(self):
        app=self.app()
        with TestClient(app) as a,TestClient(app) as b:
            self.login(a);self.login(b,KEY2)
            self.assertEqual(200,a.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
            self.assertEqual(200,b.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
            self.assertEqual([KEY1,KEY2],[p.config.api_key for p in self.personal]);self.assertTrue(all(len(p.requests)==1 for p in self.personal))
    def test_personal_key_failure_never_uses_host_credentials(self):
        with TestClient(self.app()) as c:
            self.login(c)
            async def fail(value):raise HTTPException(502,'Google model access failed')
            self.personal[0].teach=fail
            self.assertEqual(502,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code);self.assertEqual([],self.host.requests)
    def test_origin_auth_and_credential_validation_precede_paid_calls_without_echoing_keys(self):
        with TestClient(self.app()) as c:
            body={'mode':'api_key','api_key':KEY1}
            for headers in [{},{'Origin':'https://evil.example'}]:self.assertEqual(403,c.post('/v1/session',json=body,headers=headers).status_code)
            for key in [KEY1+'?',KEY1*10,{'secret':KEY1}]:
                r=c.post('/v1/session',json={'mode':'api_key','api_key':key},headers=ORIGIN)
                self.assertEqual(422,r.status_code);self.assertNotIn(KEY1,r.text)
            self.assertEqual([],self.personal)
            self.login(c)
            self.assertEqual(403,c.post('/v1/teach',json=INPUT).status_code)
            with self.assertRaises(WebSocketDisconnect):
                with c.websocket_connect('/v1/listen',headers={'Origin':'https://evil.example'}):pass
            self.assertEqual([],self.personal[0].requests)
    def test_quotas_are_separate_from_host_and_survive_key_session_rotation(self):
        with TestClient(self.app(replace(CONFIG,lessons_per_hour=1,lessons_per_day=1))) as c:
            self.login(c);self.assertEqual(200,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
            self.login(c,KEY2);self.assertEqual(429,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
            self.assertEqual(200,c.post('/v1/session',json={'token':TOKEN},headers=ORIGIN).status_code)
            self.assertEqual(200,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
            self.assertEqual(429,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code);self.assertEqual(1,len(self.host.requests))
    def test_personal_live_audio_uses_personal_model_path_and_separate_allowance(self):
        config=replace(CONFIG,provider='vertex',project='test-project-123',audio_seconds_per_hour=600,audio_seconds_per_day=600)
        with TestClient(self.app(config)) as c:
            self.login(c)
            with c.websocket_connect('/v1/listen',headers=ORIGIN) as key_ws:
                key_ws.send_json({'setup':{}});self.assertIn('setupComplete',key_ws.receive_json())
                self.assertEqual('models/'+config.transcribe_model,self.personal[0].socket.sent[0]['setup']['model'])
                frame={'realtimeInput':{'audio':{'mimeType':'audio/pcm;rate=16000','data':base64.b64encode(bytes(3200)).decode()}}}
                key_ws.send_json(frame);self.assertIn('inputTranscription',key_ws.receive_json()['serverContent'])
                with c.websocket_connect('/v1/listen',headers={'Authorization':'Bearer '+TOKEN}) as host_ws:
                    host_ws.send_json({'setup':{}});self.assertIn('setupComplete',host_ws.receive_json())
                    self.assertIn('projects/test-project-123/',self.host.socket.sent[0]['setup']['model'])
    def test_logout_revokes_copied_cookie_and_closes_personal_live_stream(self):
        with TestClient(self.app()) as c:
            self.login(c);cookie=c.cookies.get(COOKIE)
            with c.websocket_connect('/v1/listen',headers=ORIGIN) as ws:
                ws.send_json({'setup':{}});ws.receive_json()
                self.assertEqual(204,c.delete('/v1/session',headers=ORIGIN).status_code)
                with self.assertRaises(WebSocketDisconnect):ws.receive_json()
            c.cookies.set(COOKIE,cookie,domain='testserver.local',path='/v1')
            self.assertEqual(401,c.get('/v1/session').status_code);self.assertEqual(401,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
            self.assertEqual([],self.host.requests)
    def test_expiry_tampering_restart_and_replacement_do_not_fall_back(self):
        app=self.app()
        with TestClient(app) as c:
            self.login(c);cookie=c.cookies.get(COOKIE)
            with patch('backend.app.time.time',return_value=time.time()+SESSION_SECONDS+1):self.assertEqual(401,c.get('/v1/session').status_code)
            self.assertEqual(401,c.get('/v1/session').status_code)
            self.login(c);old=c.cookies.get(COOKIE);self.login(c,KEY2)
            c.cookies.set(COOKIE,old,domain='testserver.local',path='/v1');self.assertEqual(401,c.get('/v1/session').status_code)
            c.cookies.set(COOKIE,cookie[:-1]+'x',domain='testserver.local',path='/v1');self.assertEqual(401,c.get('/v1/session').status_code)
        with TestClient(self.app()) as restarted:
            restarted.cookies.set(COOKIE,cookie,domain='testserver.local',path='/v1');self.assertEqual(401,restarted.get('/v1/session').status_code)
        self.assertEqual([],self.host.requests)
    def test_host_can_disable_keys_and_pause_all_ai(self):
        with patch.dict('os.environ',{'LINGOLIVE_BYOK_ENABLED':'false'}):self.assertFalse(Config.environment().byok_enabled)
        with TestClient(self.app(replace(CONFIG,byok_enabled=False))) as c:
            self.assertFalse(c.get('/v1/auth/config').json()['api_key_available']);self.assertEqual(403,self.login(c).status_code)
        with TestClient(self.app(replace(CONFIG,ai_enabled=False))) as c:
            self.login(c);self.assertEqual(503,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
            with self.assertRaises(WebSocketDisconnect):
                with c.websocket_connect('/v1/listen',headers=ORIGIN):pass
            self.assertEqual([],self.personal[-1].requests)
    def test_own_key_does_not_bypass_host_google_requirements(self):
        with TestClient(self.app(replace(CONFIG,google_signin_required=True))) as c:
            self.assertEqual(200,self.login(c).status_code)
            self.assertEqual(503,c.post('/v1/session',json={'token':TOKEN},headers=ORIGIN).status_code)
            self.assertEqual(200,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code);self.assertEqual([],self.host.requests)

class PersonalTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_upstreams_receive_only_personal_key_with_no_vertex_access(self):
        config=replace(CONFIG,provider='gemini',api_key=KEY1,access_token='',project='')
        provider=GoogleProvider(config);original=httpx.AsyncClient
        def handler(request):
            self.assertEqual(KEY1,request.headers['x-goog-api-key']);self.assertNotIn('authorization',request.headers)
            self.assertNotIn(KEY1,str(request.url)+request.content.decode())
            self.assertEqual('generativelanguage.googleapis.com',request.url.host)
            return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':json.dumps(EXAMPLE['lesson'])}]}}]})
        def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
        with patch('backend.app.httpx.AsyncClient',side_effect=client):await provider.teach(TeachRequest.model_validate(INPUT))
        seen=[]
        @asynccontextmanager
        async def socket(url,**kwargs):seen.append((url,kwargs));yield object()
        with patch('backend.app.connect',side_effect=socket):
            async with provider.live():pass
        self.assertIn('key='+KEY1,seen[0][0]);self.assertNotIn('additional_headers',seen[0][1]);self.assertNotIn(TOKEN,seen[0][0])

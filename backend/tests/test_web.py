import base64, time, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from backend.app import Config,create_app,COOKIE
from test_app import CONFIG,TOKEN,INPUT,FakeProvider

ORIGIN={'Origin':'http://testserver'}
class WebTests(unittest.TestCase):
    def setUp(self):self.provider=FakeProvider();self.client=TestClient(create_app(CONFIG,self.provider))
    def signin(self):return self.client.post('/v1/session',json={'token':TOKEN},headers=ORIGIN)
    def test_web_assets_and_example_work_without_google_configuration(self):
        with TestClient(create_app(Config(),self.provider)) as client:
            index=client.get('/');self.assertEqual(200,index.status_code);self.assertIn('Real conversations.',index.text)
            for name in ['style.css','app.js','core.mjs','pcm-worklet.js','microphone.js','memory.js','languages.json','example.json','icon.svg']:
                self.assertEqual(200,client.get('/assets/'+name).status_code,name)
            self.assertIn("script-src 'self'",index.headers['Content-Security-Policy'])
            self.assertIn('frame-ancestors',index.headers['Content-Security-Policy'])
            self.assertNotIn(CONFIG.api_key,index.text);self.assertNotIn(TOKEN,index.text)
            self.assertEqual(404,client.get('/assets/../backend/.env.example').status_code)
    def test_cookie_session_signin_teach_and_signout(self):
        self.assertEqual(401,self.client.get('/v1/session').status_code)
        response=self.signin();self.assertEqual(200,response.status_code)
        cookie=response.headers['set-cookie'];self.assertIn('HttpOnly',cookie);self.assertIn('SameSite=strict',cookie);self.assertNotIn(TOKEN,cookie)
        self.assertEqual(200,self.client.get('/v1/session').status_code)
        self.assertEqual(200,self.client.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
        self.assertEqual(204,self.client.delete('/v1/session',headers=ORIGIN).status_code)
        self.assertEqual(401,self.client.get('/v1/session').status_code)
    def test_bad_code_no_origin_and_cross_origin_cannot_sign_in(self):
        self.assertEqual(403,self.client.post('/v1/session',json={'token':TOKEN}).status_code)
        self.assertEqual(403,self.client.post('/v1/session',json={'token':TOKEN},headers={'Origin':'https://evil.example'}).status_code)
        self.assertEqual(401,self.client.post('/v1/session',json={'token':'wrong'},headers=ORIGIN).status_code)
    def test_cookie_writes_require_same_origin_even_with_valid_session(self):
        self.signin()
        for headers in [{},{'Origin':'https://evil.example'},{'Origin':'null'}]:
            self.assertEqual(403,self.client.post('/v1/teach',json=INPUT,headers=headers).status_code)
        self.assertEqual([],self.provider.requests)
    def test_tampered_and_expired_cookies_are_rejected(self):
        self.signin();original=self.client.cookies.get(COOKIE)
        self.client.cookies.set(COOKIE,original[:-1]+('1' if original[-1]!='1' else '2'),domain='testserver.local',path='/v1')
        self.assertEqual(401,self.client.get('/v1/session').status_code)
        self.client.cookies.set(COOKIE,original,domain='testserver.local',path='/v1')
        with patch('backend.app.time.time',return_value=time.time()+8*3600+5):
            self.assertEqual(401,self.client.get('/v1/session').status_code)
    def test_browser_websocket_accepts_only_same_origin_cookie(self):
        self.signin()
        for headers in [{},{'Origin':'https://evil.example'}]:
            with self.assertRaises(WebSocketDisconnect):
                with self.client.websocket_connect('/v1/listen',headers=headers):pass
        with self.client.websocket_connect('/v1/listen',headers=ORIGIN) as socket:
            socket.send_json({'setup':{}});self.assertIn('setupComplete',socket.receive_json())
            socket.send_json({'realtimeInput':{'audio':{'mimeType':'audio/pcm;rate=16000','data':base64.b64encode(bytes(3200)).decode()}}})
            self.assertIn('inputTranscription',socket.receive_json()['serverContent'])
    def test_cloud_host_sets_secure_cookie_and_rejects_plain_http_origin(self):
        with TestClient(create_app(CONFIG,self.provider),base_url='https://lingolive.example') as client:
            response=client.post('/v1/session',json={'token':TOKEN},headers={'Origin':'https://lingolive.example'})
            self.assertEqual(200,response.status_code);self.assertIn('Secure',response.headers['set-cookie'])
            self.assertEqual(403,client.post('/v1/teach',json=INPUT,headers={'Origin':'http://lingolive.example'}).status_code)
    def test_connection_attempts_are_bounded(self):
        for _ in range(12):self.assertEqual(401,self.client.post('/v1/session',json={'token':'wrong'},headers=ORIGIN).status_code)
        self.assertEqual(429,self.signin().status_code)

if __name__=='__main__':unittest.main()

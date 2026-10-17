"""Real RSA-signed fixture tokens exercise Google's verifier; no live Google login."""
import base64,json,time,unittest
from dataclasses import replace
from unittest.mock import patch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import crypt,jwt
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from backend.app import Config,COOKIE,GOOGLE_NONCE_COOKIE,GoogleIdentityVerifier,create_app
from test_app import AUTH,CONFIG,INPUT,TOKEN,FakeProvider

ORIGIN={'Origin':'http://testserver'}
EMAIL='ashish.t.vasant@gmail.com'
CLIENT_ID='123456789-test-only.apps.googleusercontent.com'
GOOGLE_CONFIG=replace(CONFIG,google_client_id=CLIENT_ID,google_signin_required=True,allowed_google_emails=(EMAIL,))
KEY=rsa.generate_private_key(public_exponent=65537,key_size=2048)
PRIVATE=KEY.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
PUBLIC=KEY.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
SIGNER=crypt.RSASigner.from_string(PRIVATE,key_id='fixture-key')
class Certificates:
    status=200
    data=json.dumps({'fixture-key':PUBLIC}).encode()
    def __init__(self):self.calls=0
    def __call__(self,*args,**kwargs):self.calls+=1;return self

class GoogleSignInTests(unittest.TestCase):
    def setUp(self):
        self.provider=FakeProvider();self.verifier=GoogleIdentityVerifier();self.certs=Certificates();self.verifier.transport=self.certs
        self.client=TestClient(create_app(GOOGLE_CONFIG,self.provider,self.verifier))
    def challenge(self):
        response=self.client.get('/v1/auth/config');self.assertEqual(200,response.status_code)
        return response.json()['nonce']
    def credential(self,nonce,**extra):
        now=int(time.time());claims={'iat':now,'exp':now+300,'aud':CLIENT_ID,'iss':'https://accounts.google.com','sub':'fixture-google-user','email':EMAIL,'email_verified':True,'nonce':nonce}
        claims.update(extra);return jwt.encode(SIGNER,claims).decode()
    def signin(self,credential):return self.client.post('/v1/session',json={'token':TOKEN,'google_credential':credential},headers=ORIGIN)
    def test_public_config_exposes_only_client_id_and_short_lived_nonce(self):
        response=self.client.get('/v1/auth/config');data=response.json()
        self.assertTrue(data['google_required']);self.assertEqual(CLIENT_ID,data['google_client_id'])
        self.assertNotIn(TOKEN,response.text);self.assertNotIn(EMAIL,response.text)
        self.assertIn('HttpOnly',response.headers['set-cookie']);self.assertIn('Max-Age=600',response.headers['set-cookie'])
        self.assertEqual('no-store',response.headers['Cache-Control'])
    def test_private_code_or_legacy_cookie_cannot_bypass_google_for_http_or_audio(self):
        self.assertEqual(401,self.client.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
        with self.assertRaises(WebSocketDisconnect):
            with self.client.websocket_connect('/v1/listen',headers=AUTH):pass
        old=TestClient(create_app(CONFIG,FakeProvider()));old.post('/v1/session',json={'token':TOKEN},headers=ORIGIN)
        self.client.cookies.set(COOKIE,old.cookies.get(COOKIE),domain='testserver.local',path='/v1')
        self.assertEqual(401,self.client.get('/v1/session').status_code)
        self.challenge();self.assertEqual(401,self.signin('').status_code)
        self.assertEqual([],self.provider.requests);self.assertIsNone(self.provider.socket);self.assertEqual(0,self.certs.calls)
    def test_real_signature_verified_invited_account_reaches_both_paid_routes(self):
        nonce=self.challenge();response=self.signin(self.credential(nonce));self.assertEqual(200,response.status_code)
        cookie=self.client.cookies.get(COOKIE);self.assertEqual(4,len(cookie.split('.')))
        self.assertNotIn('google_credential',response.text);self.assertNotIn(GOOGLE_NONCE_COOKIE,self.client.cookies)
        self.assertEqual(200,self.client.get('/v1/session').status_code)
        self.assertEqual(200,self.client.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
        with self.client.websocket_connect('/v1/listen',headers=ORIGIN) as ws:
            ws.send_json({'setup':{}});self.assertIn('setupComplete',ws.receive_json())
        self.assertEqual(1,self.certs.calls)
    def test_uninvited_or_unverified_google_account_cannot_get_a_session(self):
        nonce=self.challenge()
        self.assertEqual(403,self.signin(self.credential(nonce,email='uninvited@example.com')).status_code)
        self.assertEqual(401,self.signin(self.credential(nonce,email_verified=False)).status_code)
        self.assertEqual(401,self.client.get('/v1/session').status_code)
        self.assertEqual(1,self.certs.calls) # public cert response reused
    def test_expiry_wrong_audience_and_wrong_issuer_fail_real_verification(self):
        nonce=self.challenge()
        for claims in [{'exp':int(time.time())-10},{'aud':'other-app.apps.googleusercontent.com'},{'iss':'https://attacker.example'}]:
            self.assertEqual(401,self.signin(self.credential(nonce,**claims)).status_code)
        self.assertEqual(401,self.client.get('/v1/session').status_code)
    def test_tampered_signature_wrong_nonce_and_missing_challenge_fail(self):
        nonce=self.challenge();credential=self.credential(nonce);parts=credential.split('.')
        signature=bytearray(base64.urlsafe_b64decode(parts[2]+'='*(-len(parts[2])%4)));signature[0]^=1
        parts[2]=base64.urlsafe_b64encode(signature).decode().rstrip('=')
        self.assertEqual(401,self.signin('.'.join(parts)).status_code)
        self.assertEqual(401,self.signin(self.credential('wrong-nonce')).status_code)
        self.client.cookies.clear();self.assertEqual(401,self.signin(credential).status_code)
    def test_google_challenge_is_single_use_and_expires(self):
        nonce=self.challenge();challenge_cookie=self.client.cookies.get(GOOGLE_NONCE_COOKIE);credential=self.credential(nonce)
        self.assertEqual(200,self.signin(credential).status_code)
        self.client.cookies.set(GOOGLE_NONCE_COOKIE,challenge_cookie,domain='testserver.local',path='/v1')
        self.assertEqual(401,self.signin(credential).status_code)
        nonce=self.challenge()
        with patch('backend.app.time.time',return_value=time.time()+601):
            self.assertEqual(401,self.signin(self.credential(nonce)).status_code)
    def test_allowlist_removal_invalidates_existing_google_cookie(self):
        nonce=self.challenge();self.assertEqual(200,self.signin(self.credential(nonce)).status_code)
        cookie=self.client.cookies.get(COOKIE)
        other=TestClient(create_app(replace(GOOGLE_CONFIG,allowed_google_emails=('other@example.com',)),FakeProvider()))
        other.cookies.set(COOKIE,cookie,domain='testserver.local',path='/v1')
        self.assertEqual(401,other.get('/v1/session').status_code)
    def test_bad_private_code_is_rejected_before_google_verification(self):
        nonce=self.challenge()
        response=self.client.post('/v1/session',json={'token':'wrong','google_credential':self.credential(nonce)},headers=ORIGIN)
        self.assertEqual(401,response.status_code);self.assertEqual(0,self.certs.calls)
    def test_required_google_mode_with_missing_registration_fails_closed(self):
        for config in [replace(GOOGLE_CONFIG,google_client_id=''),replace(GOOGLE_CONFIG,allowed_google_emails=())]:
            c=TestClient(create_app(config,FakeProvider()))
            self.assertEqual(503,c.get('/v1/auth/config').status_code)
            self.assertEqual(503,c.post('/v1/session',json={'token':TOKEN},headers=ORIGIN).status_code)
            self.assertEqual(401,c.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
    def test_google_mode_has_only_required_csp_origins_and_popup_policy(self):
        response=self.client.get('/');csp=response.headers['Content-Security-Policy']
        self.assertIn('https://accounts.google.com/gsi/client',csp);self.assertIn('frame-src https://accounts.google.com/gsi/',csp)
        self.assertNotIn("'unsafe-inline'",csp);self.assertIn("frame-ancestors 'none'",csp)
        self.assertEqual('same-origin-allow-popups',response.headers['Cross-Origin-Opener-Policy'])
    def test_runtime_google_settings_use_explicit_invited_emails(self):
        with patch.dict('os.environ',{'LINGOLIVE_GOOGLE_CLIENT_ID':CLIENT_ID,'LINGOLIVE_GOOGLE_SIGNIN_REQUIRED':'true','LINGOLIVE_ALLOWED_GOOGLE_EMAILS':'ASHISH.T.VASANT@gmail.com, friend@example.com'}):
            config=Config.environment();self.assertTrue(config.google_signin_required)
            self.assertEqual((EMAIL,'friend@example.com'),config.allowed_google_emails)

if __name__=='__main__':unittest.main()

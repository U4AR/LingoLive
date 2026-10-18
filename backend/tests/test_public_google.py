"""Passcode-free verified Google access; durable quotas shared by every provider."""
import asyncio,time,unittest
from dataclasses import replace
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.app import Config,create_app,FirebaseIdentityVerifier
from backend.daily_quota import AudioReservation,quota_day
from test_app import CONFIG,INPUT,AUTH,FakeProvider
from test_google_signin import SIGNER,Certificates
from google.auth import jwt
ORIGIN={'Origin':'http://testserver'}
class Quota:
 def __init__(self):self.calls=0;self.audio=0;self.fail=False;self.settled=[]
 async def aclose(self):pass
 async def reserve_calls(self,units,limit):
  if self.fail:raise HTTPException(503,'Allowance unavailable')
  if self.calls+units>limit:return False
  self.calls+=units;return True
 async def reserve_audio(self,seconds,limit):
  if self.fail:raise HTTPException(503,'Allowance unavailable')
  if self.audio+seconds>limit:return None
  self.audio+=seconds;return AudioReservation(quota_day()[0],'test-ticket',seconds)
 async def settle_audio(self,reservation,seconds):self.settled.append(seconds)
class PublicGoogleTests(unittest.TestCase):
 def setUp(self):
  self.q=Quota();self.p=FakeProvider();self.personal=[];self.v=FirebaseIdentityVerifier();self.v.transport=Certificates()
  self.config=replace(CONFIG,public_demo=True,google_signin_required=True,google_client_id='fixture-google.apps.googleusercontent.com',google_auth_provider='firebase',firebase_api_key='fixture-public-browser-config',firebase_auth_domain='test-project-123.firebaseapp.com',project='test-project-123',public_model_calls_per_day=2)
 def app(self):
  def factory(c):p=FakeProvider();self.personal.append(p);return p
  return create_app(self.config,self.p,self.v,factory,self.q)
 def credential(self,**changes):
  now=int(time.time());claims={'iat':now,'exp':now+300,'aud':self.config.project,'iss':'https://securetoken.google.com/'+self.config.project,'sub':'fixture-google-user','email':'judge@example.com','email_verified':True,'firebase':{'sign_in_provider':'google.com'}};claims.update(changes);return jwt.encode(SIGNER,claims).decode()
 def login(self,c,**claims):
  challenge=c.get('/v1/auth/config').json()['nonce']
  return c.post('/v1/session',json={'mode':'public','google_credential':self.credential(**claims),'google_nonce':challenge},headers=ORIGIN)
 def test_public_setup_requires_durable_quota_and_never_silently_uses_ram(self):
  with self.assertRaises(ValueError):create_app(self.config,self.p)
 def test_google_is_required_and_previous_access_code_cannot_bypass_it(self):
  with TestClient(self.app()) as c:
   self.assertEqual(401,c.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
   self.assertEqual(401,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
   self.assertEqual([],self.p.requests)
 def test_any_verified_google_user_connects_without_a_passcode(self):
  with TestClient(self.app()) as c:
   r=self.login(c);self.assertEqual(200,r.status_code,r.text);self.assertEqual('public',r.json()['mode']);self.assertEqual('public',c.get('/v1/session').json()['mode'])
   self.assertEqual(200,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
   self.assertEqual(1,len(self.p.requests))
 def test_firebase_other_provider_unverified_and_wrong_issuer_are_rejected(self):
  with TestClient(self.app()) as c:
   for claims in [{'email_verified':False},{'iss':'https://attacker.example'},{'firebase':{'sign_in_provider':'password'}},{'aud':'other-project'}]:self.assertEqual(401,self.login(c,**claims).status_code)
   self.assertEqual([],self.p.requests)
 def test_nonce_must_match_and_cannot_be_replayed(self):
  with TestClient(self.app()) as c:
   c.get('/v1/auth/config');r=c.post('/v1/session',json={'mode':'public','google_credential':self.credential(),'google_nonce':'wrong'},headers=ORIGIN);self.assertEqual(401,r.status_code)
   self.assertEqual(200,self.login(c).status_code)
   r=c.post('/v1/session',json={'mode':'public','google_credential':self.credential(),'google_nonce':'wrong'},headers=ORIGIN);self.assertEqual(401,r.status_code)
 def test_daily_counter_survives_sign_out_and_app_restart(self):
  for index in range(3):
   with TestClient(self.app()) as c:
    self.assertEqual(200,self.login(c).status_code)
    self.assertEqual(200 if index<2 else 429,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
  self.assertEqual(2,len(self.p.requests))
 def test_personal_key_cannot_bypass_the_shared_host_infrastructure_cap(self):
  self.q.calls=2
  with TestClient(self.app()) as c:
   c.post('/v1/session',json={'mode':'api_key','api_key':'synthetic-personal-key-test-12345'},headers=ORIGIN)
   self.assertEqual(429,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code);self.assertEqual([],self.personal[0].requests)
 def test_parallel_lesson_spends_two_units_and_stops_at_daily_limit(self):
  self.config=replace(self.config,lesson_strategy='parallel')
  with TestClient(self.app()) as c:
   self.login(c);self.assertEqual(200,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
   self.assertEqual(429,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code)
  self.assertEqual(2,self.q.calls);self.assertEqual(1,len(self.p.requests))
 def test_quota_outage_prevents_model_call(self):
  self.q.fail=True
  with TestClient(self.app()) as c:
   self.login(c);self.assertEqual(503,c.post('/v1/teach',json=INPUT,headers=ORIGIN).status_code);self.assertEqual([],self.p.requests)
 def test_exhausted_audio_does_not_open_google_connection(self):
  self.q.audio=1200
  with TestClient(self.app()) as c:
   self.login(c)
   with c.websocket_connect('/v1/listen',headers=ORIGIN) as ws:
    ws.send_json({'setup':{}});self.assertIn('midnight IST',ws.receive_json()['error']['message'])
   self.assertIsNone(self.p.socket)
 def test_short_remaining_audio_reservation_limits_the_live_duration(self):
  async def short(seconds,limit):return AudioReservation(quota_day()[0],'short-reservation',12)
  self.q.reserve_audio=short
  with TestClient(self.app()) as c:
   self.login(c)
   with c.websocket_connect('/v1/listen',headers=ORIGIN) as ws:
    ws.send_json({'setup':{}});self.assertIn('setupComplete',ws.receive_json());self.assertIn('error',ws.receive_json())
  self.assertTrue(self.q.settled);self.assertLess(self.q.settled[0],12)
 def test_same_origin_is_enforced_after_google_login(self):
  with TestClient(self.app()) as c:
   self.login(c);self.assertEqual(403,c.post('/v1/teach',json=INPUT,headers={'Origin':'https://evil.example'}).status_code)
if __name__=='__main__':unittest.main()

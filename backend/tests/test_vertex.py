import asyncio,json,unittest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock,patch
import httpx
from fastapi.testclient import TestClient
from backend.app import Config,GoogleProvider,create_app,setup_message,VERTEX_WS
from test_app import TOKEN,AUTH,EXAMPLE,INPUT,FakeProvider
CONFIG=Config('',TOKEN,provider='vertex',project='locateassist')
class VertexConfigTests(unittest.TestCase):
 def test_keyless_vertex_configuration_requires_project_and_access_code(self):
  self.assertTrue(CONFIG.configured)
  self.assertFalse(Config('',TOKEN,provider='vertex').configured)
  self.assertFalse(Config('',TOKEN,provider='vertex',project='https://evil.example').configured)
  self.assertFalse(Config('',TOKEN,provider='other',project='locateassist').configured)
 def test_vertex_websocket_uses_server_project_model_without_an_api_key(self):
  provider=FakeProvider()
  with TestClient(create_app(CONFIG,provider)) as client:
   with client.websocket_connect('/v1/listen',headers=AUTH) as socket:
    socket.send_json({'setup':{'model':'untrusted'}});self.assertIn('setupComplete',socket.receive_json())
    expected=setup_message(CONFIG.transcribe_model,'locateassist')
    self.assertEqual(expected,provider.socket.sent[0])
    self.assertEqual('projects/locateassist/locations/global/publishers/google/models/gemini-3.5-transcribe-live',expected['setup']['model'])
class VertexContractTests(unittest.IsolatedAsyncioTestCase):
 async def test_vertex_teach_uses_cloud_oauth_and_keeps_structured_source_coverage(self):
  original=httpx.AsyncClient;received=[]
  def handler(request):
   received.append(request)
   self.assertEqual('https://aiplatform.googleapis.com/v1/projects/locateassist/locations/global/publishers/google/models/gemini-3.8-flash:generateContent',str(request.url))
   self.assertEqual('Bearer test-only-vertex-oauth',request.headers['authorization']);self.assertNotIn('x-goog-api-key',request.headers)
   return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(EXAMPLE['lesson'])}]}}]})
  def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
  from backend.app import TeachRequest
  provider=GoogleProvider(CONFIG)
  with patch.object(provider,'_vertex_token',new=AsyncMock(return_value='test-only-vertex-oauth')),patch('backend.app.httpx.AsyncClient',side_effect=client):
   lesson=await provider.teach(TeachRequest.model_validate(INPUT))
  self.assertEqual(EXAMPLE['text'],''.join(w['text'] for w in lesson['words']));self.assertEqual(1,len(received))
 async def test_vertex_live_uses_authenticated_cloud_websocket_without_a_query_key(self):
  captured=[];marker=object()
  @asynccontextmanager
  async def connect(url,**kwargs):captured.append((url,kwargs));yield marker
  provider=GoogleProvider(CONFIG)
  with patch.object(provider,'_vertex_token',new=AsyncMock(return_value='test-only-vertex-oauth')),patch('backend.app.connect',side_effect=connect):
   async with provider.live() as socket:self.assertIs(marker,socket)
  self.assertEqual(VERTEX_WS,captured[0][0]);self.assertNotIn('?',captured[0][0])
  self.assertEqual({'Authorization':'Bearer test-only-vertex-oauth'},captured[0][1]['additional_headers'])
 async def test_runtime_credentials_are_reused_and_refreshed_once_for_concurrent_calls(self):
  class Credentials:
   valid=False;token='test-only-metadata-token';refreshes=0
   def refresh(self,request):self.refreshes+=1;self.valid=True
  credentials=Credentials();provider=GoogleProvider(CONFIG)
  with patch('backend.app.google.auth.default',return_value=(credentials,'locateassist')) as default:
   tokens=await asyncio.gather(provider._vertex_token(),provider._vertex_token())
  self.assertEqual(['test-only-metadata-token']*2,tokens);self.assertEqual(1,credentials.refreshes);default.assert_called_once()

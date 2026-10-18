"""Local-only public-demo UI fixture; external Google login is not simulated as live."""
from dataclasses import replace
from tools.web_fixture import Provider
from backend.app import Config,create_app
class Quota:
 async def aclose(self):pass
 async def reserve_calls(self,*args):return True
 async def reserve_audio(self,*args):raise RuntimeError('No live audio in this UI fixture')
config=Config('synthetic-fixture-key','test-only-browser-access-code-32-characters',public_demo=True,google_signin_required=True,google_client_id='test-web.apps.googleusercontent.com',google_auth_provider='firebase',firebase_api_key='synthetic-firebase-config-key',firebase_auth_domain='test-project-123.firebaseapp.com',project='test-project-123',lesson_strategy='parallel')
app=create_app(config,Provider(),daily_quota=Quota())

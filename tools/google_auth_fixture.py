"""Local-only Google UI fixture. Never include tools/ in a deployed container."""
import json,time
from fastapi import Request
from google.auth import crypt,jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from backend.app import Config,GoogleIdentityVerifier,create_app
from tools.web_fixture import Provider
KEY=rsa.generate_private_key(public_exponent=65537,key_size=2048)
PRIVATE=KEY.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
PUBLIC=KEY.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
SIGNER=crypt.RSASigner.from_string(PRIVATE,key_id='browser-fixture')
CLIENT='123456789-browser-fixture.apps.googleusercontent.com'
OWNER='ashish.t.vasant@gmail.com'
class CertificateResponse:
    status=200
    data=json.dumps({'browser-fixture':PUBLIC}).encode()
    def __call__(self,*args,**kwargs):return self
identity=GoogleIdentityVerifier();identity.transport=CertificateResponse()
provider=Provider()
app=create_app(Config('test-only-google-key','test-only-browser-access-code-32-characters',google_client_id=CLIENT,google_signin_required=True,allowed_google_emails=(OWNER,)),provider,identity)
@app.get('/fixture/google-credential')
async def credential(request:Request):
    now=int(time.time());claims={'iat':now,'exp':now+300,'iss':'https://accounts.google.com','aud':CLIENT,'nonce':request.query_params['nonce'],'email':request.query_params.get('email',OWNER),'email_verified':True,'sub':'fixture-google-user'}
    return {'credential':jwt.encode(SIGNER,claims).decode()}
@app.get('/fixture/status')
async def status():return {'requests':len(provider.requests)}

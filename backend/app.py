"""Cloud Run relay for Google Transcribe Live and Gemini Flash.

No audio, transcripts or lessons are persisted by the service. Credentials are
runtime bindings or expiring personal-key sessions, never mobile build inputs.
The access token is for a private
hackathon/personal deployment; a public multi-user service should use user auth.
"""
from __future__ import annotations
import io, wave
import asyncio, base64, binascii, collections, hashlib, hmac, json, os, re, secrets, time, unicodedata
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlencode
from typing import Literal
import httpx
import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token as google_id_token
from google.auth.exceptions import GoogleAuthError
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from websockets.asyncio.client import connect
from backend.daily_quota import GCSQuota, quota_day
from backend.fast_lessons import SOURCE_SCHEMA, REPLY_SCHEMA, EXPRESS_SCHEMA, SOURCE_PROMPT, EXPRESS_SOURCE_PROMPT, REPLY_PROMPT, EXPRESS_PROMPT, known_language_hint, language_base, merge as merge_parallel

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'shared/lesson_schema.json').read_text())
# Keep explicit field names: compact word aliases proved unreliable in live
# multilingual output. Bound optional detail while preserving every definition.
MODEL_SCHEMA = json.loads(json.dumps(SCHEMA))
for key,limit in (('text',1000),('reading',80),('meaning',160),('note',120)):
    MODEL_SCHEMA['$defs']['word']['properties'][key]['maxLength']=limit
MODEL_SCHEMA['$defs']['word']['properties']['reading']['description']='One short Latin transliteration only, for example kōhī. For Latin-script words copy text exactly. No alternatives, explanations or analysis.'
MODEL_SCHEMA['$defs']['word']['properties']['meaning']['description']='Brief contextual word meaning in the learner known language.'
INSTRUCTIONS = (ROOT / 'shared/teach_prompt.txt').read_text()
MODEL_INSTRUCTIONS = INSTRUCTIONS + "\nUse the full specified field names. Every source and reply word needs its meaning. Give ONE short Latin transliteration per word, for example kōhī, with no alternatives, IPA, repetition or analysis. For words already in Latin script, reading copies text exactly. Leave note empty unless essential. Supply exactly three short replies if contains_learning_language is true OR source is the known language OR assistance_mode=say_this. For known-language/say_this input express the current intention in the target language instead of answering it.\n"
GOOGLE_WS = 'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent'
VERTEX_WS = 'wss://aiplatform.googleapis.com/ws/google.cloud.aiplatform.v1.LlmBidiService/BidiGenerateContent'
WEB = ROOT / 'web'
COOKIE = 'lingolive_session'
GOOGLE_NONCE_COOKIE = 'lingolive_google_nonce'
SESSION_SECONDS = 60 * 60

@dataclass(frozen=True)
class Config:
    api_key: str = ''
    access_token: str = ''
    flash_model: str = 'gemini-3.8-flash'
    transcribe_model: str = 'gemini-3.5-transcribe-live'
    requests_per_minute: int = 24
    provider: str = 'gemini'
    project: str = ''
    location: str = 'global'
    ai_enabled: bool = True
    lessons_per_hour: int = 360
    lessons_per_day: int = 400
    audio_seconds_per_hour: int = 2400
    audio_seconds_per_day: int = 3600
    max_output_tokens: int = 4096
    google_client_id: str = ''
    google_signin_required: bool = False
    allowed_google_emails: tuple[str, ...] = ()
    byok_enabled: bool = True
    lesson_strategy: str = 'single'
    thinking_level: str = 'auto'
    public_demo: bool = False
    quota_bucket: str = ''
    public_audio_seconds_per_day: int = 1200
    public_model_calls_per_day: int = 200
    google_auth_provider: str = 'gis'
    firebase_api_key: str = ''
    firebase_auth_domain: str = ''
    @classmethod
    def environment(cls):
        return cls(os.getenv('GEMINI_API_KEY', ''), os.getenv('LINGOLIVE_ACCESS_TOKEN', ''),
            os.getenv('LINGOLIVE_FLASH_MODEL', 'gemini-3.8-flash'), os.getenv('LINGOLIVE_TRANSCRIBE_MODEL', 'gemini-3.5-transcribe-live'),
            provider=os.getenv('LINGOLIVE_PROVIDER','gemini'), project=os.getenv('LINGOLIVE_VERTEX_PROJECT',''), location=os.getenv('LINGOLIVE_VERTEX_LOCATION','global'),
            requests_per_minute=int(os.getenv('LINGOLIVE_REQUESTS_PER_MINUTE','24')),
            ai_enabled=os.getenv('LINGOLIVE_AI_ENABLED','true').lower()=='true',
            lessons_per_hour=int(os.getenv('LINGOLIVE_LESSONS_PER_HOUR','360')),
            lessons_per_day=int(os.getenv('LINGOLIVE_LESSONS_PER_DAY','400')),
            audio_seconds_per_hour=int(os.getenv('LINGOLIVE_AUDIO_SECONDS_PER_HOUR','2400')),
            audio_seconds_per_day=int(os.getenv('LINGOLIVE_AUDIO_SECONDS_PER_DAY','3600')),
            max_output_tokens=int(os.getenv('LINGOLIVE_MAX_OUTPUT_TOKENS','4096')),
            byok_enabled=os.getenv('LINGOLIVE_BYOK_ENABLED','true').lower()=='true',
            lesson_strategy=os.getenv('LINGOLIVE_LESSON_STRATEGY','single'),
            thinking_level=os.getenv('LINGOLIVE_THINKING_LEVEL','auto'),
            public_demo=os.getenv('LINGOLIVE_PUBLIC_DEMO','false').lower()=='true',
            quota_bucket=os.getenv('LINGOLIVE_QUOTA_BUCKET',''),
            public_audio_seconds_per_day=int(os.getenv('LINGOLIVE_PUBLIC_AUDIO_SECONDS_PER_DAY','1200')),
            public_model_calls_per_day=int(os.getenv('LINGOLIVE_PUBLIC_MODEL_CALLS_PER_DAY','200')),
            google_auth_provider=os.getenv('LINGOLIVE_GOOGLE_AUTH_PROVIDER','gis'),
            firebase_api_key=os.getenv('LINGOLIVE_FIREBASE_API_KEY',''),
            firebase_auth_domain=os.getenv('LINGOLIVE_FIREBASE_AUTH_DOMAIN',''),
            google_client_id=os.getenv('LINGOLIVE_GOOGLE_CLIENT_ID',''),
            google_signin_required=os.getenv('LINGOLIVE_GOOGLE_SIGNIN_REQUIRED','false').lower()=='true',
            allowed_google_emails=tuple(e.strip().casefold() for e in os.getenv('LINGOLIVE_ALLOWED_GOOGLE_EMAILS','').split(',') if e.strip()))
    @property
    def configured(self):
        vertex=bool(re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]',self.project) and re.fullmatch(r'[a-z0-9-]{1,40}',self.location))
        return len(self.access_token)>=32 and ((self.provider=='gemini' and bool(self.api_key)) or (self.provider=='vertex' and vertex))

class ConversationTurn(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    speaker: Literal['unattributed','user','likely_user','likely_other']
    text: str = Field(min_length=1,max_length=400)

class PreviousReply(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    text: str = Field(min_length=1,max_length=300)
    translation: str = Field(max_length=300)

class SeenWord(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    text: str = Field(min_length=1,max_length=40)
    meaning: str = Field(max_length=120)

class LocationContext(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    latitude: float = Field(ge=-90,le=90)
    longitude: float = Field(ge=-180,le=180)
    accuracy_m: float = Field(ge=1000,le=1000000)
    speed_kmh: float | None = Field(default=None,ge=0,le=500)
    captured_at: int
    @model_validator(mode='after')
    def approximate(self):
        self.latitude=round(self.latitude,2);self.longitude=round(self.longitude,2)
        return self

class AudioContext(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    mime_type: Literal['audio/wav'] = 'audio/wav'
    data: str = Field(min_length=60,max_length=171000)
    @model_validator(mode='after')
    def short_mono_pcm(self):
        try:
            raw=base64.b64decode(self.data,validate=True)
            if len(raw)>128100:raise ValueError()
            with wave.open(io.BytesIO(raw),'rb') as wav:
                frames=wav.getnframes()
                if wav.getnchannels()!=1 or wav.getsampwidth()!=2 or wav.getframerate()!=16000 or wav.getcomptype()!='NONE' or not 0<frames<=64000:raise ValueError()
                if len(wav.readframes(frames))!=frames*2:raise ValueError()
        except (ValueError,wave.Error,EOFError):raise ValueError('Use at most four seconds of mono 16 kHz PCM WAV') from None
        return self

class PersonalMemoryItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['activity','place','preference']
    text: str = Field(min_length=1,max_length=160)
    status: Literal['possible','confirmed']
    setting: Literal['any','home','office','travelling','train','cafe','restaurant','shop','other']
    observations: int = Field(ge=1,le=99)

class MemoryCandidate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['activity','place','preference']
    topic: str = Field(min_length=1,max_length=40)
    text: str = Field(min_length=1,max_length=160)
    evidence: str = Field(min_length=1,max_length=200)
    setting: Literal['any','home','office','travelling','train','cafe','restaurant','shop','other']
    duration: Literal['recent','routine']

class PlaceContext(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    label: str = Field(min_length=1,max_length=60)
    fact: str = Field(min_length=1,max_length=160)
    status: Literal['possible','confirmed']

class PlaceCandidate(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    label: str = Field(min_length=1,max_length=60)
    fact: str = Field(min_length=1,max_length=160)
    evidence: str = Field(min_length=1,max_length=200)

class PlanStep(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    label: str = Field(min_length=1,max_length=100)
    optional: bool
    state: Literal['pending','done','skipped']

class TaskPlan(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    intent: str = Field(min_length=1,max_length=600)
    steps: list[PlanStep] = Field(default_factory=list,max_length=6)
    current_step: int | None = Field(default=None,ge=0,le=5)
    @model_validator(mode='after')
    def active_step_exists(self):
        if self.steps and (self.current_step is None or self.current_step>=len(self.steps) or self.steps[self.current_step].state!='pending'):
            raise ValueError('Choose a pending current step')
        if not self.steps and self.current_step is not None:raise ValueError('No current step without steps')
        return self

class SuggestedPlanStep(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    label: str = Field(min_length=1,max_length=100)
    optional: bool

class TeachRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    text: str = Field(min_length=1, max_length=1000)
    known_code: str = Field(pattern=r'^[a-z]{2,3}(?:-[A-Za-z0-9]+)*$', max_length=40)
    known_name: str = Field(min_length=1, max_length=80)
    learning_code: str = Field(pattern=r'^[a-z]{2,3}(?:-[A-Za-z0-9]+)*$', max_length=40)
    learning_name: str = Field(min_length=1, max_length=80)
    user_goal: str = Field(default='',max_length=600)
    task_plan: TaskPlan | None = None
    assistance_mode: Literal['auto','say_this'] = 'auto'
    inferred_user_goal: str = Field(default='',max_length=300)
    current_speaker_hint: Literal['auto','user'] = 'auto'
    memory_notes: str = Field(default='',max_length=800)
    personal_memories: list[PersonalMemoryItem] = Field(default_factory=list,max_length=5)
    learn_personal_memory: bool = False
    place_context: list[PlaceContext] = Field(default_factory=list,max_length=2)
    learn_place_memory: bool = False
    setting: Literal['auto','home','office','travelling','train','cafe','restaurant','shop','other'] = 'auto'
    previous_reply_source: str = Field(default='',max_length=400)
    previous_replies: list[PreviousReply] = Field(default_factory=list,max_length=3)
    previously_seen_words: list[SeenWord] = Field(default_factory=list,max_length=12)
    location_context: LocationContext | None = None
    audio_context: AudioContext | None = None
    conversation_summary: str = Field(default='',max_length=600)
    recent_turns: list[ConversationTurn] = Field(default_factory=list,max_length=8)
    @model_validator(mode='after')
    def different_languages(self):
        aliases = {'cmn':'zh','iw':'he','in':'id','tl':'fil','no':'nb'}
        def base(code): return aliases.get(code.split('-')[0], code.split('-')[0])
        if base(self.known_code) == base(self.learning_code) or not self.text.strip(): raise ValueError('Choose different languages and a non-empty phrase')
        return self

class SessionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    token: str = Field(default='', max_length=2048)
    mode: Literal['access_code','api_key','public'] = 'access_code'
    api_key: str = Field(default='', max_length=256)
    google_credential: str = Field(default='',max_length=10000)
    google_nonce: str = Field(default='',max_length=200)

class Word(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    text: str = Field(min_length=1, max_length=1000)
    reading: str = Field(max_length=2000)
    meaning: str = Field(max_length=2000)
    note: str = Field(max_length=2000)
    is_word: bool
    @model_validator(mode='after')
    def defined(self):
        if self.is_word and (not self.meaning.strip() or not self.reading.strip()): raise ValueError('Missing word definition')
        if not self.is_word and any(c.isalnum() for c in self.text): raise ValueError('Unexplained word')
        return self

class Reply(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    label: str = Field(min_length=1, max_length=300)
    translation: str = Field(min_length=1, max_length=4000)
    words: list[Word] = Field(min_length=1, max_length=300)
    @model_validator(mode='after')
    def has_words(self):
        if not any(w.is_word for w in self.words): raise ValueError('Reply has no words')
        return self

class Lesson(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    detected_language: str = Field(min_length=2, max_length=40)
    contains_learning_language: bool
    translation: str = Field(max_length=10000)
    explanation: str = Field(max_length=10000)
    tip: str = Field(max_length=4000)
    words: list[Word] = Field(max_length=1200)
    replies: list[Reply] = Field(max_length=3)
    context_summary: str = Field(default='',max_length=600)
    inferred_setting: Literal['unknown','home','office','travelling','train','cafe','restaurant','shop','other'] = 'unknown'
    context_confidence: Literal['low','medium','high'] = 'low'
    current_speaker: Literal['user','other','unknown'] = 'unknown'
    speaker_confidence: Literal['low','medium','high'] = 'low'
    inferred_user_intent: str = Field(default='',max_length=300)
    memory_candidates: list[MemoryCandidate] = Field(default_factory=list,max_length=2)
    place_candidates: list[PlaceCandidate] = Field(default_factory=list,max_length=1)
    reply_mode: Literal['none','respond','express'] = 'none'
    suggested_plan_steps: list[SuggestedPlanStep] = Field(default_factory=list,max_length=6)

def validate_lesson(value, source):
    lesson = Lesson.model_validate(value)
    # A model's memory proposal must cite the current utterance verbatim, not a suggestion.
    if 'memory_candidates' in value:
        lesson.memory_candidates=[m for m in lesson.memory_candidates if m.evidence in source]
    if 'place_candidates' in value:
        lesson.place_candidates=[m for m in lesson.place_candidates if m.evidence in source]
    if lesson.contains_learning_language:
        if ''.join(w.text for w in lesson.words) != source or not any(w.is_word for w in lesson.words) or len(lesson.replies) != 3:
            raise ValueError('Lesson must cover the exact source and supply three replies')
    elif lesson.reply_mode=='express' and (lesson.words or len(lesson.replies)!=3):
        raise ValueError('Express mode needs three complete target-language phrases, without invented source words')
    return lesson.model_dump(exclude_unset=True)

def normalize_model_lesson(value):
    """Latin text is already transliterated; do not generate alternative spellings."""
    def words(items):
        if not isinstance(items,list):raise ValueError('Invalid word list')
        result=[]
        for word in items:
            if not isinstance(word,dict):raise ValueError('Invalid word')
            word=dict(word);text=word.get('text')
            if isinstance(text,str) and word.get('is_word') is True:
                latin=all(not c.isalpha() or 'LATIN' in unicodedata.name(c,'') for c in text)
                if latin:word['reading']=text
                elif isinstance(word.get('reading'),str) and len(word['reading'])>80:
                    raise ValueError('Word pronunciation is too long')
            result.append(word)
        return result
    if not isinstance(value,dict):raise ValueError('Invalid lesson')
    value=dict(value);value['words']=words(value['words'])
    if not isinstance(value['replies'],list) or any(not isinstance(r,dict) for r in value['replies']):
        raise ValueError('Invalid replies')
    value['replies']=[dict(reply,words=words(reply['words'])) for reply in value['replies']]
    return value

def setup_message(model,project=None,location='global'):
    if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]{1,80}-transcribe-live', model): raise ValueError('Invalid transcription model')
    if project is not None:
        if not re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]',project) or not re.fullmatch(r'[a-z0-9-]{1,40}',location):raise ValueError('Invalid Vertex configuration')
        name=f'projects/{project}/locations/{location}/publishers/google/models/{model}'
    else:name='models/'+model
    return {'setup': {'model': name, 'generationConfig': {'responseModalities': ['TEXT']}, 'inputAudioTranscription': {'languageCodes': [], 'mode': 'VERBATIM'}}}

def validate_audio(message):
    if set(message) != {'realtimeInput'} or not isinstance(message['realtimeInput'], dict): raise ValueError('Expected audio input')
    data = message['realtimeInput']
    if data == {'audioStreamEnd': True}: return 0
    if set(data) != {'audio'} or not isinstance(data['audio'], dict): raise ValueError('Expected PCM audio')
    audio = data['audio']
    if set(audio) != {'data','mimeType'} or audio['mimeType'] != 'audio/pcm;rate=16000' or not isinstance(audio['data'], str): raise ValueError('Expected 16 kHz PCM')
    raw = base64.b64decode(audio['data'], validate=True)
    if not raw or len(raw) > 6400 or len(raw) % 2: raise ValueError('Invalid audio frame')
    return len(raw)

class Window:
    def __init__(self, limit): self.limit=limit; self.starts=collections.deque()
    def allow(self,amount=1):
        now=time.monotonic()
        while self.starts and now-self.starts[0]>=60: self.starts.popleft()
        if len(self.starts)+amount>self.limit: return False
        self.starts.extend([now]*amount); return True

class Budget:
    """Rolling per-instance usage; reserve before upstream access, including idle time."""
    def __init__(self, hourly, daily):
        self.hourly=hourly; self.daily=daily; self.entries=collections.deque()
    def reserve(self, amount):
        now=time.monotonic()
        while self.entries and now-self.entries[0][0]>=86400: self.entries.popleft()
        hour=sum(e[1] for e in self.entries if now-e[0]<3600)
        day=sum(e[1] for e in self.entries)
        if hour+amount>self.hourly or day+amount>self.daily: return None
        entry=[now,amount]; self.entries.append(entry); return entry
    def settle(self, entry, amount):
        entry[1]=min(entry[1],max(0,amount))

class AudioPace:
    def __init__(self): self.started=time.monotonic(); self.bytes=0
    def accept(self, size):
        self.bytes+=size
        if self.bytes>32000*(time.monotonic()-self.started+5):
            raise ValueError('Audio must be sent in real time')

class GoogleIdentityVerifier:
    """Verify Google signature, issuer, audience and expiry with cached public certs."""
    def __init__(self):
        self.lock=asyncio.Lock(); self.cached=None; self.expires=0
        self.transport=GoogleAuthRequest()
    def certificates(self,url,method='GET',**kwargs):
        if self.cached is None or time.monotonic()>=self.expires:
            response=self.transport(url,method=method,timeout=10,**kwargs)
            if response.status==200:
                self.cached=response; self.expires=time.monotonic()+300
            return response
        return self.cached
    async def verify(self,credential,client_id):
        try:
            async with self.lock:
                return await asyncio.to_thread(google_id_token.verify_oauth2_token,credential,self.certificates,audience=client_id)
        except (ValueError,GoogleAuthError):
            raise HTTPException(401,'Google sign-in could not be verified. Please sign in again.') from None

class FirebaseIdentityVerifier(GoogleIdentityVerifier):
    async def verify(self,credential,project):
        async with self.lock:
            try:return await asyncio.to_thread(google_id_token.verify_firebase_token,credential,self.certificates,audience=project)
            except (ValueError,GoogleAuthError):raise HTTPException(401,'Google account verification failed. Please sign in again.') from None

class GoogleProvider:
    def __init__(self, config: Config):
        self.config=config;self._credentials=None;self._credential_lock=asyncio.Lock();self._http_client=None
    async def _vertex_token(self):
        async with self._credential_lock:
            try:
                if self._credentials is None:
                    self._credentials,_=await asyncio.to_thread(google.auth.default,scopes=['https://www.googleapis.com/auth/cloud-platform'])
                if not self._credentials.valid:await asyncio.to_thread(self._credentials.refresh,GoogleAuthRequest())
                return self._credentials.token
            except Exception:raise HTTPException(503,'Google Cloud model access is not ready. Ask the host to check the runtime service account.') from None
    def _vertex_model(self,model):
        if not re.fullmatch(r'[a-z][a-z0-9-]{4,61}[a-z0-9]',self.config.project) or not re.fullmatch(r'[a-z0-9-]{1,40}',self.config.location):raise HTTPException(503,'Invalid Vertex project configuration')
        return f'projects/{self.config.project}/locations/{self.config.location}/publishers/google/models/{model}'
    @asynccontextmanager
    async def _http_session(self):
        if self.config.lesson_strategy=='parallel':
            if self._http_client is None or self._http_client.is_closed:
                self._http_client=httpx.AsyncClient(timeout=httpx.Timeout(90,connect=15),
                    limits=httpx.Limits(max_connections=4,max_keepalive_connections=4,keepalive_expiry=60))
            yield self._http_client
        else:
            async with httpx.AsyncClient(timeout=httpx.Timeout(90,connect=15)) as client:yield client
    async def aclose(self):
        if self._http_client is not None:await self._http_client.aclose()
    async def teach(self, value: TeachRequest):
        payload=value.model_dump(exclude_defaults=True,exclude={'audio_context'})
        express_hint=value.assistance_mode=='say_this' or known_language_hint(value.text,value.known_code,value.learning_code)
        if express_hint:payload['assistance_mode']='say_this'
        if value.location_context and not 0<=time.time()-value.location_context.captured_at<=300:
            payload.pop('location_context',None)
        parts=[{'text':json.dumps(payload,ensure_ascii=False)}]
        if value.audio_context:parts.append({'inlineData':{'mimeType':'audio/wav','data':value.audio_context.data}})
        if self.config.lesson_strategy not in ('single','parallel'):raise HTTPException(503,'Invalid lesson strategy')
        thinking=self.config.thinking_level
        if thinking=='auto':thinking='minimal' if self.config.flash_model=='gemini-3.1-flash-lite' else 'low'
        if thinking not in ('minimal','low','medium','high'):raise HTTPException(503,'Invalid reasoning setting')
        def body(prompt,schema,content,cap):
            return {'systemInstruction':{'parts':[{'text':prompt}]},'contents':[{'role':'user','parts':content}],
                'generationConfig':{'responseMimeType':'application/json','responseJsonSchema':schema,
                    'maxOutputTokens':cap,'thinkingConfig':{'thinkingLevel':thinking}}}
        if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]{1,80}',self.config.flash_model): raise HTTPException(503,'Invalid Flash model configuration')
        if self.config.provider=='vertex':
            url='https://aiplatform.googleapis.com/v1/'+self._vertex_model(self.config.flash_model)+':generateContent'
            headers={'Authorization':'Bearer '+await self._vertex_token()}
        else:
            url=f'https://generativelanguage.googleapis.com/v1beta/models/{self.config.flash_model}:generateContent'
            headers={'x-goog-api-key':self.config.api_key}
        async def generate(client,request_body):
            async with client.stream('POST',url,headers=headers,json=request_body) as response:
                if response.status_code==429: raise HTTPException(429,'Google rate limit reached; retry shortly',headers={'Retry-After':'15'})
                if response.status_code==402: raise HTTPException(503,'Google AI billing needs credit. Check the API key’s AI Studio billing, then retry this saved phrase.')
                if response.status_code in (400,401,403,404): raise HTTPException(502,'Google model access failed; check the API key or server credentials and model availability')
                if not response.is_success: raise HTTPException(502,'Google could not complete the lesson')
                chunks=[];size=0
                async for chunk in response.aiter_bytes():
                    size+=len(chunk)
                    if size>500000: raise HTTPException(502,'Lesson response too large')
                    chunks.append(chunk)
            data=json.loads(b''.join(chunks));candidate=data.get('candidates',[{}])[0]
            if candidate.get('finishReason','STOP')!='STOP': raise ValueError('Incomplete lesson')
            text=''.join(p.get('text','') for p in candidate['content']['parts'] if not p.get('thought'))
            return json.loads(text)
        def express_source(source):
            return value.assistance_mode=='say_this' or (not source.get('contains_learning_language') and language_base(source.get('detected_language'))==language_base(value.known_code))
        try:
            async with self._http_session() as client:
                if self.config.lesson_strategy=='parallel':
                    source_cap=self.config.max_output_tokens//2;reply_cap=self.config.max_output_tokens-source_cap
                    if source_cap<128:raise HTTPException(503,'Output allowance is too small for two branches')
                    tasks=[asyncio.create_task(generate(client,body(EXPRESS_SOURCE_PROMPT if express_hint else SOURCE_PROMPT,SOURCE_SCHEMA,parts,source_cap))),
                        asyncio.create_task(generate(client,body(EXPRESS_PROMPT if express_hint else REPLY_PROMPT,EXPRESS_SCHEMA if express_hint else REPLY_SCHEMA,parts[:1],reply_cap)))]
                    try:source,replies=await asyncio.gather(*tasks)
                    except BaseException:
                        for task in tasks:task.cancel()
                        await asyncio.gather(*tasks,return_exceptions=True)
                        raise
                    result=merge_parallel(source,replies,value.text,force_express=express_source(source))
                else:
                    result=normalize_model_lesson(await generate(client,body(MODEL_INSTRUCTIONS,MODEL_SCHEMA,parts,self.config.max_output_tokens)))
                    if express_source(result):result['reply_mode']='express'
            if not value.learn_personal_memory:result.pop('memory_candidates',None)
            elif result.get('current_speaker')!='user' or result.get('speaker_confidence') not in ('medium','high'):
                result['memory_candidates']=[]
            if not value.task_plan or value.task_plan.steps:result.pop('suggested_plan_steps',None)
            if not value.learn_place_memory:result.pop('place_candidates',None)
            elif result.get('current_speaker')!='user' or (value.current_speaker_hint!='user' and result.get('speaker_confidence')!='high'):
                result['place_candidates']=[]
            return validate_lesson(result,value.text)
        except HTTPException: raise
        except httpx.HTTPError: raise HTTPException(502,'Cannot reach Google; the client can retry its saved transcript') from None
        except (ValueError,KeyError,IndexError,TypeError): raise HTTPException(502,'Google returned an incomplete lesson; retry the saved transcript') from None
    @asynccontextmanager
    async def live(self):
        # Never log this URL or upstream exceptions: it contains a runtime secret.
        if self.config.provider=='vertex':
            url=VERTEX_WS;options={'additional_headers':{'Authorization':'Bearer '+await self._vertex_token()}}
        else:
            url=GOOGLE_WS+'?'+urlencode({'key':self.config.api_key});options={}
        async with connect(url,open_timeout=15,close_timeout=5,max_size=500000,ping_interval=20,**options) as socket:
            yield socket

@dataclass
class KeySession:
    provider: GoogleProvider
    config: Config
    expires_at: float
    revoked: asyncio.Event
    timer: asyncio.TimerHandle | None = None

def create_app(config: Config | None = None, provider=None, identity_verifier=None, key_provider_factory=None, daily_quota=None):
    config=config or Config.environment();provider=provider or GoogleProvider(config)
    identity_verifier=identity_verifier or (FirebaseIdentityVerifier() if config.google_auth_provider=='firebase' else GoogleIdentityVerifier())
    daily_quota=daily_quota or (GCSQuota(config.quota_bucket,provider._vertex_token) if config.quota_bucket else None)
    if config.public_demo and (daily_quota is None or config.public_audio_seconds_per_day<=10 or config.public_model_calls_per_day<2):
        raise ValueError('Public access requires a durable daily allowance')
    used_nonces={}
    key_sessions: dict[str, KeySession] = {}
    key_provider_factory=key_provider_factory or GoogleProvider
    signing_key=config.access_token.encode() if len(config.access_token)>=32 else secrets.token_bytes(32)
    cleanup_tasks=set()
    @asynccontextmanager
    async def lifespan(_):
        try:yield
        finally:
            for nonce in list(key_sessions):forget_key(nonce)
            if daily_quota:await daily_quota.aclose()
            if callable(getattr(provider,'aclose',None)):await provider.aclose()
            if cleanup_tasks:await asyncio.gather(*list(cleanup_tasks),return_exceptions=True)
    app=FastAPI(title='LingoLive',docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    lessons=Window(config.requests_per_minute);sessions=Window(12);signins=Window(12)
    live_slots=asyncio.Semaphore(2); connections=asyncio.Semaphore(4); lesson_slots=asyncio.Semaphore(2)
    lesson_budget=Budget(config.lessons_per_hour,config.lessons_per_day)
    audio_budget=Budget(config.audio_seconds_per_hour,config.audio_seconds_per_day)
    # Personal-key usage has independent allowances; it never spends host model quota.
    key_lessons=Window(config.requests_per_minute)
    key_lesson_budget=Budget(config.lessons_per_hour,config.lessons_per_day)
    key_audio_budget=Budget(config.audio_seconds_per_hour,config.audio_seconds_per_day)
    def forget_key(nonce):
        entry=key_sessions.pop(nonce,None)
        if entry:
            entry.revoked.set()
            if entry.timer:entry.timer.cancel()
            if callable(getattr(entry.provider,'aclose',None)):
                task=asyncio.create_task(entry.provider.aclose());cleanup_tasks.add(task);task.add_done_callback(cleanup_tasks.discard)
    def prune_keys():
        for nonce,entry in list(key_sessions.items()):
            if entry.expires_at<=time.time():forget_key(nonce)
    def personal_session(request):
        prune_keys()
        if not config.byok_enabled:return None
        parts=request.cookies.get(COOKIE,'').split('.')
        if len(parts)!=4 or parts[2]!='key':return None
        try:
            if not 0<=time.time()-int(parts[0])<SESSION_SECONDS:return None
            if not hmac.compare_digest(parts[3],signed_session('.'.join(parts[:3]))):return None
        except (ValueError,TypeError):return None
        return key_sessions.get(parts[1])
    def selection(request):
        if bearer_authorized(request.headers.get('authorization','')):return provider,config,None
        entry=personal_session(request)
        if request.cookies.get(COOKIE,'').split('.')[2:3]==['key'] and entry is None:
            raise HTTPException(401,'Reconnect with your Google API key.')
        return (entry.provider,entry.config,entry) if entry else (provider,config,None)
    def authorized(header):
        if not config.configured: return False
        supplied=header.removeprefix('Bearer ') if header.startswith('Bearer ') else ''
        return hmac.compare_digest(hashlib.sha256(supplied.encode()).digest(),hashlib.sha256(config.access_token.encode()).digest())
    def bearer_authorized(header):
        return not config.google_signin_required and authorized(header)
    def same_origin(request):
        origin=request.headers.get('origin','')
        # Cloud Run terminates TLS upstream; compare the public Host, not ASGI scheme.
        # Origin is compulsory for cookie-authenticated writes and WebSockets.
        return origin in ('https://'+request.headers.get('host',''), 'http://'+request.headers.get('host','')) and (
            origin.startswith('https://') or request.url.hostname in ('127.0.0.1','localhost','testserver'))
    def signed_session(payload):
        return hmac.new(signing_key,('web-session:'+payload).encode(),hashlib.sha256).hexdigest()
    def cookie_authorized(request):
        if personal_session(request):return True
        if config.public_demo and not config.google_signin_required and config.configured and request.cookies.get(COOKIE,'').split('.')[2:3]!=['key']:return True
        if not config.configured: return False
        value=request.cookies.get(COOKIE,'')
        try:
            parts=value.split('.')
            if len(parts)==3:
                if config.google_signin_required: return False
                issued,nonce,signature=parts
            elif len(parts)==4:
                issued,nonce,identity,signature=parts
                claims=json.loads(base64.urlsafe_b64decode(identity+'='*(-len(identity)%4)))
                if config.google_signin_required and (not claims.get('sub') or (bool(config.allowed_google_emails) and claims.get('email','').casefold() not in config.allowed_google_emails)):return False
            else:return False
            age=time.time()-int(issued)
            return 0<=age<SESSION_SECONDS and len(nonce)==32 and hmac.compare_digest(signature,signed_session('.'.join(parts[:-1])))
        except (ValueError,TypeError,KeyError,AttributeError): return False
    @app.middleware('http')
    async def authorize_http(request: Request, next_handler):
        if request.url.path.startswith('/v1/'):
            public_auth=request.url.path in ('/v1/session','/v1/auth/config')
            if not config.configured and not personal_session(request) and not (config.byok_enabled and public_auth):
                return JSONResponse({'detail':'Configure Google model access and a private access code on the server'},503)
            bearer=bearer_authorized(request.headers.get('authorization',''))
            signing_in=(request.url.path=='/v1/session' and request.method=='POST') or (request.url.path=='/v1/auth/config' and request.method=='GET')
            if not signing_in and not (bearer or cookie_authorized(request)):
                return JSONResponse({'detail':('Sign in with Google to continue.' if config.public_demo else 'Connect with Google and your access code') if config.google_signin_required else 'Connect with a valid access code'},401)
            if request.method not in ('GET','HEAD') and not bearer and not same_origin(request):
                return JSONResponse({'detail':'Use this application from its own origin'},403)
            try: length=int(request.headers.get('content-length','0') or 0)
            except ValueError: return JSONResponse({'detail':'Invalid request size'},400)
            body_limit=300000 if request.url.path=='/v1/teach' else 40000
            if length>body_limit: return JSONResponse({'detail':'Request too large'},413)
            chunks=[];size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>body_limit: return JSONResponse({'detail':'Request too large'},413)
                chunks.append(chunk)
            request._body=b''.join(chunks)
        response=await next_handler(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cross-Origin-Opener-Policy']='same-origin-allow-popups'
        response.headers['Permissions-Policy']='microphone=(self), geolocation=(self), camera=()'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'; media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if config.google_signin_required:
            response.headers['Content-Security-Policy']=response.headers['Content-Security-Policy'].replace("script-src 'self'", "script-src 'self' https://accounts.google.com/gsi/client").replace("style-src 'self'", "style-src 'self' https://accounts.google.com/gsi/style").replace("connect-src 'self'", "connect-src 'self' https://accounts.google.com/gsi/")+"; frame-src https://accounts.google.com/gsi/"
        if config.google_signin_required and config.google_auth_provider=='firebase':
            response.headers['Content-Security-Policy']=response.headers['Content-Security-Policy'].replace("connect-src 'self'", "connect-src 'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://www.googleapis.com https://"+config.firebase_auth_domain).replace("frame-src https://accounts.google.com/gsi/", "frame-src https://accounts.google.com https://"+config.firebase_auth_domain)
        response.headers['Cache-Control']='no-store' if request.url.path.startswith(('/v1/','/health')) or request.url.path=='/' else 'no-cache'
        return response
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        # Framework validation errors otherwise echo invalid credential input values.
        if request.url.path=='/v1/session':return JSONResponse({'detail':'Check your connection method and credential.'},422)
        return await request_validation_exception_handler(request,exc)
    @app.get('/health')
    async def health(): return {'service':'LingoLive','configured':config.configured,'byok_available':config.byok_enabled,'version':'1.12'}
    @app.get('/v1/auth/config')
    async def auth_config(request: Request):
        ready=config.configured and (not config.google_signin_required or bool(config.google_client_id and (config.allowed_google_emails or config.public_demo)))
        if config.google_auth_provider=='firebase' and config.google_signin_required:ready=ready and bool(config.firebase_api_key and config.firebase_auth_domain)
        data={'google_required':config.google_signin_required,'google_client_id':config.google_client_id if config.google_signin_required else '',
              'access_code_available':ready,'api_key_available':config.byok_enabled,'public_demo':config.public_demo and ready,
              'daily_audio_seconds':config.public_audio_seconds_per_day if config.public_demo else None,
              'daily_lessons':config.public_model_calls_per_day//(2 if config.lesson_strategy=='parallel' else 1) if config.public_demo else None,
              'quota_timezone':'Asia/Kolkata' if config.public_demo else None,
              'google_provider':config.google_auth_provider,
              'firebase':{'apiKey':config.firebase_api_key,'projectId':config.project,'authDomain':config.firebase_auth_domain} if ready and config.google_auth_provider=='firebase' else None}
        response=JSONResponse(data)
        if config.google_signin_required and ready:
            nonce=str(int(time.time()))+'.'+secrets.token_hex(16)
            response=JSONResponse(dict(data,nonce=nonce))
            response.set_cookie(GOOGLE_NONCE_COOKIE,nonce+'.'+signed_session('google-nonce:'+nonce),max_age=600,httponly=True,
                secure=request.url.hostname not in ('127.0.0.1','localhost','testserver'),samesite='strict',path='/v1')
        return response
    @app.post('/v1/session')
    async def signin(value: SessionRequest, request: Request):
        if not signins.allow(): raise HTTPException(429,'Too many connection attempts; try again in a minute')
        if value.mode=='public':
            if not config.public_demo:raise HTTPException(403,'Public demo access is disabled.')
            if value.token or value.api_key:raise HTTPException(422,'The demo needs no access code.')
            if not config.google_signin_required:
                if personal_session(request):forget_key(request.cookies[COOKIE].split('.')[1])
                return session_response(request,str(int(time.time()))+'.'+secrets.token_hex(16),'public')
        if value.mode=='api_key':
            if not config.byok_enabled:raise HTTPException(403,'Personal API keys are disabled by the host.')
            if value.token or value.google_credential or not re.fullmatch(r'[A-Za-z0-9_.-]{20,256}',value.api_key):
                raise HTTPException(422,'Enter a Google AI Studio API key, without an access code.')
            prune_keys()
            old=personal_session(request)
            if len(key_sessions)>=64 and old is None:raise HTTPException(429,'Too many key sessions; try again later.')
            if old:forget_key(request.cookies[COOKIE].split('.')[1])
            personal=replace(config,api_key=value.api_key,access_token='',provider='gemini',project='',google_signin_required=False)
            nonce=secrets.token_hex(16);payload=str(int(time.time()))+'.'+nonce+'.key'
            entry=KeySession(key_provider_factory(personal),personal,time.time()+SESSION_SECONDS,asyncio.Event())
            key_sessions[nonce]=entry
            entry.timer=asyncio.get_running_loop().call_later(SESSION_SECONDS,forget_key,nonce)
            return session_response(request,payload,'api_key')
        if value.api_key:raise HTTPException(422,'Select Use my Google API key to connect with a key.')
        if not (config.public_demo and value.mode=='public') and not authorized('Bearer '+value.token): raise HTTPException(401,'That access code was not recognized')
        identity=''
        if config.google_signin_required:
            if not config.google_client_id or (not config.allowed_google_emails and not config.public_demo):
                raise HTTPException(503,'Google sign-in setup is not complete.')
            try:
                issued,nonce,signature=request.cookies.get(GOOGLE_NONCE_COOKIE,'').split('.')
                challenge=issued+'.'+nonce
                if not (0<=time.time()-int(issued)<600 and len(nonce)==32 and hmac.compare_digest(signature,signed_session('google-nonce:'+challenge))):raise ValueError()
            except (ValueError,TypeError):raise HTTPException(401,'Open Connect and sign in with Google again.') from None
            if not value.google_credential:raise HTTPException(401,'Sign in with Google before connecting.')
            claims=await identity_verifier.verify(value.google_credential,config.project if config.google_auth_provider=='firebase' else config.google_client_id)
            valid_challenge=(value.google_nonce==challenge and claims.get('iss')=='https://securetoken.google.com/'+config.project and claims.get('firebase',{}).get('sign_in_provider')=='google.com') if config.google_auth_provider=='firebase' else claims.get('nonce')==challenge
            if not valid_challenge or claims.get('email_verified') is not True or not isinstance(claims.get('sub'),str) or not 1<=len(claims['sub'])<=255:
                raise HTTPException(401,'Google account verification failed. Please sign in again.')
            if not isinstance(claims.get('email'),str) or not claims['email']:raise HTTPException(401,'Google account verification failed.')
            email=claims['email'].casefold()
            if config.allowed_google_emails and email not in config.allowed_google_emails:raise HTTPException(403,'This Google account has not been invited. Ask the host for access.')
            now=time.time()
            for old in list(used_nonces):
                if now-used_nonces[old]>=600:del used_nonces[old]
            if challenge in used_nonces:raise HTTPException(401,'This sign-in has already been used. Open Connect to sign in again.')
            used_nonces[challenge]=now
            identity=base64.urlsafe_b64encode(json.dumps({'sub':claims['sub'],'email':email},separators=(',',':')).encode()).decode().rstrip('=')
        payload=str(int(time.time()))+'.'+secrets.token_hex(16)+(('.'+identity) if identity else '')
        if personal_session(request):forget_key(request.cookies[COOKIE].split('.')[1])
        return session_response(request,payload,'public' if value.mode=='public' else 'access_code')
    def session_response(request,payload,mode):
        response=JSONResponse({'connected':True,'mode':mode})
        response.delete_cookie(GOOGLE_NONCE_COOKIE,path='/v1')
        response.set_cookie(COOKIE,payload+'.'+signed_session(payload),max_age=SESSION_SECONDS,httponly=True,
            secure=request.url.hostname not in ('127.0.0.1','localhost','testserver'),samesite='strict',path='/v1')
        return response
    @app.get('/v1/session')
    async def session_status(request: Request): return {'connected':True,'mode':'api_key' if personal_session(request) else 'public' if config.public_demo else 'access_code'}
    @app.delete('/v1/session')
    async def signout(request: Request):
        if personal_session(request):forget_key(request.cookies[COOKIE].split('.')[1])
        response=Response(status_code=204);response.delete_cookie(COOKIE,path='/v1');return response
    @app.post('/v1/teach')
    async def teach(value: TeachRequest,request: Request):
        selected,selected_config,key_entry=selection(request)
        call_units=2 if selected_config.lesson_strategy=='parallel' else 1
        rate=key_lessons if key_entry else lessons
        budget=key_lesson_budget if key_entry else lesson_budget
        if not config.ai_enabled: raise HTTPException(503,'AI is paused by the host. Your saved lessons remain available.')
        if not rate.allow(call_units): raise HTTPException(429,'Lesson limit reached; retry your saved transcript shortly',headers={'Retry-After':'15'})
        try: await asyncio.wait_for(lesson_slots.acquire(),timeout=1)
        except asyncio.TimeoutError: raise HTTPException(429,'Two lessons are being prepared; retry shortly',headers={'Retry-After':'5'}) from None
        try:
            if budget.reserve(call_units) is None:
                raise HTTPException(429,'The demo lesson allowance has been reached. Saved lessons remain available.',headers={'Retry-After':'3600'})
            if key_entry and (key_entry.revoked.is_set() or key_entry.expires_at<=time.time()):raise HTTPException(401,'Reconnect with your Google API key.')
            if daily_quota and not await daily_quota.reserve_calls(call_units,config.public_model_calls_per_day):
                raise HTTPException(429,'Today’s shared demo lesson allowance is used up. It resets at midnight IST; Saved still works.',headers={'Retry-After':str(max(1,quota_day()[1]))})
            result=await selected.teach(value)
        finally: lesson_slots.release()
        try:return validate_lesson(result,value.text)
        except ValueError:raise HTTPException(502,'The lesson omitted or changed words; retry your saved transcript') from None
    @app.websocket('/v1/listen')
    async def listen(client: WebSocket):
        if not (bearer_authorized(client.headers.get('authorization','')) or (same_origin(client) and cookie_authorized(client))): await client.close(code=4401);return
        try:selected,selected_config,key_entry=selection(client)
        except HTTPException:await client.close(code=4401);return
        budget=key_audio_budget if key_entry else audio_budget
        if not config.ai_enabled: await client.close(code=4403);return
        if not sessions.allow(): await client.close(code=4429);return
        await client.accept()
        acquired=False; connected=False; reservation=None; durable_reservation=None; upstream_started=None
        try:
            await asyncio.wait_for(connections.acquire(),timeout=1);connected=True
            await asyncio.wait_for(live_slots.acquire(),timeout=1);acquired=True
            first=await asyncio.wait_for(client.receive_text(),timeout=10)
            if len(first)>8192 or not isinstance(json.loads(first).get('setup'),dict): raise ValueError('Expected setup')
            # Reserve the maximum billed connection duration before contacting Google.
            if daily_quota:
                durable_reservation=await daily_quota.reserve_audio(600,config.public_audio_seconds_per_day)
                reserved_seconds=durable_reservation.seconds if durable_reservation else 0
            else:
                reservation=budget.reserve(600);reserved_seconds=600 if reservation is not None else 0
            if not reserved_seconds:
                await client.send_json({'error':{'message':'Today’s shared listening allowance is used up. It resets at midnight IST; Saved still works.'}})
                return
            upstream_started=time.monotonic()
            duration=min(590,reserved_seconds-10)
            if durable_reservation:
                day,boundary=quota_day()
                if day!=durable_reservation.day:return
                duration=min(duration,boundary-10)
            if key_entry:duration=min(duration,max(0,key_entry.expires_at-time.time()))
            if duration<=0 or (key_entry and key_entry.revoked.is_set()):return
            async with asyncio.timeout(duration), selected.live() as upstream:
                # The server controls model and capabilities, irrespective of client input.
                await upstream.send(json.dumps(setup_message(selected_config.transcribe_model,selected_config.project if selected_config.provider=='vertex' else None,selected_config.location)))
                async def to_google():
                    nonlocal acquired
                    pace=AudioPace()
                    while True:
                        raw=await asyncio.wait_for(client.receive_text(),timeout=20)
                        if len(raw)>12000: raise ValueError('Audio frame too large')
                        value=json.loads(raw);size=validate_audio(value);pace.accept(size)
                        await upstream.send(json.dumps(value))
                        if not size:
                            # Free an active slot for renewal, retaining at most two short
                            # draining connections to deliver final transcriptions.
                            live_slots.release();acquired=False
                            await asyncio.sleep(5)
                            return
                async def to_phone():
                    async for raw in upstream:
                        if isinstance(raw,bytes):raw=raw.decode()
                        value=json.loads(raw)
                        if 'error' in value:raw=json.dumps({'error':{'message':'Google transcription is unavailable; check server model access'}})
                        await client.send_text(raw)
                tasks=[asyncio.create_task(to_google()),asyncio.create_task(to_phone())]
                if key_entry:tasks.append(asyncio.create_task(key_entry.revoked.wait()))
                try:
                    done,_=await asyncio.wait(tasks,timeout=590,return_when=asyncio.FIRST_COMPLETED)
                    for task in done:task.result()
                finally:
                    for task in tasks:task.cancel()
                    await asyncio.gather(*tasks,return_exceptions=True)
        except WebSocketDisconnect:pass
        except HTTPException as error:
            try:await client.send_json({'error':{'message':error.detail}})
            except Exception:pass
        except (ValueError,binascii.Error):
            try:await client.close(code=1008,reason='Invalid transcription input')
            except RuntimeError:pass
        except Exception:
            try:await client.send_json({'error':{'message':'Google transcription disconnected; reconnect to continue'}})
            except Exception:pass
        finally:
            if durable_reservation is not None:
                try:await daily_quota.settle_audio(durable_reservation,0 if upstream_started is None else time.monotonic()-upstream_started)
                except HTTPException:pass # keep the full reservation spent if storage fails
            if reservation is not None:
                budget.settle(reservation,0 if upstream_started is None else time.monotonic()-upstream_started)
            if acquired:live_slots.release()
            if connected:connections.release()
            try:await client.close()
            except Exception:pass
    @app.get('/',include_in_schema=False)
    async def index(): return FileResponse(WEB/'index.html')
    @app.get('/sw.js',include_in_schema=False)
    async def service_worker(): return FileResponse(WEB/'sw.js',media_type='application/javascript',headers={'Cache-Control':'no-cache'})
    app.mount('/assets',StaticFiles(directory=WEB),name='web')
    return app

app=create_app()

"""Local-only browser test fixture; never included in the Cloud Run image."""
import asyncio,base64,copy,json
from contextlib import asynccontextmanager
from pathlib import Path
from backend.app import Config,create_app
EXAMPLE=json.loads((Path(__file__).resolve().parents[1]/'web/example.json').read_text())
class FixtureSocket:
    def __init__(self,provider):self.provider=provider;self.queue=asyncio.Queue();self.frames=0
    async def send(self,raw):
        value=json.loads(raw)
        if 'setup' in value:
            self.provider.setups.append(value);await self.queue.put(json.dumps({'setupComplete':{}}));return
        audio=value['realtimeInput']
        if audio.get('audioStreamEnd'):
            await self.queue.put(json.dumps({'serverContent':{'inputTranscription':{'text':'Thank you.'}}}));return
        pcm=base64.b64decode(audio['audio']['data']);self.provider.frames+=1;self.provider.bytes+=len(pcm);self.frames+=1
        if self.frames==2:await self.queue.put(json.dumps({'serverContent':{'interimInputTranscription':{'text':'コーヒー…'}}}))
        if self.frames==5:await self.queue.put(json.dumps({'serverContent':{'inputTranscription':{'text':getattr(self.provider,'next_text',EXAMPLE['text'])}}}))
    def __aiter__(self):return self
    async def __anext__(self):return await self.queue.get()
class Provider:
    def __init__(self):self.requests=[];self.setups=[];self.frames=0;self.bytes=0
    async def teach(self,value):
        self.requests.append(value.model_dump())
        if value.text in ('I need a cab to the railway station.','Please stop for tea first.') or value.assistance_mode=='say_this' and value.text.isascii() and value.text not in ('Every weekday I take the metro from Indiranagar.','I am at my usual tea stall. I order ginger tea here.'):
            target=[('ನನಗೆ','nanage','for me'),('ರೈಲ್ವೇ','railve','railway'),('ನಿಲ್ದಾಣಕ್ಕೆ','nildanakke','to station'),('ಹೋಗಬೇಕು','hogabeku','need to go')]
            if 'tea' in value.text:target=[('ಮೊದಲು','modalu','first'),('ಚಹಾಕ್ಕೆ','chahakke','for tea'),('ನಿಲ್ಲಿಸಿ','nillisi','please stop')]
            def words():
                result=[]
                for index,(text,reading,meaning) in enumerate(target):
                    if index:result.append({'text':' ','reading':' ','meaning':'','note':'','is_word':False})
                    result.append({'text':text,'reading':reading,'meaning':meaning,'note':'','is_word':True})
                return result
            return {'detected_language':'en-US','contains_learning_language':False,'reply_mode':'express','translation':'','explanation':'Say your intention in the learning language.','tip':'','words':[],'replies':[{'label':label,'translation':value.text,'words':words()} for label in ('Simple','Polite','Another way')],'current_speaker':'user' if value.current_speaker_hint=='user' else 'unknown','speaker_confidence':'high' if value.current_speaker_hint=='user' else 'low'}
        if value.text=='I am at my usual tea stall. I order ginger tea here.':
            return {'detected_language':'en-US','contains_learning_language':False,'translation':'','explanation':'Your tea order is saved for later review.','tip':'','words':[],'replies':[],'current_speaker':'user','speaker_confidence':'high','place_candidates':[{'label':'Tea stall','fact':'Usually orders ginger tea here','evidence':'I order ginger tea here.'}] if value.learn_place_memory else []}
        if value.text=='Every weekday I take the metro from Indiranagar.':
            return {'detected_language':'en-US','contains_learning_language':False,'translation':'','explanation':'Your commute is part of the conversation.','tip':'','words':[],'replies':[],'current_speaker':'user','speaker_confidence':'high','memory_candidates':[{'kind':'activity','topic':'commute','text':'Usually takes the metro from Indiranagar','evidence':'Every weekday I take the metro from Indiranagar.','setting':'travelling','duration':'routine'}] if value.learn_personal_memory else []}
        if value.text=='I want to catch my train.':
            return {'detected_language':'en-US','contains_learning_language':False,'translation':'','explanation':'The learner is talking about travel.','tip':'','words':[],'replies':[],'context_summary':'The learner may want to catch a train.','current_speaker':'user','speaker_confidence':'medium','inferred_user_intent':'Get to the train station.'}
        if value.text!=EXAMPLE['text']:
            return {'detected_language':'en-US','contains_learning_language':False,'translation':'','explanation':'This phrase is English, not the selected learning language.','tip':'','words':[],'replies':[],'context_summary':('A cafe conversation. '+value.user_goal)[:600]}
        result=copy.deepcopy(EXAMPLE['lesson']);result['context_summary']=('A cafe conversation. '+value.user_goal)[:600];return result
    @asynccontextmanager
    async def live(self):yield FixtureSocket(self)
provider=Provider()
personal_providers=[]
def personal_provider(config):
    value=Provider();personal_providers.append(value);return value
app=create_app(Config('test-only-google-key','test-only-browser-access-code-32-characters'),provider,key_provider_factory=personal_provider)
@app.get('/fixture/status')
async def status():return {'requests':provider.requests,'frames':provider.frames,'bytes':provider.bytes,'setups':provider.setups,'personal':[{'requests':p.requests,'frames':p.frames,'bytes':p.bytes,'setups':p.setups} for p in personal_providers]}
@app.post('/fixture/speech')
async def next_speech():provider.next_text='I need a cab to the railway station.';return {'fixture':True}

"""Single Google request, compact output, and complete pronunciation contract."""
import copy,json,unittest
from unittest.mock import AsyncMock,patch
import httpx
from fastapi import HTTPException
from backend.app import Config,GoogleProvider,TeachRequest,expand_model_lesson,validate_lesson
from test_app import EXAMPLE,INPUT,TOKEN

def compact(lesson):
    lesson=copy.deepcopy(lesson)
    def words(items):
        return [dict(t=w['text'],r=w['reading'],m=w['meaning'],n=w['note']) if w['is_word'] else {'t':w['text']} for w in items]
    lesson['words']=words(lesson['words'])
    for reply in lesson['replies']:reply['words']=words(reply['words'])
    return lesson

class FastLessonTests(unittest.IsolatedAsyncioTestCase):
    async def test_both_providers_make_one_call_for_translation_replies_and_all_readings(self):
        original=httpx.AsyncClient
        for provider in ('gemini','vertex'):
            with self.subTest(provider=provider):
                received=[]
                def handler(request):
                    received.append(request);body=json.loads(request.content)
                    self.assertIn('/gemini-3.8-flash:generateContent',str(request.url))
                    generation=body['generationConfig']
                    self.assertEqual({'thinkingLevel':'low'},generation['thinkingConfig'])
                    self.assertEqual(4096,generation['maxOutputTokens'])
                    self.assertEqual({'t','r','m','n'},set(generation['responseJsonSchema']['$defs']['word']['properties']))
                    self.assertIn('recent_turns',json.loads(body['contents'][0]['parts'][0]['text']))
                    return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(compact(EXAMPLE['lesson']))}]}}]})
                def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
                model=GoogleProvider(Config('test-only-personal-api-key',TOKEN,provider=provider,project='locateassist'))
                with patch.object(model,'_vertex_token',new=AsyncMock(return_value='test-only-oauth')),patch('backend.app.httpx.AsyncClient',side_effect=client):
                    lesson=await model.teach(TeachRequest.model_validate({**INPUT,'recent_turns':[{'speaker':'user','text':'I would like a coffee.'}]}))
                self.assertEqual(1,len(received));self.assertEqual(EXAMPLE['lesson'],lesson)
                self.assertEqual(3,len(lesson['replies']))
                for group in [lesson['words']]+[r['words'] for r in lesson['replies']]:
                    self.assertTrue(all(w['reading'] and w['meaning'] for w in group if w['is_word']))

    async def test_incomplete_output_does_not_silently_retry_or_make_a_second_paid_call(self):
        original=httpx.AsyncClient;calls=[]
        def handler(request):
            calls.append(request)
            return httpx.Response(200,json={'candidates':[{'finishReason':'MAX_TOKENS'}]})
        def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
        with patch('backend.app.httpx.AsyncClient',side_effect=client):
            with self.assertRaises(HTTPException):await GoogleProvider(Config('test-only-api-key',TOKEN)).teach(TeachRequest.model_validate(INPUT))
        self.assertEqual(1,len(calls))

    def test_compact_words_cannot_omit_definition_or_change_source(self):
        for field in ('r','m'):
            value=compact(EXAMPLE['lesson']);del value['words'][0][field]
            with self.assertRaises(ValueError):validate_lesson(expand_model_lesson(value),EXAMPLE['text'])
        value=compact(EXAMPLE['lesson']);value['words'][0]['t']='Changed'
        with self.assertRaises(ValueError):validate_lesson(expand_model_lesson(value),EXAMPLE['text'])
        with self.assertRaises(ValueError):expand_model_lesson({'words':[{'t':'word','m':12}],'replies':[]})
        for words in ('text',['t'],[None]):
            with self.assertRaises(ValueError):expand_model_lesson({'words':words,'replies':[]})

    def test_sparse_punctuation_and_optional_notes_expand_without_losing_exact_spacing(self):
        value=compact(EXAMPLE['lesson'])
        for group in [value['words']]+[r['words'] for r in value['replies']]:
            for w in group:w.pop('n',None)
        result=validate_lesson(expand_model_lesson(value),EXAMPLE['text'])
        self.assertEqual(EXAMPLE['text'],''.join(w['text'] for w in result['words']))
        self.assertTrue(all(w['note']=='' for w in result['words']))
        self.assertLess(len(json.dumps(value)),len(json.dumps(EXAMPLE['lesson'])))

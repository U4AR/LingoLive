"""One Google request, bounded readings and complete translation/reply coverage."""
import copy,json,unittest
from unittest.mock import AsyncMock,patch
import httpx
from fastapi import HTTPException
from backend.app import Config,GoogleProvider,TeachRequest,normalize_model_lesson,validate_lesson
from test_app import EXAMPLE,INPUT,TOKEN

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
                    word=generation['responseJsonSchema']['$defs']['word']
                    self.assertEqual({'text','reading','meaning','note','is_word'},set(word['required']))
                    self.assertEqual(80,word['properties']['reading']['maxLength'])
                    self.assertIn('recent_turns',json.loads(body['contents'][0]['parts'][0]['text']))
                    return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(EXAMPLE['lesson'])}]}}]})
                def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
                model=GoogleProvider(Config('test-only-personal-api-key',TOKEN,provider=provider,project='locateassist'))
                with patch.object(model,'_vertex_token',new=AsyncMock(return_value='test-only-oauth')),patch('backend.app.httpx.AsyncClient',side_effect=client):
                    lesson=await model.teach(TeachRequest.model_validate({**INPUT,'recent_turns':[{'speaker':'user','text':'I would like a coffee.'}]}))
                self.assertEqual(1,len(received));self.assertEqual(EXAMPLE['lesson'],lesson)
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

    def test_words_cannot_omit_definitions_change_source_or_contain_runaway_readings(self):
        for field in ('reading','meaning'):
            value=copy.deepcopy(EXAMPLE['lesson']);del value['words'][0][field]
            with self.assertRaises(ValueError):validate_lesson(normalize_model_lesson(value),EXAMPLE['text'])
        value=copy.deepcopy(EXAMPLE['lesson']);value['words'][0]['text']='Changed'
        with self.assertRaises(ValueError):validate_lesson(normalize_model_lesson(value),EXAMPLE['text'])
        value=copy.deepcopy(EXAMPLE['lesson']);value['words'][0]['reading']='repeated '*100
        with self.assertRaises(ValueError):normalize_model_lesson(value)
        for words in ('text',['text'],[None]):
            with self.assertRaises(ValueError):normalize_model_lesson({'words':words,'replies':[]})

    def test_spacing_and_empty_optional_detail_survive_normalization(self):
        value=copy.deepcopy(EXAMPLE['lesson'])
        for group in [value['words']]+[r['words'] for r in value['replies']]:
            for w in group:w['note']=''
        result=validate_lesson(normalize_model_lesson(value),EXAMPLE['text'])
        self.assertEqual(value,result)
        self.assertEqual(EXAMPLE['text'],''.join(w['text'] for w in result['words']))

    def test_latin_words_and_numbers_reuse_original_script_without_model_spellings(self):
        words=[{'text':t,'reading':'unneeded alternative','meaning':'example','note':'','is_word':True} for t in ('Hello','école','16')]
        result=normalize_model_lesson({'words':words,'replies':[]})
        self.assertEqual(['Hello','école','16'],[w['reading'] for w in result['words']])
        self.assertEqual('unneeded alternative',words[0]['reading'])

    def test_non_latin_words_still_require_a_generated_reading(self):
        from backend.app import Word
        for text in ('你好','Привет','ありがとう'):
            value=normalize_model_lesson({'words':[{'text':text,'reading':'','meaning':'greeting','note':'','is_word':True}],'replies':[]})
            with self.assertRaises(ValueError):Word.model_validate(value['words'][0])

import copy,json,unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from backend.app import Config,GoogleProvider,TeachRequest,create_app,validate_lesson,INSTRUCTIONS
from test_app import AUTH,CONFIG,EXAMPLE,INPUT,FakeProvider

CONTEXT={'user_goal':'Order vegetarian takeaway.','conversation_summary':'A worker is taking a food order.','recent_turns':[{'speaker':'user','text':'I want a vegetarian lunch.'},{'speaker':'unattributed','text':'こちらでお召し上がりですか？'}]}
class ContextApiTests(unittest.TestCase):
    def test_goal_and_chronological_roles_reach_the_lesson_provider(self):
        provider=FakeProvider();client=TestClient(create_app(CONFIG,provider))
        response=client.post('/v1/teach',json={**INPUT,**CONTEXT},headers=AUTH)
        self.assertEqual(200,response.status_code)
        for key,value in CONTEXT.items():self.assertEqual(value,provider.requests[0][key])
    def test_oversized_or_untyped_context_is_rejected_without_paid_calls(self):
        provider=FakeProvider();client=TestClient(create_app(CONFIG,provider))
        for fields in [{'user_goal':'x'*601},{'conversation_summary':'x'*601},{'recent_turns':[{'speaker':'user','text':'x'*401}]},{'recent_turns':[{'speaker':'user','text':'ok'}]*9},{'recent_turns':[{'speaker':'assistant','text':'proposed reply'}]},{'recent_turns':[{'text':'Missing speaker'}]},{'user_goal':{'injection':'not a string'}}]:
            self.assertEqual(422,client.post('/v1/teach',json={**INPUT,**fields},headers=AUTH).status_code)
        self.assertEqual([],provider.requests)
    def test_old_clients_can_still_request_lessons_without_context_fields(self):
        provider=FakeProvider();client=TestClient(create_app(CONFIG,provider))
        self.assertEqual(200,client.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
        self.assertEqual(INPUT,provider.requests[0])
    def test_summary_may_be_returned_when_current_text_is_not_the_learning_language(self):
        response={'detected_language':'en-US','contains_learning_language':False,'translation':'','explanation':'This is English.','tip':'','words':[],'replies':[],'context_summary':'The learner explicitly wants vegetarian takeaway.'}
        self.assertEqual(response,validate_lesson(response,'I want takeaway.'))
    def test_summary_limits_and_exact_current_source_coverage_still_apply(self):
        response=copy.deepcopy(EXAMPLE['lesson']);response['context_summary']='x'*601
        with self.assertRaises(ValueError):validate_lesson(response,EXAMPLE['text'])
        response['context_summary']='At a cafe.';response['words'][0]['text']='history instead'
        with self.assertRaises(ValueError):validate_lesson(response,EXAMPLE['text'])
    def test_context_does_not_bypass_authentication_or_change_the_output_cap(self):
        provider=FakeProvider();client=TestClient(create_app(CONFIG,provider))
        self.assertEqual(401,client.post('/v1/teach',json={**INPUT,**CONTEXT}).status_code)
        self.assertEqual([],provider.requests);self.assertEqual(4096,CONFIG.max_output_tokens)

class ContextProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_google_request_contains_context_in_user_data_with_system_boundaries(self):
        original=httpx.AsyncClient;seen=[];response=copy.deepcopy(EXAMPLE['lesson']);response['context_summary']='At a cafe; learner explicitly wants vegetarian takeaway.'
        def handler(request):
            body=json.loads(request.content);seen.append(body)
            data=json.loads(body['contents'][0]['parts'][0]['text'])
            for key,value in CONTEXT.items():self.assertEqual(value,data[key])
            self.assertEqual(INPUT['text'],data['text'])
            self.assertIn('untrusted',body['systemInstruction']['parts'][0]['text'])
            self.assertIn('context_summary',body['generationConfig']['responseJsonSchema']['required'])
            self.assertEqual(4096,body['generationConfig']['maxOutputTokens'])
            return httpx.Response(200,json={'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(response)}]}}]})
        def client(**kwargs):return original(transport=httpx.MockTransport(handler),**kwargs)
        with patch('backend.app.httpx.AsyncClient',side_effect=client):
            result=await GoogleProvider(CONFIG).teach(TeachRequest.model_validate({**INPUT,**CONTEXT}))
        self.assertEqual(response,result);self.assertEqual(1,len(seen))

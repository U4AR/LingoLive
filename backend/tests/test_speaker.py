import copy,unittest
from fastapi.testclient import TestClient
from backend.app import TeachRequest,create_app,validate_lesson
from test_app import AUTH,CONFIG,EXAMPLE,INPUT,FakeProvider
class SpeakerTests(unittest.TestCase):
 def test_likely_speakers_and_confirmed_speakers_remain_distinct(self):
  provider=FakeProvider();c=TestClient(create_app(CONFIG,provider))
  turns=[{'speaker':'likely_user','text':'Maybe the learner spoke'},{'speaker':'likely_other','text':'Maybe another person'},{'speaker':'user','text':'Confirmed user statement'}]
  self.assertEqual(200,c.post('/v1/teach',json={**INPUT,'recent_turns':turns,'inferred_user_goal':'A tentative plan'},headers=AUTH).status_code)
  self.assertEqual(turns,provider.requests[0]['recent_turns']);self.assertEqual('A tentative plan',provider.requests[0]['inferred_user_goal'])
 def test_speaker_and_intent_outputs_are_bounded_and_validated(self):
  for values in [{'current_speaker':'a-known-person'},{'speaker_confidence':'certain'},{'inferred_user_intent':'x'*301}]:
   with self.assertRaises(ValueError):validate_lesson({**copy.deepcopy(EXAMPLE['lesson']),**values},EXAMPLE['text'])
 def test_confirmed_hint_and_explicit_goal_do_not_overwrite_the_inferred_goal_field(self):
  request=TeachRequest.model_validate({**INPUT,'current_speaker_hint':'user','user_goal':'New explicit goal','inferred_user_goal':'Older guess'})
  self.assertEqual('New explicit goal',request.user_goal);self.assertEqual('Older guess',request.inferred_user_goal)

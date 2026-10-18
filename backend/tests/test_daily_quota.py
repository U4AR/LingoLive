"""Atomic quota reservations, restart survival, failure closure and IST boundaries."""
import asyncio,copy,json,unittest
from unittest.mock import patch
import httpx
from urllib.parse import unquote
from fastapi import HTTPException
from backend.daily_quota import GCSQuota,quota_day
class Storage:
 def __init__(self):self.docs={};self.reads=0;self.writes=0;self.conflicts=0;self.fail=False
 async def handle(self,r):
  if self.fail:return httpx.Response(503)
  if r.method=='GET':
   self.reads+=1;name=unquote(r.url.path.split('/o/')[1])
   doc=copy.deepcopy(self.docs.get(name));await asyncio.sleep(0)
   return httpx.Response(200,headers={'x-goog-generation':str(doc[0])},json=doc[1]) if doc else httpx.Response(404)
  name=r.url.params['name'];old=self.docs.get(name);generation=old[0] if old else 0
  if str(generation)!=r.url.params['ifGenerationMatch']:
   self.conflicts+=1;return httpx.Response(412)
  self.writes+=1;data=json.loads(r.content);self.docs[name]=(generation+1,data);return httpx.Response(200,json={'generation':str(generation+1)})
 def value(self):return next(iter(self.docs.values()))[1]
async def token():return 'synthetic-quota-oauth-for-fixtures'
def store(storage):return GCSQuota('test-private-quota',token,httpx.AsyncClient(transport=httpx.MockTransport(storage.handle)))
class QuotaTests(unittest.IsolatedAsyncioTestCase):
 async def test_atomic_limit_across_two_independent_instances_and_conflict_retries(self):
  storage=Storage();a,b=store(storage),store(storage)
  for _ in range(5):
   results=await asyncio.gather(a.reserve_calls(2,10),b.reserve_calls(2,10))
  self.assertEqual(10,storage.value()['model_calls']);self.assertGreater(storage.conflicts,0)
  self.assertFalse(await store(storage).reserve_calls(2,10))
 async def test_restart_and_session_rotation_cannot_reset_spent_allowance(self):
  storage=Storage();a=store(storage);self.assertTrue(await a.reserve_calls(2,2));await a.aclose()
  self.assertFalse(await store(storage).reserve_calls(1,2))
 async def test_full_reservations_prevent_concurrent_audio_overspend(self):
  storage=Storage();a,b=store(storage),store(storage)
  first,second=await asyncio.gather(a.reserve_audio(600,1200),b.reserve_audio(600,1200))
  self.assertEqual((600,600),(first.seconds,second.seconds));self.assertIsNone(await store(storage).reserve_audio(600,1200))
  await a.settle_audio(first,300.2);self.assertEqual(901,storage.value()['audio_seconds'])
  await a.settle_audio(first,0);self.assertEqual(901,storage.value()['audio_seconds'])
  remainder=await b.reserve_audio(600,1200);self.assertEqual(299,remainder.seconds)
 async def test_crash_keeps_reservation_spent_and_does_not_make_free_minutes(self):
  storage=Storage();await store(storage).reserve_audio(600,600)
  self.assertIsNone(await store(storage).reserve_audio(600,600))
 async def test_storage_outage_fails_closed_instead_of_local_fallback(self):
  storage=Storage();storage.fail=True
  with self.assertRaises(HTTPException) as error:await store(storage).reserve_calls(1,2)
  self.assertEqual(503,error.exception.status_code)
 async def test_corrupt_counter_fails_closed(self):
  storage=Storage();a=store(storage);await a.reserve_calls(1,2);storage.value()['model_calls']=-5
  with self.assertRaises(HTTPException):await a.reserve_calls(1,2)
 async def test_day_reset_is_ist_and_new_day_has_its_own_object(self):
  with patch('backend.daily_quota.time.time',return_value=1792348199):
   day,left=quota_day();self.assertEqual('2026-10-18',day);self.assertEqual(1,left)
  with patch('backend.daily_quota.time.time',return_value=1792348200):self.assertEqual('2026-10-19',quota_day()[0])
  storage=Storage();a=store(storage)
  with patch('backend.daily_quota.quota_day',return_value=('2026-10-18',100)):self.assertTrue(await a.reserve_calls(2,2))
  with patch('backend.daily_quota.quota_day',return_value=('2026-10-19',86400)):self.assertTrue(await a.reserve_calls(2,2))
  self.assertEqual(2,len(storage.docs))
 async def test_audio_reservation_never_spends_tomorrows_time(self):
  storage=Storage();a=store(storage)
  with patch('backend.daily_quota.quota_day',return_value=('2026-10-18',45)):
   r=await a.reserve_audio(600,1200);self.assertEqual(45,r.seconds)
  with patch('backend.daily_quota.quota_day',return_value=('2026-10-18',9)):self.assertIsNone(await a.reserve_audio(600,1200))
 async def test_store_contains_counters_and_reservations_without_user_data(self):
  storage=Storage();a=store(storage);await a.reserve_audio(600,1200);await a.reserve_calls(2,200)
  self.assertEqual({'schema','day','audio_seconds','model_calls','reservations'},set(storage.value()))
if __name__=='__main__':unittest.main()

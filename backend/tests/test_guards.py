import base64, unittest
from dataclasses import replace
from unittest.mock import patch
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from backend.app import AudioPace, Budget, Config, create_app
from test_app import AUTH, CONFIG, INPUT, FakeProvider

class GuardTests(unittest.TestCase):
    def test_usage_budget_blocks_before_another_google_call(self):
        provider=FakeProvider()
        with TestClient(create_app(replace(CONFIG,lessons_per_hour=1,lessons_per_day=2),provider)) as c:
            self.assertEqual(200,c.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
            self.assertEqual(429,c.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
            self.assertEqual(1,len(provider.requests))
    def test_emergency_pause_blocks_both_paid_routes(self):
        provider=FakeProvider()
        with TestClient(create_app(replace(CONFIG,ai_enabled=False),provider)) as c:
            self.assertEqual(503,c.post('/v1/teach',json=INPUT,headers=AUTH).status_code)
            with self.assertRaises(WebSocketDisconnect):
                with c.websocket_connect('/v1/listen',headers=AUTH):pass
            self.assertEqual([],provider.requests);self.assertIsNone(provider.socket)
    def test_audio_budget_blocks_before_opening_google(self):
        provider=FakeProvider()
        with TestClient(create_app(replace(CONFIG,audio_seconds_per_day=599),provider)) as c:
            with c.websocket_connect('/v1/listen',headers=AUTH) as ws:
                ws.send_json({'setup':{}})
                self.assertIn('allowance',ws.receive_json()['error']['message'])
            self.assertIsNone(provider.socket)
    def test_fast_audio_is_rejected_before_forwarding_excess(self):
        provider=FakeProvider()
        frame={'realtimeInput':{'audio':{'mimeType':'audio/pcm;rate=16000','data':base64.b64encode(bytes(6400)).decode()}}}
        with TestClient(create_app(CONFIG,provider)) as c:
            with c.websocket_connect('/v1/listen',headers=AUTH) as ws:
                ws.send_json({'setup':{}});ws.receive_json()
                for _ in range(25):
                    ws.send_json(frame);ws.receive_json()
                ws.send_json(frame)
                with self.assertRaises(WebSocketDisconnect) as error:ws.receive_json()
                self.assertEqual(1008,error.exception.code)
                self.assertEqual(26,len(provider.socket.sent)) # setup + five seconds only
    def test_two_listeners_can_renew_without_losing_the_final_transcript(self):
        provider=FakeProvider()
        with TestClient(create_app(CONFIG,provider)) as c:
            with c.websocket_connect('/v1/listen',headers=AUTH) as first, c.websocket_connect('/v1/listen',headers=AUTH) as second:
                first.send_json({'setup':{}});first.receive_json()
                second.send_json({'setup':{}});second.receive_json()
                first.send_json({'realtimeInput':{'audioStreamEnd':True}})
                self.assertIn('inputTranscription',first.receive_json()['serverContent'])
                with c.websocket_connect('/v1/listen',headers=AUTH) as renewed:
                    renewed.send_json({'setup':{}});self.assertIn('setupComplete',renewed.receive_json())
                    with c.websocket_connect('/v1/listen',headers=AUTH) as extra:
                        extra.send_json({'setup':{}})
                        self.assertIn('error',extra.receive_json())
    def test_rolling_daily_limit_survives_hour_rollover(self):
        with patch('backend.app.time.monotonic',return_value=0) as clock:
            budget=Budget(2,3)
            self.assertIsNotNone(budget.reserve(2));self.assertIsNone(budget.reserve(1))
            clock.return_value=3601
            self.assertIsNotNone(budget.reserve(1));self.assertIsNone(budget.reserve(1))
            clock.return_value=86401
            self.assertIsNotNone(budget.reserve(2))
    def test_two_fifteen_minute_listeners_fit_with_renewal_reservations(self):
        with patch('backend.app.time.monotonic',return_value=0) as clock:
            budget=Budget(2400,3600)
            first=budget.reserve(600);second=budget.reserve(600)
            self.assertIsNotNone(first);self.assertIsNotNone(second)
            clock.return_value=570
            # Both renewals can start even while both old connections drain.
            renewed_first=budget.reserve(600);renewed_second=budget.reserve(600)
            self.assertIsNotNone(renewed_first);self.assertIsNotNone(renewed_second)
            budget.settle(first,575);budget.settle(second,575)
            clock.return_value=900
            budget.settle(renewed_first,330);budget.settle(renewed_second,330)
            self.assertEqual(1810,sum(e[1] for e in budget.entries))
    def test_pacing_allows_normal_pcm_for_fifteen_minutes_and_connection_buffer(self):
        with patch('backend.app.time.monotonic',return_value=0) as clock:
            pace=AudioPace()
            for tenth in range(9000):
                clock.return_value=tenth/10;pace.accept(3200)
            clock.return_value=900
            pace.accept(160000)
            with self.assertRaises(ValueError):pace.accept(6400)
    def test_chunked_oversized_body_is_rejected_before_google(self):
        provider=FakeProvider()
        with TestClient(create_app(CONFIG,provider)) as c:
            response=c.post('/v1/teach',content=(b'x'*10000 for _ in range(31)),headers=AUTH)
            self.assertEqual(413,response.status_code);self.assertEqual([],provider.requests)
    def test_limits_are_read_from_runtime_environment(self):
        with patch.dict('os.environ',{'LINGOLIVE_AI_ENABLED':'false','LINGOLIVE_LESSONS_PER_DAY':'50','LINGOLIVE_AUDIO_SECONDS_PER_DAY':'1800','LINGOLIVE_MAX_OUTPUT_TOKENS':'2048'}):
            config=Config.environment()
            self.assertFalse(config.ai_enabled);self.assertEqual(50,config.lessons_per_day)
            self.assertEqual(1800,config.audio_seconds_per_day);self.assertEqual(2048,config.max_output_tokens)

if __name__=='__main__':unittest.main()

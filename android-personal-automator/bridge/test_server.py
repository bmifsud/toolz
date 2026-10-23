import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
import server

TOKEN = 'x' * 48


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def proposal(task):
            self.calls.append(task)
            return {'action': 'OPEN_DEMO', 'explanation': 'Open the demo PR.'}
        self.server = server.make_server(('127.0.0.1', 0), TOKEN, proposal)
        server.Handler.last_call = 0
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, value, token=TOKEN):
        request = Request(f'http://127.0.0.1:{self.server.server_port}/proposal',
                          data=json.dumps(value).encode(), headers={
                              'Authorization': 'Bearer ' + token,
                              'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=2) as result:
                return result.status, json.load(result)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_authentication_before_provider(self):
        self.assertEqual(401, self.request({'task': 'open', 'version': 1}, 'wrong')[0])
        self.assertEqual([], self.calls)

    def test_rejects_bad_and_oversized_requests(self):
        for body in ({'task': 'x' * 2001, 'version': 1}, {'task': ' ', 'version': 1},
                     {'task': 'open', 'version': True}, {'task': 'open', 'version': 1, 'url': 'bad'}, []):
            self.assertEqual(400, self.request(body)[0])
        self.assertEqual([], self.calls)

    def test_valid_response_and_rate_limit(self):
        self.assertEqual((200, {'action': 'OPEN_DEMO', 'explanation': 'Open the demo PR.'}),
                         self.request({'task': 'open', 'version': 1}))
        self.assertEqual(429, self.request({'task': 'open', 'version': 1})[0])
        self.assertEqual(['open'], self.calls)

    def test_invalid_provider_action_fails_closed(self):
        self.server.proposer = lambda _: {'action': 'TAP', 'explanation': 'tap'}
        self.assertEqual(502, self.request({'task': 'tap', 'version': 1})[0])

    def test_provider_error_does_not_leak(self):
        def fail(_):
            raise ValueError('secret provider details')
        self.server.proposer = fail
        code, body = self.request({'task': 'open', 'version': 1})
        self.assertEqual(502, code)
        self.assertNotIn('secret', str(body))

    def test_provider_parsing_and_no_storage(self):
        response = {'status': 'completed', 'output': [{'type': 'message', 'content': [
            {'type': 'output_text', 'text': '{"action":"NONE","explanation":"Unsupported"}'}]}]}
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, _): return json.dumps(response).encode()
        with patch.dict('os.environ', {'OPENAI_MODEL': 'test-model', 'OPENAI_API_KEY': 'test-key'}), \
                patch('server.urlopen', return_value=Response()) as request:
            self.assertEqual('NONE', server.propose('task')['action'])
            payload = json.loads(request.call_args.args[0].data)
            self.assertFalse(payload['store'])
            self.assertEqual('task', payload['input'])

    def test_schema_rejects_extra_or_unknown_actions(self):
        for value in ({'action': 'OPEN_URL', 'explanation': 'x'},
                      {'action': 'OPEN_DEMO', 'explanation': ''},
                      {'action': 'OPEN_DEMO', 'explanation': 'x', 'url': 'https://evil.test'}, []):
            with self.assertRaises(ValueError): server.validate_proposal(value)


if __name__ == '__main__':
    unittest.main()

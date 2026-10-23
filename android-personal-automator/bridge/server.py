"""Single-user proposal bridge. Put behind an HTTPS reverse proxy; no device control."""
import hmac
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen

MAX_BODY = 8192
ALLOWED = {'OPEN_DEMO', 'NONE'}
INSTRUCTIONS = '''You propose actions for a supervised Android demo. The ONLY supported
operation is OPEN_DEMO, opening https://github.com/bmifsud/POC-ARTRIOUT/pull/299.
For any other request use NONE and explain that it is unsupported. Never claim you
have viewed or controlled the device. Return ONLY a JSON object with exactly two
string keys: action (OPEN_DEMO or NONE) and explanation (1-2000 characters).
Do not include markdown. The user must separately approve every action.'''


def validate_proposal(value):
    if (not isinstance(value, dict) or set(value) != {'action', 'explanation'}
            or not isinstance(value['action'], str) or value['action'] not in ALLOWED
            or not isinstance(value['explanation'], str)
            or not 1 <= len(value['explanation']) <= 2000):
        raise ValueError('Invalid proposal')
    return value


def propose(task):
    payload = json.dumps({'model': os.environ['OPENAI_MODEL'], 'input': task,
                          'instructions': INSTRUCTIONS, 'store': False,
                          'max_output_tokens': 1200}).encode()
    request = Request('https://api.openai.com/v1/responses', data=payload, headers={
        'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'],
        'Content-Type': 'application/json'})
    with urlopen(request, timeout=35) as response:
        raw = response.read(262145)
    if len(raw) > 262144:
        raise ValueError('Provider response too large')
    response = json.loads(raw)
    if response.get('status') != 'completed':
        raise ValueError('Incomplete provider response')
    text = ''.join(part['text'] for item in response.get('output', [])
                   if item.get('type') == 'message'
                   for part in item.get('content', []) if part.get('type') == 'output_text')
    return validate_proposal(json.loads(text))


class Handler(BaseHTTPRequestHandler):
    # One provider call at a time and at most one call per 5 seconds per process.
    provider_lock = threading.Lock()
    last_call = 0.0

    def log_message(self, *_args):
        pass  # Never log tokens, task text, or provider errors.

    def reply(self, code, value):
        body = json.dumps(value).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.connection.settimeout(10)
        if self.path != '/proposal':
            self.reply(404, {'error': 'not_found'})
            return
        expected = 'Bearer ' + self.server.access_token
        if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), expected.encode()):
            self.reply(401, {'error': 'unauthorized'})
            return
        try:
            if self.headers.get('Transfer-Encoding'):
                raise ValueError()
            length = int(self.headers.get('Content-Length', '0'))
            if not 1 <= length <= MAX_BODY:
                raise ValueError()
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError()
            value = json.loads(raw)
            if (not isinstance(value, dict) or set(value) != {'task', 'version'}
                    or type(value['version']) is not int or value['version'] != 1
                    or not isinstance(value['task'], str)
                    or not value['task'].strip() or len(value['task']) > 2000):
                raise ValueError()
        except (ValueError, OSError):
            self.reply(400, {'error': 'invalid_request'})
            return
        if not self.provider_lock.acquire(blocking=False):
            self.reply(429, {'error': 'busy'})
            return
        try:
            if time.monotonic() - Handler.last_call < 5:
                self.reply(429, {'error': 'rate_limited'})
                return
            Handler.last_call = time.monotonic()
            try:
                proposal = validate_proposal(self.server.proposer(value['task']))
            except Exception:
                self.reply(502, {'error': 'proposal_failed'})
                return
            self.reply(200, proposal)
        finally:
            self.provider_lock.release()


def make_server(address, token, proposer=propose):
    if not 32 <= len(token) <= 512 or any(not 33 <= ord(c) <= 126 for c in token):
        raise ValueError('BRIDGE_TOKEN must contain 32-512 printable non-space ASCII characters')
    server = ThreadingHTTPServer(address, Handler)
    server.daemon_threads = True
    server.access_token = token
    server.proposer = proposer
    return server


if __name__ == '__main__':
    # Fail at startup, rather than accepting tasks with missing provider settings.
    for name in ('OPENAI_API_KEY', 'OPENAI_MODEL', 'BRIDGE_TOKEN'):
        if not os.environ.get(name):
            raise SystemExit('Missing required environment variable: ' + name)
    make_server((os.environ.get('BRIDGE_HOST', '127.0.0.1'),
                 int(os.environ.get('PORT', '8080'))), os.environ['BRIDGE_TOKEN']).serve_forever()

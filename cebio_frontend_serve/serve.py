"""
Servidor unificado CEBIO Brasil.
Serve o frontend estático E faz proxy para o backend FastAPI.
Tudo na mesma porta — sem problemas de CORS.
"""
import http.server
import socketserver
import urllib.request
import urllib.error
import os
import json

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
BACKEND_URL = "http://localhost:8000"


class ProxyHandler(http.server.BaseHTTPRequestHandler):

    def _is_api(self):
        return self.path.startswith('/api/')

    def _serve_static(self):
        # Delega para SimpleHTTPRequestHandler internamente
        path = self.path.split('?')[0]
        if path == '/' or path == '':
            path = '/login.html'
        filepath = os.path.join(DIRECTORY, path.lstrip('/'))
        if os.path.isfile(filepath):
            ext = os.path.splitext(filepath)[1].lower()
            mime = {
                '.html': 'text/html; charset=utf-8',
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon',
                '.woff': 'font/woff',
                '.woff2': 'font/woff2',
                '.ttf': 'font/ttf',
            }.get(ext, 'application/octet-stream')
            with open(filepath, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(data)
        else:
            # SPA fallback: serve login.html
            fallback = os.path.join(DIRECTORY, 'login.html')
            if os.path.isfile(fallback):
                with open(fallback, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404)

    def _proxy_request(self, method):
        target_url = BACKEND_URL + self.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        headers = {}
        for key in ['Content-Type', 'Authorization', 'Accept', 'X-Requested-With']:
            val = self.headers.get(key)
            if val:
                headers[key] = val

        try:
            req = urllib.request.Request(target_url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                for key, val in resp.headers.items():
                    if key.lower() not in ('transfer-encoding', 'connection', 'server'):
                        self.send_header(key, val)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            resp_body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as ex:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'detail': str(ex)}).encode())

    def do_GET(self):
        if self._is_api():
            self._proxy_request('GET')
        else:
            self._serve_static()

    def do_POST(self):
        if self._is_api():
            self._proxy_request('POST')
        else:
            self.send_error(405)

    def do_PUT(self):
        if self._is_api():
            self._proxy_request('PUT')
        else:
            self.send_error(405)

    def do_DELETE(self):
        if self._is_api():
            self._proxy_request('DELETE')
        else:
            self.send_error(405)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # silencia logs verbosos


if __name__ == '__main__':
    # Mata processo anterior na porta 8080 se houver
    os.system("fuser -k 8080/tcp 2>/dev/null || true")
    import time; time.sleep(1)

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), ProxyHandler) as httpd:
        print(f"✅ CEBIO Brasil rodando em http://0.0.0.0:{PORT}")
        print(f"   Frontend: http://localhost:{PORT}/login.html")
        print(f"   API proxy: http://localhost:{PORT}/api/...")
        httpd.serve_forever()

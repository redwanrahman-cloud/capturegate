import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from service import dispatch,MAX_BODY

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass  # Never log images, payloads or personal paths.
    def do_GET(self): self.serve()
    def do_POST(self): self.serve()
    def serve(self):
        host=self.headers.get('Host','')
        if host not in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}:
            self.send_error(403,'Invalid host');return
        origin=self.headers.get('Origin')
        if origin and origin not in {f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}:
            self.send_error(403,'Invalid origin');return
        body=b''
        if self.command=='POST':
            try:length=int(self.headers.get('Content-Length','-1'))
            except ValueError:length=-1
            if not 0<=length<=MAX_BODY:self.send_error(413,'Invalid request size');return
            self.connection.settimeout(10);body=self.rfile.read(length)
            # Drain a size-validated body before rejection. Closing with unread
            # bytes can reset the connection on Windows, hiding the 415 reply.
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':self.send_error(415,'Expected JSON');return
        try:status,headers,data=dispatch(self.command,urlsplit(self.path).path,body)
        except Exception:status,headers,data=500,{'Content-Type':'application/json'},b'{"error":"Analysis unavailable"}'
        self.send_response(status)
        for key,value in headers.items():self.send_header(key,value)
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=4174);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'CaptureGate at http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MyHandler(BaseHTTPRequestHandler):
    Sub_handler: type
    def _send_json(self, response, status=200):
        body = json.dumps(response).encode('utf-8')
        self.send_response(status)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            my_infos = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON invalide")
            return
        request = my_infos.get('request')
        data = my_infos.get('data')
        response = self.Sub_handler(request, data)
        self._send_json(response)


def run(translator, Adr, Port, server_class=HTTPServer, handler_class=MyHandler):
    MyHandler.Sub_handler = translator
    server_address = (Adr, Port)
    httpd = server_class(server_address, handler_class)
    print(f'Adr, Port : {Adr}, {Port}')
    httpd.serve_forever()
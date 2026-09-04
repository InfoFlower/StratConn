from urllib.request import Request, urlopen
import json


class BasicClient:
    def __init__(self, HOST, PORT):
        self.server_url = f"http://{HOST}:{PORT}"

    def send_request(self, request_type, data=None):
        """Envoie une requête au serveur et retourne la réponse JSON"""
        payload = {
            'request': request_type,
            'data': data or {}
        }
        data_encoded = json.dumps(payload).encode('utf-8')
        print(f'SENDING to {self.server_url} request {request_type}')
        req = Request(self.server_url, data=data_encoded, headers={'Content-Type': 'application/json'})
        print(f'REQUEST SENDED')
        try:
            with urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {'status': 'FAILED', 'error': str(e)}

    def __call__(self, request_type, data=None):
        return self.send_request(request_type, data)
from urllib.request import Request, urlopen
import json
from enum import Enum

class BasicClient:
    def __init__(self, HOST, PORT):
        self.server_url = f"http://{HOST}:{PORT}"

    def send_request(self, request_type, data=None):
        """Envoie une requête au serveur et retourne la réponse JSON"""
        payload = {
            'request': request_type,
            'data': data or {}
        }
        try :
            data_encoded = json.dumps(payload, default=lambda o: o.name if isinstance(o, Enum) else str(o)).encode('utf-8')
        except Exception as e:
            print(f'[STRATCONN] ERROR SENDING {payload}')
            return {'status': 'FAILED', 'error': repr(e)}
        print(f'[STRATCONN] SENDING to {self.server_url} request {request_type}')
        req = Request(self.server_url, data=data_encoded, headers={'Content-Type': 'application/json'})
        print(f'[STRATCONN] REQUEST SENDED')
        try:
            with urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {'status': 'FAILED', 'error': str(e)}

    def __call__(self, request_type, data=None):
        return self.send_request(request_type, data)
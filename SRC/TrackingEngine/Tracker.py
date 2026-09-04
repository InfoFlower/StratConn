import threading
import socket
from SRC.TrackingEngine.ConnStrat import ConnStrat
import json

class GenTrack :
    def __init__(self, stratpath, WEBSOC='0.0.0.0', WSPORT=8000) -> None:
        self._lock = threading.Lock()
        self.CStrat = ConnStrat(stratpath)
        self.running = False
        self.WEBSOC=WEBSOC
        self.WSPORT=WSPORT
        pass

    def __call__(self, request, my_infos=None):
            if request == 'START_SIMULATION':
                response = self._start_simulation()
            elif request == 'SEND_EVENT':
                response = self.CStrat.SendEvent(my_infos)
            else :
                response = {
                    'statut' : 'FAILED',
                    'bc' : 'DUMB'
                }
            return response

    def _start_simulation(self):
        with self._lock:
            if self.running:
                return {
                    "status": "already_running",
                    "message": "Simulation already running"
                }
            host, port = self.WEBSOC, self.WSPORT
            self.running = True
            self._thread = threading.Thread(
                target=self._run_simulation,
                args=(host, port),
                daemon=True
            )
            self._thread.start()

        return {"status": "started","message": "Simulation started successfully"}

    def _run_simulation(self, HOST, PORT):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((HOST, PORT))
            sock.listen(1)
            conn, addr = sock.accept()
            with conn:
                print('Connected by', addr)
                buffer = b''
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    buffer += chunk
                    # Process complete lines (separated by \n)
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        if line:
                            try:
                                data = json.loads(line.decode('utf-8'))
                                res = self.CStrat.UpdatePrice(data)
                                conn.sendall(json.dumps(res).encode('utf-8') + b'\n')
                            except json.JSONDecodeError as e:
                                print(f'JSON decode error: {e}')
                                conn.sendall(json.dumps({'error': 'Invalid JSON'}).encode('utf-8') + b'\n')
        with self._lock:
            self.running = False
        print('End')
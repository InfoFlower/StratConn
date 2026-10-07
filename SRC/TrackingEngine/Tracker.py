import threading
import socket

from attrs import asdict
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
            sock.bind((HOST, PORT))
            sock.listen(1)
            conn, addr = sock.accept()
            with conn:
                print('Connected by', addr)
                while True:
                    bdata = conn.recv(1024)
                    if not bdata: break
                    data = json.loads(bdata)
                    res = self.CStrat.UpdatePrice(data)
                    dres = asdict(res)
                    fres = json.dumps(dres).encode('utf-8')
                    conn.sendall(fres)
        self.running = False
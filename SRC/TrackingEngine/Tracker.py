import threading
import socket

from .ConnStrat import ConnStrat
import json

class GenTrack :
    def __init__(self, stratpath, WEBSOC, WSPORT, BROKER_ADR, BROKER_PORT) -> None:
        self._lock = threading.Lock()
        self.CStrat = ConnStrat(stratpath, BROKER_ADR, BROKER_PORT)
        self.running = False
        self.WEBSOC=WEBSOC
        self.WSPORT=WSPORT
        pass

    def __call__(self, request, my_infos=None):
        with self._lock:
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

    # des 2 côtés, ex. SRC/Core/json_enum.py + Sisimulation/src/engine/...
    def _enum_encoder(self, o):
        from enum import Enum
        return o.name if isinstance(o, Enum) else o

    def _run_simulation(self, HOST, PORT):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((HOST, PORT))
                sock.listen(1)
                conn, addr = sock.accept()
                # Framing NDJSON : un message JSON par ligne ('\n'), dans les deux sens
                with conn, conn.makefile('r', encoding='utf-8') as reader:
                    print('[STRATCONN] Connected by', addr)
                    for line in reader:                  # s'arrête quand le client ferme
                        if not line.strip():
                            continue
                        dres = self._process_line(line)
                        fres = json.dumps(dres, default=self._enum_encoder) + '\n'
                        conn.sendall(fres.encode('utf-8'))
        finally:
            self.running = False

    def _process_line(self, line):
        """Traite un tick ; une erreur renvoie FAILED sans couper la connexion"""
        try:
            data = json.loads(line)
            return self.CStrat.UpdatePrice(data)
        except Exception as e:
            print(f'[STRATCONN] Invalid tick: {e!r}')
            return {'status': 'FAILED', 'error': 'INVALID_TICK', 'message': repr(e)}
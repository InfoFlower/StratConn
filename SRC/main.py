from TrackingEngine.Tracker import GenTrack
from Interfaces.WEB.HTTPServer import run

Adr = '127.0.0.1'
PORT = 8081

a = 'a'
WS_ADR= '127.0.0.1'
WS_PORT= 8000

BROKER_ADR = '127.0.0.1'
BROKER_PORT = 8080

strategie_path = 'Strategies.RouteTestStrat'
Tracker = GenTrack(strategie_path, WS_ADR, WS_PORT, BROKER_ADR, BROKER_PORT)
run(Tracker, Adr, PORT)
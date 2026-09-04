from SRC.TrackingEngine.Tracker import GenTrack
from SRC.Interfaces.WEB.HTTPServer import run

Adr = '0.0.0.0'
PORT = 8080
strategie_path = 'SRC.Strategies.TestStrat'
Tracker = GenTrack(strategie_path)
run(Tracker, Adr, PORT)
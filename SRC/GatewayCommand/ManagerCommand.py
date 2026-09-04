from ..Interfaces.WEB.HTTPClient import BasicClient

class GateComm:
    def __init__(self, HOST='0.0.0.0', PORT=8080) -> None:
        self.sender = BasicClient(HOST, PORT)
        pass

    def get_price(self):
        """Récupère le prix actuel"""
        return self.sender.send_request('GET_PRICE')

    def start_simulation(self):
        """Démarre la simulation"""
        return self.sender.send_request('START_SIMULATION')
from SRC.Interfaces.WEB.HTTPClient import BasicClient
from SRC.Core.order import Order

class GateComm:
    def __init__(self, HOST='0.0.0.0', PORT=8080) -> None:
        self.sender = BasicClient(HOST, PORT)
        pass

    def submit_order(self, order_data:Order):
        """Soumet une commande"""
        return self.sender.send_request('SUBMIT_ORDER', order_data)

    def cancel_order(self, order_id):
        """Annule une commande"""
        return self.sender.send_request('CANCEL_ORDER', {'OrderId': order_id})

    def close_position(self, position_id):
        """Ferme une position"""
        return self.sender.send_request('CLOSE_POSITION', {'PositionId': position_id})
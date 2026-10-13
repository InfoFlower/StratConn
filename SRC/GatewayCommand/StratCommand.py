from Interfaces.WEB.HTTPClient import BasicClient
from Core.order import Order
from dataclasses import asdict

class GateComm:
    def __init__(self, HTTP_HOST, HTTP_PORT) -> None:
        self.sender = BasicClient(HTTP_HOST, HTTP_PORT)
        pass

    def submit_order(self, order_data:Order):
        """Soumet une commande"""
        return self.sender.send_request('SUBMIT_ORDER', asdict(order_data))

    def cancel_order(self, order_id):
        """Annule une commande"""
        return self.sender.send_request('CANCEL_ORDER', {'OrderId': order_id})

    def close_position(self, position_id):
        """Ferme une position"""
        return self.sender.send_request('CLOSE_POSITION', {'PositionId': position_id})

    def get_price(self):
        """Demande le prix courant au broker"""
        return self.sender.send_request('GET_PRICE')

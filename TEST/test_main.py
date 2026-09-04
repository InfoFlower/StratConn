import socket


list_of_structured_data = []

with open('TEST/test_data.csv', 'r') as f:
    lines = f.readlines()
    header = lines[0].strip().split(',')
    structured_data = {}
    for item in header:
        structured_data[item] = 0
    for i in lines[1:]:
        values = i.strip().split(',')
        for j, key in enumerate(header):
            structured_data[key] = values[j]
        list_of_structured_data.append(structured_data)


from SRC.Interfaces.WEB.HTTPClient import BasicClient
Client = BasicClient('127.0.0.1' , 8080)
print('STARTING SIM')
response = Client('START_SIMULATION', {'host': '127.0.0.1', 'port': 8000})
print('SIM STARTED')
print(f'Server response: {response}')
import socket
import json
import time
HOST = '127.0.0.1'
PORT = 8000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((HOST, PORT))
    for id, i in enumerate(list_of_structured_data):
        data = {"id": id, "timestamp": structured_data['Open time'], "price": structured_data['Open']}
        dump = json.dumps({"id": id, "timestamp": structured_data['Open time'], "price": structured_data['Open']})+'\n'
        sock.sendall(dump.encode('utf-8'))
        data = sock.recv(1024)   # bloque jusqu'à recevoir la réponse
        if not data:
            break
        print("Réponse:", data)
        if id % 100==0:
            Client('SEND_EVENT', {'EventType' : 'ORDER_EXECUTED', 'data':{'Id':1}})
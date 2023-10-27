import socket

client = socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
client.connect(("B8:27:EB:55:55:59",5))
while True:
    yeah = input("Command : ")
    client.send(yeah.encode())
    print(client.recv(1024).decode())
    if yeah == "stop":
        client.close()
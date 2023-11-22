import tkinter as tk
import socket
import threading

root = tk.Tk()

def containerInput(client : socket.socket):
    while True:
        data = client.recv(1024)
        if data is None:
            break

        message = data.decode()
        print(f"message -> {message}")


def sendCommand(event: tk.Event):
    command = event.widget.get()
    client.send(command.encode())

def attemptToConnect(port : int, address : str):
    try:
        client = socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        client.connect(("B8:27:EB:55:55:59",5))
        return client
    except Exception:
        print("failed to connect")
        return None


root.geometry(f"{int(root.winfo_screenwidth())}x{root.winfo_screenheight()}")
root.title("Bluetoinum Canister")

frame = tk.Frame(root)
frame.pack(expand=True, fill="both")

commandInput = tk.Entry(frame)
commandInput.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
commandInput.bind("<Return>", sendCommand)


sendCommandButton = tk.Button(frame, text="send command")
sendCommandButton.grid(row=0, column=1, padx=10, pady=10, sticky="e")

frame.columnconfigure(0, weight=1)

client = attemptToConnect(5,"B8:27:EB:55:55:59")

if client is not None:
    commandListener = threading.Thread(target=containerInput,args=[client,])
    commandListener.start()
    root.mainloop()
else:
    print("failed to do something")
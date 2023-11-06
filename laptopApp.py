import tkinter as tk
import socket


root = tk.Tk()


def containerInput():
    pass


def sendCommand(event: tk.Event):
    command = event.widget.get().split(",")


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

root.mainloop()

import time
import os
import socket
import threading
import board
import neopixel
import pygame.mixer
import json

class animation:
    def __init__(self, frames, framerate):  
        self.frames = frames
        self.currentFrame = 0
        self.timeBetweenFrames = 1/framerate

    def play(self,leds) -> list:
        if self.currentFrame == len(self.frames):
            self.currentFrame = 0
        for index in range(len(leds)):
            leds[index] = self.frames[self.currentFrame][index]
        self.currentFrame += 1
        time.sleep(self.timeBetweenFrames)

class bluetoinumContainer:
    def __init__(self):
        self.LED_COUNT = 50
        self.LED_PIN = board.D10
        self.PORT = 5
        self.ADDRESS = "B8:27:EB:55:55:59"
        self.animationDir = "animations/"
        self.soundDir = "sounds/"
        self.active = True
        self.currentAnimation = None
        self.leds = neopixel.NeoPixel(self.LED_PIN,self.LED_COUNT,brightness=1)
        self.commands = [self.fill,self.testAnimation,self.stop]
        self.stopCurrentAnimation = False    
        self.currentSound = None
    
    def loadAnimation(self, fileName : str) -> animation:
        try:
            with open(f"{self.animationDir}{fileName}") as file:
                data = json.load(file)
                if data["sound"] != "":
                    try:
                        self.currentSound = pygame.mixer.Sound(self.soundDir + data["sound"])
                    except FileNotFoundError:
                        return "Sound file not found"
                return animation(data["frames"], data["framerate"])
        except FileNotFoundError as fnfe:
            return f"Animation file not found {fnfe.filename}"
        
    def playAnimation(self, currentAnimation : animation):
        while not self.stopCurrentAnimation:
            currentAnimation.play(self.leds)
        
    def killCurrentAnimation(self):
        if self.currentAnimation is None or not self.currentAnimation.is_alive:
            return
        self.stopCurrentAnimation = True
        if self.currentSound is not None:
            self.currentSound.stop()
            self.currentSound = None
        self.currentAnimation.join()
        self.stopCurrentAnimation = False

    def startAnimation(self, fileName : str) -> str:
        self.killCurrentAnimation()
        selectedAnimation = self.loadAnimation(fileName)
        if isinstance(selectedAnimation,animation):
            if self.currentSound is not None:
                self.currentSound.play()
            self.currentAnimation = threading.Thread(target=self.playAnimation,args=(selectedAnimation,))
            self.currentAnimation.start()
            return "OK"
        else:
            return selectedAnimation

    def log(self,message : str):
        with open("log.txt","at") as file:
            file.write(message + "\n")
    
    def start(self):
        print("starting")
        server = socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        server.bind((self.ADDRESS,self.PORT))
        server.listen(2)
        while self.active:
            try:
                conn, address = server.accept()
                self.log(f"accepting connection from {address}")
                while True:
                    data = conn.recv(1024)
                    if data == None:
                        continue
                    data = data.decode()
                    print(f"recived command {data}")
                    if data == "quit":
                        break
                    for command in self.commands:
                        if command.__name__ == data:
                            try:
                                args = data.split(',')[1:]
                                response = command(*args)
                                if response is None:
                                    response = "OK"
                            except Exception as exceptionMessage:
                                response = str(exceptionMessage)
                            conn.send(response.encode())
                            break
                    else:
                        conn.send("Command not found".encode()) 
            except Exception as e:
               self.log(f"ERROR : {e}")
        server.close()

    def fill(self,color):
        self.leds.fill(tuple(color))
        return "OK"

    def testAnimation(self):
        return self.startAnimation("test.json")
    
    def anyAnimation(self, animationToPlay : str):
        return self.startAnimation(animationToPlay)

    def stop(self):
        self.killCurrentAnimation()
        self.active = False
        return "OK"
        

if __name__ == "__main__":
    pygame.mixer.init()
    thing = bluetoinumContainer()
    thing.start()
    
    thing.leds.fill((0,0,0))
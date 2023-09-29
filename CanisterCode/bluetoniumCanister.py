import socket
import threading
import board
import neopixel
import time
import pygame.mixer
import json


class animation:
    def __init__(self, frames, framerate, sound = None):
        self.frames = frames
        self.currentFrame = 0;
        self.timeBetweenFrames = 1/framerate
        self.soundDir = "sounds/"
        if sound != "":
            self.sound = pygame.mixer.Sound(self.soundDir + sound)
            self.sound.play(-1)
        else:
            self.sound = None  

    def playSound(self):
        if self.sound != None:
            self.sound.play(-1)    

    def stop(self):
        if self.sound != None:
            self.sound.stop()  

    def play(self,leds) -> list:
        if self.currentFrame == len(self.frames):
            self.currentFrame = 0
        for index in range(len(leds)):
            leds[index] = self.frames[self.currentFrame][index]
        time.sleep(self.timeBetweenFrames)
        

class bluetoinumContainer:
    def __init__(self):
        self.LED_COUNT = 50
        self.LED_PIN = board.D18
        self.PORT = 5
        self.ADDRESS = "B8:27:EB:55:55:59"
        self.animationDir = "animations/"
        self.active = True
        self.currentAnimation = None
        self.leds = neopixel.NeoPixel(self.LED_PIN,self.LED_COUNT,brightness=1)
        self.commands = [self.meltdown,self.fill,self.testAnimation,self.stop]
        self.stopCurrentAnimation = False    

    def playAnimation(self, currentAnimation : animation):
        currentAnimation.playSound()
        while not self.stopCurrentAnimation:
                currentAnimation.play()
        currentAnimation.stop()

    def loadAnimation(self, file : str) -> animation:
        try:
            with open(self.animationDir + file) as file:
                data = json.load(file)
                return animation(data["frames"], data["framerate"], data["sound"])

        except FileNotFoundError as fnfe:
            return "Animation file not found"
        except Exception:
            return "unknown error with loading animation"

    def startAnimation(self, fileName : str) -> str:
        if self.currentAnimation != None and self.currentAnimation.is_alive:
            self.stopCurrentAnimation = True
            self.currentAnimation.join()
        selectedAnimation = self.loadAnimation(fileName)
        if isinstance(selectedAnimation,animation):
            self.currentAnimation = threading.Thread(target=self.playAnimation,args=(selectedAnimation,))
            return "OK"
        else:
            return selectedAnimation

    def log(self,message : str):
        with open("log.txt","a") as file:
            file.write(message)
    
    def start(self):
        print("starting")
        server = socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        server.bind((self.ADDRESS,self.PORT))
        server.listen(2)
        print("listening")
        while self.active:
            try:
                conn, address = server.accept()
                self.log(f"accepting connection from {address}")
                while True:
                    data = conn.recv(1024)
                    if data == None:
                        continue
                    data = data.decode()
                    if data == "quit":
                        break
                    for command in self.commands():
                        if command.__name__ == data:
                            try:
                                response = command(data.split(",")[1:])
                            except Exception as e:
                                response = e
                            finally:
                                conn.send(response.encode())
                            break
                    else:
                        conn.send("Command not found") 
            except Exception as e:
                self.log(f"ERROR : {e}")
        server.close()
   
    def meltdown(self) -> str:
        return self.startAnimation("meltdown")

    def fill(self,color):
        self.leds.fill(tuple(color))

    def testAnimation(self):
        self.startAnimation("test.json")

    def stop(self):
        self.active = False
        

if __name__ == "__main__":
    pygame.mixer.init()
    print("pygame init")
    thing = bluetoinumContainer()
    print("starting")
    thing.start()
    thing.leds.fill((0,0,0))
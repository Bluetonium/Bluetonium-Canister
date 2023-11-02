#!/usr/bin/python

import time
import os
import socket
import threading
import board
import neopixel
import pygame.mixer
import json

class animation:
    def __init__(self, frames, framerate, loop = -1, repeatOnLoop = False):
        self.frames = frames
        self.currentFrame = 0
        self.timeBetweenFrames = 1/framerate
        self.loop = loop
        self.repeatOnLoop = repeatOnLoop

    def play(self,leds : neopixel.NeoPixel):
        if self.currentFrame == len(self.frames):
            self.currentFrame = 0
            if self.loop != -1:
                if self.loop > 0:
                    self.loop -= 1
                else:
                    return False
            if self.repeatOnLoop:
                pygame.mixer.music.rewind()
        for index in range(len(leds)):
            leds[index] = self.frames[self.currentFrame][index]
        leds.show()
        self.currentFrame += 1
        time.sleep(self.timeBetweenFrames)
        return True

class bluetoinumContainer:
    def __init__(self):
        self.DIR = "/home/bluetonium/CanisterCode/"
        self.LED_COUNT = 50
        self.LED_PIN = board.D10
        self.PORT = 5
        self.ADDRESS = "B8:27:EB:55:55:59"
        self.animationDir = self.DIR + "animations/"
        self.soundDir = self.DIR + "sounds/"
        self.active = True
        self.currentAnimation = None
        self.leds = neopixel.NeoPixel(self.LED_PIN,self.LED_COUNT,brightness=1,auto_write=False)
        self.leds.fill((0,0,0))
        self.commands = []
        self.stopCurrentAnimation = False
        self.defaultAnimationPresent = os.path.isfile(self.DIR + self.animationDir + "default.json")#check for default animation
        self.currentAnimationName = None
        self.currentVolume = 1
        self.shutdown = False # shutdown after stopping

    def loadSound(self, soundFile : str) -> bool:
        try:
            pygame.mixer.music.load(self.soundDir + soundFile)
            pygame.mixer.music.set_volume(self.currentVolume)
            pygame.mixer.music.play(loops=-1)
            return True
        except FileNotFoundError:
            return False

    def loadAnimation(self, fileName : str) -> animation:
        try:
            with open(self.animationDir + fileName) as file:
                data = json.load(file)
                if data["sound"] != "":
                    if not self.loadSound(data["sound"]):
                        return "Sound file not found"
                self.currentAnimation = fileName.removesuffix(".json")
                return animation(data["frames"], data["framerate"],data["loops"],data["repeatOnLoop"])
        except FileNotFoundError as fnfe:
            return f"Animation file not found {fnfe.filename}"

    def playAnimation(self, currentAnimation : animation, loop = -1):
        while not self.stopCurrentAnimation:
            if not currentAnimation.play(self.leds):
                    pygame.mixer.music.fadeout(500)
                    pygame.mixer.music.unload()
                    self.killCurrentAnimation()
                    break
        self.stopCurrentAnimation = False

    def startAnimation(self, fileName : str) -> str:
        self.killCurrentAnimation()
        selectedAnimation = self.loadAnimation(fileName)
        if isinstance(selectedAnimation,animation):
            self.currentAnimation = threading.Thread(target=self.playAnimation,args=(selectedAnimation,))
            self.currentAnimation.start()
            return "OK"
        else:
            return selectedAnimation

    def log(self,message : str) -> None:
        with open(self.DIR + "log.txt","a") as file:
            file.write(message)

    def start(self) -> None:
        if self.defaultAnimationPresent:
            self.startAnimation("default.json")
            self.log("loading default animation")
        else:
            self.log("no default animation loaded")
        print("starting")
        server = socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        server.bind((self.ADDRESS,self.PORT))
        server.listen(2)
        print("listening")
        while self.active:
            conn, address = server.accept()
            try:
                self.log(f"accepting connection from {address}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    try:
                        data = json.loads(data.decode())
                        print(data)
                        commandName = data["command"]
                        self.log(f"Command : {commandName}")
                        for command in self.commands:
                            print(f"checking command {command.__name__}")
                            if command.__name__ == commandName:
                                args = data["args"]
                                response = command(self, *args)#thank you json
                                if response is None:
                                    response = "OK"
                                    print("no response")
                                else:
                                    print("some response got")
                                    print(f"we got a response {response}")
                                break
                        else:
                            print("couldnt even find thecommand")
                            response = "Command not found"
                        conn.send(response.encode())
                    except TypeError:
                        conn.send("Incorrect command format".encode())
                    except Exception as exceptionMessage:
                        conn.send(f"Error has occured {exceptionMessage}".encode())
            except Exception as e:
                self.log(f"ERROR : {e}")
        server.close()
        return self.shutdown

    def command(self, command) -> str:
        self.commands.append(command)

    def killCurrentAnimation(self, playDefault = True) -> str:
        if self.currentAnimation is None or not self.currentAnimation.is_alive:
            return "No current animation"
        self.stopCurrentAnimation = True
        #self.currentAnimation.join()#makes looping suck if this is on and i dont think we need
        if self.currentAnimationName != "default" and self.defaultAnimationPresent and playDefault:
            self.startAnimation("default.json")
        else:
            self.currentAnimation = None
            self.currentAnimationName = None


#the real stuff here
can = bluetoinumContainer()
pygame.mixer.init()

@can.command
def meltdown(canister : bluetoinumContainer):
    return canister.startAnimation("meltdown")

@can.command
def testAnimation(canister : bluetoinumContainer):
    return canister.startAnimation("test.json")

@can.command
def fill(canister : bluetoinumContainer, color):
    canister.leds.fill(color)
    return "OK"

@can.command
def stop(canister : bluetoinumContainer) -> str:
    canister.killCurrentAnimation(playDefault=False)
    canister.active = False
    return "OK"

@can.command
def shutdown(canister : bluetoinumContainer) -> str:
    canister.killCurrentAnimation(playDefault=False)
    canister.active = False
    canister.shutdown = True

@can.command
def killAnimation(canister : bluetoinumContainer):
    return canister.killCurrentAnimation()

@can.command
def getCurrentAnimation(canister : bluetoinumContainer):
    if canister.currentAnimation is None or not canister.currentAnimation.is_alive:
        return "No active animation"
    else:
        return f"current animation : {canister.currentAnimationName}"

@can.command
def help(canister : bluetoinumContainer):
    return "Commands : " + ", ".join([x.__name__ for x in canister.commands])

@can.command
def getAnimationList(canister : bluetoinumContainer):
    return ", ".join(os.listdir(canister.animationDir))

@can.command
def getSoundList(canister : bluetoinumContainer):
    return ", ".join(os.listdir(canister.soundDir))

@can.command
def playSound(canister : bluetoinumContainer, soundFile : str):
    if canister.loadSound(soundFile):
        return "OK"
    return "Sound file not found"

@can.command
def mute(canister : bluetoinumContainer, mute : bool = True):#technically not muting, but shutup
    if mute:
        pygame.mixer.music.pause()
    else:
        pygame.mixer.music.unpause()
    return "OK"

@can.command
def setVolume(canister : bluetoinumContainer, volume : float):
    pygame.mixer.music.set_volume(volume)
    canister.currentVolume = volume

@can.command
def playAnimation(canister : bluetoinumContainer, animation):
    return canister.startAnimation(animation)

shutdown = can.start()
print("stopping")
if shutdown:
    os.system("sudo shutdown -h now")
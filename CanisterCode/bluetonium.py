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
    def __init__(self, frames, framerate, name):
        self.frames = frames
        self.currentFrame = 0
        self.timeBetweenFrames = 1/framerate
        self.animationName = name

    def play(self,leds) -> list:
        if self.currentFrame == len(self.frames):
            self.currentFrame = 0
        for index in range(len(leds)):
            leds[index] = self.frames[self.currentFrame][index]
        self.currentFrame += 1
        time.sleep(self.timeBetweenFrames)

    def muteAudio(self, muted : bool):
        pass

    def getName(self) -> str:
        return self.animationName


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
        self.leds = neopixel.NeoPixel(self.LED_PIN,self.LED_COUNT,brightness=1)
        self.commands = []
        self.stopCurrentAnimation = False
        self.defaultAnimationPresent = os.path.isfile(self.DIR + self.animationDir + "default.json")
        self.currentAnimationName = None
        self.currentVolume = 1
        self.shutdown = False # shutdown after stopping

        #check for the default        

    def loadSound(self, soundFile : str) -> bool:
        try:
            pygame.mixer.music.load(self.soundDir + soundFile)
            pygame.mixer.music.set_volume(self.currentVolume)
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
                return animation(data["frames"], data["framerate"])
        except FileNotFoundError as fnfe:
            return f"Animation file not found {fnfe.filename}"

    def playAnimation(self, currentAnimation : animation, loop = -1):
        while not self.stopCurrentAnimation:
            currentAnimation.play(self.leds)
        pygame.mixer.music.fadeout(500)
        pygame.mixer.music.unload()
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
        print(message)

    def start(self) -> None:
        if self.defaultAnimationPresent:
            self.startAnimation("default.json")
        print("starting")
        server = socket.socket(socket.AF_BLUETOOTH,socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        server.bind((self.ADDRESS,self.PORT))
        server.listen(2)
        print("listening")
        while self.active:   
            conn, address = server.accept()
            with conn:
                self.log(f"accepting connection from {address}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    try:
                        data = json.loads(data.decode())
                        commandName = data["command"]
                        self.log("Command : {command}")
                        for command in self.commands:
                            if command.__name__ == commandName:
                                args = data["args"]
                                response = command(self, *args)#thank you json
                                if response is None:
                                    response = "OK"
                            break
                        else:
                            response = "Command not found"
                    except TypeError as te:
                        response = "Incorrect command format"
                    except Exception as exceptionMessage:
                        response = str(exceptionMessage)
                    finally:
                         conn.send(response.encode())
        server.close()
        return self.shutdown

    def command(self, command) -> str:
        self.commands.append(command)

    def killCurrentAnimation(self, playDefault = True) -> str:
        if self.currentAnimation is None or not self.currentAnimation.is_alive:
            return "No current animation"
        self.stopCurrentAnimation = True
        self.currentAnimation.join()
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
        return f"current animation : {canister.currentAnimation.getName()}"

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

shutdown = can.start()
print("stopping")
if shutdown:
    os.system("sudo shutdown -h now")
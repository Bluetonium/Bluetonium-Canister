#!/usr/bin/python

import time
import os
import socket
import threading
import board
import neopixel
import pygame.mixer
import json
import RPi.GPIO as GPIO

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
        self.MAIN_LED_PIN = 6
        self.PORT = 5
        self.ADDRESS = "B8:27:EB:55:55:59"
        self.animationDir = self.DIR + "animations/"
        self.soundDir = self.DIR + "sounds/"
        self.active = True
        self.currentAnimation = None
        self.leds = neopixel.NeoPixel(self.LED_PIN,self.LED_COUNT,brightness=1)
        self.commands = []
        self.stopCurrentAnimation = False
        self.currentSound = None
        self.mainLedStatus = True# be on by default

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.MAIN_LED_PIN,GPIO.OUT)
        GPIO.output(self.MAIN_LED_PIN,GPIO.HIGH)
        self.leds.fill((0,0,0))

    def loadSound(self, soundFile : str) -> bool:
        try:
            self.currentSound = pygame.mixer.Sound(self.soundDir + soundFile)
            True
        except FileNotFoundError:
            return False

    def loadAnimation(self, fileName : str) -> animation:
        try:
            with open(f"{self.animationDir}{fileName}") as file:
                data = json.load(file)
                if data["sound"] != "":
                    if not self.loadSound(data["sound"]):
                        return "Sound file not found"
                return animation(data["frames"], data["framerate"])
        except FileNotFoundError as fnfe:
            return f"Animation file not found {fnfe.filename}"

    def playAnimation(self, currentAnimation : animation):
        while not self.stopCurrentAnimation:
            currentAnimation.play(self.leds)

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
        with open(self.DIR + "log.txt","at") as file:
            file.write(message + "\n")

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
                    print(f"recived command {data}")
                    if data == "quit":
                        break
                    commandName = data.split(",")[0]
                    for command in self.commands:
                        if command.__name__ == commandName:
                            try:
                                args = data.split(',')[1:]
                                response = command(self,*[eval(x) for x in args])#idc that its insecure, its easy
                                if response is None:
                                    response = "OK"
                            except TypeError as te:
                                response = "Incorrect number of arguments"
                            except Exception as exceptionMessage:
                                response = str(exceptionMessage)
                            conn.send(response.encode())
                            break
                    else:
                        conn.send("Command not found".encode())
            except Exception as e:
               self.log(f"ERROR : {e}")
        server.close()

    def command(self, command) -> str:
        self.commands.append(command)

    def killCurrentAnimation(self):
        if self.currentAnimation is None or not self.currentAnimation.is_alive:
            return "No current animation"
        self.stopCurrentAnimation = True
        if self.currentSound is not None:
            self.currentSound.stop()
            self.currentSound = None
        self.currentAnimation.join()
        self.stopCurrentAnimation = False



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
def setMainLed(canister : bluetoinumContainer, mode : bool) -> str:
        if mode:
            GPIO.output(canister.MAIN_LED_PIN,GPIO.HIGH)
            canister.mainLedStatus = True
        else:
            GPIO.output(canister.MAIN_LED_PIN,GPIO.LOW)
            canister.mainLedStatus = False
        return "OK"

@can.command
def getMainLed(canister : bluetoinumContainer):
    if canister.mainLedStatus:
        return "Main LED on"
    else:
        return "Main LED off"

@can.command
def stop(canister : bluetoinumContainer) -> str:
    canister.killCurrentAnimation()
    canister.active = False
    return "OK"

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
    if canister.currentSound is None:
        return "OK"
    if mute:
        pygame.mixer.pause()
    else:
        pygame.mixer.unpause()
    return "OK"

@can.command
def setVolume(canister : bluetoinumContainer, volume : float):#note only sets for the current sound, fix that later
    if canister.currentSound is not None:
        canister.currentSound.set_volume(volume)

can.start()
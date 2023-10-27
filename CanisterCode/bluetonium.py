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
        self.commands = [self.killCurrentAnimation,self.fill,self.stop,self.setMainLed,self.getMainLed]#default commands
        self.stopCurrentAnimation = False
        self.currentSound = None
        self.mainLedStatus = True# be on by default

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.MAIN_LED_PIN,GPIO.OUT)
        GPIO.output(self.MAIN_LED_PIN,GPIO.HIGH)
        self.leds.fill((0,0,0))

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
                    for command in self.commands:
                        if command.__name__ == data:
                            try:
                                args = data.split(',')[1:]
                                response = command(*args)
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

    def commmand(self, command : function) -> str:
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

    def fill(self,color) -> str:
        self.leds.fill(tuple(color))
        return "OK"

    def stop(self) -> str:
        self.killCurrentAnimation()
        self.active = False
        return "OK"

    def setMainLed(self, status : bool) -> str:
        if status:
            GPIO.output(self.MAIN_LED_PIN,GPIO.HIGH)
            self.mainLedStatus = True
        else:
            GPIO.output(self.MAIN_LED_PIN,GPIO.LOW)
            self.mainLedStatus = False
        return "OK"

    def getMainLed(self) -> str:
        if self.mainLedStatus:
            return "Main LED on"
        else:
            return "Main LED off"


#the real stuff here
can = bluetoinumContainer()
pygame.mixer.init()

@can.command
def meltdown(canister : bluetoinumContainer):
    return canister.startAnimation("meltdown")

@can.commmand
def testAnimation(canister : bluetoinumContainer):
    return canister.startAnimation("test.json")

can.start()
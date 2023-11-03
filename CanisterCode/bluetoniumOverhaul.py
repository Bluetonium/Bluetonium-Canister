# bluetonium overhaul

import time
import os
import socket
import threading
import board
import neopixel
from pygame import mixer
import json


class animation:
    def __init__(self, frames: list, audio: str, framerate: int, name: str, loop: int = -1, repeatOnLoop: bool = False):
        self.frames = frames
        self.currentFrame = 0
        self.timeBetweenFrames = 1/framerate
        self.loop = loop
        self.repeatOnLoop = repeatOnLoop
        self.hasPlayed = False
        self.audio = audio
        self.name = name

    def play(self, leds: neopixel.NeoPixel):
        if self.loop == 0:
            return

        if not self.hasPlayed:
            if len(self.audio) != 0:
                mixer.music.unload()
                mixer.music.fadeout(500)
                mixer.music.load(self.audio)
                mixer.music.play()
            self.hasPlayed = True

        if self.currentFrame == len(self.frames):
            self.currentFrame = 0
            if self.loop != -1:
                self.loop -= 1
            if self.repeatOnLoop:
                mixer.music.rewind()

        for index in range(len(leds)):
            leds[index] = self.frames[self.currentFrame][index]
        leds.show()
        self.currentFrame += 1
        time.sleep(self.timeBetweenFrames)

    def getName(self) -> str:
        return self.name


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
        self.leds = neopixel.NeoPixel(
            self.LED_PIN, self.LED_COUNT, brightness=1, auto_write=False)
        self.leds.fill((0, 0, 0))
        self.commands = []
        self.defaultAnimationPresent = os.path.isfile(
            self.animationDir + "default.json")
        self.shutdownAfterStop = False

        if self.defaultAnimationPresent:
            default = self.currentAnimation = self.loadAnimation(
                "default.json")
            if not isinstance(default, animation):
                self.log("Error starting default")
                self.loadEmptyAnimation()
                self.defaultAnimationPresent = False

        self.animationHandler = threading.Thread(
            target=self.animationPlayer, args=[])

    def start(self) -> None:
        self.animationHandler.start()
        server = socket.socket(socket.AF_BLUETOOTH,
                               socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        server.bind((self.ADDRESS, self.PORT))
        server.listen(2)
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
                            if command.__name__ == commandName:
                                args = data["args"]
                                # thank you json
                                response = command(self, *args)
                                break
                        else:
                            self.log(f"Command not found {commandName}")
                            response = "Command not found"
                        conn.send(response.encode())
                    except TypeError:
                        conn.send("Incorrect command format".encode())
                    except Exception as exceptionMessage:
                        conn.send(
                            f"Error has occured {exceptionMessage}".encode())
            except Exception as e:
                self.log(f"ERROR : {e}")
        server.close()
        return self.shutdown

    def animationPlayer(self):
        while self.active:
            self.currentAnimation.play()
        mixer.music.unload()

    def log(self, message: str) -> None:
        with open(self.DIR + "log.txt", "a") as file:
            file.write(message)

    def stopCurrentAnimation(self, loadDefault=True):
        if loadDefault and self.defaultAnimationPresent and self.currentAnimation.getName() != "default":
            self.loadAnimation("default.json")
        else:
            self.loadEmptyAnimation()

    def loadAnimation(self, fileName: str) -> animation:
        try:
            with open(self.animationDir + fileName) as file:
                data = json.load(file)
                if data["sound"] != "" and os.path.isfile(self.soundDir + data["sound"]):
                    return "Sound file not found"
                return animation(data["frames"], data["sound"], data["framerate"], fileName.removesuffix(".json"), data["loops"], data["repeatOnLoop"])
        except FileNotFoundError as fnfe:
            return f"Animation file not found {fnfe.filename}"

    def loadEmptyAnimation(self):
        emptyFrames = [[0, 0, 0] for frame in range(self.LED_COUNT)]
        self.currentAnimation = animation(emptyFrames, "", 1, "None")

    def command(self, command) -> str:
        self.commands.append(command)

    def startAnimation(self, animationFile: str):
        selectedAnimation = self.loadAnimation(animationFile)
        if isinstance(selectedAnimation, animation):
            self.currentAnimation = selectedAnimation
            return "OK"
        else:
            return selectedAnimation


# the real stuff here
can = bluetoinumContainer()
mixer.init()


@can.command
def meltdown(canister: bluetoinumContainer):
    return canister.startAnimation("meltdown")


@can.command
def testAnimation(canister: bluetoinumContainer):
    return canister.startAnimation("test.json")


@can.command
def fill(canister: bluetoinumContainer, color):
    canister.leds.fill(color)
    return "OK"


@can.command
def stop(canister: bluetoinumContainer) -> str:
    canister.stopCurrentAnimation(loadDefault=False)
    canister.active = False
    return "OK"


@can.command
def shutdown(canister: bluetoinumContainer) -> str:
    canister.stopCurrentAnimation(loadDefault=False)
    canister.active = False
    canister.shutdown = True
    return "OK"


@can.command
def stopCurrentAnimation(canister: bluetoinumContainer):
    return canister.stopCurrentAnimation


@can.command
def getCurrentAnimation(canister: bluetoinumContainer):
    return canister.currentAnimation.getName()


@can.command
def help(canister: bluetoinumContainer):
    return "Commands : " + ", ".join([x.__name__ for x in canister.commands])


@can.command
def getAnimationList(canister: bluetoinumContainer):
    return ", ".join(os.listdir(canister.animationDir))


@can.command
def getSoundList(canister: bluetoinumContainer):
    return ", ".join(os.listdir(canister.soundDir))


@can.command
def playSound(canister: bluetoinumContainer, soundFile: str):
    if os.path.isfile(canister.soundDir + soundFile):
        mixer.music.fadeout(500)
        mixer.music.unload()
        mixer.music.load(canister.soundDir + soundFile)
        mixer.music.play()


@can.command
def mute(canister: bluetoinumContainer, mute: bool = True):  # technically not muting, but shutup
    if mute:
        mixer.music.pause()
    else:
        mixer.music.unpause()
    return "OK"


@can.command
def playAnimation(canister: bluetoinumContainer, animation):
    return canister.startAnimation(animation)


shutdown = can.start()
print("stopping")
if shutdown:
    os.system("sudo shutdown -h now")

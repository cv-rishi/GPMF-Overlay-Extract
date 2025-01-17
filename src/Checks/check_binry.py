import subprocess
import sys


class CheckBinary:
    def __init__(self):
        self.binarys = ["ffmpeg", "ffprobe", "node", "npm", "python3", "pip3"]

    def check(self):
        try:
            for binary in self.binarys:
                subprocess.run(
                    [binary, "--version"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except FileNotFoundError:
            print(f"{binary} not found")
            return False

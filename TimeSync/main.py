import cv2
from pyzbar.pyzbar import decode
from PIL import Image
from datetime import datetime, timedelta
import subprocess
import os

from qr_decode import TimeCodeToUnix

# videos

# video 1 - Both start at same time, end at same time

video1 = [
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/1/IMG_5017.MOV",
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/1/VID20250123125420.mp4",
]

# video 2 - Both start at same time, 1 is shown qr code first, then 2

video2 = [
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/2/IMG_5018.MOV",
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/2/VID20250123125651.mp4",
]

# video 3 - i forgor, i think this is the one where they start at different times

video3 = [
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/3/IMG_5019.MOV",
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/3/VID20250123130033.mp4",
]

# video 4 - Qr code shown a3t different times

video4 = [
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/4/IMG_5020.MOV",
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/4/VID20250123130230.mp4",
]

# video 5 - Qr code shown at different times, diffrent framerates too.

video5 = [
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV",
    "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
]


"""
I have to sync multiple videos that have been recorded on diffrent cameras, and have diffrent framerates.

At some point in the video a qr code is shown that contains a unix timestamp. 

I have to then sync all the videos and display them side by side such that the videos look like diffrent pov's of the same event.
from qr_decode import TimeCodeToUnix

from PIL import Image
from pyzbar.pyzbar import decode
from datetime import datetime, timedelta


# Function to decode time from QR code data
def TimeCodeToUnix(qr_data):
    timestamp_str = qr_data.split("oT")[1].split("oTD")[0]
    timezone_offset_str = qr_data.split("oTZ")[1].split("oTI")[0]
    dt = datetime.strptime(timestamp_str, "%y%m%d%H%M%S.%f")
    timezone_offset_minutes = int(timezone_offset_str)
    timezone_offset = timedelta(minutes=timezone_offset_minutes)
    utc_dt = dt - timezone_offset
    unix_time = int(utc_dt.timestamp())
    return unix_time


returns the timestamp in unix time from the qr code data

I want to use ffmpeg to do most of the heavy lifiting, but i'm not sure how to do it.

My general thought process is.

for video in videos:
    make videos mp4/a common format without loosing data. (some videos are from gopros, i need to save the telimetry data.)
    find out frame rate, store it (accurate frame rate not rounded)

for video in videos: 
    blockify the video into 10-30 second blocks // can decide later (or will something like 300-600 frames blocks be better?)

    for block in blocks: 
        
        every 5 frames. 
            check for qr code 
                if qr code found, get timestamp 

    get list of all timestamps in the video. 

    now we can give a time to every single frame in the video.  

    now we can sync the videos by the timestamps for minimal error (most matching timestamps)

    trim the video (cut the start/end such that the excess is removed)

    now we can use ffmpeg to merge the videos.






"""

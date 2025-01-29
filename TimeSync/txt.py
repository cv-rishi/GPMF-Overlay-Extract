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





I have to sync multiple videos that have been recorded on diffrent cameras, and have diffrent framerates.

At some point in the video a qr code is shown that contains a unix timestamp.

I have to then sync all the videos and display them side by side such that the videos look like diffrent pov's of the same event.


this code goes through the video and finds all the frames that have a qr code, and then decodes the qr code to get the timestamp.

I need to first form pairs of frames to timestamp.

if any video shares a common timestamp => sync the video from that point.

if any video does not have a common timestamp => propogate timestamps to all the frames in the video.


lets say we find out frame 30 has timestap xyz, and frame 90 has frame abc. and now since we know the diffrence between the timestamps we can propogate the timestamps to all the frames in the video.

and for frames before / at the end of the video we can use the frame rate to calculate the timestamp.

to sync the video, trim both videos into seperate videos then display them side by side.

lets say video 1 starts at 10:00 am, and video 2 starts at 10:01 am, they record for 10+ mins and at the very end/at some point during the video both of them are shown qr codes seperatly. We need to first trim video 2 such that a minut of black screen is added at the start, and then we can sync the videos.



I have 2 videos i want to play side by side, synced up

I used qr codes that lead to unix time to find certian timestamps for certian frames in the video. 

both videos are of diffrent framerates, one is 30fps and the other is 120fps. 

I have to sync the videos such that they are displayed side by side and are synced up. 

I found the timestamps for the frames, and even found out which timestamp is shown in both video. 


in synced_videos/timestamps.json 


{
	"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4": [
		[1581, 1737598007],
		[1584, 1737598007],
		[1585, 1737598007],
		[1587, 1737598007],
		[1589, 1737598007],
		[1587, 1737598007],
		[1589, 1737598007],
		[1592, 1737598007],
		[1593, 1737598007],
		[1598, 1737598007],
		[1599, 1737598007],
		[1600, 1737598007],
		[1601, 1737598007],
		[1602, 1737598007],
		[1607, 1737598007],
		[1608, 1737598007],
		[1609, 1737598007],
		[1610, 1737598007],
		[1613, 1737598007],
		[1617, 1737598007],
		[1619, 1737598007],
		[1620, 1737598007],
		[1621, 1737598007],
		[1623, 1737598007],
		[1628, 1737598007],
		[1629, 1737598007],
		[1630, 1737598007],
		[1631, 1737598007],
		[1647, 1737598007],
		[1649, 1737598007],
		[1653, 1737598007],
		[1672, 1737598008],
		[1679, 1737598008],
		[1679, 1737598008],
		[1680, 1737598008],
		[1682, 1737598008],
		[1691, 1737598008],
		[1692, 1737598008],
		[1694, 1737598008],
		[1698, 1737598008],


	],
	"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV": [
		[395, 1737598006],
		[406, 1737598007],
		[407, 1737598007],
		[409, 1737598007],
		[411, 1737598007],
		[413, 1737598007],
		[417, 1737598007],
		[419, 1737598007],
		[421, 1737598007],
		[423, 1737598007],
		[424, 1737598007],
		[421, 1737598007],
		[423, 1737598007],
		[424, 1737598007],
		[425, 1737598007],
		[426, 1737598008],
		[427, 1737598008],
		[429, 1737598008],
		[426, 1737598008],
		[427, 1737598008],
		[429, 1737598008],
		[433, 1737598008],
		[456, 1737598009],
		[457, 1737598009],
		[459, 1737598009],
		[460, 1737598009],
		[461, 1737598009],


and in ./common_timestamps.json i have the common timestamps



{
	"1737598007": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598008": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598009": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598010": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598011": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598012": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598013": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598014": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598015": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598033": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	],
	"1737598034": [
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
		"/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV"
	]
}


I now need to sync the video such that everything side by side is happening at the same time. 


"""

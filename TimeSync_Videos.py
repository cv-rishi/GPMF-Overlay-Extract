import av
from pyzbar import pyzbar
from fractions import Fraction
import datetime
import time
import re
import pandas as pd
import numpy as np
import cv2
import sys

def detect_qr_code(frame):
	decoded_objects = pyzbar.decode(frame)
	for obj in decoded_objects:
		return obj.data.decode('utf-8')
	return None

def extract_unix_timestamp(qr_data):
    """Extracts the timestamp from the QR code data and converts it to a UNIX timestamp."""
    try:
        # Extract the portion of the string that represents the timestamp, e.g., '241126111248.96'
        # Assuming the format is YYMMDDHHMMSS.sss (Year, Month, Day, Hour, Minute, Second, Millisecond)
        timestamp_str = qr_data[2:17]  # Assuming the timestamp starts at index 2 (after 'oT')
        #print(f"Extracted timestamp string: {timestamp_str}")
        # Parse the string into a datetime object
        timestamp_dt = datetime.datetime.strptime(timestamp_str, "%y%m%d%H%M%S.%f")
        
        # Convert the datetime object to UNIX timestamp
        unix_timestamp = time.mktime(timestamp_dt.timetuple()) + timestamp_dt.microsecond / 1e6
        return unix_timestamp
    
    except (ValueError, IndexError):
        print("Failed to extract valid timestamp from QR code data")
        return None
	
def get_video_timestamp(vid, verbose=True):
	pattern = r'oT\d*.\d{3}'
	index = 0
	with(av.open(vid) as vid):
		# go through the frames till we find the first one with a matching qr and pattern
		for frame in vid.decode(streams=0): # video stream is usually stream 0
			if verbose:
				print('\r', index, end='          ')
				index +=1
			qr = detect_qr_code(frame.to_ndarray(format='rgb24'))
			if qr!=None: # is qr code detected
				if re.match(pattern, qr)!=None: # some other qr code
					time = extract_unix_timestamp(qr)
					frametime = frame.pts*vid.streams.video[0].time_base
					print(f'QR code: {qr} frame number: {index} pts: {frametime}')
					return time - frametime # hopefully this is the timestamp of the first frame of the video.
				
def get_video_times(vidfile, timestamp):
	times = []
	index = 0
	with av.open(vidfile) as vid:
		timebase = vid.streams.video[0].time_base
		for frame in vid.decode(streams=0):
			times.append(frame.pts*timebase + timestamp)
			print('\r', index, end='          ')
			index +=1
	df = pd.DataFrame(times)
	df.to_csv(vidfile[:-4] + '_timestamps.csv', index=False)
	
# def merge_timestamps(timefile1, timefile2, timefile3,timefile4, outfile):
	
# 	vid1_ts = pd.read_csv(timefile1)
# 	vid1_ts['timestamp1'] = vid1_ts['0']
# 	vid1_ts['index1'] = vid1_ts.index
	
# 	vid2_ts = pd.read_csv(timefile2)
# 	vid2_ts['timestamp2'] = vid2_ts['0']
# 	vid2_ts['index2'] = vid2_ts.index
	
# 	vid3_ts = pd.read_csv(timefile3)
# 	vid3_ts['timestamp3'] = vid3_ts['0']
# 	vid3_ts['index3'] = vid3_ts.index
# 	vid4_ts = pd.read_csv(timefile4)
# 	vid4_ts['timestamp4'] = vid4_ts['0']
# 	vid4_ts['index4'] = vid4_ts.index
	
# 	# merge the times
# 	merged1 = pd.merge_asof(vid1_ts, vid2_ts, left_on = 'timestamp1', right_on='timestamp2', direction='backward')
# 	merged2 = pd.merge_asof(merged1, vid3_ts, left_on = 'timestamp1', right_on='timestamp3', direction='backward')
# 	merged3 = pd.merge_asof(merged2, vid4_ts, left_on = 'timestamp1', right_on='timestamp4', direction= 'backward')
# 	merged = merged3.loc[:,['index1', 'index2', 'index3','index4']]
# 	merged.to_csv(outfile, index=False)

import pandas as pd

def merge_timestamps(timefile1, timefile2, timefile3, timefile4, outfile):
    # Read and rename the timestamp column
    vid1_ts = pd.read_csv(timefile1).rename(columns={'0': 'timestamp1'})
    vid1_ts['index1'] = vid1_ts.index

    vid2_ts = pd.read_csv(timefile2).rename(columns={'0': 'timestamp2'})
    vid2_ts['index2'] = vid2_ts.index

    vid3_ts = pd.read_csv(timefile3).rename(columns={'0': 'timestamp3'})
    vid3_ts['index3'] = vid3_ts.index

    vid4_ts = pd.read_csv(timefile4).rename(columns={'0': 'timestamp4'})
    vid4_ts['index4'] = vid4_ts.index

    # Merge timestamps
    merged1 = pd.merge_asof(vid1_ts, vid2_ts, left_on='timestamp1', right_on='timestamp2', direction='backward')
    merged2 = pd.merge_asof(merged1, vid3_ts, left_on='timestamp1', right_on='timestamp3', direction='backward')
    merged3 = pd.merge_asof(merged2, vid4_ts, left_on='timestamp1', right_on='timestamp4', direction='backward')

    # Keep only relevant columns
    merged = merged3[['index1', 'index2', 'index3', 'index4']]
    merged.to_csv(outfile, index=False)


def concat_videos(vid1, vid2, vid3,vid4, timestampfile, outfile):
	df = pd.read_csv(timestampfile)
	vid1 = av.open(vid1)
	stream1 = vid1.streams.video[0]
	vid2 = av.open(vid2)
	stream2 = vid2.streams.video[0]
	vid3 = av.open(vid3)
	stream3 = vid3.streams.video[0]
	vid4 = av.open(vid4)
	stream4 = vid4.streams.video[0]
	index1, index2, index3, index4 = 0,0,0,0
	
	outvid = av.open(outfile, 'w')
	outstream = outvid.add_stream("h264")
	
	outstream.options["bf"] = "0"
	outstream.options["movflags"] = "faststart"
	# outstream.gop_size = stream1.gop_size
	outstream.codec_context.height = stream1.height
	outstream.codec_context.width = stream1.width + stream2.width + stream3.width + stream4.width
	outstream.codec_context.time_base = stream1.time_base
	outstream.codec_context.bit_rate = stream1.bit_rate
	outstream.width = stream1.width + stream2.width + stream3.width + stream4.width
	outstream.height = stream1.height 
	fixed_height = stream1.height # Standardizing height
	
	with outvid:
		frame1 = next(vid1.decode(streams=0))
		frame2 = next(vid2.decode(streams=0))
		frame3 = next(vid3.decode(streams=0))
		frame4 = next(vid4.decode(streams=0))
		
		for index, row in df.iterrows():
			while index1< row['index1']:
				frame1 = next(vid1.decode(streams=0))
				index1 +=1
			while index2 < row['index2']:
				frame2 = next(vid2.decode(streams=0))
				index2 +=1
			while index3 < row['index3']:
				frame3 = next(vid3.decode(streams=0))
				index3+=1
			while index4 < row['index4']:
				frame4 = next(vid4.decode(streams=0))
				index4+=1
				
			frame1_arr = frame1.to_ndarray(format='rgb24')
			frame2_arr = frame2.to_ndarray(format='rgb24')
			frame3_arr = frame3.to_ndarray(format='rgb24')
			frame4_arr = frame4.to_ndarray(format='rgb24')
				
			frame2_arr = cv2.resize(frame2_arr, (frame2_arr.shape[1], fixed_height))
			frame3_arr = cv2.resize(frame3_arr, (frame3_arr.shape[1], fixed_height))
			frame4_arr = cv2.resize(frame4_arr, (frame4_arr.shape[1], fixed_height))
				
			# img = np.concatenate((frame1.to_ndarray(format='rgb24'), 
			# 					  frame2.to_ndarray(format='rgb24'),
			# 					 frame3.to_ndarray(format='rgb24'),
			# 					 frame4.to_ndarray(format='rgb24')), axis=1)
			img = np.concatenate((frame1_arr, frame2_arr, frame3_arr, frame4_arr), axis=1)
			
			new_frame = av.VideoFrame.from_ndarray(img, format="rgb24")
			new_frame.pts = frame1.pts
			# new_frame.time_base = outstream.time_base
			packets = outstream.encode(new_frame)
			outvid.mux(packets)
			# if index>1000: # uncomment this for checking.
			# 	break
			print(f'\r {index}', end='      ', flush=True)
		outvid.mux(outstream.encode())
		
		
if __name__== '__main__':
# concatenate dashcam and ego videos based on the sensor file which has corresponding frmes for dashcam and ego
	# arguments
	# 1: video 1 (the gaze video, used as reference
	# 2: video 2
	# 3: video 3
	# 4: output video filename
	vid1 = sys.argv[1]
	vid2 = sys.argv[2]
	vid3 = sys.argv[3]
	vid4 = sys.argv[4]
	outvid = sys.argv[5]
	
	print('Getting video cutoff times:  ')
	print(vid1,' :')
	timestamp1 = get_video_timestamp(vid1)
	print(vid2,' :')
	timestamp2 = get_video_timestamp(vid2)
	print(vid3,' :')
	timestamp3 = get_video_timestamp(vid3)
	print(vid4,':')
	timestamp4 = get_video_timestamp(vid4)

	print('Creating timestamp csv: ')
	print(vid1,' :')
	get_video_times(vid1, timestamp1)
	print(vid2, ' : ')
	get_video_times(vid2, timestamp2)
	print(vid3, ' : ')
	get_video_times(vid3, timestamp3)
	print(vid4, ' : ')
	get_video_times(vid4, timestamp4)
	

	merge_timestamps(vid1[:-4]+'_timestamps.csv', 
					 vid2[:-4] + '_timestamps.csv', 
					 vid3[:-4] + '_timestamps.csv',
					 vid4[:-4] + '_timestamps.csv',
					 'merged_timestamps.csv')
	

	print('Concatenating the videos....\n')
	concat_videos(vid1, vid2, vid3,vid4, 'merged_timestamps.csv', 'final_undistorted_output.mp4')
	# change here for the output file name
from PIL import Image
from pyzbar.pyzbar import decode
from datetime import datetime, timedelta
import cv2
from typing import List, Tuple, Dict


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


def find_qr_timestamps(video: str, block_size: int = 800) -> List[Tuple[int, float]]:
    """
    Find QR code timestamps in video

    Args:
        video (str): Path to video file
        block_size (int): Number of frames to process in each block

    Returns:
        List[Tuple[int, float]]: List of (frame_number, timestamp) pairs
    """
    cap = cv2.VideoCapture(video)
    timestamps = []
    frame_count = 0
    checked_ranges = set()

    while True:

        print(f"Processing frame {frame_count} of video {video}")
        block_timestamps = []
        for _ in range(block_size):
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % 5 == 0:
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

                decoded_objects = decode(pil_image)

                for obj in decoded_objects:
                    try:
                        timestamp = TimeCodeToUnix(obj.data.decode("utf-8"))
                        block_timestamps.append((frame_count, timestamp))
                        if timestamp:
                            print(f"Found timestamp: {timestamp}")
                            start = max(0, frame_count - 4)
                            end = min(frame_count + 5, frame_count + block_size)

                            if (start, end) not in checked_ranges:
                                checked_ranges.add((start, end))

                                cap.set(cv2.CAP_PROP_POS_FRAMES, start)
                                for check_frame in range(start, end):
                                    ret, check_image = cap.read()
                                    if not ret:
                                        break

                                    check_pil = Image.fromarray(
                                        cv2.cvtColor(check_image, cv2.COLOR_BGR2RGB)
                                    )
                                    check_decoded = decode(check_pil)

                                    for obj in check_decoded:
                                        try:
                                            timestamp = TimeCodeToUnix(
                                                obj.data.decode("utf-8")
                                            )
                                            timestamps.append((check_frame, timestamp))
                                            print(
                                                f"Found timestamp at frame {check_frame}: {timestamp}, from checking ±5"
                                            )
                                        except Exception as e:
                                            print(f"QR decode error: {e}")

                                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
                    except Exception as e:
                        print(f"QR decode error: {e}")

            frame_count += 1

        if not ret:
            break

    cap.release()
    return timestamps


def find_common_timestamps(video_timestamps) -> Dict[float, List[str]]:
    """
    Find common timestamps across videos, removing duplicates.

    Returns:
        Dict[float, List[str]]: Mapping of timestamps to unique videos
    """
    timestamp_videos = {}
    for video, timestamps in video_timestamps.items():
        for _, timestamp in timestamps:
            if timestamp not in timestamp_videos:
                timestamp_videos[timestamp] = set()
            timestamp_videos[timestamp].add(video)

    return {
        ts: list(videos) for ts, videos in timestamp_videos.items() if len(videos) > 1
    }

def propagate_timestamps_with_confidence(
    video_timestamps, video_info
) -> Dict[str, List[Tuple[int, float, int]]]:
    """
    Propagate timestamps to all frames for each video, with confidence levels:
    - 0: Directly detected from QR code
    - 1: Interpolated between two detected timestamps
    - 2: Extrapolated using frame rate (before/after known timestamps)
    
    All QR codes are stored with confidence 0, even if they seem inconsistent.
    
    Returns:
        Dict[str, List[Tuple[int, float, int]]]: Frame-wise timestamp propagation for all videos
    """
    propagated_timestamps = {}
    
    for video, timestamps in video_timestamps.items():
        video_metadata = video_info[video]
        frame_rate = video_metadata["exact_framerate"]
        total_frames = video_metadata["total_frames"]
        
        # Initialize with None for all frames
        frame_timestamps = [None] * total_frames
        
        # Store all QR code detections first
        qr_frames = {}
        for frame, timestamp in timestamps:
            frame_timestamps[frame] = (timestamp, 0)
            qr_frames[frame] = timestamp
            
        # Find the most reliable sequence of QR codes for interpolation
        sorted_qr_frames = sorted(qr_frames.items())
        reliable_sequence = []
        
        if len(sorted_qr_frames) > 1:
            current_sequence = [sorted_qr_frames[0]]
            best_sequence = current_sequence.copy()
            
            for i in range(1, len(sorted_qr_frames)):
                frame_diff = sorted_qr_frames[i][0] - current_sequence[-1][0]
                time_diff = sorted_qr_frames[i][1] - current_sequence[-1][1]
                expected_time_diff = frame_diff / frame_rate
                
                # Check if time difference is reasonable (within 10% of expected)
                if abs(time_diff - expected_time_diff) <= 0.1 * expected_time_diff:
                    current_sequence.append(sorted_qr_frames[i])
                    if len(current_sequence) > len(best_sequence):
                        best_sequence = current_sequence.copy()
                else:
                    current_sequence = [sorted_qr_frames[i]]
            
            reliable_sequence = best_sequence
        
        # If we found a reliable sequence, use it for interpolation
        if reliable_sequence:
            last_known_frame = reliable_sequence[0][0]
            last_known_timestamp = reliable_sequence[0][1]
            
            # Interpolate between reliable timestamps
            for i in range(len(reliable_sequence) - 1):
                current_frame = reliable_sequence[i][0]
                next_frame = reliable_sequence[i + 1][0]
                current_timestamp = reliable_sequence[i][1]
                next_timestamp = reliable_sequence[i + 1][1]
                
                # Interpolate frames between known timestamps
                for frame in range(current_frame + 1, next_frame):
                    if frame_timestamps[frame] is None:  # Don't override QR detections
                        progress = (frame - current_frame) / (next_frame - current_frame)
                        interpolated_time = current_timestamp + progress * (next_timestamp - current_timestamp)
                        frame_timestamps[frame] = (interpolated_time, 1)
            
            # Extrapolate before first reliable timestamp
            first_reliable_frame = reliable_sequence[0][0]
            first_reliable_time = reliable_sequence[0][1]
            for frame in range(first_reliable_frame - 1, -1, -1):
                if frame_timestamps[frame] is None:
                    extrapolated_time = first_reliable_time - ((first_reliable_frame - frame) / frame_rate)
                    frame_timestamps[frame] = (extrapolated_time, 2)
            
            # Extrapolate after last reliable timestamp
            last_reliable_frame = reliable_sequence[-1][0]
            last_reliable_time = reliable_sequence[-1][1]
            for frame in range(last_reliable_frame + 1, total_frames):
                if frame_timestamps[frame] is None:
                    extrapolated_time = last_reliable_time + ((frame - last_reliable_frame) / frame_rate)
                    frame_timestamps[frame] = (extrapolated_time, 2)
        
        # Convert to final format and store
        propagated_timestamps[video] = [
            (i, ts[0], ts[1]) 
            for i, ts in enumerate(frame_timestamps) 
            if ts is not None
        ]
    
    return propagated_timestamps

from PIL import Image
from pyzbar.pyzbar import decode
from datetime import datetime, timedelta
import cv2
from typing import List, Tuple, Dict


async def TimeCodeToUnix(qr_data):
    """
    Convert a QR code string to a Unix timestamp.

    The QR code string follows the format:
    "oTYYMMDDHHMMSS.SSSoTZ+/-MMMoTI+/-MMMoTD+/-MMMoT+/-MMMoT+/-MMM"

    Components:
    - `oT`: Marks the start of the timestamp.
    - `YYMMDDHHMMSS.SSS`: The date and time in the format (2-digit year, month, day, hour, minute, second, and milliseconds).
    - `oTZ+/-MMM`: Timezone offset in minutes from UTC.
    - `oTI+/-MMM`: Additional time offset (not currently used in this function).
    - `oTD+/-MMM`: Additional date offset (not currently used in this function).

    The function extracts the timestamp and timezone offset, adjusts for the offset,
    and returns the corresponding Unix timestamp.

    Args:
        qr_data: A string containing the QR code data.

    Returns:
        int: The Unix timestamp corresponding to the QR code data.

    Raises:
        ValueError: If the QR code data is not in the expected format.
    """
    timestamp_str = qr_data.split("oT")[1].split("oTD")[0]
    timezone_offset_str = qr_data.split("oTZ")[1].split("oTI")[0]
    dt = datetime.strptime(timestamp_str, "%y%m%d%H%M%S.%f")
    timezone_offset_minutes = int(timezone_offset_str)
    timezone_offset = timedelta(minutes=timezone_offset_minutes)
    utc_dt = dt - timezone_offset
    unix_time = int(utc_dt.timestamp())
    return unix_time


async def fetch_video_timestamps(video_path: str) -> List[Tuple[int, float]]:
    """
    Trys to fetch all timestamps shown as QR codes in the first 10 mins of the video.

    Checks if 1 in 5 frames contains a QR code, if a QR code is found, it checks the surrounding frames for more QR codes.

    Early exit if no subsequent QR codes are found in the next 800 frames.

    Args:
        video_path: The path to the video file.

    Returns:
        List[Tuple[int, float]]: A list of tuples containing the Unix timestamp and frame number for each QR code found in the video.
    """

    block_size = 800
    cap = cv2.VideoCapture(video_path)
    timestamps = []
    frame_count = 0
    checked_ranges = set()
    fps = cap.get(cv2.CAP_PROP_FPS)
    max_frames = int(600 * fps)  # 10 minutes * 60 seconds * fps
    last_qr_frame = max_frames

    while frame_count < max_frames:
        print(f"\rProcessing frame {frame_count} of video {video_path}", end="")
        block_timestamps = []
        qr_found = False

        for _ in range(block_size):
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % 5 == 0:
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                decoded_objects = decode(pil_image)

                for obj in decoded_objects:
                    try:
                        timestamp = await TimeCodeToUnix(obj.data.decode("utf-8"))
                        block_timestamps.append((frame_count, timestamp))
                        timestamps.append((frame_count, timestamp))
                        qr_found = True
                        # Check nearby frames (±5)
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
                                        timestamp = await TimeCodeToUnix(
                                            obj.data.decode("utf-8")
                                        )
                                        timestamps.append((check_frame, timestamp))
                                        print(
                                            f"\rFound timestamp at frame {check_frame}: {timestamp}",
                                            end="",
                                        )
                                    except IndexError: 
                                        print("IndexError: QR code data is not in the expected format, or the QR code is not a timestamp.")
                                    except Exception as e:
                                        print(f"QR decode error: {e}")

                            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
                    except Exception as e:
                        print(f"QR decode error: {e}")

            frame_count += 1

        if not ret:
            break

        if qr_found:
            last_qr_frame = frame_count  # Update last QR detection frame
        elif frame_count - last_qr_frame >= block_size:
            print("\nNo QR codes found in the last 800 frames. Exiting early.")
            print("\n__________________________________________________________")
            break

    cap.release()
    return timestamps

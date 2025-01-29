import cv2
from pyzbar.pyzbar import decode
from PIL import Image
from datetime import datetime, timedelta
import subprocess
import os

from qr_decode import TimeCodeToUnix


def extract_frames_with_ffmpeg(video_path, output_dir, frame_interval=15):
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-i",
        video_path,
        "-vf",
        f"select=not(mod(n\\,{frame_interval}))",
        "-vsync",
        "vfr",
        "-q:v",
        "2",
        os.path.join(output_dir, "frame_%06d.png"),
    ]
    subprocess.run(cmd)


# Detect QR codes in the extracted frames
def detect_qr_codes(frames_dir, extra_frames=30):
    timestamps = []
    frames = sorted(os.listdir(frames_dir))
    for frame in frames:
        frame_path = os.path.join(frames_dir, frame)
        image = Image.open(frame_path)
        decoded_objects = decode(image)
        for obj in decoded_objects:
            try:
                timestamp = TimeCodeToUnix(obj.data.decode("utf-8"))
                frame_number = int(frame.split("_")[1].split(".")[0])
                timestamps.append((frame_number, timestamp))
            except Exception as e:
                print(f"Error decoding QR code: {e}")
            break  # Only consider the first QR code per frame

    # Extend ranges with extra frames
    ranges = []
    for i, (frame, timestamp) in enumerate(timestamps):
        if i == 0 or frame > timestamps[i - 1][0] + 1:
            ranges.append(
                [max(0, frame - extra_frames), frame + extra_frames, timestamp]
            )
        else:
            ranges[-1][1] = frame + extra_frames

    return ranges


# Sync videos based on QR code timestamps
def sync_videos(video_paths, qr_ranges_list):
    base_timestamps = qr_ranges_list[0]
    offsets = []

    # Calculate offsets relative to the first video
    for i in range(1, len(qr_ranges_list)):
        other_timestamps = qr_ranges_list[i]
        base_time = base_timestamps[0][2]
        other_time = other_timestamps[0][2]
        offsets.append(other_time - base_time)

    # Trim and sync videos
    synced_videos = []
    for i, video_path in enumerate(video_paths):
        start_offset = offsets[i - 1] if i > 0 else 0
        output_path = f"synced_video_{i + 1}.mp4"
        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-ss",
            str(abs(start_offset)),
            "-c",
            "copy",
            output_path,
        ]
        if start_offset < 0:
            cmd.insert(4, "-t")  # Cut from the beginning if the offset is negative
        subprocess.run(cmd)
        synced_videos.append(output_path)

    return synced_videos


# Main workflow
def main(video_paths):
    all_qr_ranges = []
    for video_path in video_paths:
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        frames_dir = f"temp_frames_{video_name}"
        extract_frames_with_ffmpeg(video_path, frames_dir, frame_interval=15)
        qr_ranges = detect_qr_codes(frames_dir)
        all_qr_ranges.append(qr_ranges)
        # Clean up temporary frames
        subprocess.run(["rm", "-rf", frames_dir])

    synced_videos = sync_videos(video_paths, all_qr_ranges)
    print(f"Synced videos: {synced_videos}")


# Example usage
if __name__ == "__main__":
    video_paths = ["/media/teddy-bear/Extreme SSD/2W - Data_Capture/Front_view/GH019806.MP4", "/media/teddy-bear/Extreme SSD/2W - Data_Capture/Helmet_view/GH019814.MP4"]
    main(video_paths)

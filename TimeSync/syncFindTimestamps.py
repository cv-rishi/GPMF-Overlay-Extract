import cv2
import subprocess
import os
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image
from datetime import datetime, timedelta

from qr_decode import TimeCodeToUnix


class VideoSynchronizer:
    def __init__(self, videos):
        self.videos = videos
        self.video_info = {}

    def extract_video_metadata(self):
        """
        Extract detailed metadata for each video using FFprobe
        """

        for video in self.videos:
            cmd = [
                "ffprobe",
                "-v",
                "0",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=nb_frames,duration_ts,time_base",
                video,
            ]
            output = subprocess.check_output(cmd).decode("utf-8")

            # Parse output
            nb_frames = int(self._extract_value(output, "nb_frames"))
            duration_ts = int(self._extract_value(output, "duration_ts"))
            time_base_num, time_base_den = map(
                int, self._extract_value(output, "time_base").split("/")
            )

            # Calculate precise framerate
            precise_framerate = nb_frames / (duration_ts / time_base_den)

            self.video_info[video] = {
                "total_frames": nb_frames,
                "duration_ts": duration_ts,
                "time_base": (time_base_num, time_base_den),
                "exact_framerate": precise_framerate,
            }

    def _extract_value(self, output, key):
        """
        Extract specific value from FFprobe output
        """
        for line in output.split("\n"):
            if line.startswith(f"{key}="):
                return line.split("=")[1]
        raise ValueError(f"Could not find {key} in output")

    def find_qr_timestamps(self, video, block_size=800):
        """
        Find QR code timestamps in video blocks

        Args:
            video (str): Path to video file
            block_size (int): Number of frames to process in each block

        Returns:
            list: Timestamps found in the video
        """
        cap = cv2.VideoCapture(video)
        timestamps = []
        frame_count = 0

        while True:

            print(f"Processing frame {frame_count} of video {video}")
            # Process block of frames
            block_timestamps = []
            for _ in range(block_size):
                ret, frame = cap.read()
                if not ret:
                    break

                # Check every 5th frame for QR code
                if frame_count % 5 == 0:
                    # Convert OpenCV frame to PIL Image
                    pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

                    # Decode QR codes
                    decoded_objects = decode(pil_image)

                    for obj in decoded_objects:
                        try:
                            timestamp = TimeCodeToUnix(obj.data.decode("utf-8"))
                            block_timestamps.append((frame_count, timestamp))
                            if timestamp:
                                print(f"Found timestamp: {timestamp}")
                        except Exception as e:
                            print(f"QR decode error: {e}")

                frame_count += 1

            # Add block timestamps if found
            if block_timestamps:
                timestamps.extend(block_timestamps)

            # Break if no more frames
            if not ret:
                break

        cap.release()
        return timestamps

    def sync_videos(self, output_dir="synced_videos"):
        """
        Synchronize videos based on timestamp matches
        """
        os.makedirs(output_dir, exist_ok=True)

        # Extract metadata and timestamps
        self.extract_video_metadata()

        video_timestamps = {
            video: self.find_qr_timestamps(video) for video in self.videos
        }

        # Find best sync point (most matching timestamps)
        sync_points = {}
        for video, timestamps in video_timestamps.items():
            if timestamps:
                most_common_timestamp = max(
                    set(ts[1] for ts in timestamps),
                    key=[ts[1] for ts in timestamps].count,
                )
                sync_points[video] = [
                    ts[0] for ts in timestamps if ts[1] == most_common_timestamp
                ][0]

        # Trim and sync videos
        synced_videos = []
        for video in self.videos:
            start_frame = sync_points[video]
            output_video = os.path.join(output_dir, f"synced_{os.path.basename(video)}")

            # FFmpeg command to trim and process video
            cmd = [
                "ffmpeg",
                "-i",
                video,
                "-start_number",
                str(start_frame),
                "-vf",
                f"trim=start_frame={start_frame}",
                output_video,
            ]
            subprocess.run(cmd, check=True)
            synced_videos.append(output_video)

        # Optional: merge synced videos side by side
        self._merge_videos(
            synced_videos, os.path.join(output_dir, "final_synced_video.mp4")
        )

    def _merge_videos(self, videos, output_path):
        """
        Merge videos side by side, handling different orientations
        """
        # Get video resolutions and orientations
        video_info = []
        for video in videos:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=s=x:p=0",
                video,
            ]
            output = subprocess.check_output(cmd).decode("utf-8").strip()
            width, height = map(int, output.split("x"))
            is_portrait = height > width
            video_info.append(
                {
                    "path": video,
                    "width": width,
                    "height": height,
                    "is_portrait": is_portrait,
                }
            )

        # Determine consistent layout
        if any(info["is_portrait"] for info in video_info):
            # Use vertical stack for mixed orientations
            stack_type = "vstack"
        else:
            # Use horizontal stack for landscape videos
            stack_type = "hstack"

        # Create complex filter with scaling to match dimensions
        filter_complex = ""
        inputs = ""
        for i, info in enumerate(video_info):
            inputs += f'-i {info["path"]} '
            filter_complex += f"[{i}:v]scale=iw:ih[v{i}];"

        filter_complex += (
            " ".join(f"[v{i}]" for i in range(len(videos)))
            + f"{stack_type}=inputs={len(videos)}[v]"
        )

        # FFmpeg command
        cmd = f'ffmpeg {inputs} -filter_complex "{filter_complex}" -map "[v]" {output_path}'
        subprocess.run(cmd, shell=True, check=True)


# Usage example
if __name__ == "__main__":
    video_groups = [
        [
            "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/VID20250123130629.mp4",
            "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/5/IMG_5021.MOV",

        ]
    ]

    for video_group in video_groups:
        synchronizer = VideoSynchronizer(video_group)
        synchronizer.sync_videos()

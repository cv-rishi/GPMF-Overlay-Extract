import cv2
import subprocess
import os
from pyzbar.pyzbar import decode
from PIL import Image
from typing import List, Tuple, Dict
from qr_decode import TimeCodeToUnix
from pathlib import Path
import json


class VideoSynchronizer:
    def __init__(self, videos: List[str]):
        self.videos = videos
        self.video_info = {}
        self.video_timestamps: Dict[str, List[Tuple[int, float]]] = {}

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

    def find_qr_timestamps(
        self, video: str, block_size: int = 800
    ) -> List[Tuple[int, float]]:
        """
        Detect QR code timestamps in a video.

        Args:
            video (str): Path to the video file.
            block_size (int): Number of frames to process in each block.

        Returns:
            List[Tuple[int, float]]: List of (frame_number, timestamp) pairs.
        """
        cap = cv2.VideoCapture(video)
        timestamps = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % 5 == 0:  # Process every 5th frame
                pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                decoded_objects = decode(pil_image)

                for obj in decoded_objects:
                    try:
                        timestamp = TimeCodeToUnix(obj.data.decode("utf-8"))
                        timestamps.append((frame_count, timestamp))
                    except Exception as e:
                        print(f"QR decode error: {e}")

            frame_count += 1

        cap.release()
        return timestamps

    def populate_timestamps(self):
        """
        Populate detected timestamps for all videos.
        """
        for video in self.videos:
            self.video_timestamps[video] = self.find_qr_timestamps(video)

    def propagate_timestamps_with_confidence(self):
        """
        Propagate timestamps to all frames for each video, with confidence levels:
        - 0: Directly detected from QR code
        - 1: Interpolated between two detected timestamps
        - 2: Extrapolated using frame rate (before/after known timestamps)

        Returns:
            Dict[str, List[Tuple[int, float, int]]]: Frame-wise timestamp propagation for all videos
        """
        propagated_timestamps = {}

        for video, timestamps in self.video_timestamps.items():
            video_metadata = self.video_info[video]
            frame_rate = video_metadata["exact_framerate"]
            total_frames = video_metadata["total_frames"]

            # Initialize frame timestamps with None
            frame_timestamps = [None] * total_frames

            # Populate directly detected timestamps with confidence 0
            for frame, timestamp in timestamps:
                frame_timestamps[frame] = (timestamp, 0)

            # Forward and backward interpolation between detected timestamps
            last_known_frame = None
            last_known_timestamp = None

            for i in range(total_frames):
                if frame_timestamps[i] is not None:
                    # Update the last known values
                    last_known_frame, last_known_timestamp = i, frame_timestamps[i][0]
                elif last_known_frame is not None:
                    # Check if there's a future known frame
                    future_known_frame = next(
                        (
                            j
                            for j in range(i, total_frames)
                            if frame_timestamps[j] is not None
                        ),
                        None,
                    )

                    if future_known_frame is not None:
                        # Interpolate between last_known_frame and future_known_frame
                        future_known_timestamp = frame_timestamps[future_known_frame][0]
                        delta_frames = future_known_frame - last_known_frame
                        interpolated_timestamp = (
                            last_known_timestamp
                            + (i - last_known_frame)
                            * (future_known_timestamp - last_known_timestamp)
                            / delta_frames
                        )
                        frame_timestamps[i] = (interpolated_timestamp, 1)
                    else:
                        break

            # Extrapolate timestamps using frame rate (confidence 2)
            # Backward extrapolation
            for i in range(last_known_frame - 1, -1, -1):
                frame_timestamps[i] = (
                    frame_timestamps[i + 1][0] - (1 / frame_rate),
                    2,
                )

            # Forward extrapolation
            for i in range(last_known_frame + 1, total_frames):
                frame_timestamps[i] = (
                    frame_timestamps[i - 1][0] + (1 / frame_rate),
                    2,
                )

            # Store the propagated timestamps for this video
            propagated_timestamps[video] = [
                (i, ts[0], ts[1])
                for i, ts in enumerate(frame_timestamps)
                if ts is not None
            ]

        return propagated_timestamps

    def _find_common_timestamps(self) -> Dict[float, List[str]]:
        """
        Find common timestamps across videos, removing duplicates.

        Returns:
            Dict[float, List[str]]: Mapping of timestamps to unique videos
        """
        # Collect all unique timestamps
        timestamp_videos = {}
        for video, timestamps in self.video_timestamps.items():
            for _, timestamp, _ in timestamps:
                if timestamp not in timestamp_videos:
                    timestamp_videos[timestamp] = set()
                timestamp_videos[timestamp].add(video)

        # Filter timestamps that appear in multiple unique videos
        return {
            ts: list(videos)
            for ts, videos in timestamp_videos.items()
            if len(videos) > 1
        }

    def trim_and_merge_videos(self, sync_frames: Dict[str, int], output_file: str):
        """
        Trim and merge videos side by side based on sync frames.
        """
        # Calculate trimming times for each video
        trim_commands = []
        for video, sync_frame in sync_frames.items():
            metadata = self.video_info[video]
            frame_rate = metadata["exact_framerate"]
            sync_time = sync_frame / frame_rate

            # Trim video to start from sync_time
            trimmed_video = f"{Path(video).stem}_trimmed.mp4"
            cmd = [
                "ffmpeg",
                "-i",
                video,
                "-ss",
                str(sync_time),
                "-c:v",
                "h264_nvenc",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-y",
                trimmed_video,
            ]
            subprocess.run(cmd)
            trim_commands.append(trimmed_video)

        # Create side-by-side layout
        ffmpeg_filter = "hstack"
        cmd_merge = [
            "ffmpeg",
            "-i",
            trim_commands[0],
            "-i",
            trim_commands[1],
            "-filter_complex",
            ffmpeg_filter,
            "-c:v",
            "h264_nvenc",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-y",
            output_file,
        ]
        subprocess.run(cmd_merge)

    def sync_videos(self, output_dir="synced_videos"):
        """
        Synchronize videos based on propagated timestamps.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Extract video metadata
        self.extract_video_metadata()

        # Detect QR code timestamps
        self.populate_timestamps()

        # Propagate timestamps to all frames
        self.video_timestamps = self.propagate_timestamps_with_confidence()

        # Identify sync points (common timestamps)
        common_timestamps = self._find_common_timestamps()
        if not common_timestamps:
            print("No common timestamps found to synchronize videos.")
            return None

        reference_timestamp = list(common_timestamps.keys())[0]
        sync_frames = {}
        for video, timestamps in self.video_timestamps.items():
            sync_frame = next(
                (
                    frame
                    for frame, ts, confidence in timestamps
                    if ts == reference_timestamp
                ),
                None,
            )
            if sync_frame is not None:
                sync_frames[video] = sync_frame

        if len(sync_frames) < 2:
            print("Not enough videos to synchronize.")
            return None

        # Trim and merge videos
        self.trim_and_merge_videos(sync_frames, output_file=f"{output_dir}/output.mp4")


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

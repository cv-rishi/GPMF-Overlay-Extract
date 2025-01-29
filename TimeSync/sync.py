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
                                                timestamps.append(
                                                    (check_frame, timestamp)
                                                )
                                                print(
                                                    f"Found timestamp at frame {check_frame}: {timestamp}, from checking ±5"
                                                )
                                            except Exception as e:
                                                print(f"QR decode error: {e}")

                                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
                        except Exception as e:
                            print(f"QR decode error: {e}")

                frame_count += 1

            # Break if no more frames
            if not ret:
                break

        cap.release()
        return timestamps

    def _find_common_timestamps(self) -> Dict[float, List[str]]:
        """
        Find common timestamps across videos, removing duplicates.

        Returns:
            Dict[float, List[str]]: Mapping of timestamps to unique videos
        """
        # Collect all unique timestamps
        timestamp_videos = {}
        for video, timestamps in self.video_timestamps.items():
            for _, timestamp in timestamps:
                if timestamp not in timestamp_videos:
                    timestamp_videos[timestamp] = set()
                timestamp_videos[timestamp].add(video)

        # Filter timestamps that appear in multiple unique videos
        return {
            ts: list(videos)
            for ts, videos in timestamp_videos.items()
            if len(videos) > 1
        }

    def _calculate_frame_offsets(self):
        """
        Calculate frame offsets for each video based on common timestamps
        """
        common_timestamps = self._find_common_timestamps()

        # If no common timestamps, use frame rate to estimate
        if not common_timestamps:
            print("No common timestamps found. Unable to precisely synchronize.")
            return None

        # Choose the first common timestamp
        reference_timestamp = list(common_timestamps.keys())[0]
        reference_videos = common_timestamps[reference_timestamp]

        offsets = {}
        for video in self.videos:
            if video in reference_videos:
                offsets[video] = 0  # Reference video
            else:
                # Find closest timestamp in this video
                video_timestamps = self.video_timestamps[video]
                closest_timestamp = min(
                    video_timestamps, key=lambda x: abs(x[1] - reference_timestamp)
                )
                offset_frames = abs(closest_timestamp[0])
                offsets[video] = offset_frames

        return offsets

    def _calculate_diffrence(self, sync_frames: Dict) -> Dict:
        """
        Calculate the time from start of video to the sync frame, and the time from the sync frame to the end of the video for all videos
        """

    def sync_videos(self, output_dir="synced_videos"):
        """
        Synchronize videos based on common timestamps
        """
        os.makedirs(output_dir, exist_ok=True)

        timestamps = Path(output_dir) / "timestamps.json"

        self.extract_video_metadata()

        if timestamps.exists():
            with open(timestamps, "r") as f:
                self.video_timestamps = json.load(f)
        else:
            for video in self.videos:
                self.video_timestamps[video] = self.find_qr_timestamps(video)
                with open(timestamps, "w") as f:
                    json.dump(self.video_timestamps, f)

        print("Timestamps found:")
        common_timestamps = self._find_common_timestamps()

        if not common_timestamps:
            print(
                "No common timestamps found to synchronize videos, need to work on this"
            )
            return None

        reference_timestamp = list(common_timestamps.keys())[0]

        sync_frames = {}
        for video, timestamps in self.video_timestamps.items():
            sync_frame = next(
                (frame for frame, ts in timestamps if ts == reference_timestamp), None
            )
            if sync_frame is not None:
                sync_frames[video] = sync_frame

        if len(sync_frames) < 2:
            print("Not enough videos to synchronize.")
            return None

        time_diff = {}
        time_diff = self._calculate_diffrence(sync_frames)


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

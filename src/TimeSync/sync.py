import asyncio
from pathlib import Path
from typing import List, Tuple, Dict
import json
from .qr_decode import fetch_video_timestamps
from .trim_videos import extract_video_metadata, trim_videos


class VideoSynchronizer:
    def __init__(self, videos: List[str], output_dir):
        self.videos = videos
        self.video_info = {}
        self.video_timestamps: Dict[str, List[Tuple[int, float]]] = {}
        self.first_qr_timestamps = {}
        self.output_dir = output_dir

    def process_timestamps(self, timestamps: List[List[int]]) -> Tuple[int, float]:
        """Extract first unique timestamp and its frame number."""
        if not timestamps:
            return None
        return tuple(timestamps[0])  # Returns (frame, timestamp)

    async def sync(self):
        """
        Synchronize videos by trimming them to the same length based on the first QR code timestamp found in each video.

        Outputs trimmed videos to the specified output directory.

        Raises:
            ValueError: If no QR codes are found in the videos
            OSError: If FFmpeg fails to run on a video
        """
        await extract_video_metadata(self.videos, self.video_info)

        print("Detecting QR codes in videos...")
        for video in self.videos:
            timestamps = await fetch_video_timestamps(video)
            self.video_timestamps[video] = timestamps
            if timestamps:
                self.first_qr_timestamps[video] = self.process_timestamps(timestamps)
            else:
                print(
                    f"No QR codes found in {video}================================================================================================="
                )

        if not self.first_qr_timestamps:
            raise ValueError("No QR codes found in videos")

        latest_timestamp = max(ts[1] for ts in self.first_qr_timestamps.values())

        trim_points = {}
        for video, (frame, timestamp) in self.first_qr_timestamps.items():
            fps = self.video_info[video]["exact_framerate"]
            time_diff = latest_timestamp - timestamp
            frame_offset = int(time_diff * fps)
            trim_points[video] = [frame + frame_offset, latest_timestamp]

        with open("trim_points.json", "w") as f:
            json.dump(trim_points, f)

        trimmed_videos = await trim_videos(
            trim_points, self.video_info, self.output_dir
        )

        return trimmed_videos


if __name__ == "__main__":
    videos = [
        "/media/teddy-bear/Extreme SSD/test_videos/aria.mp4",
        "/media/teddy-bear/Extreme SSD/test_videos/rear.MP4",
        "/media/teddy-bear/Extreme SSD/test_videos/helmet.MP4",
        "/media/teddy-bear/Extreme SSD/test_videos/headlight.MP4",
    ]
    synchronizer = VideoSynchronizer(videos)
    asyncio.run(synchronizer.sync())

import subprocess
import os
from typing import List, Tuple, Dict
from pathlib import Path
import json

from qr_decode import (
    find_qr_timestamps,
    find_common_timestamps,
    propagate_timestamps_with_confidence,
)
from create_video import (
    extract_video_metadata,
    create_black_frame,
    trim_and_merge_videos,
    split_and_merge_videos,
)


class VideoSynchronizer:
    def __init__(self, videos: List[str]):
        self.videos = videos
        self.video_info = {}
        self.video_timestamps: Dict[str, List[Tuple[int, float]]] = {}

    def sync_videos(self, output_dir="synced_videos"):
        """
        Synchronize videos based on common timestamps, with fallback to closest matches
        using confidence levels.
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamps = Path(output_dir) / "timestamps.json"
        self.video_info = extract_video_metadata(self.videos, self.video_info)

        # Load or generate timestamps
        if timestamps.exists():
            with open(timestamps, "r") as f:
                self.video_timestamps = json.load(f)
        else:
            for video in self.videos:
                self.video_timestamps[video] = find_qr_timestamps(video)
                with open(timestamps, "w") as f:
                    json.dump(self.video_timestamps, f)

        print("Timestamps found:")
        common_timestamps = find_common_timestamps(self.video_timestamps)
        with open("common_timestamps.json", "w") as f:
            json.dump(common_timestamps, f)

        sync_frames = None

        if common_timestamps:
            # Try direct QR code matches first
            reference_timestamp = list(common_timestamps.keys())[0]
            sync_frames = {}
            for video, timestamps in self.video_timestamps.items():
                sync_frame = next(
                    (frame for frame, ts in timestamps if ts == reference_timestamp),
                    None,
                )
                if sync_frame is not None:
                    sync_frames[video] = sync_frame

        if not sync_frames or len(sync_frames) < len(self.videos):
            # Use propagated timestamps with confidence levels
            propagated_timestamps = propagate_timestamps_with_confidence(
                self.video_timestamps, self.video_info
            )
            with open("propagated_timestamps.json", "w") as f:
                json.dump(propagated_timestamps, f)

            # Try finding common timestamps at each confidence level
            for confidence in [0, 1, 2]:
                sync_frames = self.find_common_timestamps_by_confidence(
                    propagated_timestamps, confidence
                )
                if sync_frames and len(sync_frames) == len(self.videos):
                    print(f"Found common timestamps with confidence level {confidence}")
                    break

            # If no exact matches, find closest timestamps
            if not sync_frames or len(sync_frames) < len(self.videos):
                sync_frames = self.find_closest_timestamps(propagated_timestamps)
                print("Using closest matching timestamps")

        if sync_frames:
            split_and_merge_videos(sync_frames, f"{output_dir}/split.mp4")
        else:
            print("Could not find suitable sync points")
            return

    def find_common_timestamps_by_confidence(
        self,
        propagated_timestamps: Dict[str, List[Tuple[int, float, int]]],
        target_confidence: int,
    ) -> Dict[str, int]:
        """
        Find common timestamps across videos at a specific confidence level.
        """
        # Extract timestamps at the target confidence level
        timestamps_by_video = {}
        for video, timestamps in propagated_timestamps.items():
            timestamps_by_video[video] = [
                (frame, ts)
                for frame, ts, conf in timestamps
                if conf == target_confidence
            ]

        # Find common timestamps
        common_times = set()
        first_video = list(timestamps_by_video.keys())[0]

        for _, ts in timestamps_by_video[first_video]:
            is_common = all(
                any(abs(t - ts) < 0.001 for _, t in video_timestamps)
                for video_timestamps in timestamps_by_video.values()
            )
            if is_common:
                common_times.add(ts)

        if not common_times:
            return None

        # Get frames for the first common timestamp
        reference_time = min(common_times)
        sync_frames = {}

        for video, timestamps in timestamps_by_video.items():
            for frame, ts in timestamps:
                if abs(ts - reference_time) < 0.001:
                    sync_frames[video] = frame
                    break

        return sync_frames if len(sync_frames) == len(propagated_timestamps) else None

    def find_closest_timestamps(
        self, propagated_timestamps: Dict[str, List[Tuple[int, float, int]]]
    ) -> Dict[str, int]:
        """
        Find the timestamps across videos with minimum time difference.
        Prioritizes higher confidence matches.
        """
        videos = list(propagated_timestamps.keys())
        min_diff = float("inf")
        best_frames = {}

        # Priority order for confidence level combinations
        confidence_priorities = [
            (1, 1),  # Both confidence 1
            (1, 2),  # Mix of confidence 1 and 2
            (2, 2),  # Both confidence 2
        ]

        for conf1, conf2 in confidence_priorities:
            for v1_frame, v1_ts, v1_conf in propagated_timestamps[videos[0]]:
                if v1_conf != conf1:
                    continue

                for v2_frame, v2_ts, v2_conf in propagated_timestamps[videos[1]]:
                    if v2_conf != conf2:
                        continue

                    time_diff = abs(v1_ts - v2_ts)
                    if time_diff < min_diff:
                        min_diff = time_diff
                        best_frames = {videos[0]: v1_frame, videos[1]: v2_frame}

            if best_frames:  # If we found matches at this confidence priority, use them
                break

        return best_frames if best_frames else None


# Usage example
if __name__ == "__main__":
    video_groups = [
        [
            "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/6/IMG_5045.MOV",
            "/media/teddy-bear/Extreme SSD/time sync raw tests/time sync/6/VID20250126113004.mp4",
            # "/media/teddy-bear/Extreme SSD/2W - Data_Capture/Front_view/GH019806.MP4",
            # "/media/teddy-bear/Extreme SSD/2W - Data_Capture/Helmet_view/GH019814.MP4",
        ]
    ]

    for video_group in video_groups:
        synchronizer = VideoSynchronizer(video_group)
        synchronizer.sync_videos()

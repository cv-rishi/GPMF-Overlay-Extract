# import json
# import subprocess
# from datetime import datetime
# import os
# from typing import List, Dict
#
#
# def load_shut_data(file_path: str) -> List[Dict]:
#     """Load and parse SHUT telemetry data from JSON file."""
#     with open(file_path, "r") as f:
#         data = json.load(f)
#     return data["samples"]
#
#
# def find_common_time(data_list: List[List[Dict]]) -> datetime:
#     """Find the earliest common timestamp across all videos."""
#     timestamps = []
#     for data in data_list:
#         # Remove 'Z' and parse as ISO format
#         timestamp = datetime.fromisoformat(data[0]["date"].replace("Z", "+00:00"))
#         timestamps.append(timestamp)
#     return max(timestamps)  # Use latest start time as common point
#
#
# def calculate_offsets(
#     data_list: List[List[Dict]], common_start: datetime
# ) -> List[float]:
#     """Calculate time offsets for each video relative to common start time."""
#     offsets = []
#     for data in data_list:
#         first_time = datetime.fromisoformat(data[0]["date"].replace("Z", "+00:00"))
#         offset = (first_time - common_start).total_seconds()
#         offsets.append(abs(offset))  # Use absolute value for ffmpeg
#     return offsets
#
#
# def build_filter_complex(num_videos: int) -> str:
#     """Generate filter_complex string based on number of videos."""
#     if num_videos == 2:
#         return "hstack=inputs=2"  # Side by side
#     elif num_videos == 3:
#         return "[0][1]hstack=inputs=2[top];[top][2]vstack=inputs=2"  # 2 on top, 1 on bottom
#     elif num_videos == 4:
#         return "[0][1]hstack=inputs=2[top];[2][3]hstack=inputs=2[bottom];[top][bottom]vstack=inputs=2"  # 2x2 grid
#     else:
#         raise ValueError(f"Unsupported number of videos: {num_videos}")
#
#
# def sync_videos(video_paths: List[str], offsets: List[float], output_path: str):
#     """Sync and combine multiple videos using ffmpeg."""
#     # Create temporary files for trimmed videos
#     temp_files = []
#     try:
#         # First pass: Trim videos to sync points
#         for i, (video, offset) in enumerate(zip(video_paths, offsets)):
#             temp_file = f"temp_video_{i}.mp4"
#             temp_files.append(temp_file)
#
#             trim_cmd = [
#                 "ffmpeg",
#                 "-y",
#                 "-i",
#                 video,
#                 "-ss",
#                 str(offset),
#                 "-c:v",
#                 "copy",
#                 "-c:a",
#                 "copy",
#                 temp_file,
#             ]
#             subprocess.run(trim_cmd, check=True)
#
#         # Second pass: Combine videos
#         filter_complex = build_filter_complex(len(video_paths))
#
#         combine_cmd = ["ffmpeg", "-y"]
#         # Add input files
#         for temp_file in temp_files:
#             combine_cmd.extend(["-i", temp_file])
#
#         combine_cmd.extend(
#             [
#                 "-filter_complex",
#                 filter_complex,
#                 "-c:v",
#                 "h264_nvenc",
#                 "-preset",
#                 "p4",  # RTX optimized preset
#                 "-tune",
#                 "hq",
#                 "-rc",
#                 "vbr",  # Variable bitrate
#                 "-cq",
#                 "23",  # Quality-based VBR
#                 "-b:v",
#                 "20M",  # Maximum bitrate
#                 "-maxrate",
#                 "25M",
#                 "-bufsize",
#                 "25M",
#                 "-profile:v",
#                 "high",
#                 "-spatial_aq",
#                 "1",
#                 "-temporal_aq",
#                 "1",
#                 output_path,
#             ]
#         )
#
#         subprocess.run(combine_cmd, check=True)
#
#     finally:
#         # Clean up temp files
#         for temp_file in temp_files:
#             if os.path.exists(temp_file):
#                 os.remove(temp_file)
#
#
# def main():
#     # File paths configuration
#     shut_files = ["front_View.json", "helmet_view.json"]
#
#     video_files = [
#         "/media/teddy-bear/Extreme SSD/2W - Data_Capture/Front_view/GH019806.MP4",
#         "/media/teddy-bear/Extreme SSD/2W - Data_Capture/Helmet_view/GH019814.MP4",
#     ]
#
#     output_file = "synced_videos.mp4"
#
#     try:
#         # Load SHUT data for all videos
#         data_list = [load_shut_data(file) for file in shut_files]
#
#         # Find common start time
#         common_start = find_common_time(data_list)
#         print(f"Common start time: {common_start}")
#
#         # Calculate offsets
#         offsets = calculate_offsets(data_list, common_start)
#         print(f"Video offsets: {offsets}")
#
#         # Sync and combine videos
#         sync_videos(video_files, offsets, output_file)
#         print(f"Successfully created synchronized video: {output_file}")
#
#     except Exception as e:
#         print(f"Error: {str(e)}")
#
#
# if __name__ == "__main__":
#     main()


import json
import subprocess
from datetime import datetime
import os
from typing import List, Dict


class VideoSync:
    def __init__(self, video_paths: List[str], shut_files: List[str], output_path: str):
        """
        Initialize the VideoSync object.

        :param video_paths: List of paths to the video files.
        :param shut_files: List of paths to the SHUT telemetry JSON files.
        :param output_path: Path to save the synchronized output video.
        """
        self.video_paths = video_paths
        self.shut_files = shut_files
        self.output_path = output_path

    def load_shut_data(self, file_path: str) -> List[Dict]:
        """Load and parse SHUT telemetry data from a JSON file."""
        with open(file_path, "r") as f:
            data = json.load(f)
        return data["samples"]

    def find_common_time(self, data_list: List[List[Dict]]) -> datetime:
        """Find the earliest common timestamp across all videos."""
        timestamps = []
        for data in data_list:
            timestamp = datetime.fromisoformat(data[0]["date"].replace("Z", "+00:00"))
            timestamps.append(timestamp)
        return max(timestamps)  # Use the latest start time as the common point

    def calculate_offsets(
        self, data_list: List[List[Dict]], common_start: datetime
    ) -> List[float]:
        """Calculate time offsets for each video relative to the common start time."""
        offsets = []
        for data in data_list:
            first_time = datetime.fromisoformat(data[0]["date"].replace("Z", "+00:00"))
            offset = (first_time - common_start).total_seconds()
            offsets.append(abs(offset))  # Use absolute value for ffmpeg
        return offsets

    def build_filter_complex(self, num_videos: int) -> str:
        """Generate a filter_complex string based on the number of videos."""
        if num_videos == 2:
            return "hstack=inputs=2"  # Side by side
        elif num_videos == 3:
            return "[0][1]hstack=inputs=2[top];[top][2]vstack=inputs=2"  # 2 on top, 1 on bottom
        elif num_videos == 4:
            return "[0][1]hstack=inputs=2[top];[2][3]hstack=inputs=2[bottom];[top][bottom]vstack=inputs=2"  # 2x2 grid
        else:
            raise ValueError(f"Unsupported number of videos: {num_videos}")

    def sync_videos(self):
        """Sync and combine multiple videos using ffmpeg."""
        # Load SHUT data for all videos
        data_list = [self.load_shut_data(file) for file in self.shut_files]

        # Find the common start time
        common_start = self.find_common_time(data_list)
        print(f"Common start time: {common_start}")

        # Calculate offsets for each video
        offsets = self.calculate_offsets(data_list, common_start)
        print(f"Video offsets: {offsets}")

        # Create temporary files for trimmed videos
        temp_files = []
        try:
            # First pass: Trim videos to sync points
            for i, (video, offset) in enumerate(zip(self.video_paths, offsets)):
                temp_file = f"temp_video_{i}.mp4"
                temp_files.append(temp_file)

                trim_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    video,
                    "-ss",
                    str(offset),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    temp_file,
                ]
                subprocess.run(trim_cmd, check=True)

            # Second pass: Combine videos
            filter_complex = self.build_filter_complex(len(self.video_paths))

            combine_cmd = ["ffmpeg", "-y"]
            # Add input files
            for temp_file in temp_files:
                combine_cmd.extend(["-i", temp_file])

            combine_cmd.extend(
                [
                    "-filter_complex",
                    filter_complex,
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    "p4",  # RTX optimized preset
                    "-tune",
                    "hq",
                    "-rc",
                    "vbr",  # Variable bitrate
                    "-cq",
                    "23",  # Quality-based VBR
                    "-b:v",
                    "20M",  # Maximum bitrate
                    "-maxrate",
                    "25M",
                    "-bufsize",
                    "25M",
                    "-profile:v",
                    "high",
                    "-spatial_aq",
                    "1",
                    "-temporal_aq",
                    "1",
                    self.output_path,
                ]
            )

            subprocess.run(combine_cmd, check=True)
            print(f"Successfully created synchronized video: {self.output_path}")

        finally:
            # Clean up temp files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync multiple GoPro videos.")
    parser.add_argument(
        "--videos",
        nargs="+",
        required=True,
        help="List of video file paths.",
    )
    parser.add_argument(
        "--shut-files",
        nargs="+",
        required=True,
        help="List of SHUT telemetry JSON file paths.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the synchronized video.",
    )

    args = parser.parse_args()

    video_sync = VideoSync(
        video_paths=args.videos,
        shut_files=args.shut_files,
        output_path=args.output,
    )
    video_sync.sync_videos()

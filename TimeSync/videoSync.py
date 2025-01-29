import json
import subprocess
import os


class VideoSynchronizer:
    def __init__(self, timestamps_path, common_timestamps_path):
        self.timestamps_path = timestamps_path
        self.common_timestamps_path = common_timestamps_path
        self.videos = []
        self.video_info = {}
        self.timestamps = {}
        self.common_timestamps = {}

    def _extract_value(self, output, key):
        """
        Extract specific value from FFprobe output
        """
        for line in output.split("\n"):
            if line.startswith(f"{key}="):
                return line.split("=")[1]
        return None

    def extract_video_metadata(self):
        """
        Extract detailed metadata for each video using FFprobe
        """
        # Load video paths from timestamps
        with open(self.timestamps_path, "r") as f:
            self.timestamps = json.load(f)
        self.videos = list(self.timestamps.keys())

        for video in self.videos:
            cmd = [
                "ffprobe",
                "-v",
                "0",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=nb_frames,duration_ts,time_base,width,height,r_frame_rate",
                "-of",
                "csv=p=0",
                video,
            ]
            output = subprocess.check_output(cmd).decode("utf-8").strip().split(",")

            nb_frames = int(output[0])
            duration_ts = int(output[1])
            time_base = list(map(int, output[2].split("/")))
            width = output[3]
            height = output[4]
            frame_rate = output[5]

            # Calculate precise framerate
            precise_framerate = nb_frames / (duration_ts / time_base[1])

            self.video_info[video] = {
                "total_frames": nb_frames,
                "duration_ts": duration_ts,
                "time_base": time_base,
                "exact_framerate": precise_framerate,
                "width": width,
                "height": height,
                "frame_rate": frame_rate,
            }

    def sync_videos(self):
        """
        Synchronize videos side by side with black screens
        """
        # Load common timestamps
        with open(self.common_timestamps_path, "r") as f:
            self.common_timestamps = json.load(f)

        # Find the first common timestamp
        first_common_timestamp = min(map(int, self.common_timestamps.keys()))

        # Find corresponding frames for each video
        video_sync_points = {}
        for video_path in self.videos:
            # Find the frame index closest to the first common timestamp
            sync_frame = min(
                self.timestamps[video_path],
                key=lambda x: abs(x[1] - first_common_timestamp),
            )[0]
            video_sync_points[video_path] = sync_frame

        # Prepare output paths
        output_videos = []
        for i, video_path in enumerate(self.videos):
            output_path = f"synced_video_{i}.mp4"
            output_videos.append(output_path)

            # Get video metadata
            metadata = self.video_info[video_path]

            # Prepare black screen generation command
            black_screen_cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                f'color=black:s={metadata["width"]}x{metadata["height"]}:r={metadata["frame_rate"]}',
                "-i",
                video_path,
                "-filter_complex",
                f"[0:v][1:v]overlay=shortest=1:x=0:y=0",
                "-c:v",
                "libx264",
                "-c:a",
                "copy",
                output_path,
            ]

            subprocess.run(black_screen_cmd, check=True)

        # Create side-by-side video
        side_by_side_cmd = [
            "ffmpeg",
            "-i",
            output_videos[0],
            "-i",
            output_videos[1],
            "-filter_complex",
            "hstack",
            "synced_side_by_side.mp4",
        ]
        subprocess.run(side_by_side_cmd, check=True)

        # Clean up intermediate files
        for video in output_videos:
            os.remove(video)

        print("Video synchronization complete. Output: synced_side_by_side.mp4")


def main():
    # Paths to your JSON files
    timestamps_path = "./synced_videos/timestamps.json"
    common_timestamps_path = "./common_timestamps.json"

    # Create synchronizer
    synchronizer = VideoSynchronizer(timestamps_path, common_timestamps_path)

    # Extract metadata
    synchronizer.extract_video_metadata()

    # Synchronize videos
    synchronizer.sync_videos()


if __name__ == "__main__":
    main()

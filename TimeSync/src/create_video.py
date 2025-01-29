import subprocess
from typing import List, Dict
from pathlib import Path


def extract_video_metadata(videos: List[str], video_info: Dict) -> Dict:
    """
    extract detailed metadata for each video using ffprobe
    """

    for video in videos:
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

        # parse output
        nb_frames = int(_extract_value(output, "nb_frames"))
        duration_ts = int(_extract_value(output, "duration_ts"))
        time_base_num, time_base_den = map(
            int, _extract_value(output, "time_base").split("/")
        )

        # calculate precise framerate
        precise_framerate = nb_frames / (duration_ts / time_base_den)

        video_info[video] = {
            "total_frames": nb_frames,
            "duration_ts": duration_ts,
            "time_base": (time_base_num, time_base_den),
            "exact_framerate": precise_framerate,
        }

    return video_info


def _extract_value(output, key):
    """
    Extract specific value from FFprobe output
    """
    for line in output.split("\n"):
        if line.startswith(f"{key}="):
            return line.split("=")[1]
    raise ValueError(f"Could not find {key} in output")


def create_black_frame(reference_video, black_frame_video):
    # Get video resolution using ffprobe with multiple parsing methods
    try:
        # Try first method
        cmd_resolution = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            reference_video,
        ]
        resolution_output = subprocess.check_output(cmd_resolution).decode()
        import json

        resolution_data = json.loads(resolution_output)

        width = resolution_data["streams"][0]["width"]
        height = resolution_data["streams"][0]["height"]
    except Exception as e:
        # Fallback to a default resolution if detection fails
        print(f"Resolution detection failed: {e}")
        width, height = 1920, 1080  # Default to 1080p

    # Create black frame matching input video's resolution
    cmd_black_frame = [
        "ffmpeg",
        "-f",
        "lavfi",
        "-i",
        f"color=black:s={width}x{height}:r=30",
        "-t",
        "1",
        "-c:v",
        "libx264",
        "-y",
        black_frame_video,
    ]
    subprocess.run(cmd_black_frame, check=True)


def trim_and_merge_videos(
    self, sync_frames: Dict[str, int], output_file: str, output_dir="synced_videos"
):
    """
    Trim and merge videos side by side based on sync frames.
    """
    longest_duration = max(
        self.video_info[video]["total_frames"]
        / self.video_info[video]["exact_framerate"]
        for video in self.videos
    )
    trim_commands = []
    for video, sync_frame in sync_frames.items():
        metadata = self.video_info[video]
        frame_rate = metadata["exact_framerate"]
        sync_time = sync_frame / frame_rate
        trimmed_video = f"{output_dir}/{Path(video).stem}_trimmed.mp4"
        cmd_trim = [
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
        subprocess.run(cmd_trim)

        black_frame_video = f"{output_dir}/black_frame.mp4"
        self.create_black_frame(video, black_frame_video)

        padded_video = f"{output_dir}/{Path(video).stem}_padded.mp4"
        cmd_pad = [
            "ffmpeg",
            "-stream_loop",
            "-1",
            "-i",
            black_frame_video,
            "-t",
            str(longest_duration),
            "-i",
            trimmed_video,
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0[out]",
            "-map",
            "[out]",
            "-c:v",
            "h264_nvenc",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-y",
            padded_video,
        ]
        subprocess.run(cmd_pad)
        trim_commands.append(padded_video)

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


def split_and_merge_videos(
    sync_frames: Dict[str, int], output_file: str, output_dir="synced_videos"
):
    """
    Split videos at sync frames and merge parts side by side.
    Creates 2 output videos: pre-sync merged and post-sync merged.
    Uses frame-perfect splitting instead of time-based trimming.
    """
    trim_commands_pre = []
    trim_commands_post = []

    for video, sync_frame in sync_frames.items():
        # Extract pre-sync frames (0 to sync_frame-1)
        pre_sync = f"{output_dir}/{Path(video).stem}_pre_sync.mp4"
        cmd_pre = [
            "ffmpeg",
            "-i",
            video,
            "-vf",
            f"select=between(n\\,0\\,{sync_frame-1})",
            "-vsync",
            "0",  # Maintain frame accuracy
            "-c:v",
            "h264_nvenc",  # Use libx264 instead of nvenc
            "-preset",
            "medium",
            "-crf",
            "23",
            "-an",  # Remove audio to avoid sync issues
            "-y",
            pre_sync,
        ]
        subprocess.run(cmd_pre, check=True)

        # Extract post-sync frames (sync_frame to end)
        post_sync = f"{output_dir}/{Path(video).stem}_post_sync.mp4"
        cmd_post = [
            "ffmpeg",
            "-i",
            video,
            "-vf",
            f"select=gte(n\\,{sync_frame})",
            "-vsync",
            "0",  # Maintain frame accuracy
            "-c:v",
            "h264_nvenc",  # Use libx264 instead of nvenc
            "-preset",
            "medium",
            "-crf",
            "23",
            "-an",  # Remove audio to avoid sync issues
            "-y",
            post_sync,
        ]
        subprocess.run(cmd_post, check=True)

        trim_commands_pre.append(pre_sync)
        trim_commands_post.append(post_sync)

        # normalize the videoes that got split

    print(trim_commands_pre)
    print(trim_commands_post)
    normalize_videos(trim_commands_pre, 0)
    normalize_videos(trim_commands_post, 1)


def normalize_videos(videos: list[str], state: bool, output_dir="synced_videos"):
    """
    Get length of both videos, if state is 0, thats pre-sync, else post-sync

    for pre-sync, we normalize the video longer video to be as short at the shorter video trim from the start of the video
    for post-sync, we normalize the video longer video to be as short at the shorter video trim from the end of the video
    """

    video_info = extract_video_metadata(videos, {})

    if state == 0:
        # pre-sync

        shortest_video_length = min(
            video_info[video]["total_frames"] / video_info[video]["exact_framerate"]
            for video in videos
        )

        for video in videos:
            if (
                video_info[video]["total_frames"] / video_info[video]["exact_framerate"]
                > shortest_video_length
            ):
                # video is longer than the shortest video
                cmd = [
                    "ffmpeg",
                    "-i",
                    video,
                    "-t",
                    str(shortest_video_length),
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-y",
                    f"{output_dir}/{Path(video).stem}_normalized.mp4",
                ]
                subprocess.run(cmd)

    if state == 1:
        # post-sync

        shortest_video_length = min(
            video_info[video]["total_frames"] / video_info[video]["exact_framerate"]
            for video in videos
        )

        for video in videos:
            if (
                video_info[video]["total_frames"] / video_info[video]["exact_framerate"]
                > shortest_video_length
            ):
                # video is longer than the shortest video
                cmd = [
                    "ffmpeg",
                    "-i",
                    video,
                    "-ss",
                    str(
                        video_info[video]["total_frames"]
                        / video_info[video]["exact_framerate"]
                        - shortest_video_length
                    ),
                    "-c:v",
                    "h264_nvenc",
                    "-preset",
                    "fast",
                    "-crf",
                    "23",
                    "-y",
                    f"{output_dir}/{Path(video).stem}_normalized.mp4",
                ]
                subprocess.run(cmd)

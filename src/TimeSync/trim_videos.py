import subprocess
from typing import Dict, List
import json
import os
from pathlib import Path


async def _extract_value(output, key):
    """
    extract specific value from ffprobe output

    Args:
        output: ffprobe output
        key: key to extract

    Returns:
        value corresponding to key

    Raises:
        ValueError: if key not found in output
    """
    for line in output.split("\n"):
        if line.startswith(f"{key}="):
            return line.split("=")[1]
    raise ValueError(f"could not find {key} in output")


async def extract_video_metadata(videos: List[str], video_info: Dict) -> Dict:
    """
    extract detailed metadata for each video using ffprobe

    Args:
        videos: list of video file paths
        video_info: dictionary to store metadata

    Returns:
        video_info: dictionary containing metadata for each video

    Raises:
        subprocess.CalledProcessError: if ffprobe fails to run on a video
        ValueError: if required metadata is not found in ffprobe output
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

        nb_frames = int(await _extract_value(output, "nb_frames"))
        duration_ts = int(await _extract_value(output, "duration_ts"))
        time_base_str = await _extract_value(output, "time_base")
        time_base_num, time_base_den = map(int, time_base_str.split("/"))

        precise_framerate = nb_frames / (duration_ts / time_base_den)

        video_info[video] = {
            "total_frames": nb_frames,
            "duration_ts": duration_ts,
            "time_base": (time_base_num, time_base_den),
            "exact_framerate": precise_framerate,
        }

    return video_info


async def trim_videos(
    start_frames: Dict[str, List],
    video_info: Dict,
    output_dir: str = "trimmed_videos",
) -> Dict[str, str]:
    """
    Trim videos from specified start frames using FFmpeg.

    Args:
        start_frames: Dictionary with video paths as keys and [start_frame, timestamp] as values
        output_dir: Directory to save trimmed videos
        use_copy: If True, uses copy codec (faster but may have inaccurate cuts).
                 If False, uses NVENC (clean cuts but requires re-encoding)

    Returns:
        Dictionary with original video paths as keys and output paths as values
    """
    os.makedirs(output_dir, exist_ok=True)
    output_paths = {}

    for video_path, (start_frame, _) in start_frames.items():
        try:
            input_path = Path(video_path)
            sanitized_filename = "_".join(input_path.parts[1:])
            sanitized_filename = sanitized_filename.replace(" ", "_")
            output_video_path = Path(output_dir) / f"trimmed_{sanitized_filename}"

            output_paths[video_path] = str(output_video_path)

        #         sanitized_filename = "_".join(input_path.parts[1:])
        # sanitized_filename = sanitized_filename.replace(" ", "_")
        # output_video_path = Path(output_dir) / f"trimmed_{sanitized_filename}"

            print(f"\nProcessing {input_path.name}...")

            fps = video_info[video_path]["exact_framerate"]

            start_time = start_frame / fps

            cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file if exists
                "-ss",
                str(start_time),  # Start time
                "-i",
                str(input_path),  # Input file
                "-c",
                "copy",  # Copy streams without re-encoding
                str(output_video_path),
            ]

            print(f"Running FFmpeg command: {' '.join(cmd)}")

            subprocess.run(cmd, check=True)

        except Exception as e:
            print(f"Error processing {input_path.name}: {str(e)}")
            continue

    return output_paths


async def stack_videos_horizontally(
    trimmed_videos: Dict[str, str], output_path: str = "stacked_output.mp4"
):
    """
    Stack trimmed videos side by side.

    Args:
        trimmed_videos: Dictionary of original video paths and their trimmed output paths.
        output_path: Output file for stacked video.

    Returns:
        Path to the stacked video.
    """
    video_files = list(trimmed_videos.values())

    if len(video_files) < 2:
        print("At least two videos are required for stacking.")
        return None

    filter_complex = ";".join(
        [f"[{i}:v]scale=1280:720[v{i}]" for i in range(len(video_files))]
    )
    hstack_inputs = (
        "".join([f"[v{i}]" for i in range(len(video_files))])
        + f"hstack=inputs={len(video_files)}[stacked]"
    )

    cmd = [
        "ffmpeg",
        "-y",
    ]

    # Add input files
    for file in video_files:
        cmd.extend(["-i", file])

    cmd.extend(
        [
            "-filter_complex",
            f"{filter_complex};{hstack_inputs}",
            "-map",
            "[stacked]",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "18",
            output_path,
        ]
    )

    print(f"Running FFmpeg command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    return output_path

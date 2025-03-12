try:
    import sys
    import shutil
    import subprocess
    import pathlib
    from pathlib import Path
    import datetime
    import os
    import json
    import asyncio

except Exception:
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip3", "install", "-r", "requirements.txt"]
        )
    except Exception as e:
        print(e)
        print("Error: Unable to install required python packages.")
        sys.exit(1)


from src.Checks.check_binry import CheckBinary
from src.Checks.arguments import GPMF_arguments

from src.ExtractExif.ExtractEif import ExtractEif
from src.Checks.log import log, fatal

from src.TimeSync.sync import VideoSynchronizer

from src.Merger.merge import VideoMerger


def create_directory_structure(base_dir: Path, driver_name: str) -> dict:
    """
    Creates the directory structure for organizing video files
    Args:
        base_dir: Base directory path
        driver_name: Name of the driver
    Returns:
        Dictionary containing paths for each video type
    """
    # Create date folder (e.g., Day1_05_02_2024)
    current_date = datetime.datetime.now().strftime("Day1_%d_%m_%Y")
    date_dir = base_dir / current_date

    # Create driver folder
    driver_dir = date_dir / driver_name

    # Create view directories
    view_dirs = {
        "front": driver_dir / "FrontView",
        "helmet": driver_dir / "HelmentView",
        "back": driver_dir / "RearView",
        "glasses": driver_dir / "GLassesView",
    }

    # Create all directories
    for dir_path in view_dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return view_dirs


def assert_file_exists(path):
    """
    Check if the file exists
    Args:
        path: Path to the file or list of paths
    Returns:
        path to file if it exists, else raise an error
    """
    if isinstance(path, list):
        # If path is a list, check each item in the list
        for p in path:
            if not p.exists():
                fatal(f"{p}: File not found")
        return path
    else:
        # Handle single path
        if not path.exists():
            fatal(f"{path}: File not found")
        return path


def get_video_files(directory: pathlib.Path) -> list[pathlib.Path]:
    """
    Get all video files from a directory

    Args:
        directory: Path to the directory containing videos

    Returns:
        List of paths to video files
    """
    video_extensions = [".mp4", ".MP4", ".mov", ".MOV"]
    video_files = []

    for ext in video_extensions:
        video_files.extend(directory.glob(f"*{ext}"))

    if not video_files:
        fatal(f"No video files found in directory: {directory}")

    return sorted(video_files)


def extract_data(
    video_dir: Path, video_type: str, driver_name: str, base_output_dir: Path
):
    """
    Extract telemetry data from video files and combine data from same sensors
    Args:
        video_dir: Directory containing the video files
        video_type: Type of the video (front, helmet, back)
        driver_name: Name of the driver
    """
    if video_type == "aria" or video_type == "pupil":
        return

    current_date = datetime.datetime.now().strftime("Day1_%d_%m_%Y")
    # Determine base output directory
    if base_output_dir is None:
        base_output_dir = Path("telemetry_data")

    # Create full output directory path
    output_dir = base_output_dir / current_date / driver_name / f"{video_type}Telemetry"
    os.makedirs(output_dir, exist_ok=True)

    # Convert single path to list if needed
    videos = video_dir if isinstance(video_dir, list) else [video_dir]

    # Extract data from each video
    for video_path in videos:
        temp_output_dir = Path(f"tempData_{video_type}_{video_path.stem}")
        extractor = ExtractEif(
            input_file=video_path,
            video_type=video_type,
            driver_name=driver_name,
        )
        os.makedirs(temp_output_dir, exist_ok=True)
        extractor.extract_telemetry()

    temp_dirs = [d for d in Path().glob(f"tempData_{video_type}_*") if d.is_dir()]
    if not temp_dirs:
        print(f"No temporary data directories found for {video_type} videos")
        return

    combined_data = {}
    sensor_types = [
        "ACCL",
        "GYRO",
        "SHUT",
        "WRGB",
        "YAVG",
        "SCEN",
        "GPS5",
        "IORI",
        "WNDM",
        "AALP",
        "LSKP",
        "WBAL",
        "ISOE",
        "UNIF",
        "HUES",
        "CORI",
        "GRAV",
        "MWET",
        "MSKP",
    ]

    # Process each sensor type
    for sensor in sensor_types:
        # Initialize with metadata from first file if available
        sensor_metadata = None
        all_samples = []

        # Combine data from all temporary directories
        for temp_dir in sorted(temp_dirs):
            sensor_file = temp_dir / f"{sensor}.json"
            if sensor_file.exists():
                try:
                    with open(sensor_file, "r") as f:
                        data = json.load(f)
                        if not sensor_metadata and isinstance(data, dict):
                            # Store metadata (name, units) from first file
                            sensor_metadata = {
                                key: value
                                for key, value in data.items()
                                if key != "samples"
                            }

                        # Extract samples
                        if isinstance(data, dict) and "samples" in data:
                            all_samples.extend(data["samples"])
                        elif isinstance(data, list):
                            all_samples.extend(data)

                except json.JSONDecodeError:
                    print(f"Error reading {sensor_file}")
                    continue

        if all_samples:
            if isinstance(all_samples[0], dict) and "cts" in all_samples[0]:
                all_samples.sort(key=lambda x: x["cts"])

            if sensor_metadata:
                sensor_data = {**sensor_metadata, "samples": all_samples}
            else:
                sensor_data = {"samples": all_samples}

            combined_data[sensor] = sensor_data

            output_file = output_dir / f"{sensor}_combined.json"
            with open(output_file, "w") as f:
                json.dump(sensor_data, f, indent=4)
            print(f"Combined {sensor} data saved to {output_file}")

    # Clean up temporary directories
    for temp_dir in temp_dirs:
        try:
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Error cleaning up {temp_dir}: {e}")


def merge_all_perspectives(required_dirs: dict, output_dir: Path, driver: str):
    """
    Merge trimmed videos with their subsequent videos for all perspectives
    Args:
        trimmed_path_file: Path to the JSON file containing trimmed video paths
        required_dirs: Dictionary containing lists of video paths for each perspective
    """
    merger = VideoMerger()

    merged_dir = output_dir / "MergedVideos"
    merged_dir.mkdir(exist_ok=True)

    view_dirs = create_directory_structure(output_dir, driver)

    for prespective, videos in required_dirs.items():
        original_video = videos[0]

        trimmed_video = "_".join(original_video.parts[1:])
        trimmed_video = trimmed_video.replace(" ", "_")
        trimmed_video = Path("trimmed_videos") / f"trimmed_{trimmed_video}"

        merged_video = merged_dir / f"merged_{prespective}.mp4"

        print(f"Merging {prespective} videos:")
        merger.merge_camera_videos(trimmed_video, videos[1:], merged_video)

        # Now split the merged video into 10-minute segments.
        print(f"Splitting merged {prespective} video into 10-minute segments...")
        split_video_into_segments(
            merged_video, view_dirs[prespective], segment_length=600
        )


def split_video_into_segments(
    input_video: Path, output_directory: Path, segment_length: int = 600
):
    """
    Splits a video into segments of fixed length using ffmpeg with -c copy.

    Args:
        input_video: Path to the merged video.
        output_directory: Directory to save the segments.
        segment_length: Segment length in seconds (default 600s = 10 minutes).
    """
    output_directory.mkdir(parents=True, exist_ok=True)
    output_pattern = str(output_directory / "Video_%03d.mp4")

    command = [
        "ffmpeg",
        "-i",
        str(input_video),
        "-c",
        "copy",
        "-f",
        "segment",
        "-segment_time",
        str(segment_length),
        "-reset_timestamps",
        "1",
        output_pattern,
    ]

    try:
        # Use shell=True to ensure consistent behavior with terminal execution
        subprocess.run(
            command,
            check=True,
            shell=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(f"Successfully split {input_video} into segments in {output_directory}")
    except subprocess.CalledProcessError as e:
        print(f"Error splitting video {input_video}: {e}")
        print(f"Command output: {e.stderr}")


if __name__ == "__main__":
    check = CheckBinary()
    check.check()
    args = GPMF_arguments()
    log(f"Starting GPMF extraction with arguments: {args}")

    required_dirs = {
        "front": args.front_videos,
        "helmet": args.helmet_videos,
        "back": args.back_videos,
    }

    if args.glasses_type == "aria":
        required_dirs.update({"aria": args.glasses_videos})
    elif args.glasses_type == "pupil":
        required_dirs.update({"pupil": args.glasses_videos})

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path("/media/teddy-bear/Extreme SSD/tmp")

    driver = args.driver_name

    for view, directory in required_dirs.items():
        assert_file_exists(directory)
        log(f"Processing {view} video files from {directory}")
        extract_data(directory, view, driver, output_dir)

    log("GPMF extraction completed")

    sorted_perspectives = {
        "front": args.front_videos[0],
        "helmet": args.helmet_videos[0],
        "back": args.back_videos[0],
    }

    if args.glasses_type == "aria":
        sorted_perspectives["aria"] = args.glasses_videos[0]

    elif args.glasses_type == "pupil":
        sorted_perspectives["pupil"] = args.glasses_videos[0]
    #
    # # print("Starting video synchronization With the following videos:")
    # #
    # # for video in sorted_perspectives.values():
    # #     print(video)
    # #
    # # synchronizer = VideoSynchronizer(
    # #     [
    # #         str(sorted_perspectives["glasses"]),
    # #         str(sorted_perspectives["helmet"]),
    # #         str(sorted_perspectives["front"]),
    # #         str(sorted_perspectives["back"]),
    # #     ],
    # #     "trimmed_videos",
    # # )
    # #
    # # asyncio.run(synchronizer.sync())
    # #
    # # log("Video synchronization completed")
    # #
    # # log("Begin merging")
    # #
    # # merge_all_perspectives(
    # #     required_dirs,
    # #     output_dir,
    # #     args.driver_name,
    # # )

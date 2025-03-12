import argparse
import pathlib
from .log import fatal


def GPMF_arguments(args=None):
    parser = argparse.ArgumentParser(
        description="Overlay gadgets onto GoPro MP4",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--front_videos",
        type=pathlib.Path,
        required=True,
        nargs="+",
        help="List of front-facing video files in chronological order",
    )
    parser.add_argument(
        "--helmet_videos",
        type=pathlib.Path,
        required=True,
        nargs="+",
        help="List of helmet-mounted video files in chronological order",
    )
    parser.add_argument(
        "--back_videos",
        type=pathlib.Path,
        required=True,
        nargs="+",
        help="List of rear-facing video files in chronological order",
    )
    parser.add_argument(
        "--glasses_videos",
        type=pathlib.Path,
        required=True,
        nargs="+",
        help="List of glasses-mounted video files in chronological order",
    )
    parser.add_argument(
        "--driver_name", type=str, required=True, help="Name of the driver"
    )

    parser.add_argument(
        "--glasses_type",
        type=str,
        choices=["aria", "pupil"],
        required=True,
    )
    parser.add_argument(
        "--output_dir",
        type=pathlib.Path,
        help="Output directory for processed videos",
    )

    parser.add_argument(
        "--layout-xml", type=pathlib.Path, help="Use XML File for layout"
    )
    parser.add_argument(
        "--overlay-flags", type=str, help="Overlay flags, comma separated list of flags"
    )
    parser.add_argument(
        "--extract_data",
        action="store_true",
        help="Extract sensor data from all videos",
    )
    parser.add_argument(
        "--overlay_video",
        action="store_true",
        help="Overlay video for all provided videos",
    )

    args = parser.parse_args(args)

    # Validate that provided paths are files
    for video_list in [
        args.front_videos,
        args.helmet_videos,
        args.back_videos,
        args.glasses_videos,
    ]:
        for video_path in video_list:
            if not video_path.is_file():
                fatal(f"'{video_path}' is not a file")
            if not any(
                video_path.name.upper().endswith(ext) for ext in [".MP4", ".MOV"]
            ):
                fatal(f"'{video_path}' is not a video file (must be .mp4 or .mov)")

    return args


def process_video_files(args) -> dict:
    """
    Process video files and return a dictionary of video files
    Args:
        args: Parsed command line arguments
    Returns:
        Dictionary containing lists of video files for each camera position
    """
    return {
        "front": list(args.front_videos),
        "helmet": list(args.helmet_videos),
        "back": list(args.back_videos),
        "glasses": list(args.glasses_videos),
    }

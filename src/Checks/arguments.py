import argparse
import pathlib
import sys

from .log import fatal


def GPMF_arguments(args=None):

    parser = argparse.ArgumentParser(
        description="Overlay gadgets on to GoPro MP4",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "input",
        type=pathlib.Path,
        nargs="+",
        help="Input MP4 file",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="Output Video File - MP4/MOV/WEBM format, need to configure ffmpeg profile for other formats other than MP4",
    )

    parser.add_argument(
        "--layout-xml", type=pathlib.Path, help="Use XML File for layout"
    )

    parser.add_argument(
        "--overlay-flags", type=str, help="Overlay flags, comma separated list of flags"
    )

    parser.add_argument(
        "--extract_data",
        type=bool,
        help="Extract sensor data from all videos if gopro videos are not specified",
    )

    parser.add_argument(
        "--gopro_videos", type=pathlib.Path, nargs="+", help="GoPro videos"
    )

    parser.add_argument(
        "--overlay_video",
        type=bool,
        help="Overlay video for all videos if gopro videos are not specified",
    )

    parser.add_argument(
        "--sensor_video_sync",
        type=bool,
        help="Sync video with sensor data for all videos if gopro videos are not specified",
    )

    parser.add_argument(
        "--video_sync",
        type=bool,
        help="Sync video with uni time qr codes for all videos.",
    )

    args = parser.parse_args(args)

    def quit(reason):
        parser.print_help(file=sys.stderr)
        fatal(f"Invalid arguments: {reason}")

    return args

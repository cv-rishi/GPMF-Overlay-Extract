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
        "output",
        type=pathlib.Path,
        help="Output Video File - MP4/MOV/WEBM format, need to configure ffmpeg profile for other formats other than MP4",
    )

    parser.add_argument(
        "--layout-xml", type=pathlib.Path, help="Use XML File for layout"
    )

    parser.add_argument(
        "--overlay-flags", type=str, help="Overlay flags, comma separated list of flags"
    )

    args = parser.parse_args(args)

    def quit(reason):
        parser.print_help(file=sys.stderr)
        fatal(f"Invalid arguments: {reason}")

    return args

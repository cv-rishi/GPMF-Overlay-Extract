try:
    import sys
    import subprocess
    from typing import Optional
    from pathlib import Path

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
from src.TimeSync.sync import VideoSync
from src.Checks.log import log, fatal


def assert_file_exists(path: Path) -> Path:
    """
    Check if the file exists

    Args:
        path: Path to the file

    Returns:
        path to file if it exists, else raise an error
    """
    if not path.exists():
        fatal(f"{path}: File not found")
    return path


if __name__ == "__main__":
    check = CheckBinary()
    check.check()

    args = GPMF_arguments()

    log(f"Starting GPMF extraction with arguments: {args}")

    inputpath: Optional[Path] = None
    outputpath: Optional[Path] = None
    output_videos = []

    try:
        input_files = [assert_file_exists(f) for f in args.input]

        videos = input_files

        if args.output:
            output_dir = Path(args.output)
        else:
            output_dir = Path("output")

        output_dir.mkdir(parents=True, exist_ok=True)

        if args.extract_data:
            if args.gopro_videos:
                videos = args.gopro_videos
            else:
                videos = input_files
            for input_file in videos:
                video_name = input_file.stem
                video_output_dir = output_dir / video_name
                video_output_dir.mkdir(parents=True, exist_ok=True)

                extractor = ExtractEif(
                    input_file=input_file, output_dir=video_output_dir
                )
                extractor.extract_telemetry()

        if args.overlay_video:
            if args.gopro_videos:
                videos = args.gopro_videos

            layout_xml = (
                Path(args.layout_xml)
                if args.layout_xml
                else Path("src/gopro-dashboard-overlay/1920x1820.xml")
            )

            if not layout_xml.exists():
                fatal(f"Layout XML file not found: {layout_xml}")

            for input_file in videos:
                video_name = input_file.stem
                video_output_dir = output_dir / video_name
                output_video_path = video_output_dir / "output.mp4"
                debug_file_path = video_output_dir / "debug.txt"

                gopro_dashboard_cmd = [
                    "python3",
                    "src/gopro-dashboard-overlay/gopro-dashboard.py",
                    "--layout-xml",
                    str(layout_xml),
                    str(input_file),
                    str(output_video_path),
                    "--debug-metadata",
                ]

                if args.overlay_flags:
                    gopro_dashboard_cmd.extend(["--overlay-flags", args.overlay_flags])

                log(f"Running gopro-dashboard.py for {input_file}")

                with open(debug_file_path, "w") as debug_file:
                    try:
                        subprocess.run(
                            gopro_dashboard_cmd,
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                        )
                        output_videos.append(str(output_video_path))
                        log(f"Overlay generation completed: {output_video_path}")
                    except subprocess.CalledProcessError as e:
                        log(f"Error details: {e.stderr}")
                        log(
                            f"Error running gopro-dashboard.py for {input_file}. Please check {debug_file_path} for details."
                        )

                print(f"Output video: {output_video_path}")

        if args.sync_videos:
            if args.go_pro_videos:
                videos = args.go_pro_videos

            synced_video_dir = output_dir / "synced_videos"
            shut_files = []

            for input_file in videos:
                video_name = input_file.stem
                video_output_dir = output_dir / video_name
                shut_file = video_output_dir / "SHUT.json"
                if not shut_file.exists():
                    fatal(f"Missing SHUT telemetry file: {shut_file}")
                shut_files.append(str(shut_file))

            synced_video_path = synced_video_dir / "video.mp4"

            log(f"Syncing videos into: {synced_video_path}")
            video_sync = VideoSync(
                video_paths=videos,
                shut_files=shut_files,
                output_path=str(synced_video_path),
            )
            video_sync.sync_videos()

    except KeyboardInterrupt:
        log("User interrupted...")
    except Exception as e:
        fatal(f"Error: {e}")

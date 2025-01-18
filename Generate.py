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
from src.Checks.log import log, fatal


def assert_file_exists(path: Path) -> Path:
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

    try:
        input_files = [assert_file_exists(f) for f in args.input]

        layout_xml = (
            Path(args.layout_xml)
            if args.layout_xml
            else Path("src/gopro-dashboard-overlay/1920x1820.xml")
        )

        if not layout_xml.exists():
            fatal(f"Layout XML file not found: {layout_xml}")

        overlay_flags = None

        if args.overlay_flags:
            overlay_flags = args.overlay_flags

        output_dir = Path(args.output)

        output_dir.mkdir(parents=True, exist_ok=True)

        for input_file in input_files:
            video_name = input_file.stem
            video_output_dir = output_dir / video_name
            video_output_dir.mkdir(parents=True, exist_ok=True)

            extractor = ExtractEif(input_file=input_file, output_dir=video_output_dir)
            extractor.extract_telemetry()
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

            if overlay_flags:
                gopro_dashboard_cmd.extend(["--overlay-flags", overlay_flags])

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
                    log(f"Overlay generation completed: {output_video_path}")
                except subprocess.CalledProcessError as e:
                    log(f"Error details: {e.stderr}")
                    log(
                        f"Error running gopro-dashboard.py for {input_file}. Please check {debug_file_path} for details."
                    )

            print(f"Output video: {output_video_path}")

    except KeyboardInterrupt:
        log("User interrupted...")
    except Exception as e:
        fatal(f"Error: {e}")


# MODULE_NOT_FOUND

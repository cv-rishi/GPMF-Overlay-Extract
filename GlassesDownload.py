import requests
import argparse
import subprocess
import pathlib
import shutil
import os
import zipfile
import sys
from datetime import date
from dateutil.parser import parse
from pytz import timezone
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()


def ensure_dir_exists(dir_path):
    """Create directory if it doesn't exist and verify creation"""
    try:
        os.makedirs(dir_path, exist_ok=True)
        if not os.path.exists(dir_path):
            raise Exception(f"Failed to create directory {dir_path}")
        print(f"Ensured directory exists: {dir_path}")
    except Exception as e:
        raise Exception(f"Error creating directory {dir_path}: {e}")


def download_file(url, filename, headers):
    """Download a file from a URL to a specified filename"""
    try:
        with requests.get(url, headers=headers, stream=True) as response:
            response.raise_for_status()
            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False


def download_aria(input_file, output_dir, extra=None):
    """Process Aria data files"""
    print(f"Getting eye gaze data from {input_file}")

    base_name = os.path.basename(input_file)
    input_dir = os.path.dirname(input_file)

    command = [
        "aria_mps",
        "single",
        "-i",
        input_file,
        "--features",
        "EYE_GAZE",
        "HAND_TRACKING",
        "--force",
        "--retry-failed",
        "--no-ui",
    ]

    if extra:
        command.extend(extra)

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return False

    print("Download complete")

    try:
        json_file = os.path.join(input_dir, f"{base_name}.json")
        if os.path.exists(json_file):
            output_json = os.path.join(output_dir, f"{base_name}.json")
            print(f"Moving {json_file} to {output_json}")
            shutil.copy2(json_file, output_json)
            os.remove(json_file)

        mps_dir = os.path.join(input_dir, f"mps_{base_name.replace('.', '_')}")
        if os.path.exists(mps_dir):
            output_mps_dir = os.path.join(
                output_dir, f"mps_{base_name.replace('.', '_')}"
            )
            print(f"Moving {mps_dir} to {output_mps_dir}")
            if os.path.exists(output_mps_dir):
                shutil.rmtree(output_mps_dir)
            shutil.copytree(mps_dir, output_mps_dir)
            shutil.rmtree(mps_dir)

    except Exception as e:
        print(f"Error moving files: {e}")
        return False

    print(f"Downloading video for {input_file} and saving it as {base_name}.mp4")
    command = [
        "vrs_to_mp4",
        "--vrs",
        input_file,
        "--output_video",
        f"{output_dir}/{base_name}.mp4",
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(
            "If its a moviepy error, downgrade to moviepy==1.0.3 or upgrade above commit add099e"
        )
        return False

    return True


def download_pupil_zip(zip_file, output_dir):
    """Extract Pupil zip file to output directory"""
    print(f"Extracting Pupil data from {zip_file} to {output_dir}")

    zip_file = os.path.abspath(os.path.expanduser(zip_file))
    ensure_dir_exists(output_dir)

    try:
        with zipfile.ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(output_dir)
        print("Extraction complete")
        return True
    except Exception as e:
        print(f"Error extracting zip file: {e}")
        return False


def download_pupil_by_date(date_str, output_dir):
    """Download Pupil data for a specific date"""
    try:
        given_date = date.fromisoformat(date_str)
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD.")
        return False

    api_key = os.environ.get("PUPIL_API_KEY")
    workspace_id = os.environ.get("PUPIL_WORKSPACE_ID")
    if not api_key or not workspace_id:
        print("Set PUPIL_API_KEY and PUPIL_WORKSPACE_ID environment variables.")
        return False

    headers = {"api-key": api_key, "workspace-id": workspace_id}

    base_url = "https://api.cloud.pupil-labs.com/v2"
    recordings_url = f"{base_url}/workspaces/{workspace_id}/recordings/"

    try:
        response = requests.get(recordings_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch recordings: {e}")
        return False

    recordings = response.json().get("result", [])

    matching_recordings = []
    for recording in recordings:
        recorded_at_str = recording.get("recorded_at")
        if not recorded_at_str:
            continue
        try:
            dt = parse(recorded_at_str)
            utc_dt = dt.astimezone(timezone("UTC"))
            if utc_dt.date() == given_date:
                if recording.get("is_processed", False) and recording.get(
                    "download_url"
                ):
                    matching_recordings.append(recording)
        except Exception as e:
            print(f"Error parsing date {recorded_at_str}: {e}")
            continue

    if not matching_recordings:
        print(f"No processed recordings found for {date_str}.")
        return False

    print(f"Found {len(matching_recordings)} recordings for {date_str}")

    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving files to: {output_dir}")

    for idx, recording in enumerate(matching_recordings, 1):
        recording_id = recording["id"]
        recording_name = recording.get("name", recording_id)

        params = {
            "ids": recording_id,
        }
        export_url = f"{base_url}/workspaces/{workspace_id}/recordings:raw-data-export?{urlencode(params, doseq=True)}"

        filename = os.path.join(
            output_dir, f"{recording_name.replace(' ', '_')}_{recording_id}.zip"
        )

        print(f"\nDownloading raw data {idx}/{len(matching_recordings)}")
        print(f"Recording ID: {recording_id}")
        print(f"Export URL: {export_url}")

        if os.path.exists(filename):
            print("File already exists, skipping...")
            continue

        if download_file(export_url, filename, headers):
            print(f"Successfully downloaded to {filename}")

            # Automatically extract the zip file
            extract_dir = os.path.join(
                output_dir, f"{recording_name.replace(' ', '_')}_{recording_id}"
            )
            os.makedirs(extract_dir, exist_ok=True)
            download_pupil_zip(filename, extract_dir)
        else:
            print(f"Failed to download raw data for {recording_id}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Download and process eye tracking data"
    )

    # Create subparsers for different modes
    subparsers = parser.add_subparsers(dest="mode", help="Operating mode")

    # Aria mode
    aria_parser = subparsers.add_parser("aria", help="Process Aria eye tracking data")
    aria_parser.add_argument("input_file", type=str, help="Input VRS file")
    aria_parser.add_argument("output_dir", type=pathlib.Path, help="Output directory")
    aria_parser.add_argument(
        "--extra", type=str, nargs="+", help="Extra arguments for aria_mps"
    )

    # Pupil mode with direct zip input
    pupil_zip_parser = subparsers.add_parser(
        "pupil-zip", help="Process Pupil eye tracking data from zip file"
    )
    pupil_zip_parser.add_argument("input_file", type=str, help="Input zip file")
    pupil_zip_parser.add_argument(
        "output_dir", type=pathlib.Path, help="Output directory"
    )

    # Pupil mode with date-based download
    pupil_date_parser = subparsers.add_parser(
        "pupil-date", help="Download Pupil eye tracking data by date"
    )
    pupil_date_parser.add_argument("date", type=str, help="Date in YYYY-MM-DD format")
    pupil_date_parser.add_argument(
        "output_dir", type=pathlib.Path, help="Output directory"
    )

    args = parser.parse_args()

    if not args.mode:
        parser.print_help()
        sys.exit(1)

    # Ensure output directory exists
    ensure_dir_exists(args.output_dir)

    if args.mode == "aria":
        success = download_aria(args.input_file, args.output_dir, args.extra)
    elif args.mode == "pupil-zip":
        success = download_pupil_zip(args.input_file, args.output_dir)
    elif args.mode == "pupil-date":
        success = download_pupil_by_date(args.date, args.output_dir)
    else:
        print("Invalid mode")
        sys.exit(1)

    if success:
        print("Operation completed successfully")
        sys.exit(0)
    else:
        print("Operation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

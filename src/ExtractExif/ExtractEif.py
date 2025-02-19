import os
import json
import subprocess
from pathlib import Path
from datetime import datetime


class ExtractEif:
    def __init__(self, input_file: Path, video_type: str, driver_name: str):
        """
        Initialize ExtractEif with video-specific parameters
        Args:
            input_file: Path to the input video file
            output_dir: Base output directory
            video_type: Type of video (front, helmet, back, glasses)
            driver_name: Name of the driver
        """
        self.input_file = input_file
        self.driver_name = driver_name
        self.video_type = video_type
        self.output_dir = Path(f"tempData_{self.video_type}_{self.input_file.stem}")

        os.makedirs(f"tempData_{video_type}_{input_file.stem}", exist_ok=True)

    def extract_telemetry(self):
        """
        Extract telemetry from the GoPro video file using Node.js script and save in organized structure.
        """
        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Run Node.js script to extract telemetry
        try:
            result = subprocess.run(
                ["node", "src/ExtractExif/ExtractEif.js", str(self.input_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            telemetry_data = json.loads(result.stdout)

            # Save main telemetry.json
            telemetry_file = self.output_dir / "telemetry.json"
            with open(telemetry_file, "w") as file:
                json.dump(telemetry_data, file, indent=4)

            # Save individual stream data
            streams = telemetry_data.get("1", {}).get("streams", {})
            for stream_name, stream_data in streams.items():
                output_file = self.output_dir / f"{stream_name}.json"
                print(f"Saving {self.video_type} telemetry data to: {output_file}")
                with open(output_file, "w") as file:
                    json.dump(stream_data, file, indent=4)

            print(
                f"{self.video_type.capitalize()} telemetry data saved in: {self.output_dir}"
            )

        except subprocess.CalledProcessError as e:
            print(
                f"Error running Node.js script for {self.video_type} video: {e.stderr}"
            )
        except json.JSONDecodeError:
            print(
                f"Failed to decode JSON from Node.js output for {self.video_type} video."
            )

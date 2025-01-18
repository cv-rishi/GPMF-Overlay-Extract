import os
import json
import subprocess
from pathlib import Path


class ExtractEif:
    def __init__(self, input_file: Path, output_dir: Path):
        self.input_file = input_file
        self.output_dir = output_dir

    def extract_telemetry(self):
        """
        Extract telemetry from the GoPro video file using Node.js script.
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

            # Save telemetry.json
            telemetry_file = self.output_dir / "telemetry.json"
            with open(telemetry_file, "w") as file:
                json.dump(telemetry_data, file, indent=4)

            # Save individual stream data
            streams = telemetry_data.get("1", {}).get("streams", {})
            for stream_name, stream_data in streams.items():
                output_file = self.output_dir / f"{stream_name}.json"
                print(f"Saving telemetry data to: {output_file}")
                with open(output_file, "w") as file:
                    json.dump(stream_data, file, indent=4)

            print(f"Telemetry data saved in: {self.output_dir}")

        except subprocess.CalledProcessError as e:
            print(f"Error running Node.js script: {e.stderr}")
        except json.JSONDecodeError:
            print("Failed to decode JSON from Node.js output.")

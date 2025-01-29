import sys
import os
import json
import subprocess


def extract_telemetry(input_file, output_dir):
    """
    Extract telemetry from the GoPro video file using Node.js script.
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Run Node.js script to extract telemetry
    try:
        result = subprocess.run(
            ["node", "ExtractEif.js", input_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        telemetry_data = json.loads(result.stdout)

        with open("telemetry.json", "w") as file:
            json.dump(telemetry_data, file, indent=4)

        streams = telemetry_data.get("1", {}).get("streams", {})
        for stream_name, stream_data in streams.items():
            output_file = os.path.join(output_dir, f"{stream_name}.json")
            print("Saving telemetry data to:", output_file)
            with open(output_file, "w") as file:
                json.dump(stream_data, file, indent=4)

        print(f"Telemetry data saved in: {output_dir}")

    except subprocess.CalledProcessError as e:
        print(f"Error running Node.js script: {e.stderr}")
    except json.JSONDecodeError:
        print("Failed to decode JSON from Node.js output.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python extract_gopro_telemetry.py <input_file> <output_directory>"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    extract_telemetry(input_file, output_dir)

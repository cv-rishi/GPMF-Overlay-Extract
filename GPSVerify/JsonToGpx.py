import json
import gpxpy
import gpxpy.gpx
from datetime import datetime


def json_to_gpx(json_data, output_file):
    gpx = gpxpy.gpx.GPX()

    # Process each sample in the JSON file
    for sample in json_data.get("samples", []):
        # Extract latitude, longitude, elevation, and timestamp
        value = sample.get("value", [])
        if len(value) >= 3:  # Ensure there are at least lat, lon, and elevation
            latitude = value[0]
            longitude = value[1]
            elevation = value[2]
            timestamp_str = sample.get("date", None)

            # Convert timestamp string to datetime object
            timestamp = None
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            # Add waypoint to the GPX object
            gpx.waypoints.append(
                gpxpy.gpx.GPXWaypoint(
                    latitude=latitude,
                    longitude=longitude,
                    elevation=elevation,
                    time=timestamp,
                )
            )

    # Write the GPX object to a file
    with open(output_file, "w") as f:
        f.write(gpx.to_xml())


# Load the JSON files
with open("GPS5_19806.json") as f:
    gps_19806 = json.load(f)

with open("GPS5_109606.json") as f:
    gps_109606 = json.load(f)

# Convert JSON to GPX
json_to_gpx(gps_19806, "GPS5_19806.gpx")
json_to_gpx(gps_109606, "GPS5_109606.gpx")

print("GPX files created successfully.")

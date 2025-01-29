import math
import gpxpy


def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculate the bearing (direction) from point 1 to point 2.

    Formula: 	θ = atan2( sin Δλ ⋅ cos φ2 , cos φ1 ⋅ sin φ2 − sin φ1 ⋅ cos φ2 ⋅ cos Δλ )

    where: 	φ1,λ1 is the start point, φ2,λ2 the end point (Δλ is the difference in longitude)

    From - https://www.movable-type.co.uk/scripts/latlong.html

    Args:
        lat1: Latitude of point 1
        lon1: Longitude of point 1
        lat2: Latitude of point 2
        lon2: Longitude of point 2

    Returns:
        Bearing in degrees
    """
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(
        lon2 - lon1
    )
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360

    return bearing


def calculate_offset(lat, lon, bearing, distance):
    """
    Calculate the offset position of a point based on bearing to mitigate error in GPS sensor.

    Formula: 	φ2 = asin( sin φ1 ⋅ cos δ + cos φ1 ⋅ sin δ ⋅ cos θ )
        λ2 = λ1 + atan2( sin θ ⋅ sin δ ⋅ cos φ1, cos δ − sin φ1 ⋅ sin φ2 )

    Where: 	φ is latitude, λ is longitude, θ is the bearing (clockwise from north), δ is the angular distance d/R; d being the distance travelled, R the earth’s radius

    Args:
        lat: Latitude of point
        lon: Longitude of point
        bearing: Bearing in degrees
        distance: Distance to be offset in meters

    Returns:
        Tuple of (lat, lon) of the offset point
    """
    # Earth radius in meters
    R = 6378137

    d_radians = distance / R

    bearing_rad = math.radians(bearing)

    lat = math.radians(lat)
    new_lat = math.asin(
        math.sin(lat) * math.cos(d_radians)
        + math.cos(lat) * math.sin(d_radians) * math.cos(bearing_rad)
    )

    lon = math.radians(lon)
    new_lon = lon + math.atan2(
        math.sin(bearing_rad) * math.sin(d_radians) * math.cos(lat),
        math.cos(d_radians) - math.sin(lat) * math.sin(new_lat),
    )

    new_lat = math.degrees(new_lat)
    new_lon = math.degrees(new_lon)

    return new_lat, new_lon


def offset_gpx(input_file, output_file, offset_distance=1.5):
    """
    Read GPX data, dynamically calculate offsets for each point, and write adjusted GPX data.

    Args:
        input_file: Path to the input GPX file
        output_file: Path to the output GPX file
        offset_distance: Offset distance in meters

    Returns:
        None

    """

    with open(input_file, "r") as gpx_file:
        gpx = gpxpy.parse(gpx_file)

    waypoints = []
    for waypoint in gpx.waypoints:
        waypoints.append(
            {
                "lat": waypoint.latitude,
                "lon": waypoint.longitude,
                "ele": waypoint.elevation,
            }
        )

    bearing = 0

    for i in range(len(waypoints)):
        if i < len(waypoints) - 1:  # If not the last waypoint
            bearing = calculate_bearing(
                waypoints[i]["lat"],
                waypoints[i]["lon"],
                waypoints[i + 1]["lat"],
                waypoints[i + 1]["lon"],
            )
        else:
            bearing = bearing

        new_lat, new_lon = calculate_offset(
            waypoints[i]["lat"], waypoints[i]["lon"], bearing + 90, offset_distance
        )

        waypoints[i]["lat"] = new_lat
        waypoints[i]["lon"] = new_lon

    adjusted_gpx = gpxpy.gpx.GPX()
    for wp in waypoints:
        new_wp = gpxpy.gpx.GPXWaypoint(wp["lat"], wp["lon"], elevation=wp["ele"])
        adjusted_gpx.waypoints.append(new_wp)

    # Write the adjusted GPX data to the output file
    with open(output_file, "w") as output:
        output.write(adjusted_gpx.to_xml())

    print(f"Adjusted GPX saved to {output_file}")


if __name__ == "__main__":
    input_gpx = "./gpx/GPS5_109606.gpx"
    output_gpx = "adjusted_dynamic.gpx"

    offset_distance = 5

    offset_gpx(input_gpx, output_gpx, offset_distance)

    print("Processing completed.")

    # print("Test")
    # bering = calculate_bearing(17.4449891, 78.3504735, 17.449602, 78.3578709)
    #
    # headding = bering
    # # Convert bearing to cardinal direction
    # if bering < 22.5:
    #     bering = "N"
    # elif bering < 67.5:
    #     bering = "NE"
    # elif bering < 112.5:
    #     bering = "E"
    # elif bering < 157.5:
    #     bering = "SE"
    # elif bering < 202.5:
    #     bering = "S"
    # elif bering < 247.5:
    #     bering = "SW"
    # elif bering < 292.5:
    #     bering = "W"
    # elif bering < 337.5:
    #     bering = "NW"
    # else:
    #     bering = "N"
    #
    # print(
    #     f"We are moving in the following direction: {headding}, which is cardinally {bering}"
    # )
    #
    # # Define waypoints (original)
    # waypoints = [
    #     {"lat": 17.4449891, "lon": 78.3504735},
    #     {"lat": 17.449602, "lon": 78.3578709},
    # ]
    #
    # # Apply offsets
    # offset_distance = -3.5  # Use 50 meters for better visibility in testing
    # new_waypoints = []
    # prev_point = None
    #
    # for point in waypoints:
    #     new_lat, new_lon = calculate_offset(
    #         point["lat"], point["lon"], headding + 90, offset_distance
    #     )
    #     new_waypoints.append({"lat": new_lat, "lon": new_lon})
    #     prev_point = point
    #
    # # Display differences between original and offset points
    # print("Differences (Offset - Original):")
    # for original, offset in zip(waypoints, new_waypoints):
    #     diff_lat = offset["lat"] - original["lat"]
    #     diff_lon = offset["lon"] - original["lon"]
    #     print(f"Lat diff: {diff_lat:.8f}, Lon diff: {diff_lon:.8f}")
    #
    # map_center = [waypoints[0]["lat"], waypoints[0]["lon"]]
    # my_map = folium.Map(location=map_center, zoom_start=18)
    #
    # # Add original waypoints to the map in blue
    # for point in waypoints:
    #     folium.Marker(
    #         [point["lat"], point["lon"]],
    #         popup=f"Original Point: ({point['lat']}, {point['lon']})",
    #         icon=folium.Icon(color="blue"),
    #     ).add_to(my_map)
    #
    # # Add offset waypoints to the map in red
    # for point in new_waypoints:
    #     folium.Marker(
    #         [point["lat"], point["lon"]],
    #         popup=f"Offset Point: ({point['lat']}, {point['lon']})",
    #         icon=folium.Icon(color="red"),
    #     ).add_to(my_map)
    #
    # # Save and display the map
    # my_map.save("gpx_map_offset.html")
    #
    # print("Original waypoints:")
    # print(waypoints)
    # print("Offset waypoints:")
    # print(new_waypoints)
    # print("Map with original and offset waypoints saved as 'gpx_map_offset.html'")

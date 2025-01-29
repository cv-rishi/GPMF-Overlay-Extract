import gpxpy
import folium

# Load the GPX file
with open("./gpx/GPS5_109606.gpx", "r") as gpx_file:
    gpx = gpxpy.parse(gpx_file)

# Ofset map

# Load the GPX file
with open("./adjusted_dynamic.gpx", "r") as gpx_file:
    offset = gpxpy.parse(gpx_file)

# Extract waypoints
waypoints = []
for waypoint in gpx.waypoints:
    waypoints.append(
        {"lat": waypoint.latitude, "lon": waypoint.longitude, "ele": waypoint.elevation}
    )

offsets = []
for point in offset.waypoints:
    offsets.append(
        {"lat": point.latitude, "lon": point.longitude, "ele": point.elevation}
    )

# Create a folium map centered at the first waypoint
map_center = [waypoints[0]["lat"], waypoints[0]["lon"]]
my_map = folium.Map(location=map_center, zoom_start=18)


# create a "route" / line that passes through all the waypoints
# folium.PolyLine(
#     locations=[[point["lat"], point["lon"]] for point in waypoints],
#     color="blue",
#     weight=3,
#     opacity=1,
# ).add_to(my_map)
#
# folium.PolyLine(
#     locations=[[point["lat"], point["lon"]] for point in offsets],
#     color="red",
#     weight=2,
#     opacity=1,
# ).add_to(my_map)

# plot the waypoints for both as small cirlces

for point in waypoints:
    folium.CircleMarker(
        location=[point["lat"], point["lon"]],
        radius=2,
        color="blue",
        fill=True,
        fill_color="blue",
    ).add_to(my_map)

for point in offsets:
    folium.CircleMarker(
        location=[point["lat"], point["lon"]],
        radius=2,
        color="red",
        fill=True,
        fill_color="red",
    ).add_to(my_map)

my_map.save("gpx_map.html")
print("Map saved as gpx_map.html")

import gpxpy
import requests
import folium

# Load GPX file
with open("./gpx/GPS5_109606.gpx", "r") as gpx_file:
    gpx = gpxpy.parse(gpx_file)
with open("./adjusted_dynamic.gpx", "r") as gpx_file:
    adjusted_gpx = gpxpy.parse(gpx_file)


adjusted_waypoints = [(wpt.latitude, wpt.longitude) for wpt in adjusted_gpx.waypoints]
# Extract waypoints
waypoints = [(wpt.latitude, wpt.longitude) for wpt in gpx.waypoints]

# Split into chunks of 200
chunk_size = 150

for i in range(0, len(waypoints), chunk_size):
    chunks = waypoints[i : i + chunk_size]


# Function to get route from OSRM
def get_route(coords1, coords2):
    base_url = "http://router.project-osrm.org/route/v1/driving/"
    lat1 = coords1[0]
    lon1 = coords1[1]
    lat2 = coords2[0]
    lon2 = coords2[1]

    cords = f"{lon1},{lat1};{lon2},{lat2}"
    url = f"{base_url}{cords}?overview=full&geometries=geojson"

    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["routes"][0]["geometry"]["coordinates"]
    else:
        print("OSRM error:", response.text)
        return []


# Fetch and combine all routes
all_routes = []
# for i in range(len(chunks)):
#     try:
#         route = get_route(chunks[i], chunks[i + 1])
#     except IndexError:
#         route = get_route(chunks[i], chunks[i])
#     all_routes.extend(route)
#
# Convert to folium-friendly format

for i in range(0, len(waypoints), chunk_size):
    if i + 200 >= len(waypoints):
        route = get_route(waypoints[i], waypoints[-1])
    else:
        route = get_route(waypoints[i], waypoints[i + 200])

    all_routes.extend(route)

mapped_route = [(lat, lon) for lon, lat in all_routes]

original_points = [(lat, lon) for lat, lon in chunks]

# Display route on a map
m = folium.Map(location=mapped_route[0], zoom_start=15)
folium.PolyLine(mapped_route, color="blue", weight=2.5).add_to(m)
folium.Marker(mapped_route[0], popup="Start", icon=folium.Icon(color="green")).add_to(m)
folium.Marker(mapped_route[-1], popup="End", icon=folium.Icon(color="red")).add_to(m)
folium.PolyLine(adjusted_waypoints, color="pink", weight=2.5).add_to(m)
folium.PolyLine(waypoints, color="black", weight=2.5).add_to(m)
m.save("route.html")

print("Route saved to route.html")

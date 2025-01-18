# Install required libraries
import streamlit as st
import osmnx as ox
import networkx as nx
import requests
import folium
from streamlit_folium import st_folium

# Function to get latitude and longitude of a location using OpenCage API
def get_coordinates(location):
    api_key = "7ea4c213fda44209b4685e71ab062176"  # Replace with your OpenCage API key
    api_url = f"https://api.opencagedata.com/geocode/v1/json?q={location}&key={api_key}"
    
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            return float(data['results'][0]['geometry']['lat']), float(data['results'][0]['geometry']['lng'])
        else:
            raise ValueError(f"Location '{location}' not found!")
    else:
        raise ValueError(f"Failed to fetch coordinates for '{location}'. HTTP {response.status_code}")

# Function to get traffic data from TomTom API
def get_traffic_data(lat, lon, api_key):
    url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    params = {"key": api_key, "point": f"{lat},{lon}"}
    response = requests.get(url, params=params).json()
    try:
        current_speed = response["flowSegmentData"]["currentSpeed"]
        free_flow_speed = response["flowSegmentData"]["freeFlowSpeed"]
        congestion_level = "low" if current_speed > 0.7 * free_flow_speed else "high"
        return current_speed, free_flow_speed, congestion_level
    except KeyError:
        return None, None, "no_data"

# Function to find the best route based on traffic conditions
def find_best_route(graph, start_point, end_point, api_key):
    start_node = ox.distance.nearest_nodes(graph, start_point[1], start_point[0])
    end_node = ox.distance.nearest_nodes(graph, end_point[1], end_point[0])

    all_routes = list(nx.all_shortest_paths(graph, start_node, end_node, weight="length"))
    best_route = None
    best_congestion = float("inf")

    for route in all_routes:
        congestion_score = 0
        for i in range(len(route) - 1):
            u, v = route[i], route[i + 1]
            edge = graph[u][v][0]
            midpoint = ((graph.nodes[u]["y"] + graph.nodes[v]["y"]) / 2,
                        (graph.nodes[u]["x"] + graph.nodes[v]["x"]))
            _, _, congestion = get_traffic_data(midpoint[0], midpoint[1], api_key)
            if congestion == "no_data":
                continue
            congestion_score += 1 if congestion == "high" else 0

        if congestion_score < best_congestion:
            best_congestion = congestion_score
            best_route = route

    return all_routes, best_route

# Function to plot routes on a folium map
def plot_routes(graph, all_routes, best_route, start_coords, end_coords):
    route_map = folium.Map(location=start_coords, zoom_start=14, tiles="OpenStreetMap")

    for route in all_routes:
        route_coords = [(graph.nodes[node]["y"], graph.nodes[node]["x"]) for node in route]
        folium.PolyLine(route_coords, color="gray", weight=3, opacity=0.5).add_to(route_map)

    if best_route:
        best_coords = [(graph.nodes[node]["y"], graph.nodes[node]["x"]) for node in best_route]
        folium.PolyLine(best_coords, color="green", weight=5, opacity=1, tooltip="Best Route").add_to(route_map)

    folium.Marker(location=start_coords, popup="Start", icon=folium.Icon(color="blue")).add_to(route_map)
    folium.Marker(location=end_coords, popup="End", icon=folium.Icon(color="red")).add_to(route_map)

    return route_map

def main():
    st.title("Route Finder with Traffic Optimization 🚗")
    st.sidebar.title("Input Locations")
    
    # Initialize session state for map
    if "route_map" not in st.session_state:
        st.session_state["route_map"] = None

    # Inputs
    start_location = st.sidebar.text_input("Enter Start Location", "MG Road, Bangalore")
    end_location = st.sidebar.text_input("Enter End Location", "Whitefield, Bangalore")
    api_key = "OgANJbyPxG0w5IMI1EkUjHrecucquDgG"

    if st.sidebar.button("Find Routes"):
        try:
            # Get coordinates
            start_coords = get_coordinates(start_location)
            end_coords = get_coordinates(end_location)

            # Display coordinates
            st.write(f"**Start Coordinates**: {start_coords}")
            st.write(f"**End Coordinates**: {end_coords}")

            # Get graph and find routes
            graph = ox.graph_from_point(start_coords, dist=15000, network_type="drive")
            all_routes, best_route = find_best_route(graph, start_coords, end_coords, api_key)

            # Plot routes on the map
            route_map = plot_routes(graph, all_routes, best_route, start_coords, end_coords)

            # Save the map in session state
            st.session_state["route_map"] = route_map

        except ValueError as e:
            st.error(f"Error: {e}")

    # Display the map if available
    if st.session_state["route_map"]:
        st_folium(st.session_state["route_map"], width=800, height=500)


if __name__ == "__main__":
    main()

import matplotlib.pyplot as plt
import contextily as cx
from pyproj import Transformer
import numpy as np
import osmnx as ox

def display_map(location):
    """
    Display a simple map with highlighted roads.
    
    Args:
        location (tuple): (latitude, longitude) coordinates
    """
    # Set figure properties for black background
    plt.style.use('dark_background')
    plt.rcParams['figure.dpi'] = 100  # Set to standard DPI for exact pixel mapping
    
    # Create figure with black background at exactly 1920x1080 pixels
    fig, ax = plt.subplots(figsize=(19.20, 10.80), facecolor='black')  # Size in inches at 100 DPI = 1920x1080 pixels
    ax.set_facecolor('black')
    
    # Get the street network for a 7km radius
    lat, lon = location
    G = ox.graph_from_point((lat, lon), dist=7000, network_type='drive')
    
    # Plot the street network
    ox.plot_graph(G, ax=ax, 
                 node_size=0,  # Hide intersection nodes
                 edge_color='#404040',  # Medium grey for streets
                 edge_linewidth=0.5,  # Thinner lines for better appearance
                 edge_alpha=1,
                 bgcolor='black',
                 show=False,  # Don't create a new figure
                 close=False)  # Don't close our existing figure
    
    # Remove axes and set tight layout
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    # Ensure the figure background is black
    fig.patch.set_facecolor('black')
    
    plt.show()
    plt.close()  # Clean up after showing

# Example usage - Paris coordinates
coords = (48.8575, 2.3514)
display_map(coords)


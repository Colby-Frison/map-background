import matplotlib.pyplot as plt
import contextily as cx
from pyproj import Transformer
import numpy as np
import osmnx as ox
from PIL import Image, ImageDraw, ImageFont
import os
import glob
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

def crop_to_16_9(image_path, aspect_ratio):
    """
    Crop an image to 16:9 aspect ratio and remove padding.
    
    Args:
        image_path (str): Path to the image to crop
    """
    # Open the image
    img = Image.open(image_path)
    
    # Get current dimensions
    width, height = img.size
    
    # First, remove the padding (roughly 50 pixels from each side)
    padding = 150
    img = img.crop((padding, padding, width - padding, height - padding))
    
    # Get new dimensions after padding removal
    width, height = img.size
    
    # Calculate target dimensions (1920x1080)
    target_width = 1920
    target_height = 1080
    
    # Calculate dimensions to crop to 16:9
    if width/height > aspect_ratio:  # Image is too wide
        new_width = int(height * aspect_ratio)
        left = (width - new_width) // 2
        img = img.crop((left, 0, left + new_width, height))
    else:  # Image is too tall
        new_height = int(width / aspect_ratio)
        top = (height - new_height) // 2
        img = img.crop((0, top, width, top + new_height))
    
    # Resize to exactly 1920x1080
    img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    
    # Save the cropped image
    img.save(image_path)

def cleanup_cache():
    """Remove cache files created by osmnx and matplotlib"""
    # Remove osmnx cache
    if os.path.exists(".cache"):
        for file in glob.glob(".cache/*"):
            os.remove(file)
        os.rmdir(".cache")
    
    # Remove matplotlib cache
    for file in glob.glob("*.cache"):
        os.remove(file)

def add_location_text(image_path, location_name):
    """
    Add location name to the top right corner of the image.
    
    Args:
        image_path (str): Path to the image
        location_name (str): Name of the location to add
    """
    # Open the image
    img = Image.open(image_path)
    
    # Create drawing object
    draw = ImageDraw.Draw(img)
    
    # Load font from fonts directory
    font_path = os.path.join('fonts', 'Ubuntu-Regular.ttf')
    try:
        font = ImageFont.truetype(font_path, 16)
    except OSError:
        print(f"Font not found at {font_path}, using default font")
        font = ImageFont.load_default()
    
    # Calculate text size
    text_bbox = draw.textbbox((0, 0), location_name, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    
    # Position text in top right with padding
    padding = 25
    position = (img.width - text_width - padding, padding)
    
    # Add text shadow for better visibility
    shadow_offset = 2
    shadow_color = 'black'
    text_color = '#6f6f6f'
    
    # Draw text with shadow
    draw.text((position[0] + shadow_offset, position[1] + shadow_offset), 
              location_name, 
              font=font, 
              fill=shadow_color)
    
    # Draw main text
    draw.text(position, location_name, font=font, fill=text_color)
    
    # Save the image
    img.save(image_path)

def display_map(location, radius, dpi, aspect_ratio, output_path, location_name):
    """
    Create and save a map with highlighted roads.
    
    Args:
        location (tuple): (latitude, longitude) coordinates
        radius (float): radius in meters
        dpi (int): dots per inch for the output image
        aspect_ratio (float): desired aspect ratio
        output_path (str): Path where to save the output image
        location_name (str): Name of the location to display
    """
    # Set figure properties for black background
    plt.style.use('dark_background')
    plt.rcParams['figure.dpi'] = dpi  # Set to standard DPI for exact pixel mapping
    
    # Create figure with black background at exactly 16:9 pixels
    fig, ax = plt.subplots(figsize=(16, 9), facecolor='black') 
    ax.set_facecolor('black')
    
    # Get the street network for a 10km radius
    lat, lon = location
    G = ox.graph_from_point((lat, lon), dist=radius, network_type='all')
    
    # Plot the street network
    ox.plot_graph(G, ax=ax, 
                 node_size=0,  # Hide intersection nodes
                 edge_color='#262626',  # Medium grey for streets
                 edge_linewidth=0.4,  # Thinner lines for better appearance
                 edge_alpha=1,
                 bgcolor='black',
                 show=False,  # Don't create a new figure
                 close=False)  # Don't close our existing figure
    
    # Remove axes and set tight layout
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    # Ensure the figure background is black
    fig.patch.set_facecolor('black')
    
    # Save the figure with format-specific settings
    if output_path.endswith('.svg'):
        plt.savefig(output_path, 
                   format='svg',
                   bbox_inches='tight',
                   pad_inches=0,
                   facecolor='black',
                   edgecolor='none')
    else:
        plt.savefig(output_path, 
                   dpi=750,
                   bbox_inches='tight',
                   pad_inches=0,
                   facecolor='black',
                   edgecolor='none')
    
    # Clean up matplotlib
    plt.close()
    
    # Only process with PIL if it's a PNG file
    if output_path.endswith('.png'):
        # Crop the saved image to exact 16:9 ratio
        crop_to_16_9(output_path, aspect_ratio)
        
        # Add location name to the image
        add_location_text(output_path, location_name)
    
    # Clean up cache files
    cleanup_cache()


# Get user inputs

## get location
location = input("Enter location(City, Country || lat, lon): ")
if location == "default":
    coords = (37.9838, 23.7275)  # Athens, Greece
    location_name = "Athens, Greece"
else:
    # Check if input might be coordinates
    try:
        # Try to split and convert to float
        lat, lon = map(float, location.replace(' ', '').split(','))
        coords = (lat, lon)
        
        # Get location name from coordinates
        geolocator = Nominatim(user_agent="my_map_generator")
        location_data = geolocator.reverse(coords, language='en')  # Force English results
        
        if location_data is None:
            print("Could not find location name for coordinates.")
            location_name = input("Please enter the location name (City, Country): ")
        else:
            # Parse the address components
            address = location_data.raw.get('address', {})
            
            # Try to get city or town
            city = address.get('city')
            town = address.get('town')
            country = address.get('country')
            
            if city and country:
                location_name = f"{city}, {country}"
            elif town and country:
                location_name = f"{town}, {country}"
            else:
                print("Could not determine city/town name from coordinates.")
                location_name = input("Please enter the location name (City, Country): ")
            
            print(f"Location found: {location_name}")
            
    except ValueError:
        # If not coordinates, treat as location name
        try:
            # Initialize the geocoder
            geolocator = Nominatim(user_agent="my_map_generator")
            
            # Get the location
            location_data = geolocator.geocode(location)
            
            if location_data is None:
                print("Location not found. Using default coordinates (Athens, Greece)")
                coords = (37.9838, 23.7275)
                location_name = "Athens, Greece"
            else:
                coords = (location_data.latitude, location_data.longitude)
                location_name = location  # Use the full input string
                print(f"Coordinates found: {coords}")
        except GeocoderTimedOut:
            print("Geocoding service timed out. Using default coordinates (Athens, Greece)")
            coords = (37.9838, 23.7275)
            location_name = "Athens, Greece"

## get radius
radius = input("Enter the radius (in km): ")
if radius == "default":
    radius = 18000
else:
    radius = float(radius)

## get DPI
dpi = input("Enter the DPI: ")
if dpi == "default":
    dpi = 750
else:
    dpi = float(dpi)

## get aspect ratio
aspect_ratio = input("Enter the aspect ratio (16:9, 4:3, 1:1, etc): ")
if aspect_ratio == "default":
    aspect_ratio = 16/9
else:
    aspect_ratio = float(aspect_ratio)

## get output format
output_format = input("Enter the output format (png/svg): ")
if output_format.lower() not in ['png', 'svg']:
    print("Invalid format. Using default (png)")
    output_format = 'png'
else:
    output_format = output_format.lower()

# Create output filename with correct extension
output_file = f'map.{output_format}'

display_map(coords, radius, dpi, aspect_ratio, output_file, location_name)


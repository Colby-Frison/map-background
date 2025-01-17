"""
Downloading and Plotting Maps
-----------------------------

Plotting maps with Contextily.

This script displays a map of a specified location using Contextily.
"""
import matplotlib.pyplot as plt
import contextily as cx

# Specify the location
place = "norman"

# Create a Place object for the location
loc = cx.Place(place, zoom_adjust=1)

# Create a single figure
fig, ax = plt.subplots(figsize=(12, 8))

# Plot the map and set the title
cx.plot_map(loc, ax=ax, title=place.title())

plt.show()
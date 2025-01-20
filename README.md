# Map Background



The python program creates a black and grey map in a 16:9 aspect ratio of paris. The location can be changed by inputing corrdinates of another place, but for right now it has a preset location

The program takes quite a long time to execute because it interacts with an external source to pull the map info, it is also very high resolution, so it takes a while to render and crop.

requirements.txt contains all dependencies for the program. run `pip install -r requirements.txt` to install them.

To change what level of detail is used, change the network_type on this line: `G = ox.graph_from_point((lat, lon), dist=radius, network_type='all')`. 
Here are the options:
1. 'drive' - Get drivable public streets (but not service roads)
2. 'drive_service' - Get drivable public streets including service roads
3. 'walk' - Get all streets and paths that pedestrians can use
4. 'bike' - Get all streets and paths that cyclists can use
5. 'all' - Get all non-private streets and paths
6. 'all_private' - Get all streets and paths, including private ones

Be careful with the 'all' option, it will take a long time to render.

---

At some point I will implement the following features:
- Color selection
- Possibly a way to also highlight water features
---
example:
![map](https://github.com/user-attachments/assets/3edd3adb-c42b-4dca-962a-c862ab57d572)


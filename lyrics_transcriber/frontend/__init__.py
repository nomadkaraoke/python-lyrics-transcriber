"""Frontend module for lyrics transcriber web interface."""

import os

# Get the directory containing this file
__frontend_dir__ = os.path.dirname(os.path.abspath(__file__))

def get_frontend_assets_dir():
    """Get the path to the frontend assets directory.
    
    Returns the web_assets directory if it exists (packaged version),
    otherwise returns the dist directory (development version).
    """
    web_assets_dir = os.path.join(__frontend_dir__, "web_assets")
    dist_dir = os.path.join(__frontend_dir__, "dist")
    
    if os.path.exists(web_assets_dir):
        return web_assets_dir
    elif os.path.exists(dist_dir):
        return dist_dir
    else:
        raise FileNotFoundError(
            "Frontend assets not found. Please build the frontend first with: "
            "./scripts/build_frontend.sh"
        ) 
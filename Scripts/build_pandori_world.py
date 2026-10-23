"""Build the geographically sourced Pandori Nijjaran map in Unreal."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_open_world as world
import world_layout
import pandori_layout

# GIS source has no DEM: use an explicit flat datum, not invented hills.
world.height = world_layout.height = lambda x,y: 0.0
world.main(pandori_layout)

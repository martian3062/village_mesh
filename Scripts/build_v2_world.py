"""Generate V2 in its own namespace; never overwrite V1 or authored content."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_open_world as world
import world_layout
import v2_layout
import build_v2_pilot

world.DEST='/Game/VillageMeshV2'
world.MAT=world.DEST+'/Materials'
world.TMP=world.ROOT/'Saved/VillageMeshV2'
world.height=world_layout.height=lambda x,y:0.0
world.main(v2_layout, post_build=build_v2_pilot.build, map_name='/Lvl_PandoriV2')

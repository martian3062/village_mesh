"""Enable static-mesh usages needed by V2's generated HLOD instances."""
import sys
from pathlib import Path


def build(api):
    if api.MAT!='/Game/VillageMeshV2/Materials':raise ValueError('V2 materials only')
    # The shared lamp builder predates HLOD instancing and bypasses api.finish.
    bulb=api.EAL.load_asset(api.MAT+'/M_VGBulb')
    if bulb is None:raise RuntimeError('Generate the V2 lamp material first')
    api.finish(bulb)


if __name__=='__main__':
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import build_open_world as api
    api.MAT='/Game/VillageMeshV2/Materials'
    build(api)
    api.unreal.log('VILLAGE_V2_MATERIAL_USAGES_OK')

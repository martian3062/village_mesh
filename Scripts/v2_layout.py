"""V2 uses the same map inputs, with isolated pilot replacements and stable IDs."""
from pathlib import Path
import math
import pandori_layout as base
import v2_data as data

ROOT, LAT, LON = base.ROOT, base.LAT, base.LON
PILOT = data.read('Assets/Routes/pilot_street.json')
BUILDINGS = data.normalized_buildings()
ROADS, SEGMENTS = base.ROADS, base.SEGMENTS
DETAIL_EXCLUSIONS = {f['building_id'] for f in PILOT['frontages']}
clear_site, distance_to_segment = base.clear_site, base.distance_to_segment


def generate(directory):
    background = [b for b in BUILDINGS if b['id'] not in DETAIL_EXCLUSIONS]
    # Pilot roads are replaced by continuous mitered cross-sections in the detail pass.
    roads = [(a,b,r['width']) for r in ROADS if r['id'] not in PILOT['road_ids']
             for a,b in zip(r['points'],r['points'][1:])]
    return base.generate(directory, background, roads)


def road_surfaces(points, width):
    """Continuous shared cross-sections; 6 cm crown, 2.5 cm edge, flat shoulders.

    All elevations/widths are declared inference. Miter length is capped to avoid
    spikes at sharp bends; adjacent sections share exact vertices.
    """
    rows=[]
    for i,p in enumerate(points):
        prev=points[max(0,i-1)]; nxt=points[min(len(points)-1,i+1)]
        dx,dy=nxt[0]-prev[0],nxt[1]-prev[1]
        mag=max(math.hypot(dx,dy),1e-9); nx,ny=-dy/mag,dx/mag
        if i<len(points)-1:
            ex,ey=nxt[0]-p[0],nxt[1]-p[1]
        else: ex,ey=p[0]-prev[0],p[1]-prev[1]
        el=max(math.hypot(ex,ey),1e-9)
        miter=min(1.5,1/max(.01,nx*(-ey/el)+ny*(ex/el)))
        rows.append([(p[0]+nx*d*miter,p[1]+ny*d*miter,z)
                     for d,z in ((-width/2-70,0),(-width/2,2.5),(0,6),(width/2,2.5),(width/2+70,0))])
    asphalt,shoulder=base.Obj(),base.Obj()
    for a,b in zip(rows,rows[1:]):
        for j in range(4):
            (asphalt if j in (1,2) else shoulder).quad([a[j],b[j],b[j+1],a[j+1]])
    return asphalt,shoulder,rows

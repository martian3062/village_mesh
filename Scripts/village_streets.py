"""Road surfaces on existing OSM alignments; material choices are authored, not surveyed."""
import collections
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SURFACES = ('asphalt', 'brick', 'pavers', 'dirt')


def surface_for(road):
    tagged = road.get('surface', '')
    if tagged in ('asphalt', 'paved', 'concrete'): return 'asphalt'
    if tagged in ('unpaved', 'ground', 'dirt', 'earth', 'gravel'): return 'dirt'
    if tagged in ('paving_stones', 'sett'): return 'pavers'
    if tagged == 'brick': return 'brick'
    if road['kind'] in ('primary', 'secondary', 'tertiary', 'unclassified'): return 'asphalt'
    if road['kind'] in ('track', 'path', 'footway'): return 'dirt'
    return 'brick' if int(road['id']) % 3 == 0 else 'pavers'


def clipped_segment(a, b, extent=63000):
    lo, hi = 0., 1.
    dx, dy = b[0]-a[0], b[1]-a[1]
    for p, q in ((-dx,a[0]+extent),(dx,extent-a[0]),(-dy,a[1]+extent),(dy,extent-a[1])):
        if abs(p)<1e-9:
            if q<0: return None
        elif p<0: lo=max(lo,q/p)
        else: hi=min(hi,q/p)
    if lo>hi: return None
    return ([a[0]+lo*dx,a[1]+lo*dy], [a[0]+hi*dx,a[1]+hi*dy])


def cross_section(points, index):
    a=points[max(0,index-1)];p=points[index];b=points[min(len(points)-1,index+1)]
    def unit(x,y):
        length=max(math.hypot(x,y),1e-9);return (x/length,y/length)
    incoming=unit(p[0]-a[0],p[1]-a[1]) if index else unit(b[0]-p[0],b[1]-p[1])
    outgoing=unit(b[0]-p[0],b[1]-p[1]) if index<len(points)-1 else incoming
    tangent=unit(incoming[0]+outgoing[0],incoming[1]+outgoing[1])
    nx,ny=-tangent[1],tangent[0]
    scale=min(1.5,1/max(.01,nx*(-outgoing[1])+ny*outgoing[0]))
    return nx*scale,ny*scale


class RoadMesh:
    def __init__(self): self.vertices=[]; self.uv=[]; self.faces=[]
    def quad(self, vertices, uv):
        i=len(self.vertices)+1; self.vertices.extend(vertices); self.uv.extend(uv)
        self.faces.extend(((i,i+1,i+2),(i,i+2,i+3)))
    def save(self, path):
        with path.open('w') as f:
            f.write('o VillageStreet\n')
            for x,y,z in self.vertices: f.write(f'v {x:.5f} {-y:.5f} {z:.5f}\n')
            for u,v in self.uv: f.write(f'vt {u:.7f} {v:.7f}\n')
            for a,b,c in self.faces: f.write(f'f {a}/{a} {c}/{c} {b}/{b}\n')


def generate():
    plan=json.loads((ROOT/'Assets/World/v3_world.json').read_text())
    osm=json.loads((ROOT/'Assets/Geodata/pandori_nijjaran.osm.json').read_text())
    tags={e['id']:e.get('tags',{}) for e in osm['elements'] if e['type']=='way'}
    out=ROOT/'Saved/VillageStreets'; out.mkdir(parents=True,exist_ok=True)
    groups={}; roads=[]
    for original in plan['roads']:
        road=dict(original, surface=tags.get(original['id'],{}).get('surface',''))
        surface=surface_for(road); length=0; visible=[]
        for index,(a,b) in enumerate(zip(road['points'],road['points'][1:])):
            original_a,original_b=a,b
            clipped=clipped_segment(a,b)
            if not clipped: continue
            a,b=clipped; distance=math.dist(a,b)
            if distance<1: continue
            dx,dy=(b[0]-a[0])/distance,(b[1]-a[1])/distance
            nx,ny=-dy,dx; width=road['width']
            na=cross_section(road['points'],index) if math.dist(a,original_a)<.01 else (nx,ny)
            nb=cross_section(road['points'],index+1) if math.dist(b,original_b)<.01 else (nx,ny)
            # The 5 cm crown and 2 cm edges are collision geometry, not displacement.
            offsets=(-width/2,0,width/2)
            elevations=(2,5,2) if surface!='dirt' else (1,3,1)
            for j in range(2):
                pts=[(p[0]+n[0]*offsets[k],p[1]+n[1]*offsets[k],elevations[k]) for p,n,k in ((a,na,j),(b,nb,j),(b,nb,j+1),(a,na,j+1))]
                uv=[(offsets[k]/100,t/100) for t,k in ((length,j),(length+distance,j),(length+distance,j+1),(length,j+1))]
                cell=(int((a[0]+b[0])/2//16000),int((a[1]+b[1])/2//16000),surface)
                groups.setdefault(cell,RoadMesh()).quad(pts,uv)
            # Recessed earthen verges give paving a visible edge without blocking the lane.
            for side in (-1,1):
                offsets2=(side*width/2,side*(width/2+45))
                pairs=((a,na,0),(b,nb,0),(b,nb,1),(a,na,1))
                if side<0: pairs=tuple(reversed(pairs))
                pts=[(p[0]+n[0]*offsets2[k],p[1]+n[1]*offsets2[k],1 if k==0 else .2) for p,n,k in pairs]
                groups.setdefault((cell[0],cell[1],'shoulder'),RoadMesh()).quad(pts,[(p[0]/250,p[1]/250) for p in pts])
            visible.append([a,b]); length+=distance
        roads.append(dict(id=road['id'],kind=road['kind'],surface=surface,width_cm=road['width'],
            length_m=round(length/100,2),segments_cm=visible,
            confidence='OSM surface tag' if road['surface'] else 'authored surface requested by user; not surveyed'))
    items=[]
    for (x,y,surface),mesh in sorted(groups.items()):
        name=f'SM_Street_{x+4}_{y+4}_{surface}'; path=out/(name+'.obj');mesh.save(path)
        items.append(dict(name=name,file=str(path),surface=surface,triangles=len(mesh.faces),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    report=dict(schema_version=1,roads=roads,counts=dict(collections.Counter(r['surface'] for r in roads)),items=items,
        note='Mapped alignments retained; authored paving classification and widths are not a ground survey.')
    (out/'geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    contract=ROOT/'Content/V3/Data/street_surfaces.json'
    contract.write_text(json.dumps({k:v for k,v in report.items() if k!='items'},indent=2)+'\n')
    print(json.dumps(dict(roads=len(roads),chunks=len(items),counts=report['counts'])))
    return report


if __name__=='__main__': generate()

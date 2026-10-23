"""Pandori Nijjaran GIS layout. X=east, Y=north, centimeters; elevations are assumed flat.

Road centerlines: OSM. Building outlines: Overture, 2026-10-21.0.
The map has no surveyed building heights or facades; those are procedural.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAT, LON = 31.4610594, 75.7240654
EARTH = 6371008.8


def project(lon, lat):
    return ((lon - LON) * math.pi / 180 * EARTH * math.cos(math.radians(LAT)) * 100,
            (lat - LAT) * math.pi / 180 * EARTH * 100)


def distance_to_segment(x, y, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy) / max(1, dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx, y-a[1]-t*dy)


def load():
    osm = json.loads((ROOT / "Assets/Geodata/pandori_nijjaran.osm.json").read_text())
    nodes = {n["id"]: project(n["lon"], n["lat"]) for n in osm["elements"] if n["type"] == "node"}
    roads = []
    for way in osm["elements"]:
        tags = way.get("tags", {})
        if way["type"] != "way" or "highway" not in tags:
            continue
        coords = [nodes[n] for n in way["nodes"] if n in nodes]
        width = {"primary": 900, "secondary": 700, "tertiary": 600, "residential": 420,
                 "unclassified": 450, "service": 320, "track": 280, "footway": 160,
                 "path": 140}.get(tags["highway"], 350)
        roads.append(dict(id=way["id"], points=coords, width=width, kind=tags["highway"]))
    geo = json.loads((ROOT / "Assets/Geodata/pandori_nijjaran.buildings.geojson").read_text())
    buildings = []
    for i, feature in enumerate(geo["features"]):
        geometry = feature["geometry"]
        polys = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        for rings in polys:
            ring = [project(*point[:2]) for point in rings[0][:-1]]
            if len(ring) < 3:
                continue
            cx, cy = [sum(p[k] for p in ring)/len(ring) for k in (0,1)]
            if abs(cx) > 63000 or abs(cy) > 63000:
                continue
            if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1])) < 0:
                ring.reverse()
            buildings.append(dict(id=feature.get("id", str(i)), points=ring, center=(cx,cy),
                # No height measurement is present in this extract.
                height=330 + (330 if i % 3 == 0 else 0), material="brick" if i % 4 == 0 else "plaster"))
    return roads, buildings


ROADS, BUILDINGS = load()
SEGMENTS = [(a,b,r["width"]) for r in ROADS for a,b in zip(r["points"],r["points"][1:])]
BOXES = [(min(p[0] for p in b["points"]),min(p[1] for p in b["points"]),
          max(p[0] for p in b["points"]),max(p[1] for p in b["points"])) for b in BUILDINGS]
BOX_GRID = {}
for box in BOXES:
    for gx in range(math.floor(box[0]/5000),math.floor(box[2]/5000)+1):
        for gy in range(math.floor(box[1]/5000),math.floor(box[3]/5000)+1):
            BOX_GRID.setdefault((gx,gy),[]).append(box)


def clear_site(x,y,margin=100):
    if any(distance_to_segment(x,y,a,b) < width/2+margin for a,b,width in SEGMENTS):
        return False
    for gx in range(math.floor((x-margin)/5000),math.floor((x+margin)/5000)+1):
        for gy in range(math.floor((y-margin)/5000),math.floor((y+margin)/5000)+1):
            if any(a-margin<x<c+margin and b-margin<y<d+margin for a,b,c,d in BOX_GRID.get((gx,gy),[])):
                return False
    return True


def triangulate(points):
    """Ear clipping for simple counterclockwise footprints (the extract has no holes)."""
    remaining = list(range(len(points)))
    triangles=[]
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    while len(remaining)>3:
        for j,current in enumerate(remaining):
            prev,nxt=remaining[j-1],remaining[(j+1)%len(remaining)]
            a,b,c=points[prev],points[current],points[nxt]
            if cross(a,b,c)<=0.001:
                continue
            if any(cross(a,b,points[k])>=-0.001 and cross(b,c,points[k])>=-0.001 and cross(c,a,points[k])>=-0.001
                   for k in remaining if k not in (prev,current,nxt)):
                continue
            triangles.append((prev,current,nxt)); remaining.pop(j);break
        else:
            raise ValueError("Invalid building footprint polygon")
    triangles.append(tuple(remaining))
    return triangles


class Obj:
    def __init__(self): self.vertices=[];self.faces=[]
    def quad(self,points):
        i=len(self.vertices)+1;self.vertices.extend(points);self.faces.extend(((i,i+1,i+2),(i,i+2,i+3)))
    def polygon(self,points,z):
        i=len(self.vertices)+1;self.vertices.extend((x,y,z) for x,y in points)
        self.faces.extend(tuple(i+k for k in tri) for tri in triangulate(points))
    def save(self,path):
        with open(path,"w") as f:
            f.write("o PandoriGeometry\n")
            for x,y,z in self.vertices:
                f.write(f"v {x:.4f} {-y:.4f} {z:.4f}\nvt {x/300:.6f} {y/300:.6f}\n")
            for a,b,c in self.faces: f.write(f"f {a}/{a} {c}/{c} {b}/{b}\n")


def generate(directory):
    """Write spatially chunked shells and sourced road strips, never guessed house positions."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    groups={}
    def group(x,y,mat):
        key=(int(x//16000),int(y//16000),mat)
        return groups.setdefault(key,Obj())
    for building in BUILDINGS:
        pts=building["points"];cx,cy=building["center"];h=building["height"]
        wall=group(cx,cy,building["material"]);roof=group(cx,cy,"roof")
        roof.polygon(pts,h)
        # Outward-facing walls, raised parapets, street-facing door and glazing.
        for a,b in zip(pts,pts[1:]+pts[:1]):
            wall.quad([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],h+55),(a[0],a[1],h+55)])
            length=math.dist(a,b)
            if length<180:continue
            dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length
            nx,ny=dy,-dx
            midpoint=((a[0]+b[0])/2,(a[1]+b[1])/2)
            # Details are invented, not extracted from aerial imagery.
            glass=group(cx,cy,"glass")
            for z in range(160,h,330):
                for j in range(max(1,int(length/300))):
                    t=(j+0.5)/max(1,int(length/300));px=a[0]+t*(b[0]-a[0])+nx*3;py=a[1]+t*(b[1]-a[1])+ny*3
                    glass.quad([(px-dx*45,py-dy*45,z-50),(px+dx*45,py+dy*45,z-50),
                        (px+dx*45,py+dy*45,z+50),(px-dx*45,py-dy*45,z+50)])
            if length>250 and min((distance_to_segment(*midpoint,s,t) for s,t,_ in SEGMENTS),default=1e9)<1800:
                px,py=midpoint[0]+nx*5,midpoint[1]+ny*5
                group(cx,cy,"door").quad([(px-dx*55,py-dy*55,0),(px+dx*55,py+dy*55,0),
                    (px+dx*55,py+dy*55,215),(px-dx*55,py-dy*55,215)])
    for a,b,width in SEGMENTS:
        cx,cy=(a[0]+b[0])/2,(a[1]+b[1])/2
        if abs(cx)>63500 or abs(cy)>63500:continue
        length=math.dist(a,b)
        if length<1:continue
        dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length
        nx,ny=-dy*width/2,dx*width/2
        group(cx,cy,"road").quad([(a[0]+nx,a[1]+ny,3),(a[0]-nx,a[1]-ny,3),
            (b[0]-nx,b[1]-ny,3),(b[0]+nx,b[1]+ny,3)])
    output=[]
    for (x,y,material),obj in groups.items():
        if not obj.faces:continue
        name=f"SM_GIS_{x+8}_{y+8}_{material}"
        path=directory/(name+".obj");obj.save(path);output.append((str(path),name,material))
    return output


if __name__=="__main__":
    files=generate(ROOT/"Saved/VillageMeshGenerated/Pandori")
    print(json.dumps(dict(center=[LAT,LON],roads=len(ROADS),buildings=len(BUILDINGS),mesh_chunks=len(files))))

"""Original folded-cloth pagri geometry, in centimetres; no photo textures."""
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def generate():
    out=ROOT/'Saved/PardeepPlayer';out.mkdir(parents=True,exist_ok=True)
    path=out/'SM_PardeepTurban.obj'
    segments,rings=192,100
    vertices=[];uv=[];faces=[]
    # Canonical +X faces forward. The arched forehead edge descends to the ears.
    for j in range(rings):
        u=j/rings
        for i in range(segments+1):
            angle=2*math.pi*i/segments
            front=max(0,math.cos(angle))
            bottom=4.8+7.0*front**2
            z=bottom+(18.7-bottom)*u
            radius=math.cos(u*math.pi/2)**.35
            bulge=1+.085*math.sin(math.pi*u)
            # Offset winding creates diagonal overlaps rather than stacked rings.
            phase=2*math.pi*(8*u+1.3*math.sin(angle)+.6*math.sin(2*angle))
            fold=(.06*math.cos(phase)+.02*math.cos(phase*2))*(1-u**5)
            rx=10.8*radius*bulge+fold
            ry=9.3*radius*bulge+fold
            vertices.append((rx*math.cos(angle)-1.5*u,ry*math.sin(angle),z))
            uv.append((i/segments,u))
    for j in range(rings-1):
        for i in range(segments):
            a=j*(segments+1)+i+1;b=a+1;c=b+segments+1;d=a+segments+1
            faces.extend(((a,b,c),(a,c,d)))
    vertices.append((-1.5,0,18.7));uv.append((.5,1.));top=len(vertices)
    for i in range(segments):
        a=(rings-1)*(segments+1)+i+1;faces.append((a,a+1,top))
    # A narrow inward hem gives the forehead/ear edge actual cloth thickness.
    inner_start=len(vertices)+1
    for i in range(segments+1):
        x,y,z=vertices[i]
        radius=math.hypot(x,y)
        shrink=(radius-.35)/radius
        vertices.append((x*shrink,y*shrink,z+.10));uv.append((i/segments,-.015))
    for i in range(segments):
        a=i+1;b=inner_start+i;c=b+1;d=a+1
        faces.extend(((a,b,c),(a,c,d)))
    with path.open('w') as stream:
        stream.write('o PardeepFoldedTurban\ns 1\n')
        for x,y,z in vertices:stream.write(f'v {x:.6f} {-y:.6f} {z:.6f}\n')
        for u,v in uv:stream.write(f'vt {u:.6f} {v:.6f}\n')
        for a,b,c in faces:stream.write(f'f {a}/{a} {c}/{c} {b}/{b}\n')
    print(f'TURBAN_GEOMETRY vertices={len(vertices)} triangles={len(faces)}')
    return path


if __name__=='__main__':generate()

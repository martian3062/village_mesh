"""Procedural Punjabi residential details; decorative, not surveyed architecture."""
import math
import unreal


def build(api, site):
    cube = api.EAL.load_asset("/Engine/BasicShapes/Cube.Cube")
    cylinder = api.EAL.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
    trim = api.solid("M_PandoriTrim", (0.65,0.63,0.53))
    tank = api.solid("M_PandoriTank", (0.03,0.055,0.075), 0.45)
    count = 0
    for i,b in enumerate(site.BUILDINGS):
        x,y=b["center"];z=b["height"]
        if i%11==0:
            api.mesh_actor(cube,trim,"VM_ApproxTankBase_"+str(i),(x,y,z+8),(1.3,1.3,0.16))
            api.mesh_actor(cylinder,tank,"VM_ApproxTank_"+str(i),(x,y,z+60),(1,1,1.05))
            count += 2
        if i%3:continue
        pts=b["points"]
        edges=list(zip(pts,pts[1:]+pts[:1]))
        a,bp=min(edges,key=lambda e:min(site.distance_to_segment((e[0][0]+e[1][0])/2,(e[0][1]+e[1][1])/2,s,t) for s,t,_ in site.SEGMENTS))
        length=math.dist(a,bp)
        if not 350<length<2400:continue
        yaw=math.degrees(math.atan2(bp[1]-a[1],bp[0]-a[0]))
        nx,ny=(bp[1]-a[1])/length,-(bp[0]-a[0])/length
        cx,cy=(a[0]+bp[0])/2+nx*35,(a[1]+bp[1])/2+ny*35
        api.mesh_actor(cube,trim,"VM_ApproxSunshade_"+str(i),(cx,cy,250),(length/110,0.9,0.12),yaw)
        count+=1
    return count

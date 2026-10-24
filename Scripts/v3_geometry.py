"""Original Punjabi village mesh recipes, batched by cell/material for streaming.

These are regional interpretations, never photogrammetry or surveyed facades.
"""
import math,json,hashlib
from pathlib import Path
import pandori_layout as base
from v3_layout import ROOT,COLORS

def face_uvs(vertices):
    """Project onto the face's dominant plane; vertical walls must not get XY UVs."""
    a,b,c=vertices
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    drop=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=drop]
    # Local origins also avoid losing tiny railing/flagpole UV differences at
    # large world coordinates. Photographed wall materials use world-space UVs.
    return [((p[axes[0]]-a[axes[0]])/300,(p[axes[1]]-a[axes[1]])/300) for p in vertices]

def write_obj(obj,path):
    with path.open('w') as f:
        f.write('o VillageArchitecture\n')
        for x,y,z in obj.vertices:f.write(f'v {x:.4f} {-y:.4f} {z:.4f}\n')
        for face in obj.faces:
            for u,v in face_uvs([obj.vertices[i-1] for i in face]):f.write(f'vt {u:.8f} {v:.8f}\n')
        for index,(a,b,c) in enumerate(obj.faces):
            i=index*3+1;f.write(f'f {a}/{i} {c}/{i+2} {b}/{i+1}\n')

def clear_veranda_posts(points):
    """Keep the entire inferred road width clear; use a cantilever if too tight."""
    return points if all(base.distance_to_segment(p[0],p[1],a,b)>=width/2+50
                         for p in points for a,b,width in base.SEGMENTS) else []

class Geometry:
    def __init__(self):self.groups={};self.anchor=(0,0);self.stats={}
    def obj(self,mat):
        key=(int(self.anchor[0]//24000),int(self.anchor[1]//24000),mat)
        return self.groups.setdefault(key,base.Obj())
    def quad(self,mat,p):self.obj(mat).quad(p)
    def box(self,mat,p,size,yaw=0):
        x,y,z=p;w,d,h=[v/2 for v in size];c,s=math.cos(yaw),math.sin(yaw)
        pts=[(x+c*a-s*b,y+s*a+c*b,z+k) for k in (-h,h) for a,b in [(-w,-d),(w,-d),(w,d),(-w,d)]]
        for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:self.quad(mat,[pts[i] for i in f])
    def rod(self,mat,a,b,r=8,n=8):
        # Stable orthonormal frame around a cylinder of arbitrary direction.
        v=[b[i]-a[i] for i in range(3)];length=math.sqrt(sum(q*q for q in v))
        if length<.001:return
        v=[q/length for q in v];ref=[0,0,1] if abs(v[2])<.9 else [1,0,0]
        u=[v[1]*ref[2]-v[2]*ref[1],v[2]*ref[0]-v[0]*ref[2],v[0]*ref[1]-v[1]*ref[0]]
        m=math.sqrt(sum(q*q for q in u));u=[q/m for q in u]
        w=[v[1]*u[2]-v[2]*u[1],v[2]*u[0]-v[0]*u[2],v[0]*u[1]-v[1]*u[0]]
        rings=[[(p[j]+r*(u[j]*math.cos(i*2*math.pi/n)+w[j]*math.sin(i*2*math.pi/n))) for j in range(3)] for p in (a,b) for i in range(n)]
        for i in range(n):self.quad(mat,[rings[i],rings[(i+1)%n],rings[(i+1)%n+n],rings[i+n]])
        ob=self.obj(mat)
        for offset,rev in ((0,True),(n,False)):
            for i in range(1,n-1):
                q=[rings[offset],rings[offset+i],rings[offset+i+1]]
                if rev:q.reverse()
                st=len(ob.vertices)+1;ob.vertices.extend(q);ob.faces.append((st,st+1,st+2))
    def dome(self,mat,p,r,h):
        x,y,z=p;rows=[];n=32
        for j in range(13):
            t=j/12*math.pi/2
            rr=max(.5,math.cos(t)*r*(1+.12*math.sin(t*2)))
            rows.append([(x+rr*math.cos(i*2*math.pi/n),y+rr*math.sin(i*2*math.pi/n),z+math.sin(t)*h) for i in range(n)])
        for a,b in zip(rows,rows[1:]):
            for i in range(n):self.quad(mat,[a[i],a[(i+1)%n],b[(i+1)%n],b[i]])
    def beam(self,mat,a,b,w=12,h=12):
        self.box(mat,((a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2),(math.dist(a[:2],b[:2]),w,h),math.atan2(b[1]-a[1],b[0]-a[0]))
    def save(self,dest):
        dest.mkdir(parents=True,exist_ok=True);items=[]
        for (x,y,mat),obj in sorted(self.groups.items()):
            name=f'SM_V3_{x+4}_{y+4}_{mat}';path=dest/(name+'.obj');write_obj(obj,path)
            items.append(dict(name=name,file=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),material=mat,triangles=len(obj.faces),collision=mat not in ('glass','leaves','crop','water')))
        return items

def house(g,b):
    if b['pilot']:return
    pts=b['points'];cx,cy=b['center'];g.anchor=(cx,cy);h=b['height'];seed=b['seed'];style=b['style']
    paint='paint'+str(b['palette']);trim='cream' if seed%3 else 'ochre'
    wall='brick' if style in ('brick_courtyard','farmhouse') else paint
    # Modern family homes have a genuine set-back upper floor and usable roof silhouette.
    stepped=style in ('modern_terrace','stepped_family_home') and h>500
    lower=330 if stepped else h
    for a,z,ring in [(0,lower,pts)]+([(330,h,[(cx+(p[0]-cx)*.76,cy+(p[1]-cy)*.76) for p in pts])] if stepped else []):
        for p,q in zip(ring,ring[1:]+ring[:1]):
            g.quad(wall,[(p[0],p[1],a),(q[0],q[1],a),(q[0],q[1],z),(p[0],p[1],z)])
            g.beam(trim,(*p,z+22),(*q,z+22),22,44)
        g.obj('roof').polygon(ring,z)
    if style=='brick_courtyard':
        # Raised courtyard ventilation pavilion, open on four sides.
        for u in (-85,85):
            for v in (-85,85):g.rod(trim,(cx+u,cy+v,h),(cx+u,cy+v,h+165),13)
        g.box('terracotta',(cx,cy,h+174),(235,235,18))
    edges=list(zip(pts,pts[1:]+pts[:1]))
    # Choose the facade nearest a mapped road (deterministic tie-break by edge).
    front=min(range(len(edges)),key=lambda i:min(base.distance_to_segment((edges[i][0][0]+edges[i][1][0])/2,(edges[i][0][1]+edges[i][1][1])/2,a,b) for a,b,_ in base.SEGMENTS))
    for ei,(a,bp) in enumerate(edges):
        length=math.dist(a,bp)
        if length<160:continue
        dx,dy=(bp[0]-a[0])/length,(bp[1]-a[1])/length;nx,ny=dy,-dx;angle=math.atan2(dy,dx)
        def p(u,v,z):return (a[0]+dx*u+nx*v,a[1]+dy*u+ny*v,z)
        def box(mat,u,v,z,w,d,hh):g.box(mat,p(u,v,z),(w,d,hh),angle)
        box('concrete',length/2,2,25,length,20,50)
        for z in range(145,int(lower),330):
            for i in range(max(1,int(length/360))):
                u=(i+.5)*length/max(1,int(length/360))
                if ei==front and z==145 and abs(u-length/2)<125:continue
                box(trim,u,9,z,114,14,134);box('glass',u,18,z,91,10,111)
                box('wood' if style=='farmhouse' else 'metal',u,27,z,5,10,112)
                box('metal',u,27,z,92,10,5)
                # Deep chajja with side brackets casts useful sun shadows.
                box(trim,u,42,z+78,140,95,12)
                if style in ('pastel_jali','haveli_balcony'):
                    for off in (-30,0,30):box('metal',u+off,29,z,3,8,110)
        if ei!=front:continue
        doorw=min(155,length*.30);u=length*(.40 if seed%2 else .59)
        box(trim,u,11,117,doorw+32,22,234);box('wood' if seed%2 else 'metal',u,24,110,doorw,10,220)
        for j in range(1,5):box('ochre',u-doorw/2+j*doorw/5,31,110,4,6,200)
        box('metal',u+doorw*.3,39,105,9,7,15)
        box(trim,u,65,244,doorw+90,145,16)
        if style in ('lime_veranda','farmhouse'):
            width=min(length-40,800 if style=='farmhouse' else 650)
            box('roof',length/2,100,278,width,260 if style=='farmhouse' else 220,20)
            posts=clear_veranda_posts([p(length/2+s*width,182,0) for s in (-.43,.43)])
            for point in posts:g.rod(trim,point,(point[0],point[1],270),16,12)
            if style=='farmhouse':
                box('brick',length/2,0,h+98,min(240,width*.4),80,150)
                for j in (-1,0,1):box('metal',length/2+j*50,44,h+98,22,8,70)
        if style=='haveli_balcony' and h>500:
            width=min(length-40,500);box(trim,length/2,70,342,width,155,22)
            box(trim,length/2,155,427,width,12,12)
            for j in range(int(width/35)+1):box('metal',length/2-width/2+j*35,155,387,5,6,75)
            box(trim,length/2,65,590,width+55,170,16)
        if style=='pastel_jali':
            for j in range(int(length/65)):
                box(trim,(j+.5)*65,6,h+68,34,16,64)
            box(trim,length/2,6,h+105,length,24,12)
        if style=='corner_shop_home' and length>360:
            width=min(300,length*.45);box('metal',length/2,30,115,width,12,225)
            for z in range(15,220,15):box('concrete',length/2,38,z,width,4,3)
            box('ochre' if seed%2 else 'teal',length/2,75,255,width+55,155,14)
            box('cream',length/2,40,287,width+40,20,40)
        # Rainwater downpipe on one end, plus visible coping and storey bands.
        g.rod('metal',p(35,15,25),p(35,15,h+15),4)
        if h>500:box(trim,length/2,6,330,length,20,18)
    if seed%3!=0:
        g.rod('tank',(cx,cy,h+10),(cx,cy,h+135),55,16)
        for z in (h+40,h+85,h+120):g.rod('metal',(cx,cy,z),(cx,cy,z+4),57,16)
    if seed%4==0:
        g.box('solar',(cx+105,cy,h+45),(145,210,9))
        for j in range(3):g.box('metal',(cx+55+j*50,cy,h+52),(3,210,3))
    if style=='stepped_family_home':
        for j in range(10):g.box('concrete',(cx-100+j*19,cy+100,h+7+j*12),(22,90,14))

def landmark(g,p):
    x,y,_=p['center_cm'];w,d=p['size_cm'];g.anchor=(x,y);k=p['kind']
    def box(mat,a,b,z,ww,dd,h):g.box(mat,(x+a,y+b,z),(ww,dd,h))
    def rod(mat,a,b,r=10):g.rod(mat,(x+a[0],y+a[1],a[2]),(x+b[0],y+b[1],b[2]),r,12)
    def dome(mat,a,b,z,r,h):g.dome(mat,(x+a,y+b,z),r,h)
    box('paving',0,0,4,w,d,8)
    # Low compound walls, an actual 5m entrance, and continuous flat walkable paving.
    for a in (-1,1):box('cream',a*(w/4+125),-d/2,55,w/2-250,22,110)
    for a in (-1,1):box('cream',a*w/2,0,55,22,d,110)
    box('cream',0,d/2,55,w,22,110)
    if k in ('gurdwara','mandir'):
        ww,dd=(2200,2000) if k=='gurdwara' else (1100,1300)
        # Raised hall with open south entry and deep porch. No real interior claimed.
        box('cream',0,450,20,ww+160,dd+160,40)
        for a in (-1,1):box('cream',a*(ww/4+90),450-dd/2,270,ww/2-180,35,500)
        box('cream',0,450-dd/2,495,ww,35,55)
        for a in (-1,1):box('cream',a*ww/2,450,270,35,dd,500)
        box('cream',0,450+dd/2,270,ww,35,500)
        box('cream',0,450,540,ww+100,dd+100,35)
        for a in (-1,1):
            rod('cream',(a*ww*.4,330-dd/2,40),(a*ww*.4,330-dd/2,510),30)
            for j in (-1,0,1):
                box('teal',a*(ww/2+20),450+j*dd*.27,290,8,150,240)
                box('ochre',a*(ww/2+28),450+j*dd*.27,415,12,180,14)
        if k=='gurdwara':
            dome('cream',0,450,555,420,430)
            for a in (-1,1):
                for b in (-1,1):
                    rod('cream',(a*ww*.43,450+b*dd*.43,540),(a*ww*.43,450+b*dd*.43,680),86)
                    dome('cream',a*ww*.43,450+b*dd*.43,680,108,120)
            rod('ochre',(0,450,980),(0,450,1090),12)
            rod('ochre',(-w*.36,-d*.3,0),(-w*.36,-d*.3,1500),13)
            # Saffron triangular Nishan Sahib flag; no invented religious text.
            a=(x-w*.36,y-d*.3,1450);g.quad('saffron',[a,(a[0]+240,a[1],1380),(a[0]+35,a[1],1320),(a[0],a[1],1320)])
            # Langar veranda to one side, outside main hall.
            box('cream',w*.38,450,300,450,1600,25)
            for j in (-1,0,1):rod('cream',(w*.44,450+j*650,0),(w*.44,450+j*650,290),17)
        else:
            for i in range(10):
                side=650-i*46;box('terracotta' if i%2 else 'ochre',0,600,580+i*57,side,side,60)
            dome('ochre',0,600,1145,90,70);rod('saffron',(0,600,1200),(0,600,1450),8)
            g.quad('saffron',[(x,y+600,1440),(x+180,y+600,1390),(x+40,y+600,1340),(x,y+600,1340)])
            rod('ochre',(0,450-dd/2-80,350),(0,450-dd/2-80,470),5)
            dome('ochre',0,450-dd/2-80,330,30,25)
    elif k=='school':
        # U-shaped classroom wings and shaded veranda face a spacious court.
        for a in (-1,0,1):
            bx=a*1250;box('paint8',bx,1100,175,1150,900,350);box('cream',bx,1100,360,1230,1000,20)
            for j in (-1,1):box('teal',bx+j*320,640,180,180,15,170)
            box('metal',bx,635,110,140,18,220)
            box('terracotta',bx,475,285,1220,380,20)
            for j in (-1,1):rod('cream',(bx+j*500,320,0),(bx+j*500,320,280),16)
        box('paint8',-1650,-200,175,650,1600,350);box('cream',-1650,-200,360,720,1700,22)
        rod('metal',(0,-600,0),(0,-600,900),9)
        box('soil',850,-600,9,1400,1200,12)
        # Benches, blackboard and handwash station.
        for j in range(4):box('wood',-750+j*500,150,42,220,45,15)
        box('teal',-1610,-1020,170,420,14,155)
        box('concrete',1450,-1100,60,400,90,120)
    elif k=='market':
        for j,mat in enumerate(('paint4','paint8','paint7','paint3','brick')):
            bx=(j-2)*610;box(mat,bx,400,165,590,1000,330);box('roof',bx,400,340,620,1060,20)
            box('metal',bx,-110,120,400,15,240)
            for z in range(20,235,18):box('concrete',bx,-121,z,395,4,4)
            box('saffron' if j%2 else 'teal',bx,-255,255,600,330,15)
            box('cream',bx,-120,292,490,20,48)
            # Produce bins at accessible pavement, separate from doorway.
            box('wood',bx+220,-480,45,130,110,90)
            for f in range(4):g.dome('crop',(x+bx+185+(f%2)*50,y-510+(f//2)*50,92),20,20)
        box('wood',-950,-850,100,240,80,12)
        for a in (-1,1):rod('metal',(-950+a*100,-850,0),(-950+a*100,-850,100),5)
    elif k=='playground':
        box('soil',0,100,10,w-400,d-500,12)
        # Football goal frames and cricket pitch, line markings remain flat.
        for side in (-1,1):
            yy=side*(d/2-550)
            for xx in (-350,350):rod('cream',(xx,yy,0),(xx,yy,240),6)
            rod('cream',(-350,yy,240),(350,yy,240),6)
        box('concrete',0,0,18,300,2000,5)
        for side in (-1,1):
            for xx in (-15,0,15):rod('wood',(xx,side*950,20),(xx,side*950,90),2)
        for side in (-1,1):box('cream',side*(w/2-400),100,20,8,d-1100,3)
        # Swing frames and a slide; original non-interactive playground props.
        for bx in (-1500,-850):
            rod('teal',(bx,-1400,0),(bx,-1200,300),8);rod('teal',(bx,-1000,0),(bx,-1200,300),8)
        rod('teal',(-1500,-1200,300),(-850,-1200,300),8)
        for bx in (-1360,-980):rod('metal',(bx,-1200,290),(bx,-1200,70),2)
        box('wood',-1170,-1200,65,420,60,10)
    elif k in ('dairy','farm'):
        box('brick',0,d*.24,140,w*.7,32,280)
        for xx in (-w*.35,0,w*.35):
            for yy in (0,d*.36):rod('cream',(xx,yy,0),(xx,yy,300),17)
        box('roof',0,d*.18,315,w*.8,d*.45,22)
        # Open cattle shed, troughs, fodder stacks, milk churns.
        for j in range(6):
            box('concrete',-w*.32+j*w*.128,20,40,170,90,80)
            box('water',-w*.32+j*w*.128,20,82,145,65,4)
        for j in range(3):g.rod('straw',(x+w*.3,y+d*.1+j*120,0),(x+w*.3,y+d*.1+j*120,130),85,14)
        for j in range(4):g.rod('metal',(x-w*.36+j*70,y-250,0),(x-w*.36+j*70,y-250,80),26,12)
        for xx in (-w*.38,w*.38):
            for yy in range(-int(d*.4),10,230):rod('wood',(xx,yy,0),(xx,yy,110),7)
            for zz in (45,95):rod('wood',(xx,-d*.4,zz),(xx,0,zz),6)
    elif k=='tower':
        for xx in (-350,350):
            for yy in (-350,350):rod('concrete',(xx,yy,0),(xx,yy,2200),44)
        for z in (700,1400,2050):
            for yy in (-350,350):rod('concrete',(-350,yy,z),(350,yy,z),22)
            for xx in (-350,350):rod('concrete',(xx,-350,z),(xx,350,z),22)
        rod('paint4',(0,0,2100),(0,0,2800),530)
        dome('cream',0,0,2800,530,140)
        rod('metal',(560,0,0),(560,0,2800),12)
        for z in range(50,2900,40):rod('metal',(530,-30,z),(630,-30,z),3)
    elif k=='telecom':
        corners=[(-260,-260),(260,-260),(0,260)]
        for xx,yy in corners:rod('metal',(xx,yy,0),(xx*.12,yy*.12,3600),12)
        for z in range(0,3400,300):
            scale=1-z/4100;nexts=1-(z+300)/4100
            for i,(xx,yy) in enumerate(corners):
                a,b=corners[(i+1)%3];rod('metal',(xx*scale,yy*scale,z),(a*nexts,b*nexts,z+300),5)
        for a in (-1,1):box('cream',a*110,0,3250,55,90,350)
        box('brick',500,400,140,500,450,280)

def fields(g,plan):
    for p in plan['fields']:
        x,y,_=p['center_cm'];w,d=p['size_cm'];g.anchor=(x,y);crop=p['crop']
        g.box('soil',(x,y,2),(w,d,4))
        for off in range(-int(w/2)+70,int(w/2),130):
            if crop=='tilled_soil':g.box('soil_light',(x+off,y,8),(50,d-80,12))
            elif crop=='rice_stubble':
                for yy in range(-int(d/2)+100,int(d/2),230):g.box('straw',(x+off,y+yy,22),(18,22,38))
            else:
                g.box('soil_light',(x+off,y,9),(70,d-100,16))
                g.box('crop' if crop=='vegetables' else 'leaves',(x+off,y,30),(45,d-150,45))
        for side in (-1,1):
            g.box('soil_light',(x+side*w/2,y,17),(70,d,30))
            g.box('soil_light',(x,y+side*d/2,17),(w,70,30))
        # Narrow irrigation channel alongside each demonstration parcel.
        g.box('water',(x-w/2+100,y,9),(55,d-120,5))

def generate(plan,directory):
    g=Geometry()
    for b in plan['buildings']:house(g,b)
    for p in plan['landmarks']:landmark(g,p)
    fields(g,plan)
    return g.save(Path(directory))

if __name__=='__main__':
    p=json.loads((ROOT/'Assets/World/v3_world.json').read_text())
    items=generate(p,ROOT/'Saved/VillageMeshV3/Geometry')
    manifest=dict(plan_sha256=hashlib.sha256((ROOT/'Assets/World/v3_world.json').read_bytes()).hexdigest(),
                  generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),items=items)
    (ROOT/'Saved/VillageMeshV3/geometry_manifest.json').write_text(json.dumps(manifest,indent=2))
    print('V3 meshes:',len(items),'triangles:',sum(i['triangles'] for i in items))

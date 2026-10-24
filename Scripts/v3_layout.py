"""Full mapped village design. Source footprints remain separate from authored land uses.

All dimensions are cm; +X east, +Y north. No private resident data is used.
"""
import json, math, random, hashlib
from pathlib import Path
from collections import Counter
import pandori_layout as base
import v2_data

ROOT = Path(__file__).resolve().parents[1]
STYLES = ['lime_veranda', 'brick_courtyard', 'haveli_balcony', 'modern_terrace',
          'pastel_jali', 'farmhouse', 'corner_shop_home', 'stepped_family_home']
COLORS = [(.73,.67,.52),(.61,.36,.24),(.72,.67,.60),(.72,.76,.70),
          (.37,.56,.52),(.72,.53,.39),(.61,.65,.72),(.70,.46,.47),
          (.82,.76,.57),(.49,.57,.42),(.71,.63,.51),(.58,.52,.43)]
PILOT = v2_data.read('Assets/Routes/pilot_street.json')
PILOT_IDS = {f['building_id'] for f in PILOT['frontages']}
BUILDINGS = v2_data.normalized_buildings()

def rect(x,y,w,d): return [x-w/2,y-d/2,x+w/2,y+d/2]
def overlap(a,b,pad=0): return a[0]-pad<b[2] and a[2]+pad>b[0] and a[1]-pad<b[3] and a[3]+pad>b[1]
def bbox(points): return [min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
def nearest_road(p):
    best=(float('inf'),None)
    for a,b,w in base.SEGMENTS:
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/max(1,dx*dx+dy*dy)))
        q=[a[0]+t*dx,a[1]+t*dy]
        d=math.dist(p,q)
        if d<best[0]:best=(d,q)
    return best

def road_intersects(box,margin=120):
    # Liang-Barsky segment/expanded rectangle test (full segments, not sampled points).
    for a,b,width in base.SEGMENTS:
        r=[box[0]-width/2-margin,box[1]-width/2-margin,box[2]+width/2+margin,box[3]+width/2+margin]
        lo,hi=0.,1.; dx,dy=b[0]-a[0],b[1]-a[1]
        hit=True
        for p,q in [(-dx,a[0]-r[0]),(dx,r[2]-a[0]),(-dy,a[1]-r[1]),(dy,r[3]-a[1])]:
            if abs(p)<1e-9:
                if q<0:hit=False;break
            elif p<0:lo=max(lo,q/p)
            else:hi=min(hi,q/p)
        if hit and lo<=hi:return True
    return False

def make_plan():
    occupied=[bbox(b['points']) for b in BUILDINGS]
    # Preserve the pilot's door/farm paths and physics yard.
    reserved=[[-16000,-7500,8000,6000],[-56000,-47000,-44000,-35000]]
    landmarks=[]
    def add(identifier,name,kind,w,d,preferred,source=None,reference=None):
        # Reference coordinates inform the neighbourhood; never claim an inferred
        # building replacement is an observed facade or surveyed site boundary.
        candidates=[]
        search=sorted((math.dist((x,y),preferred),x,y) for x in range(-54000,55000,1000) for y in range(-53000,54000,1000))
        for lower,x,y in search:
                if candidates and lower>min(candidates)[0]:break
                r=rect(x,y,w+250,d+250)
                if any(overlap(r,b) for b in reserved+occupied) or road_intersects(r):continue
                rd,_=nearest_road((x,y))
                if rd>6000:continue
                candidates.append((lower+rd*.8,x,y))
        if not candidates:raise ValueError('No clear land for '+identifier)
        _,x,y=min(candidates)
        area=rect(x,y,w,d);reserved.append(rect(x,y,w+500,d+500))
        approach=[x,y-d/2-140,100]
        if any(overlap(rect(approach[0],approach[1],150,150),b) for b in occupied):
            approach=[x,y-d/2+160,100]
        landmarks.append(dict(id=identifier,name=name,kind=kind,center_cm=[x,y,0],size_cm=[w,d],
            arrival_cm=approach,reference_wgs84=reference,source=source,
            look_at_cm=[x,y,{'tower':1450,'telecom':1800,'gurdwara':450,'mandir':400,'playground':90,'dairy':100,'farm':100}.get(kind,220)],
            location_confidence='representative clear-site placement',
            architecture_confidence='original regional interpretation; facade unverified'))
    temple=base.project(75.7194471,31.4597992)
    add('mandir','Shiv Mandir','mandir',2300,2800,temple,
        'http://wikimapia.org/15450774/Shiv-Temple',[31.4597992,75.7194471])
    # The public listing supplies a short Plus Code, not a surveyed site polygon.
    add('gurdwara','Gurdwara Sahib','gurdwara',3800,4200,(17000,-3000),
        'https://yappe.in/punjab/pandori-nijjaran/gurudwara-nihang-singh-pandori-nijjaran/1529679')
    add('school','Village School','school',4200,4200,(-18000,16000),
        'https://www.icbse.com/schools/gps-pandori-nijjaran-ezqk9')
    add('playground','Sports Ground','playground',4800,5600,(-17000,22000))
    add('market','Village Bazaar','market',3600,2600,(5000,6500))
    add('dairy','Dairy and Cattle Yard','dairy',4600,3800,(25000,-22000))
    add('tower','Water Tower','tower',2000,2200,(-21000,-20000))
    add('telecom','Telecom Mast','telecom',1800,2000,(27000,18000))
    add('farm','Agriculture Centre','farm',3600,2800,(32000,-35000))
    farms=[]
    for y in range(-53000,54000,8500):
        for x in range(-54000,55000,8500):
            area=rect(x,y,6500,6500)
            if any(overlap(area,b,200) for b in occupied+reserved) or road_intersects(area):continue
            farms.append(dict(id='field_'+str(len(farms)),center_cm=[x,y,0],size_cm=[6500,6500],
                              crop=['rice_stubble','vegetables','fodder','tilled_soil'][len(farms)%4],
                              confidence='representative farming; not a cadastral or crop survey'))
    homes=[]
    for b in BUILDINGS:
        seed=v2_data.seed(b['id']);style=STYLES[seed%len(STYLES)]
        # Variation follows persistent IDs and never depends on input order.
        homes.append(dict(id=b['id'],points=b['points'],center=b['center'],height=b['height'],
                          style=style,palette=(seed//8)%len(COLORS),seed=seed,
                          pilot=b['id'] in PILOT_IDS))
    return dict(schema_version=1,extent_cm=[-64000,-64000,64000,64000],
        place='Pandori Nijjaran / Adampur / Punjab 144102',origin_wgs84=[base.LAT,base.LON],
        confidence='OSM roads and Overture outlines; authored architecture and land uses',
        buildings=homes,roads=base.ROADS,landmarks=landmarks,fields=farms,
        navigation_stops=[dict(id='homes_walk',name='Residential Lane',kind='residential',
            center_cm=[3748,-18128,0],arrival_cm=[3748,-18128,100],look_at_cm=[3672,-17432,145],
            confidence='Navigation viewpoint on a mapped road, outside the preserved pilot; not an official street name')],
        counts=dict(buildings=len(homes),roads=len(base.ROADS),landmarks=len(landmarks),fields=len(farms),
                    styles=dict(Counter(h['style'] for h in homes))))

def render_map(plan,path):
    from PIL import Image,ImageDraw
    size=1536;im=Image.new('RGB',(size,size),(31,47,40));d=ImageDraw.Draw(im)
    def xy(p):return ((p[0]+64000)/128000*size,(64000-p[1])/128000*size)
    for k in range(0,size,192):d.line((k,0,k,size),fill=(40,57,48));d.line((0,k,size,k),fill=(40,57,48))
    for f in plan['fields']:
        x,y,_=f['center_cm'];w,h=f['size_cm'];a,b=xy((x-w/2,y+h/2)),xy((x+w/2,y-h/2))
        d.rectangle((*a,*b),fill=(70,84,48),outline=(101,105,65),width=2)
        for j in range(int(a[1])+4,int(b[1]),8):d.line((a[0]+2,j,b[0]-2,j),fill=(81,94,52))
    for h in plan['buildings']:
        c=COLORS[h['palette']];d.polygon([xy(p) for p in h['points']],fill=tuple(int(v*175) for v in c),outline=(157,151,125))
    for r in plan['roads']:
        d.line([xy(p) for p in r['points']],fill=(180,164,127),width=max(2,int(r['width']/128000*size)),joint='curve')
    for p in plan['landmarks']:
        x,y,_=p['center_cm'];w,h=p['size_cm'];a,b=xy((x-w/2,y+h/2)),xy((x+w/2,y-h/2))
        d.rectangle((*a,*b),fill=(133,112,66),outline=(230,195,112),width=2)
    path.parent.mkdir(parents=True,exist_ok=True);im.save(path)

def main():
    plan=make_plan()
    dest=ROOT/'Assets/World';dest.mkdir(parents=True,exist_ok=True)
    (dest/'v3_world.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    render_map(plan,dest/'v3_map.png')
    staged=ROOT/'Content/V3/Data';staged.mkdir(parents=True,exist_ok=True)
    (staged/'v3_world.json').write_bytes((dest/'v3_world.json').read_bytes())
    print(json.dumps(plan['counts']))

if __name__=='__main__':main()

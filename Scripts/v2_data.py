"""Engine-independent V2 inputs. Preserve IDs, confidence and reviewed overrides.

No measurement is fabricated: source attributes, explicit corrections and seeded
inference remain separate. Generation never writes any of the source manifests.
"""
import hashlib
import json
import math
from pathlib import Path
import pandori_layout as base

ROOT = Path(__file__).resolve().parents[1]
CONFIDENCE = {'measured', 'photo-estimated', 'sourced map attribute', 'procedural inference'}


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


def seed(identifier):
    return int.from_bytes(hashlib.sha256(identifier.encode()).digest()[:8], 'big')


def normalized_buildings(features=None, overrides=None):
    features = features if features is not None else read('Assets/Geodata/pandori_nijjaran.buildings.geojson')['features']
    overrides = overrides if overrides is not None else read('Assets/Geodata/overrides.geojson')['features']
    lookup = {}
    for override in overrides:
        props = override['properties']
        identifier = props['building_id']
        if identifier in lookup:
            raise ValueError('Duplicate building override: ' + identifier)
        if props.get('confidence') not in CONFIDENCE or not props.get('reason'):
            raise ValueError('Override requires explicit confidence and reason')
        lookup[identifier] = props
    output = []
    seen = set()
    for feature in features:
        identifier = feature.get('id') or feature.get('properties', {}).get('id')
        if not identifier:
            raise ValueError('Stable source ID required; array indices are not building IDs')
        geometry = feature['geometry']
        polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
        for part, rings in enumerate(polygons):
            stable = identifier if len(polygons) == 1 else identifier + ':part:' + str(part)
            if stable in seen:
                raise ValueError('Duplicate building ID: ' + stable)
            seen.add(stable)
            points = [base.project(*p[:2]) for p in rings[0][:-1]]
            if len(rings) != 1:
                raise ValueError('Courtyard rings need explicit hole triangulation: ' + stable)
            center = tuple(sum(p[k] for p in points) / len(points) for k in (0, 1))
            if max(abs(v) for v in center) > 63000:
                continue
            if sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])) < 0:
                points.reverse()
            props = feature['properties']
            source_height = props.get('height')
            source_floors = props.get('num_floors')
            height_m = source_height if isinstance(source_height, (int,float)) and source_height > 0 else None
            if height_m is None and isinstance(source_floors, int) and source_floors > 0:
                height_m = source_floors * 3.3
                confidence = 'procedural inference'
                reason = 'Source floor count multiplied by inferred 3.3 m storey height'
            elif height_m is not None:
                confidence, reason = 'sourced map attribute', 'Overture height attribute; not independently surveyed'
            else:
                height_m = 3.3 * (1 + int(seed(stable) % 3 == 0))
                confidence, reason = 'procedural inference', 'Stable seeded one/two-storey fallback'
            correction = lookup.get(stable, {})
            if 'height_m' in correction:
                height_m = correction['height_m']
                confidence, reason = correction['confidence'], correction['reason']
            if not isinstance(height_m, (int,float)) or not math.isfinite(height_m) or not 2.4 <= height_m <= 60:
                raise ValueError('Invalid building height: ' + stable)
            output.append(dict(id=stable, source_id=identifier, source_release='2026-10-21.0',
                points=points, center=center, height=height_m*100,
                material=correction.get('material', 'brick' if seed(stable)%4 == 0 else 'plaster'),
                confidence=confidence, height_reason=reason, source_attributes=props,
                override=correction, seed=seed(stable)))
    missing = set(lookup) - {b['id'] for b in output}
    if missing:
        raise ValueError('Orphaned overrides require explicit review: ' + ', '.join(sorted(missing)))
    return sorted(output, key=lambda b:b['id'])


def closest(point, polyline):
    best = None
    travelled = 0.0
    for a,b in zip(polyline, polyline[1:]):
        dx,dy = b[0]-a[0],b[1]-a[1]
        length = math.hypot(dx,dy)
        if length < .001: continue
        t = max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/(length*length)))
        hit = (a[0]+t*dx,a[1]+t*dy)
        candidate = (math.dist(point[:2],hit),travelled+t*length,hit,(dx/length,dy/length))
        if best is None or candidate[0] < best[0]: best = candidate
        travelled += length
    return best


def at_distance(polyline, distance):
    for a,b in zip(polyline,polyline[1:]):
        length=math.dist(a,b)
        if distance <= length:
            t=distance/max(length,1e-9)
            return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t), math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
        distance-=length
    a,b=polyline[-2:]
    return tuple(b), math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))


def front_edge(building, route):
    options=[]
    points=building['points']
    for index,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
        length=math.dist(a,b)
        if not 450 <= length <= 2600: continue
        midpoint=((a[0]+b[0])/2,(a[1]+b[1])/2)
        d,chain,hit,tangent=closest(midpoint,route)
        nx,ny=(b[1]-a[1])/length,-(b[0]-a[0])/length
        facing=(hit[0]-midpoint[0])*nx+(hit[1]-midpoint[1])*ny
        if facing < 150 or d > 2200: continue
        options.append((d,index,chain))
    return min(options) if options else None


def point_inside(point, ring):
    x,y=point[:2];inside=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside=not inside
    return inside


def entrance_clear(building, edge_index, buildings):
    """Check the 34 cm player capsule plus margin on a representative approach.

    This rejects second-row facades behind another footprint; it does not replace
    the runtime collision walk through the generated opening.
    """
    ring=building['points'];a,b=ring[edge_index],ring[(edge_index+1)%len(ring)]
    length=math.dist(a,b);nx,ny=-(b[1]-a[1])/length,(b[0]-a[0])/length
    center=((a[0]+b[0])/2,(a[1]+b[1])/2)
    for offset in range(-240,141,20):
        point=(center[0]+nx*offset,center[1]+ny*offset)
        for other in buildings:
            if other['id']==building['id']:continue
            if math.dist(point,other['center'])>6000:continue
            if point_inside(point,other['points']):return False
            if min(base.distance_to_segment(*point,p,q) for p,q in zip(other['points'],other['points'][1:]+other['points'][:1]))<45:
                return False
        if offset>=60 and not point_inside(point,ring):return False
    return True


def sightline_clear(start, end, target_id, buildings):
    steps=max(1,math.ceil(math.dist(start[:2],end[:2])/40))
    for i in range(steps):
        p=tuple(start[j]+(end[j]-start[j])*i/steps for j in (0,1))
        for b in buildings:
            if b['id']!=target_id and math.dist(p,b['center'])<6000 and point_inside(p,b['points']):return False
    return True


def aim_pilot_cameras(pilot, buildings):
    """Keep route viewpoints fixed and aim at visible frontages, not occluding shells."""
    lookup={b['id']:b for b in buildings}
    for camera in pilot['cameras']:
        start=camera['position_cm']
        options=[]
        for f in pilot['frontages']:
            b=lookup[f['building_id']];p=b['points'];edge=f['edge_index'];a,c=p[edge],p[(edge+1)%len(p)]
            target=((a[0]+c[0])/2,(a[1]+c[1])/2)
            length=math.dist(a,c);nx,ny=(c[1]-a[1])/length,-(c[0]-a[0])/length
            if (start[0]-target[0])*nx+(start[1]-target[1])*ny<=0:continue
            if sightline_clear(start,target,b['id'],buildings):options.append((math.dist(start[:2],target),b['id'],target))
        if not options:raise ValueError('No visible pilot frontage for '+camera['id'])
        _,identifier,target=min(options)
        camera['target_building_id']=identifier
        camera['yaw_degrees']=math.degrees(math.atan2(target[1]-start[1],target[0]-start[0]))
    return pilot

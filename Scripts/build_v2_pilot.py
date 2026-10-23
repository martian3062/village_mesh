"""Original procedural architecture kit. All facade/interior dimensions are inferred.

Sixteen separate mapped buildings keep their outline; three have representative
enterable rooms. Modules use thick geometry and simple collision. No private
interior or landmark is claimed to have been observed.
"""
import json
import hashlib
import math
import random
import unreal
import pandori_layout as base
import v2_data as data


def build(api,site,world):
    import finalize_v2_materials
    finalize_v2_materials.build(api)
    kit=data.read('Assets/Architecture/archetypes.json')
    cube=api.EAL.load_asset('/Engine/BasicShapes/Cube.Cube')
    cylinder=api.EAL.load_asset('/Engine/BasicShapes/Cylinder.Cylinder')
    mats={}
    for i,style in enumerate(kit['styles']):
        mat=api.pbr('M_V2Paint_'+str(i),'rough_plaster_03',True)
        original=api.MEL.get_material_property_input_node(mat,unreal.MaterialProperty.MP_BASE_COLOR)
        tint=api.expr(mat,unreal.MaterialExpressionLinearInterpolate)
        api.link(original,tint,'A')
        api.link(api.expr(mat,unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(*style['paint'],1)),tint,'B')
        api.link(api.scalar(mat,.88),tint,'Alpha')
        api.MEL.connect_material_property(tint,'',unreal.MaterialProperty.MP_BASE_COLOR)
        # Flatten the scan's large bumps: these are painted masonry surfaces.
        normal=api.MEL.get_material_property_input_node(mat,unreal.MaterialProperty.MP_NORMAL)
        blend=api.expr(mat,unreal.MaterialExpressionLinearInterpolate)
        api.link(normal,blend,'A','RGB')
        api.link(api.expr(mat,unreal.MaterialExpressionConstant3Vector,constant=unreal.LinearColor(0,0,1,1)),blend,'B')
        api.link(api.scalar(mat,.8),blend,'Alpha')
        api.MEL.connect_material_property(blend,'',unreal.MaterialProperty.MP_NORMAL)
        mats['paint'+str(i)]=api.finish(mat)
        mats['trim'+str(i)]=api.solid('M_V2Trim_'+str(i),style['trim'])
    for name,color,rough in [('metal',(.065,.12,.13),.42),('glass',(.018,.055,.07),.12),
        ('concrete',(.36,.34,.29),.88),('wood',(.21,.12,.055),.73),
        ('interior',(.61,.55,.43),.92),('tank',(.025,.03,.035),.5),
        ('soil',(.23,.17,.10),.96),('terracotta',(.38,.15,.075),.86),('drain',(.06,.055,.04),.98)]:
        mats[name]=api.solid('M_V2_'+name,color,rough)
    mats['road']=api.EAL.load_asset(api.MAT+'/M_PandoriRoad')
    mats['soil']=api.pbr('M_V2RoadsideSoil','brown_mud_leaves_01')
    # Replace the earlier broad triangle groundcover with small CC0 verge plants.
    for actor in api.EAS.get_all_level_actors():
        if actor.get_actor_label()=='VM_Groundcover':api.EAS.destroy_actor(actor)
    shrub=api.EAL.load_asset(api.DEST+'/Vegetation/shrub_01/SM_shrub_01')
    verge_points=[];rng=random.Random(3062)
    for chain in range(0,int(site.PILOT['length_m']*100),320):
        pos,angle=data.at_distance(site.PILOT['centerline_cm'],chain)
        nx,ny=-math.sin(math.radians(angle)),math.cos(math.radians(angle))
        for side in (-1,1):
            offset=side*rng.uniform(285,380)
            x,y=pos[0]+nx*offset,pos[1]+ny*offset
            if site.clear_site(x,y,60):verge_points.append(((x,y,0),rng.uniform(.12,.22),rng.uniform(0,360)))
    import build_pcg_biome
    verge_count=build_pcg_biome.build(api,[(shrub,verge_points)],'PCG_PilotVerges','V2_PCG_Verges')
    for actor in api.EAS.get_all_level_actors():
        if actor.get_actor_label()=='V2_PCG_Verges':actor.set_editor_property('is_spatially_loaded',False)
    count=0
    interior_records=[]
    def box(label,position,size,material,yaw=0,collision=True):
        nonlocal count
        count+=1
        actor=api.mesh_actor(cube,material,label,position,tuple(max(.01,v)/100 for v in size),yaw,collision)
        actor.set_folder_path('V2/Pilot')
        return actor
    def import_surface(obj,name,material,collision=True):
        path=api.TMP/(name+'.obj');obj.save(path)
        mesh=api.import_file(path,name,api.DEST+'/Pilot')
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        settings=mesh.get_editor_property('nanite_settings')
        settings.set_editor_property('fallback_target',unreal.NaniteFallbackTarget.RELATIVE_ERROR)
        settings.set_editor_property('fallback_relative_error',0.0)
        mesh.set_editor_property('nanite_settings',settings)
        api.EAL.save_loaded_asset(mesh)
        return api.mesh_actor(mesh,material,name,(0,0,0),collide=collision)
    lookup={b['id']:b for b in site.BUILDINGS}
    for number,selection in enumerate(site.PILOT['frontages']):
        b=lookup[selection['building_id']]
        identifier=b['id'];tag='V2_'+identifier[:8]
        pts=b['points'];h=b['height'];floor=12.0;thick=kit['wall_thickness']
        style_index=data.seed(identifier)%len(kit['styles']);style=kit['styles'][style_index]
        paint=mats['paint'+str(style_index)];trim=mats['trim'+str(style_index)]
        front_index=selection['edge_index'];a,bp=pts[front_index],pts[(front_index+1)%len(pts)]
        length=math.dist(a,bp);dx,dy=(bp[0]-a[0])/length,(bp[1]-a[1])/length
        nx,ny=-dy,dx # inward normal of CCW boundary
        yaw=math.degrees(math.atan2(dy,dx))
        def xyz(u,v,z):return (a[0]+dx*u+nx*v,a[1]+dy*u+ny*v,z)
        def local(label,u,v,z,sx,sy,sz,material,collide=True):
            return box(tag+'_'+label,xyz(u,v,z),(sx,sy,sz),material,yaw,collide)
        # Each wall is independent, thick and collidable; no giant merged interior.
        door_center=length*.5;door_width=kit['door_width'];door_top=floor+kit['door_height']
        windows=[]
        for center in (length*.21,length*.79):
            if abs(center-door_center) > (door_width+kit['window_width'])/2+35:
                windows.append(center)
        openings=[(door_center-door_width/2,door_center+door_width/2,floor,door_top)]
        openings += [(c-kit['window_width']/2,c+kit['window_width']/2,floor+kit['window_sill'],floor+kit['window_sill']+kit['window_height']) for c in windows]
        openings.sort()
        for index,(p,q) in enumerate(zip(pts,pts[1:]+pts[:1])):
            edge_length=math.dist(p,q);angle=math.degrees(math.atan2(q[1]-p[1],q[0]-p[0]))
            inward=(-(q[1]-p[1])/edge_length,(q[0]-p[0])/edge_length)
            center=((p[0]+q[0])/2+inward[0]*thick/2,(p[1]+q[1])/2+inward[1]*thick/2)
            if index != front_index:
                box(tag+'_wall_'+str(index),(*center,(h+floor)/2),(edge_length+thick,thick,h-floor),paint,angle)
            else:
                cursor=0
                for j,(left,right,bottom,top) in enumerate(openings):
                    if left>cursor:
                        local('pier_'+str(j),(cursor+left)/2,thick/2,(h+floor)/2,left-cursor,thick,h-floor,paint)
                    if bottom>floor:
                        local('sillwall_'+str(j),(left+right)/2,thick/2,(bottom+floor)/2,right-left,thick,bottom-floor,paint)
                    local('lintel_'+str(j),(left+right)/2,thick/2,(h+top)/2,right-left,thick,h-top,paint)
                    cursor=right
                if cursor<length:
                    local('lastpier',(cursor+length)/2,thick/2,(h+floor)/2,length-cursor,thick,h-floor,paint)
            box(tag+'_parapet_'+str(index),(*center,h+32.5),(edge_length+8,18,65),paint,angle)
            box(tag+'_coping_'+str(index),(*center,h+69),(edge_length+12,27,8),trim,angle)
            box(tag+'_plinth_'+str(index),(*center,6),(edge_length+10,thick+12,12),mats['concrete'],angle)
        floor_mesh=base.Obj();floor_mesh.polygon(pts,floor)
        import_surface(floor_mesh,tag+'_floor',mats['interior'])
        roof=base.Obj();roof.polygon(pts,h)
        # Separate reverse-facing ceiling provides interior lighting geometry.
        import_surface(roof,tag+'_roof',mats['concrete'])
        ceiling=base.Obj();ceiling.polygon(pts,h-15)
        ceiling.faces=[tuple(reversed(face)) for face in ceiling.faces]
        import_surface(ceiling,tag+'_ceiling',mats['interior'])
        for side in (-1,1):
            local('door_frame_'+str(side),door_center+side*(door_width/2+5),-3,(floor+door_top)/2,10,12,door_top-floor+8,trim)
        local('door_head',door_center,-3,door_top+5,door_width+20,12,10,trim)
        # E-operated hinged door; native state survives stream-out/in by stable ID.
        door=api.EAS.spawn_actor_from_class(unreal.VillageDoor,unreal.Vector(*xyz(door_center-door_width/2,thick*.55,floor)),unreal.Rotator(yaw=yaw))
        door.set_actor_label(tag+'_Door')
        door.set_editor_property('persistent_id',identifier+':entry')
        door.set_editor_property('door_width_cm',door_width)
        door.set_editor_property('door_height_cm',kit['door_height'])
        door.set_editor_property('can_open',selection['interior'])
        door.get_editor_property('leaf').set_material(0,mats['metal'])
        local('threshold',door_center,-32,6,door_width+20,90,12,mats['concrete'])
        for j,c in enumerate(windows):
            bottom=floor+kit['window_sill'];top=bottom+kit['window_height'];ww=kit['window_width']
            local('glass_'+str(j),c,thick*.7,(bottom+top)/2,ww-8,3,top-bottom-8,mats['glass'],False)
            for side in (-1,1):
                local('jamb_%s_%s'%(j,side),c+side*(ww/2-3),thick/2,(bottom+top)/2,7,thick,top-bottom,trim)
            for z in (bottom,top):
                local('frame_%s_%s'%(j,int(z)),c,thick/2,z,ww,thick,7,trim)
            for bar in range(1,6):
                local('grill_%s_%s'%(j,bar),c-ww/2+bar*ww/6,-5,(bottom+top)/2,2.1,3,top-bottom,mats['metal'],False)
            local('sunshade_'+str(j),c,-38,top+18,ww+42,105,10,trim)
            local('sill_'+str(j),c,-12,bottom-4,ww+20,55,8,mats['concrete'])
        # Covered porch, downpipe, modest furniture and varied rooftop service kit.
        porch_width=min(length-50,360)
        local('porch',door_center,-88,door_top+32,porch_width,185,16,trim)
        for side in (-1,1):
            local('porch_post_'+str(side),door_center+side*(porch_width/2-14),-165,(door_top+floor)/2,15,15,door_top-floor,trim)
        local('pipe',length-28,-12,h/2,8,9,h,mats['metal'],False)
        local('runoff',length-28,-20,5,35,65,10,mats['drain'],False)
        if number%3 != 1:
            local('bench',length*.2,-80,47,115,38,8,mats['wood'])
            for off in (-43,43):local('bench_leg'+str(off),length*.2+off,-80,24,8,30,42,mats['metal'])
        if style['roof_tank']:
            cx,cy=b['center']
            box(tag+'_tank_support',(cx,cy,h+15),(150,150,30),mats['concrete'])
            api.mesh_actor(cylinder,mats['tank'],tag+'_tank',(cx,cy,h+82),(1.1,1.1,1.3))
        if selection['interior']:
            # Purpose-built representative space, not a resident's observed room.
            local('table',door_center+150,210,80,105,65,9,mats['wood'])
            for u in (-40,40):
                for v in (-22,22):local('table_leg_%s_%s'%(u,v),door_center+150+u,210+v,45,6,6,70,mats['metal'])
            for z in (65,120,175):local('shelf_'+str(z),door_center-140,85,z,90,30,5,mats['wood'])
            interior_records.append(dict(building_id=identifier,door_id=identifier+':entry',
                entrance_cm=xyz(door_center,0,110),inside_cm=xyz(door_center,140,110),
                outside_cm=xyz(door_center,-240,110),confidence='procedural inference'))
        for actor in (door,): actor.set_folder_path('V2/Pilot/Interactions')
    # Continuous pilot road crown and shoulder meshes, separate from building shells.
    for road in site.ROADS:
        if road['id'] not in site.PILOT['road_ids']:continue
        asphalt,shoulder,rows=site.road_surfaces(road['points'],road['width'])
        import_surface(asphalt,'V2_Road_'+str(road['id']),mats['road'])
        import_surface(shoulder,'V2_Shoulder_'+str(road['id']),mats['soil'])
    weather=next(a for a in api.EAS.get_all_level_actors() if isinstance(a,unreal.WeatherManager))
    import v2_rain
    weather.set_editor_property('rain_shell_material',v2_rain.build(api))
    weather.set_editor_property('use_geographic_sun',True)
    weather.set_editor_property('use_v2_environment',True)
    weather.set_editor_property('day_night_cycle',False)
    weather.set_editor_property('auto_cycle',False)
    weather.set_editor_property('time_of_day_hours',15.5)
    for actor in api.EAS.get_all_level_actors():
        if isinstance(actor,unreal.PlayerStart):
            actor.set_actor_location(unreal.Vector(600,2080,110),False,False)
            actor.set_actor_rotation(unreal.Rotator(yaw=187),False)
    report=dict(pilot_length_m=site.PILOT['length_m'],frontages=16,enterable_spaces=interior_records,
        component_kinds=len(kit['components']),detail_box_actors=count,local_review='pending',
        semantic_verge_instances=verge_count,
        namespace=api.DEST,authored_namespace_touched=False,confidence='procedural inference')
    (api.TMP/'pilot_report.json').write_text(json.dumps(report,indent=2)+'\n')
    inputs=[*api.ROOT.glob('Scripts/*.py'),*api.ROOT.glob('Source/**/*.cpp'),*api.ROOT.glob('Source/**/*.h'),
        *api.ROOT.glob('Source/**/*.cs'),*api.ROOT.glob('Config/*.ini'),api.ROOT/'rural_pardeep.uproject',
        *api.ROOT.glob('Assets/Architecture/*.json'),*api.ROOT.glob('Assets/Routes/*.json'),
        *api.ROOT.glob('Assets/Reference/*.json'),*api.ROOT.glob('Assets/Geodata/*.json'),
        *api.ROOT.glob('Assets/Geodata/*.geojson'),api.ROOT/'Assets/textures.lock.json',api.ROOT/'Assets/models.lock.json']
    provenance=dict(schema_version=1,map=api.DEST+'/Lvl_PandoriV2',seed=3062,
        input_sha256={str(p.relative_to(api.ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)},
        architectural_confidence='procedural inference',source_footprints='Overture 2026-10-21.0')
    (api.TMP/'generation_manifest.json').write_text(json.dumps(provenance,indent=2)+'\n')
    # Runtime validation inputs are generated deterministically from tracked recipes.
    validation=api.ROOT/'Content/Validation';validation.mkdir(parents=True,exist_ok=True)
    payload=dict(route=data.read('Assets/Routes/validation_route.json'),cameras=site.PILOT['cameras'],interiors=interior_records)
    (validation/'pilot.json').write_text(json.dumps(payload,indent=2)+'\n')
    unreal.log('VILLAGE_V2_PILOT_OK '+json.dumps(report))

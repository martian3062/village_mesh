"""Native PCG point sources and instanced mesh spawners for the vegetation biome."""
import unreal


def build(api, layers, name='PCG_VillageBiome', label='VM_PCG_Biome'):
    graph = api.create(name, unreal.PCGGraph, unreal.PCGGraphFactory(), api.DEST + "/PCG")
    for node in list(graph.get_editor_property("nodes")):
        graph.remove_node(node)
    total = 0
    for layer_index, (mesh, transforms) in enumerate(layers):
        source, settings = graph.add_node_of_type(unreal.PCGCreatePointsSettings)
        points = []
        for index, (xyz, scale, yaw) in enumerate(transforms):
            point = unreal.PCGPoint()
            point.set_editor_property("transform", unreal.Transform(
                location=unreal.Vector(*xyz), rotation=unreal.Rotator(yaw=yaw),
                scale=unreal.Vector(scale, scale, scale)))
            point.set_editor_property("seed", 3062 + index)
            points.append(point)
        settings.set_editor_property("points_to_create", points)
        source.set_editor_property("node_title", "Village " + str(layer_index) + " sites")
        spawner, spawn_settings = graph.add_node_of_type(unreal.PCGStaticMeshSpawnerSettings)
        spawn_settings.set_mesh_selector_type(unreal.PCGMeshSelectorWeighted)
        entry = unreal.PCGMeshSelectorWeightedEntry()
        descriptor = entry.get_editor_property("descriptor")
        descriptor.set_editor_property("static_mesh", mesh)
        entry.set_editor_property("descriptor", descriptor)
        spawn_settings.get_editor_property("mesh_selector_parameters").set_editor_property("mesh_entries", [entry])
        spawn_settings.set_editor_property("synchronous_load", True)
        graph.add_edge(source, "Out", spawner, "In")
        graph.add_edge(spawner, "Out", graph.get_output_node(), "Out")
        total += len(points)
    api.EAL.save_loaded_asset(graph)
    actor = api.EAS.spawn_actor_from_class(unreal.PCGVolume, unreal.Vector())
    actor.set_actor_label(label)
    component = actor.get_editor_property("pcg_component")
    component.set_graph(graph)
    component.set_editor_property("generation_trigger", unreal.PCGComponentGenerationTrigger.GENERATE_ON_LOAD)
    unreal.log("VM PCG configured with " + str(total) + " seeded vegetation instances")
    return total

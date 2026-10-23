"""Import Poly Haven vegetation with explicit alpha, normal and roughness materials."""
import unreal


def build(api, asset, resolution):
    root = api.ROOT / "Assets/Downloaded/Models" / asset
    folder = api.DEST + "/Vegetation/" + asset
    name = "SM_" + asset
    path = folder + "/" + name
    mesh = unreal.EditorAssetLibrary.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if not mesh:
        unreal.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
        options = unreal.FbxImportUI()
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("import_materials", False)
        options.set_editor_property("import_textures", False)
        options.set_editor_property("import_as_skeletal", False)
        options.set_editor_property("automated_import_should_detect_type", False)
        options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        options.static_mesh_import_data.set_editor_property("combine_meshes", True)
        options.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
        task = unreal.AssetImportTask()
        for key, value in dict(filename=str(root / (asset + "_" + resolution + ".fbx")),
                destination_path=folder, destination_name=name, automated=True,
                replace_existing=True, save=True, options=options).items():
            task.set_editor_property(key, value)
        task.set_editor_property("factory", unreal.FbxFactory())
        api.TOOLS.import_asset_tasks([task])
        mesh = unreal.EditorAssetLibrary.load_asset(path)
    if not mesh:
        raise RuntimeError("Vegetation mesh import failed: " + asset)
    textures = list((root / "textures").iterdir())
    for index, slot in enumerate(mesh.get_editor_property("static_materials")):
        slot_name = str(slot.material_slot_name).lower()
        part = "leaves" if "leav" in slot_name else "branch" if "branch" in slot_name else ""
        prefix = asset + ("_" + part if part else "")
        material = api.solid("M_PH_" + prefix, (0.2, 0.25, 0.08))
        api.MEL.delete_all_material_expressions(material)
        masked = part in ("leaves", "branch") or asset == "shrub_01"
        material.set_editor_property("two_sided", masked)
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE)
        material.set_editor_property("opacity_mask_clip_value", 0.33)
        samples = {}
        for key, prop in (("diff", unreal.MaterialProperty.MP_BASE_COLOR),
                          ("nor_gl", unreal.MaterialProperty.MP_NORMAL),
                          ("rough", unreal.MaterialProperty.MP_ROUGHNESS),
                          ("alpha", unreal.MaterialProperty.MP_OPACITY_MASK)):
            source = next((p for p in textures if p.stem == prefix + "_" + key + "_" + resolution), None)
            if not source:
                continue
            texture = api.import_file(source, "T_" + source.stem, folder + "/Textures")
            texture.set_editor_property("srgb", key == "diff")
            if key == "nor_gl":
                texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
                texture.set_editor_property("flip_green_channel", True)
            api.EAL.save_loaded_asset(texture)
            sample = api.expr(material, unreal.MaterialExpressionTextureSample, texture=texture)
            sample.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if key == "nor_gl"
                else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if key == "diff" else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            api.MEL.connect_material_property(sample, "RGB" if key in ("diff", "nor_gl") else "R", prop)
            samples[key] = sample
        if masked and "alpha" not in samples and "diff" in samples:
            api.MEL.connect_material_property(samples["diff"], "A", unreal.MaterialProperty.MP_OPACITY_MASK)
        if masked:
            api.atmosphere.build_wind_wpo(material, api.WEATHER_MPC, 7.0, 1200.0)
        api.MEL.set_material_usage(material, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
        api.finish(material)
        mesh.set_material(index, material)
        unreal.log("VM vegetation material: " + slot_name + " -> " + prefix)
    settings = mesh.get_editor_property("nanite_settings")
    settings.set_editor_property("enabled", True)
    settings.set_editor_property("shape_preservation", unreal.NaniteShapePreservation.PRESERVE_AREA)
    mesh.set_editor_property("nanite_settings", settings)
    api.EAL.save_loaded_asset(mesh)
    unreal.log("VM vegetation bounds " + asset + ": " + str(mesh.get_bounding_box()))
    return mesh

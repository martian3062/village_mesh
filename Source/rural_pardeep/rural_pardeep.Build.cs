using UnrealBuildTool;

public class rural_pardeep : ModuleRules
{
	public rural_pardeep(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// Module-root-relative includes ("Character/...", "MiniGames/...").
		// BuildSettingsVersion.Latest no longer adds the module root itself.
		PublicIncludePaths.Add(ModuleDirectory);

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",   // IA_/IMC_ input assets, UEnhancedInputComponent
			"Niagara",         // footstep dust puffs
			"UMG",             // UGameHUDWidget
			"Slate",
			"SlateCore",
			"PhysicsCore",     // UPhysicalMaterial (footstep surface reads, marble physics)
			"AIModule",        // AAIController for villager NPCs
			"NavigationSystem",
			"GameplayTasks"    // AIModule dependency (move requests)
		});
	}
}

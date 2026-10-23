using UnrealBuildTool;
using System.Collections.Generic;

public class rural_pardeepTarget : TargetRules
{
	public rural_pardeepTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("rural_pardeep");
	}
}

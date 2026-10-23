using UnrealBuildTool;
using System.Collections.Generic;

public class rural_pardeepEditorTarget : TargetRules
{
	public rural_pardeepEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("rural_pardeep");
	}
}

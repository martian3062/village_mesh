#pragma once

#include "CoreMinimal.h"
#include "VillagerLook.generated.h"

class ACharacter;

/**
 * One villager's appearance. The project has no human skeletal meshes, so a
 * "real" look is composed on top of the mannequin: every material slot is
 * replaced with a cloth-coloured dynamic instance (kurta / kameez), and a
 * head overlay — skin-toned face, eyes, nose, pagri or chunni, beard — is
 * attached to the head bone inside a tunable frame.
 *
 * FrameRotation/FrameOffset map the head bone's local axes onto the overlay's
 * canonical frame (+X face forward, +Z up). They are EditAnywhere so the
 * dressing script (or a live MCP property tweak) can calibrate once without a
 * recompile.
 */
USTRUCT(BlueprintType)
struct FVillagerLook
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Look")
	bool bFemale = false;

	/** Warm brown default; script varies shade per villager. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Look")
	FLinearColor SkinTone = FLinearColor(0.40f, 0.24f, 0.13f);

	/** Kurta / kameez body cloth. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Look")
	FLinearColor ClothColor = FLinearColor(0.90f, 0.86f, 0.74f);

	/** Pagri (men) / chunni (women). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Look")
	FLinearColor HeadwearColor = FLinearColor(0.85f, 0.40f, 0.08f);

	/** 0 = clean-shaven, 1 = full beard, 2 = moustache. Ignored for women. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Look", meta = (ClampMin = "0", ClampMax = "2"))
	int32 BeardStyle = 1;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Look")
	FLinearColor BeardColor = FLinearColor(0.06f, 0.05f, 0.04f);

	/** Head-bone -> overlay frame calibration. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Look|Frame")
	FVector FrameOffset = FVector(0.f, 0.f, 0.f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Look|Frame")
	FRotator FrameRotation = FRotator(0.f, 0.f, 0.f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Look|Frame", meta = (ClampMin = "0.5", ClampMax = "2"))
	float HeadScale = 1.0f;
};

namespace VillagerLookUtil
{
	/** Applies materials + head overlay. Idempotent: earlier overlay parts
	 *  (tagged) are destroyed first, so construction re-runs are safe. */
	RURAL_PARDEEP_API void Apply(ACharacter* Character, const FVillagerLook& Look);
}

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "FootstepNotify.generated.h"

/**
 * Anim notify that fires AVillageCharacter::OnFootstep (ground trace + dust
 * puff) — drop it on foot-plant frames of walk/run sequences and set
 * bAutoFootsteps=false on the character to switch from stride-synthesised
 * footsteps to hand-placed ones. No ABP event-graph wiring needed.
 */
UCLASS(meta = (DisplayName = "Footstep (village dust)"))
class RURAL_PARDEEP_API UFootstepNotify : public UAnimNotify
{
	GENERATED_BODY()

public:
	virtual void Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
		const FAnimNotifyEventReference& EventReference) override;

	virtual FString GetNotifyName_Implementation() const override { return TEXT("Footstep"); }
};

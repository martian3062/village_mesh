#include "Character/FootstepNotify.h"

#include "Character/VillageCharacter.h"
#include "Components/SkeletalMeshComponent.h"

void UFootstepNotify::Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
	const FAnimNotifyEventReference& EventReference)
{
	Super::Notify(MeshComp, Animation, EventReference);

	if (AVillageCharacter* Character = MeshComp ? Cast<AVillageCharacter>(MeshComp->GetOwner()) : nullptr)
	{
		Character->OnFootstep();
	}
}

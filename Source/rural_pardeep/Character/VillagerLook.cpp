#include "Character/VillagerLook.h"

#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
	const FName LookPartTag(TEXT("VillagerLookPart"));
	const FName HeadBone(TEXT("head"));
	const FName HandBoneL(TEXT("hand_l"));
	const FName HandBoneR(TEXT("hand_r"));

	UStaticMesh* Basic(const TCHAR* Name)
	{
		return LoadObject<UStaticMesh>(nullptr,
			*FString::Printf(TEXT("/Engine/BasicShapes/%s.%s"), Name, Name));
	}

	UMaterialInterface* ClothBase()
	{
		return LoadObject<UMaterialInterface>(nullptr,
			TEXT("/Game/Village/Materials/M_VGClothBase.M_VGClothBase"));
	}

	UStaticMeshComponent* MakePart(ACharacter* Owner, USceneComponent* Parent,
		UStaticMesh* Mesh, UMaterialInterface* Base,
		const FLinearColor& Color, float Rough,
		const FVector& Loc, const FRotator& Rot, const FVector& Scale,
		FName Socket = NAME_None)
	{
		UStaticMeshComponent* Comp = NewObject<UStaticMeshComponent>(Owner);
		Comp->ComponentTags.Add(LookPartTag);
		Comp->SetStaticMesh(Mesh);
		Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Comp->AttachToComponent(Parent,
			FAttachmentTransformRules::KeepRelativeTransform, Socket);
		Comp->SetRelativeLocation(Loc);
		Comp->SetRelativeRotation(Rot);
		Comp->SetRelativeScale3D(Scale);
		Comp->RegisterComponent();
		if (Base)
		{
			UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(Base, Owner);
			MID->SetVectorParameterValue(TEXT("Color"), Color);
			MID->SetScalarParameterValue(TEXT("Rough"), Rough);
			for (int32 i = 0; i < Comp->GetNumMaterials(); ++i)
			{
				Comp->SetMaterial(i, MID);
			}
		}
		return Comp;
	}
}

void VillagerLookUtil::Apply(ACharacter* Character, const FVillagerLook& Look)
{
	if (!Character)
	{
		return;
	}
	USkeletalMeshComponent* MeshComp = Character->GetMesh();
	if (!MeshComp || !MeshComp->GetSkeletalMeshAsset())
	{
		return;
	}

	// ---- idempotency: clear any overlay from a previous Apply ----
	// (USceneComponent covers the frame and every mesh part)
	TArray<UActorComponent*> Old = Character->GetComponentsByTag(
		USceneComponent::StaticClass(), LookPartTag);
	for (UActorComponent* Comp : Old)
	{
		Comp->DestroyComponent();
	}

	UMaterialInterface* Base = ClothBase();

	// ---- body: every slot becomes kurta / kameez cloth ----
	// (skin shows through the overlay parts: head, neck, ears, hands)
	if (Base)
	{
		UMaterialInstanceDynamic* Cloth = UMaterialInstanceDynamic::Create(Base, Character);
		Cloth->SetVectorParameterValue(TEXT("Color"), Look.ClothColor);
		Cloth->SetScalarParameterValue(TEXT("Rough"), 0.88f);
		for (int32 i = 0; i < MeshComp->GetNumMaterials(); ++i)
		{
			MeshComp->SetMaterial(i, Cloth);
		}
	}
	else
	{
		// cloth base not created yet (stage-4 script hasn't run): tint the
		// mannequin master's own parameters as a stopgap
		for (int32 i = 0; i < MeshComp->GetNumMaterials(); ++i)
		{
			if (UMaterialInstanceDynamic* MID = MeshComp->CreateDynamicMaterialInstance(i))
			{
				MID->SetVectorParameterValue(TEXT("Paint Tint"), Look.ClothColor);
				MID->SetVectorParameterValue(TEXT("Global BaseColor"), Look.ClothColor);
			}
		}
	}

	UStaticMesh* Sphere = Basic(TEXT("Sphere"));
	UStaticMesh* Cube = Basic(TEXT("Cube"));
	UStaticMesh* Cylinder = Basic(TEXT("Cylinder"));
	if (!Sphere || !Cube || !Cylinder)
	{
		return;
	}

	const FLinearColor SkinDark(Look.SkinTone.R * 0.55f, Look.SkinTone.G * 0.55f,
		Look.SkinTone.B * 0.55f, 1.f);

	// ---- hands: skin peeking from the kurta sleeves ----
	for (const FName& HandBone : { HandBoneL, HandBoneR })
	{
		if (MeshComp->DoesSocketExist(HandBone))
		{
			MakePart(Character, MeshComp, Sphere, Base, Look.SkinTone, 0.6f,
				FVector::ZeroVector, FRotator::ZeroRotator,
				FVector(0.11f, 0.065f, 0.05f), HandBone);
		}
	}

	if (!MeshComp->DoesSocketExist(HeadBone))
	{
		return; // no head bone (odd mesh) — cloth-only look
	}

	// NOTE: do NOT HideBoneByName(head) — hiding zero-scales the bone, which
	// corrupts the socket transform of everything attached to it (the overlay
	// came in inverted). Instead the skin head below is sized to fully enclose
	// the mannequin's robot head, same trick the original dome used.

	// ---- calibration frame on the head bone: +X face fwd, +Z up ----
	USceneComponent* Frame = NewObject<USceneComponent>(Character);
	Frame->ComponentTags.Add(LookPartTag);
	Frame->AttachToComponent(MeshComp,
		FAttachmentTransformRules::KeepRelativeTransform, HeadBone);
	Frame->SetRelativeLocation(Look.FrameOffset);
	Frame->SetRelativeRotation(Look.FrameRotation);
	Frame->RegisterComponent();

	const float S = Look.HeadScale;
	auto Part = [&](UStaticMesh* Mesh, const FLinearColor& Color, float Rough,
		const FVector& Loc, const FRotator& Rot, const FVector& Scale)
	{
		MakePart(Character, Frame, Mesh, Base, Color, Rough, Loc * S, Rot, Scale * S);
	};

	// ---- head: skin, sized to fully enclose the mannequin's robot head ----
	Part(Sphere, Look.SkinTone, 0.55f,
		FVector(1.5f, 0.f, 10.2f), FRotator::ZeroRotator, FVector(0.27f, 0.235f, 0.285f));
	// neck
	Part(Cylinder, Look.SkinTone, 0.55f,
		FVector(0.5f, 0.f, 1.5f), FRotator::ZeroRotator, FVector(0.10f, 0.10f, 0.10f));
	// ears
	for (float Side : { -1.f, 1.f })
	{
		Part(Sphere, Look.SkinTone, 0.55f,
			FVector(1.5f, Side * 11.4f, 10.4f), FRotator::ZeroRotator,
			FVector(0.026f, 0.014f, 0.05f));
	}

	// ---- face (features sit on the skin dome's surface) ----
	for (float Side : { -1.f, 1.f })
	{
		// sclera + pupil
		Part(Sphere, FLinearColor(0.92f, 0.90f, 0.86f), 0.35f,
			FVector(12.2f, Side * 4.2f, 12.2f), FRotator::ZeroRotator,
			FVector(0.030f, 0.040f, 0.044f));
		Part(Sphere, FLinearColor(0.05f, 0.035f, 0.025f), 0.3f,
			FVector(13.7f, Side * 4.2f, 12.2f), FRotator::ZeroRotator,
			FVector(0.013f, 0.018f, 0.020f));
		// brow
		Part(Cube, Look.BeardColor, 0.9f,
			FVector(12.4f, Side * 4.2f, 14.8f), FRotator(-6.f, 0.f, 0.f),
			FVector(0.014f, 0.050f, 0.011f));
	}
	// nose
	Part(Sphere, SkinDark, 0.55f,
		FVector(13.8f, 0.f, 10.2f), FRotator::ZeroRotator, FVector(0.036f, 0.030f, 0.058f));
	// mouth
	Part(Cube, FLinearColor(0.32f, 0.13f, 0.10f), 0.6f,
		FVector(13.0f, 0.f, 6.4f), FRotator::ZeroRotator, FVector(0.011f, 0.046f, 0.009f));

	if (Look.bFemale)
	{
		// hair behind the head, then the chunni: hood + back drape
		Part(Sphere, Look.BeardColor, 0.85f,
			FVector(-3.0f, 0.f, 9.8f), FRotator::ZeroRotator, FVector(0.245f, 0.215f, 0.25f));
		Part(Sphere, Look.HeadwearColor, 0.8f,
			FVector(-0.6f, 0.f, 17.4f), FRotator(-4.f, 0.f, 0.f), FVector(0.29f, 0.25f, 0.225f));
		Part(Cube, Look.HeadwearColor, 0.8f,
			FVector(-11.0f, 0.f, 2.0f), FRotator(16.f, 0.f, 0.f), FVector(0.06f, 0.24f, 0.40f));
	}
	else
	{
		// pagri: two wrap layers (flat ellipses) + crown dome + front peak —
		// wraps the whole crown, no bare patch at the back
		Part(Cylinder, Look.HeadwearColor, 0.8f,
			FVector(1.2f, 0.f, 16.2f), FRotator::ZeroRotator, FVector(0.30f, 0.26f, 0.052f));
		Part(Cylinder, Look.HeadwearColor, 0.8f,
			FVector(1.0f, 0.f, 18.1f), FRotator::ZeroRotator, FVector(0.285f, 0.245f, 0.052f));
		Part(Sphere, Look.HeadwearColor, 0.8f,
			FVector(0.6f, 0.f, 20.4f), FRotator(-6.f, 0.f, 0.f), FVector(0.27f, 0.235f, 0.155f));
		Part(Sphere, Look.HeadwearColor, 0.8f,
			FVector(9.0f, 0.f, 20.6f), FRotator(24.f, 0.f, 0.f), FVector(0.06f, 0.06f, 0.055f));

		if (Look.BeardStyle == 1)
		{
			Part(Sphere, Look.BeardColor, 0.9f,
				FVector(10.2f, 0.f, 4.4f), FRotator(12.f, 0.f, 0.f), FVector(0.12f, 0.15f, 0.17f));
		}
		if (Look.BeardStyle >= 1)
		{
			// moustache (also sits over the full beard)
			Part(Sphere, Look.BeardColor, 0.9f,
				FVector(13.4f, 0.f, 8.6f), FRotator::ZeroRotator, FVector(0.022f, 0.080f, 0.018f));
		}
	}
}

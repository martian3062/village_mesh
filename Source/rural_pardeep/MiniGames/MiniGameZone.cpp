#include "MiniGames/MiniGameZone.h"

#include "Camera/CameraComponent.h"
#include "Character/VillageCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/DecalComponent.h"
#include "Engine/Engine.h"
#include "Interaction/InteractionComponent.h"
#include "UI/GameHUDWidget.h"

AMiniGameZone::AMiniGameZone()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SetRootComponent(SceneRoot);

	Trigger = CreateDefaultSubobject<UBoxComponent>(TEXT("Trigger"));
	Trigger->SetupAttachment(SceneRoot);
	Trigger->SetBoxExtent(FVector(400.f, 400.f, 250.f));
	Trigger->SetCollisionProfileName(TEXT("Trigger"));

	PlayAreaDecal = CreateDefaultSubobject<UDecalComponent>(TEXT("PlayAreaDecal"));
	PlayAreaDecal->SetupAttachment(SceneRoot);
	// Point the decal down at the ground; DecalSize.X is projection depth.
	PlayAreaDecal->SetRelativeRotation(FRotator(-90.f, 0.f, 0.f));
	PlayAreaDecal->DecalSize = FVector(200.f, 300.f, 300.f);

	GameCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("GameCamera"));
	GameCamera->SetupAttachment(SceneRoot);
	GameCamera->SetRelativeLocation(FVector(-150.f, 0.f, 200.f));

	// Lets SetViewTargetWithBlend(this) resolve to GameCamera.
	bFindCameraComponentWhenViewTarget = true;

	GameDisplayName = NSLOCTEXT("MiniGames", "GenericGame", "Mini-Game");
}

void AMiniGameZone::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	if (bGameActive)
	{
		TickGame(DeltaTime);
	}
}

void AMiniGameZone::PostInitializeComponents()
{
	Super::PostInitializeComponents();

	Trigger->OnComponentBeginOverlap.AddDynamic(this, &AMiniGameZone::OnTriggerBeginOverlap);
	Trigger->OnComponentEndOverlap.AddDynamic(this, &AMiniGameZone::OnTriggerEndOverlap);
}

void AMiniGameZone::OnTriggerBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (const AVillageCharacter* Character = Cast<AVillageCharacter>(OtherActor))
	{
		if (UInteractionComponent* Interaction = Character->GetInteractionComponent())
		{
			Interaction->NotifyZoneEntered(this);
		}
	}
}

void AMiniGameZone::OnTriggerEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex)
{
	if (const AVillageCharacter* Character = Cast<AVillageCharacter>(OtherActor))
	{
		if (UInteractionComponent* Interaction = Character->GetInteractionComponent())
		{
			Interaction->NotifyZoneExited(this);
		}
	}
}

void AMiniGameZone::StartGame(UInteractionComponent* InInteraction)
{
	OwningInteraction = InInteraction;
	bGameActive = true;

	if (UGameHUDWidget* HUD = GetHUD())
	{
		HUD->ShowGamePanel(HUDPanelName);
	}
}

void AMiniGameZone::EndGame()
{
	if (UGameHUDWidget* HUD = GetHUD())
	{
		HUD->HideGamePanel(HUDPanelName);
		HUD->UpdatePowerMeter(0.f, false);
	}

	bGameActive = false;
	OwningInteraction = nullptr;
}

UGameHUDWidget* AMiniGameZone::GetHUD() const
{
	return OwningInteraction ? OwningInteraction->GetHUD() : nullptr;
}

void AMiniGameZone::DebugHUD(int32 Slot, const FString& Text) const
{
	if (!GetHUD() && GEngine)
	{
		// Duration 0 + stable key = refreshed every tick without stacking.
		GEngine->AddOnScreenDebugMessage(static_cast<uint64>(0xE100 + Slot), 0.f,
			FColor::Cyan, Text);
	}
}

AVillageCharacter* AMiniGameZone::GetPlayerCharacter() const
{
	return OwningInteraction ? OwningInteraction->GetVillageCharacter() : nullptr;
}

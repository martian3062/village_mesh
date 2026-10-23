#include "MiniGames/DartsZone.h"

#include "Camera/CameraComponent.h"
#include "Character/VillageCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/DecalComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "MiniGames/DartProjectile.h"
#include "UI/GameHUDWidget.h"
#include "UObject/ConstructorHelpers.h"

ADartsZone::ADartsZone()
{
	GameDisplayName = NSLOCTEXT("MiniGames", "Darts", "Darts");
	HUDPanelName = TEXT("Darts");

	// Trigger covers the oche + board area.
	Trigger->SetBoxExtent(FVector(350.f, 300.f, 250.f));
	Trigger->SetRelativeLocation(FVector(120.f, 0.f, 100.f));

	// <DARTBOARD_MESH_PLACEHOLDER>: flat engine cylinder stands in for the board.
	DartboardMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DartboardMesh"));
	DartboardMesh->SetupAttachment(SceneRoot);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(
		TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (CylinderMesh.Succeeded())
	{
		DartboardMesh->SetStaticMesh(CylinderMesh.Object);
	}
	// 120 cm face (60 cm radius, matching the outermost score ring) pointing
	// back down -X toward the thrower, 8 cm deep.
	DartboardMesh->SetRelativeScale3D(FVector(1.2f, 1.2f, 0.08f));
	DartboardMesh->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
	DartboardMesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));

	ThrowLineDecal = CreateDefaultSubobject<UDecalComponent>(TEXT("ThrowLineDecal"));
	ThrowLineDecal->SetupAttachment(SceneRoot);
	ThrowLineDecal->SetRelativeRotation(FRotator(-90.f, 0.f, 0.f));
	ThrowLineDecal->DecalSize = FVector(50.f, 20.f, 120.f); // thin stripe across the oche

	// Camera behind the throw line at head height, looking at the board.
	GameCamera->SetRelativeLocation(FVector(-80.f, 0.f, 170.f));

	// Default simple rings: bulls + three bands on an oversized 60 cm-radius
	// board (forgiving for gamepad/mouse arcs). All editable per-instance.
	// The outer ring scores 1 so a 501 checkout is actually reachable
	// (501 is not a multiple of 5 — with only {50,25,15,10,5} the countdown
	// could never land exactly on 0).
	ScoreRings = {
		{ 6.f, 50 },   // inner bull
		{ 14.f, 25 },  // outer bull
		{ 30.f, 15 },
		{ 45.f, 10 },
		{ 60.f, 1 },
	};

	DartClass = ADartProjectile::StaticClass();
}

void ADartsZone::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	// Keep the board + camera consistent with the tunable layout numbers.
	DartboardMesh->SetRelativeLocation(FVector(OcheDistance, 0.f, BoardHeight));
	const FVector CameraPos = GameCamera->GetRelativeLocation();
	GameCamera->SetRelativeRotation(
		(DartboardMesh->GetRelativeLocation() - CameraPos).Rotation());
}

void ADartsZone::StartGame(UInteractionComponent* InInteraction)
{
	Super::StartGame(InInteraction);

	Score = (GameMode == EDartsMode::Countdown501) ? 501 : 0;
	LastThrowScore = 0;
	TurnsPlayed = 0;
	DartsInFlight = 0;
	bGameOver = false;
	AimYaw = 0.f;
	AimPitch = 0.f;
	BeginTurn();
}

void ADartsZone::EndGame()
{
	// Set before destroying darts: their OnDestroyed callbacks route back into
	// OnDartLost, which must not advance turns during cleanup.
	bGameOver = true;

	TArray<TObjectPtr<ADartProjectile>> DartsToDestroy = MoveTemp(ActiveDarts);
	ActiveDarts.Reset();
	for (ADartProjectile* Dart : DartsToDestroy)
	{
		if (IsValid(Dart))
		{
			Dart->Destroy();
		}
	}
	DartsInFlight = 0;
	bCharging = false;

	Super::EndGame();
}

void ADartsZone::BeginTurn()
{
	DartsLeftInTurn = DartsPerTurn;
	TurnStartScore = Score;
	PushHUD();
}

void ADartsZone::HandleLookInput(const FVector2D& Value)
{
	if (bGameOver)
	{
		return;
	}
	AimYaw = FMath::Clamp(AimYaw + Value.X * AimSensitivity, -MaxAimYaw, MaxAimYaw);
	AimPitch = FMath::Clamp(AimPitch + Value.Y * AimSensitivity, -MaxAimPitch, MaxAimPitch);
}

void ADartsZone::HandleInteractPressed()
{
	// One dart airborne at a time: prevents cross-turn score attribution and
	// matches real darts pacing.
	if (bGameOver || DartsLeftInTurn <= 0 || DartsInFlight > 0)
	{
		return;
	}
	bCharging = true;
	ChargePower = 0.f;
}

void ADartsZone::HandleInteractReleased()
{
	if (!bCharging || bGameOver)
	{
		return;
	}
	bCharging = false;

	if (UGameHUDWidget* HUD = GetHUD())
	{
		HUD->UpdatePowerMeter(0.f, false);
	}

	// Throw from just under the camera, along the aimed direction. The aim
	// offset is already baked into the camera rotation by TickGame, so the
	// dart departs exactly along the screen-centre reticle.
	const FRotator AimRot = GameCamera->GetComponentRotation();
	const FVector SpawnLocation =
		GameCamera->GetComponentLocation() + AimRot.Vector() * 40.f - FVector(0.f, 0.f, 15.f);
	const float Speed = FMath::Lerp(MinThrowSpeed, MaxThrowSpeed, ChargePower);

	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ADartProjectile* Dart = GetWorld()->SpawnActor<ADartProjectile>(
		DartClass ? *DartClass : ADartProjectile::StaticClass(),
		SpawnLocation, AimRot, SpawnParams);
	if (!Dart)
	{
		return;
	}

	Dart->Launch(AimRot.Vector() * Speed, this);
	ActiveDarts.Add(Dart);
	DartsInFlight++;

	if (AVillageCharacter* Character = GetPlayerCharacter())
	{
		Character->PlayGameMontage(Character->DartThrowMontage);
	}

	DartsLeftInTurn--;
	PushHUD();
}

void ADartsZone::TickGame(float DeltaTime)
{
	if (bCharging)
	{
		ChargePower = FMath::Min(ChargePower + ChargeRate * DeltaTime, 1.f);
		if (UGameHUDWidget* HUD = GetHUD())
		{
			HUD->UpdatePowerMeter(ChargePower, true);
		}
	}

	// Steer the camera with the current aim so the screen-centre reticle
	// (in WBP_GameHUD's darts panel) is the true aim point.
	const FVector ToBoard = DartboardMesh->GetComponentLocation() - GameCamera->GetComponentLocation();
	GameCamera->SetWorldRotation(ToBoard.Rotation() + FRotator(AimPitch, AimYaw, 0.f));
}

int32 ADartsZone::ComputeScore(const FHitResult& Hit) const
{
	if (Hit.GetComponent() != DartboardMesh)
	{
		return 0; // wall / ground / wide throw
	}

	// Radial distance from board centre, measured in the board's face plane
	// (independent of how the placeholder/final mesh is oriented).
	const FVector Centre = DartboardMesh->GetComponentLocation();
	const FVector Normal = DartboardMesh->GetUpVector(); // cylinder axis = face normal
	const FVector Offset = Hit.ImpactPoint - Centre;
	const float RadialDist = (Offset - FVector::DotProduct(Offset, Normal) * Normal).Size();

	for (const FDartScoreRing& Ring : ScoreRings)
	{
		if (RadialDist <= Ring.Radius)
		{
			return Ring.Score;
		}
	}
	return 0;
}

void ADartsZone::OnDartLanded(ADartProjectile* Dart, const FHitResult& Hit)
{
	DartsInFlight = FMath::Max(0, DartsInFlight - 1);

	if (!bGameActive || bGameOver)
	{
		return;
	}

	LastThrowScore = ComputeScore(Hit);

	if (GameMode == EDartsMode::Countdown501)
	{
		Score -= LastThrowScore;
		if (Score == 0)
		{
			FinishGame(); // checked out!
			return;
		}
		if (Score < 0)
		{
			// Bust: restore the score from the start of the turn, turn ends.
			Score = TurnStartScore;
			DartsLeftInTurn = 0;
			if (UGameHUDWidget* HUD = GetHUD())
			{
				HUD->ShowStatusMessage(NSLOCTEXT("MiniGames", "DartsBust", "BUST!"));
			}
		}
	}
	else
	{
		Score += LastThrowScore;
	}

	PushHUD();
	AdvanceTurnIfNeeded();
}

void ADartsZone::OnDartLost(ADartProjectile* Dart)
{
	// A dart expired or fell out of the world without hitting anything —
	// treat it as a zero-score throw so the turn can never soft-lock.
	DartsInFlight = FMath::Max(0, DartsInFlight - 1);
	ActiveDarts.Remove(Dart);

	if (!bGameActive || bGameOver)
	{
		return;
	}

	LastThrowScore = 0;
	PushHUD();
	AdvanceTurnIfNeeded();
}

void ADartsZone::AdvanceTurnIfNeeded()
{
	if (bGameOver || DartsLeftInTurn > 0 || DartsInFlight > 0)
	{
		return;
	}

	TurnsPlayed++;
	if (GameMode == EDartsMode::BestOfThreeTurns && TurnsPlayed >= TotalTurns)
	{
		FinishGame();
	}
	else
	{
		BeginTurn();
	}
}

void ADartsZone::FinishGame()
{
	bGameOver = true;
	PushHUD();
	if (UGameHUDWidget* HUD = GetHUD())
	{
		HUD->ShowStatusMessage(NSLOCTEXT("MiniGames", "DartsDone", "Game over — press Esc to leave"));
	}
}

void ADartsZone::PushHUD()
{
	if (UGameHUDWidget* HUD = GetHUD())
	{
		HUD->UpdateDartsHUD(Score, DartsLeftInTurn, LastThrowScore);
	}
}

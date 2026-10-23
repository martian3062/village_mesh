#include "MiniGames/KanchaZone.h"

#include "Camera/CameraComponent.h"
#include "Character/VillageCharacter.h"
#include "Components/BoxComponent.h"
#include "Components/DecalComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DrawDebugHelpers.h"
#include "MiniGames/MarbleActor.h"
#include "UI/GameHUDWidget.h"

AKanchaZone::AKanchaZone()
{
	GameDisplayName = NSLOCTEXT("MiniGames", "Kancha", "Kancha (Marbles)");
	HUDPanelName = TEXT("Kancha");

	Trigger->SetBoxExtent(FVector(450.f, 450.f, 250.f));
	Trigger->SetRelativeLocation(FVector(0.f, 0.f, 100.f));

	// Ring decal sized against RingRadius in OnConstruction-ish defaults;
	// assign a chalk-circle decal material in the editor.
	PlayAreaDecal->DecalSize = FVector(50.f, RingRadius, RingRadius);

	GameCamera->SetRelativeLocation(FVector(-RingRadius - 150.f, 0.f, 150.f));

	MarbleClass = AMarbleActor::StaticClass();
}

void AKanchaZone::StartGame(UInteractionComponent* InInteraction)
{
	Super::StartGame(InInteraction);

	TurnState = EKanchaTurnState::Aiming;
	AimYaw = 0.f;
	ChargePower = 0.f;
	TurnsTaken = 0;
	MarblesWon = 0;

	SpawnMarbles();
	PushHUD();
}

void AKanchaZone::EndGame()
{
	DestroyMarbles();
	Super::EndGame();
}

void AKanchaZone::SpawnMarbles()
{
	DestroyMarbles();

	UWorld* World = GetWorld();
	const FVector Centre = GetActorLocation();
	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride =
		ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;

	const TSubclassOf<AMarbleActor> ClassToSpawn =
		MarbleClass ? MarbleClass : TSubclassOf<AMarbleActor>(AMarbleActor::StaticClass());

	// Shooter starts at the ring edge on the camera side.
	const FVector PlayerPos = Centre + FVector(-RingRadius, 0.f, 10.f);
	PlayerMarble = World->SpawnActor<AMarbleActor>(ClassToSpawn, PlayerPos, FRotator::ZeroRotator, SpawnParams);
	if (PlayerMarble)
	{
		PlayerMarble->InitMarble(this, true, MarbleMass, MarbleFriction, MarbleRestitution);
	}

	// Rivals spread deterministically on a golden-angle spiral inside the ring.
	for (int32 i = 0; i < RivalCount; ++i)
	{
		const float Radius = RingRadius * 0.45f * FMath::Sqrt(float(i + 1) / float(RivalCount));
		const float AngleRad = FMath::DegreesToRadians(137.5f * i);
		const FVector Pos = Centre + FVector(
			Radius * FMath::Cos(AngleRad), Radius * FMath::Sin(AngleRad), 10.f);

		AMarbleActor* Rival = World->SpawnActor<AMarbleActor>(ClassToSpawn, Pos, FRotator::ZeroRotator, SpawnParams);
		if (Rival)
		{
			Rival->InitMarble(this, false, MarbleMass, MarbleFriction, MarbleRestitution);
			RivalMarbles.Add(Rival);
		}
	}
}

void AKanchaZone::DestroyMarbles()
{
	if (IsValid(PlayerMarble))
	{
		PlayerMarble->Destroy();
	}
	PlayerMarble = nullptr;

	for (AMarbleActor* Rival : RivalMarbles)
	{
		if (IsValid(Rival))
		{
			Rival->Destroy();
		}
	}
	RivalMarbles.Empty();
}

void AKanchaZone::HandleLookInput(const FVector2D& Value)
{
	if (TurnState == EKanchaTurnState::Aiming || TurnState == EKanchaTurnState::Charging)
	{
		AimYaw += Value.X * AimSensitivity;
	}
}

void AKanchaZone::HandleInteractPressed()
{
	if (TurnState == EKanchaTurnState::Aiming && IsValid(PlayerMarble))
	{
		TurnState = EKanchaTurnState::Charging;
		ChargePower = 0.f;
	}
}

void AKanchaZone::HandleInteractReleased()
{
	if (TurnState != EKanchaTurnState::Charging || !IsValid(PlayerMarble))
	{
		return;
	}

	if (UGameHUDWidget* HUD = GetHUD())
	{
		HUD->UpdatePowerMeter(0.f, false);
	}

	const FRotator AimRot(FlickElevationDeg, AimYaw, 0.f);
	const float Speed = FMath::Lerp(MinFlickSpeed, MaxFlickSpeed, ChargePower);
	// bVelChange=true -> impulse is applied as a velocity change, so flick
	// feel is independent of MarbleMass tuning.
	PlayerMarble->MeshComp->AddImpulse(AimRot.Vector() * Speed, NAME_None, true);

	if (AVillageCharacter* Character = GetPlayerCharacter())
	{
		Character->PlayGameMontage(Character->MarbleFlickMontage);
	}

	TurnState = EKanchaTurnState::Rolling;
	SettleTimer = 0.f;
	RollTimer = 0.f;
	TurnsTaken++;
	PushHUD();
}

void AKanchaZone::TickGame(float DeltaTime)
{
	if (!IsValid(PlayerMarble))
	{
		return;
	}

	const FVector MarblePos = PlayerMarble->GetActorLocation();
	const FVector AimDir = FRotator(0.f, AimYaw, 0.f).Vector();

	// Over-shoulder camera orbits the shooter marble behind the aim direction.
	const FVector CameraPos = MarblePos - AimDir * 200.f + FVector(0.f, 0.f, 110.f);
	GameCamera->SetWorldLocation(CameraPos);
	GameCamera->SetWorldRotation((MarblePos + AimDir * 120.f - CameraPos).Rotation());

	switch (TurnState)
	{
	case EKanchaTurnState::Aiming:
	case EKanchaTurnState::Charging:
	{
		if (TurnState == EKanchaTurnState::Charging)
		{
			ChargePower = FMath::Min(ChargePower + ChargeRate * DeltaTime, 1.f);
			if (UGameHUDWidget* HUD = GetHUD())
			{
				HUD->UpdatePowerMeter(ChargePower, true);
			}
		}
		// Debug aim arrow — replace with an arrow decal / spline mesh later.
		DrawDebugDirectionalArrow(GetWorld(), MarblePos + FVector(0, 0, 5),
			MarblePos + FVector(0, 0, 5) + AimDir * 120.f, 25.f, FColor::Yellow,
			false, -1.f, 0, 1.5f);
		break;
	}
	case EKanchaTurnState::Rolling:
	{
		RollTimer += DeltaTime;

		bool bAllSettled = PlayerMarble->GetMarbleVelocity().Size() < SettleSpeedThreshold;
		for (const AMarbleActor* Rival : RivalMarbles)
		{
			if (IsValid(Rival) && Rival->GetMarbleVelocity().Size() >= SettleSpeedThreshold)
			{
				bAllSettled = false;
				break;
			}
		}

		SettleTimer = bAllSettled ? SettleTimer + DeltaTime : 0.f;

		if (SettleTimer >= SettleTime || RollTimer >= RollTimeout)
		{
			ResolveShot();
		}
		break;
	}
	default:
		break;
	}
}

void AKanchaZone::NotifyMarbleHit(AMarbleActor* Marble, AActor* OtherActor)
{
	// Authentic rule: your shooter striking a rival during the shot wins it.
	if (!bGameActive || TurnState != EKanchaTurnState::Rolling ||
		WinRule != EKanchaRule::HitRivalToWin || Marble != PlayerMarble)
	{
		return;
	}

	if (AMarbleActor* Rival = Cast<AMarbleActor>(OtherActor))
	{
		if (!Rival->IsPlayerMarble() && RivalMarbles.Contains(Rival))
		{
			ClaimRival(Rival);
		}
	}
}

void AKanchaZone::ClaimRival(AMarbleActor* Rival)
{
	RivalMarbles.Remove(Rival);
	if (IsValid(Rival))
	{
		Rival->Destroy();
	}
	MarblesWon++;

	if (UGameHUDWidget* HUD = GetHUD())
	{
		HUD->ShowStatusMessage(NSLOCTEXT("MiniGames", "KanchaWon", "Marble won!"));
	}
	PushHUD();
}

void AKanchaZone::ResolveShot()
{
	// Ring variant resolves on settle: rivals now outside the circle are won.
	if (WinRule == EKanchaRule::KnockOutOfRing)
	{
		const FVector Centre = GetActorLocation();
		for (int32 i = RivalMarbles.Num() - 1; i >= 0; --i)
		{
			AMarbleActor* Rival = RivalMarbles[i];
			if (!IsValid(Rival))
			{
				RivalMarbles.RemoveAt(i);
				continue;
			}
			const float Dist2D = FVector::Dist2D(Rival->GetActorLocation(), Centre);
			if (Dist2D > RingRadius)
			{
				ClaimRival(Rival);
			}
		}
	}

	if (RivalMarbles.Num() == 0 || TurnsTaken >= MaxTurns)
	{
		TurnState = EKanchaTurnState::GameOver;
		if (UGameHUDWidget* HUD = GetHUD())
		{
			HUD->ShowStatusMessage(RivalMarbles.Num() == 0
				? NSLOCTEXT("MiniGames", "KanchaSweep", "You won them all! Press Esc to leave")
				: NSLOCTEXT("MiniGames", "KanchaDone", "Out of turns — press Esc to leave"));
		}
	}
	else
	{
		// Shooter plays on from where it lies, like the street game.
		TurnState = EKanchaTurnState::Aiming;
	}
	PushHUD();
}

void AKanchaZone::PushHUD()
{
	if (UGameHUDWidget* HUD = GetHUD())
	{
		HUD->UpdateKanchaHUD(RivalMarbles.Num(), MarblesWon);
	}
}

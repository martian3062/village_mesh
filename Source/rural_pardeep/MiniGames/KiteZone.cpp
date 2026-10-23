#include "MiniGames/KiteZone.h"

#include "Camera/CameraComponent.h"
#include "Character/VillageCharacter.h"
#include "Components/BoxComponent.h"
#include "DrawDebugHelpers.h"
#include "MiniGames/KiteActor.h"
#include "TimerManager.h"
#include "UI/GameHUDWidget.h"

AKiteZone::AKiteZone()
{
	GameDisplayName = NSLOCTEXT("MiniGames", "Kite", "Patang (Kite Flying)");
	HUDPanelName = TEXT("Kite");

	// The placement script resizes this to the actual rooftop.
	Trigger->SetBoxExtent(FVector(450.f, 350.f, 200.f));
	Trigger->SetRelativeLocation(FVector(0.f, 0.f, 120.f));

	GameCamera->SetRelativeLocation(FVector(-250.f, 0.f, 220.f));

	PlayerKiteClass = AKiteActor::StaticClass();
	RivalKiteClass = AKiteActor::StaticClass();
}

void AKiteZone::StartGame(UInteractionComponent* InInteraction)
{
	Super::StartGame(InInteraction);

	ZoneTime = 0.f;
	KitesCut = 0;
	bContestActive = false;
	bPullHeld = false;
	CurrentSteer = FVector2D::ZeroVector;
	bLetOutHeld = false;
	bReelInHeld = false;
	ReelInput = 0.f;

	// Anchors: the flyer's hands, just above the roof at the zone root.
	PlayerAnchor = GetActorLocation() + FVector(0.f, 0.f, 150.f);
	RivalAnchor = GetActorLocation() + RivalAnchorOffset + FVector(0.f, 0.f, 150.f);

	PlayerKite = SpawnKite(PlayerKiteClass, PlayerAnchor, false);
	RivalKite = SpawnKite(RivalKiteClass, RivalAnchor, true);
	PushHUD();
}

void AKiteZone::EndGame()
{
	GetWorldTimerManager().ClearTimer(RivalRespawnTimer);
	GetWorldTimerManager().ClearTimer(PlayerRelaunchTimer);

	if (IsValid(PlayerKite))
	{
		PlayerKite->Destroy();
	}
	if (IsValid(RivalKite))
	{
		RivalKite->Destroy();
	}
	PlayerKite = nullptr;
	RivalKite = nullptr;

	Super::EndGame();
}

AKiteActor* AKiteZone::SpawnKite(TSubclassOf<AKiteActor> KiteClass, const FVector& InAnchor, bool bAutoPilot)
{
	FActorSpawnParameters SpawnParams;
	SpawnParams.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

	// Launch downwind of the anchor so the string starts taut-ish.
	const FVector Start = InAnchor + WindDirection.GetSafeNormal() * 300.f + FVector(0.f, 0.f, 450.f);
	AKiteActor* Kite = GetWorld()->SpawnActor<AKiteActor>(
		KiteClass ? *KiteClass : AKiteActor::StaticClass(),
		Start, FRotator::ZeroRotator, SpawnParams);
	if (Kite)
	{
		Kite->SetAnchor(InAnchor);
		Kite->SetAutoPilot(bAutoPilot);
	}
	return Kite;
}

// -------------------- input --------------------

void AKiteZone::HandleMoveInput(const FVector2D& Value)
{
	CurrentSteer.X = FMath::Clamp(CurrentSteer.X + Value.X, -1.f, 1.f);
	CurrentSteer.Y = FMath::Clamp(CurrentSteer.Y + Value.Y, -1.f, 1.f);
}

void AKiteZone::HandleLookInput(const FVector2D& Value)
{
	// Fine steering on the mouse/right stick.
	CurrentSteer.X = FMath::Clamp(CurrentSteer.X + Value.X * 0.4f, -1.f, 1.f);
	CurrentSteer.Y = FMath::Clamp(CurrentSteer.Y + Value.Y * 0.4f, -1.f, 1.f);
}

void AKiteZone::HandleJumpInput(bool bPressed)
{
	bLetOutHeld = bPressed; // let string out
	UpdateReelInput();
}

void AKiteZone::HandleSprintInput(bool bPressed)
{
	bReelInHeld = bPressed; // reel string in
	UpdateReelInput();
}

void AKiteZone::UpdateReelInput()
{
	// Both keys can be held at once; releasing one must not cancel the other
	// (these arrive as one-shot Started/Completed events, not per-tick state).
	ReelInput = (bLetOutHeld ? 1.f : 0.f) + (bReelInHeld ? -1.f : 0.f);
}

void AKiteZone::HandleInteractPressed()
{
	bPullHeld = true;
	if (bContestActive)
	{
		PlayerTension = FMath::Min(PlayerTension + TensionPerPress, TensionToWin);
		if (AVillageCharacter* Character = GetPlayerCharacter())
		{
			Character->PlayGameMontage(Character->KitePullMontage);
		}
	}
}

void AKiteZone::HandleInteractReleased()
{
	bPullHeld = false;
}

// -------------------- per-frame --------------------

void AKiteZone::TickGame(float DeltaTime)
{
	ZoneTime += DeltaTime;

	const FVector Wind = WindDirection.GetSafeNormal() *
		(WindStrength + GustAmplitude * FMath::Sin(ZoneTime * GustFrequency * 2.f * PI));

	if (IsValid(PlayerKite) && !PlayerKite->IsCut())
	{
		PlayerKite->UpdateFlight(DeltaTime, CurrentSteer, ReelInput, Wind);
	}
	if (IsValid(RivalKite))
	{
		RivalKite->SetWind(Wind); // autopilot ticks itself with this wind
	}
	// Steer input is consumed each frame; Triggered events refill it while held.
	CurrentSteer = FVector2D::ZeroVector;

	// Debug strings — swap for CableComponents once art passes start.
	if (IsValid(PlayerKite) && !PlayerKite->IsCut())
	{
		DrawDebugLine(GetWorld(), PlayerAnchor, PlayerKite->GetActorLocation(),
			FColor::Green, false, -1.f, 0, 1.f);
	}
	if (IsValid(RivalKite) && !RivalKite->IsCut())
	{
		DrawDebugLine(GetWorld(), RivalAnchor, RivalKite->GetActorLocation(),
			FColor::Red, false, -1.f, 0, 1.f);
	}

	// ---- pech detection + contest ----
	const bool bBothFlying = IsValid(PlayerKite) && !PlayerKite->IsCut() &&
		IsValid(RivalKite) && !RivalKite->IsCut();

	if (bBothFlying)
	{
		FVector NearestOnPlayer, NearestOnRival;
		FMath::SegmentDistToSegmentSafe(
			PlayerAnchor, PlayerKite->GetActorLocation(),
			RivalAnchor, RivalKite->GetActorLocation(),
			NearestOnPlayer, NearestOnRival);
		const float StringDistance = FVector::Dist(NearestOnPlayer, NearestOnRival);

		if (!bContestActive && StringDistance < StringCrossDistance)
		{
			bContestActive = true;
			PlayerTension = 0.f;
			RivalTension = 0.f;
			if (UGameHUDWidget* HUD = GetHUD())
			{
				HUD->ShowStatusMessage(NSLOCTEXT("MiniGames", "PechStart", "PECH! Pull (E) to cut!"));
			}
		}
		else if (bContestActive && StringDistance > StringCrossDistance * 2.5f)
		{
			bContestActive = false; // strings drifted apart, no cut
		}

		if (bContestActive)
		{
			PlayerTension = FMath::Clamp(
				PlayerTension + (bPullHeld ? TensionHoldRate : 0.f) * DeltaTime
				- TensionDecayRate * DeltaTime,
				0.f, TensionToWin);
			// Wobble is centred on 1.0 so RivalTensionRate is the true average.
			RivalTension = FMath::Clamp(
				RivalTension + RivalTensionRate * (1.f + 0.5f * FMath::Sin(ZoneTime * 1.7f)) * DeltaTime,
				0.f, TensionToWin);

			if (PlayerTension >= TensionToWin)
			{
				ResolveContest(true);
			}
			else if (RivalTension >= TensionToWin)
			{
				ResolveContest(false);
			}
		}
	}
	else
	{
		bContestActive = false;
	}

	// ---- kite-follow camera: stand at the anchor side, look up at the kite ----
	if (IsValid(PlayerKite))
	{
		const FVector KitePos = PlayerKite->GetActorLocation();
		FVector Horizontal = KitePos - PlayerAnchor;
		Horizontal.Z = 0.f;
		if (!Horizontal.Normalize())
		{
			Horizontal = GetActorForwardVector();
		}
		const FVector CameraPos = PlayerAnchor - Horizontal * 260.f + FVector(0.f, 0.f, 200.f);
		GameCamera->SetWorldLocation(CameraPos);
		GameCamera->SetWorldRotation((KitePos - CameraPos).Rotation());
	}

	PushHUD();
}

// -------------------- contest resolution --------------------

void AKiteZone::ResolveContest(bool bPlayerWon)
{
	bContestActive = false;

	if (bPlayerWon)
	{
		if (IsValid(RivalKite))
		{
			RivalKite->Cut();
		}
		KitesCut++;
		if (UGameHUDWidget* HUD = GetHUD())
		{
			HUD->ShowStatusMessage(NSLOCTEXT("MiniGames", "KiteCutWin", "Bo kata! Kite cut!"));
		}
		GetWorldTimerManager().SetTimer(RivalRespawnTimer, this,
			&AKiteZone::RespawnRivalKite, RivalRespawnDelay, false);
	}
	else
	{
		if (IsValid(PlayerKite))
		{
			PlayerKite->Cut();
		}
		if (UGameHUDWidget* HUD = GetHUD())
		{
			HUD->ShowStatusMessage(NSLOCTEXT("MiniGames", "KiteCutLoss", "Your string was cut!"));
		}
		GetWorldTimerManager().SetTimer(PlayerRelaunchTimer, this,
			&AKiteZone::RelaunchPlayerKite, PlayerRelaunchDelay, false);
	}
	PushHUD();
}

void AKiteZone::RespawnRivalKite()
{
	if (bGameActive)
	{
		RivalKite = SpawnKite(RivalKiteClass, RivalAnchor, true);
	}
}

void AKiteZone::RelaunchPlayerKite()
{
	if (bGameActive)
	{
		PlayerKite = SpawnKite(PlayerKiteClass, PlayerAnchor, false);
	}
}

void AKiteZone::PushHUD()
{
	if (UGameHUDWidget* HUD = GetHUD())
	{
		const bool bKiteUp = IsValid(PlayerKite) && !PlayerKite->IsCut();
		const float Altitude = bKiteUp ? PlayerKite->GetActorLocation().Z - PlayerAnchor.Z : 0.f;
		const float String = bKiteUp ? PlayerKite->GetStringLength() : 0.f;
		// Meter reads 0.5 when even, 1 when you are about to cut, 0 when about to be cut.
		const float Meter = bContestActive
			? FMath::Clamp(0.5f + (PlayerTension - RivalTension) / (2.f * TensionToWin), 0.f, 1.f)
			: 0.5f;
		HUD->UpdateKiteHUD(Altitude, String, KitesCut, Meter, bContestActive);
	}
}

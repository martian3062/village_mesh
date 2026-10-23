#include "Interaction/InteractionComponent.h"

#include "Blueprint/UserWidget.h"
#include "Character/VillageCharacter.h"
#include "Character/VillagerNPC.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
#include "MiniGames/MiniGameZone.h"
#include "UI/GameHUDWidget.h"

UInteractionComponent::UInteractionComponent()
{
	PrimaryComponentTick.bCanEverTick = true;

	// The C++ widget builds its own tree, so the HUD works with no content
	// pass. Point this at a designed WBP_GameHUD child to restyle it.
	HUDWidgetClass = UGameHUDWidget::StaticClass();
}

void UInteractionComponent::BeginPlay()
{
	Super::BeginPlay();

	EnsureHUDWidget();
}

void UInteractionComponent::EnsureHUDWidget()
{
	// BeginPlay runs before possession for pawns spawned after the world has
	// begun play (see AVillageCharacter::NotifyControllerChanged, which calls
	// this again once a controller exists), so creation must be retryable.
	if (HUDWidget || !HUDWidgetClass)
	{
		return;
	}
	if (APlayerController* PC = GetPlayerController())
	{
		HUDWidget = CreateWidget<UGameHUDWidget>(PC, HUDWidgetClass);
		if (HUDWidget)
		{
			HUDWidget->AddToViewport();
		}
	}
}

AVillageCharacter* UInteractionComponent::GetVillageCharacter() const
{
	return Cast<AVillageCharacter>(GetOwner());
}

APlayerController* UInteractionComponent::GetPlayerController() const
{
	if (const APawn* Pawn = Cast<APawn>(GetOwner()))
	{
		return Cast<APlayerController>(Pawn->GetController());
	}
	return nullptr;
}

void UInteractionComponent::TickComponent(float DeltaTime, ELevelTick TickType,
	FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

	if (PlayerMode == EPlayerMode::FreeRoam)
	{
		UpdateFocusedZone();
	}
}

// -------------------- zone bookkeeping --------------------

void UInteractionComponent::NotifyZoneEntered(AMiniGameZone* Zone)
{
	if (Zone)
	{
		OverlappingZones.AddUnique(Zone);
	}
}

void UInteractionComponent::NotifyZoneExited(AMiniGameZone* Zone)
{
	OverlappingZones.Remove(Zone);

	// Walking out of the trigger mid-game cancels the game.
	if (PlayerMode == EPlayerMode::InGame && Zone == ActiveZone)
	{
		EndActiveGame();
	}
}

// -------------------- NPC bookkeeping --------------------

void UInteractionComponent::NotifyNPCEntered(AVillagerNPC* NPC)
{
	if (NPC)
	{
		NearbyNPCs.AddUnique(NPC);
	}
}

void UInteractionComponent::NotifyNPCExited(AVillagerNPC* NPC)
{
	NearbyNPCs.Remove(NPC);
	if (NPC && NPC == TalkingNPC)
	{
		EndTalk();
	}
}

void UInteractionComponent::UpdateFocusedZone()
{
	// Drop any zones that were destroyed while we overlapped them.
	OverlappingZones.RemoveAll([](const TWeakObjectPtr<AMiniGameZone>& Zone)
	{
		return !Zone.IsValid();
	});

	AMiniGameZone* Nearest = nullptr;
	float NearestDistSq = TNumericLimits<float>::Max();
	const FVector OwnerLocation = GetOwner()->GetActorLocation();

	for (const TWeakObjectPtr<AMiniGameZone>& Zone : OverlappingZones)
	{
		const float DistSq = FVector::DistSquared(OwnerLocation, Zone->GetActorLocation());
		if (DistSq < NearestDistSq)
		{
			NearestDistSq = DistSq;
			Nearest = Zone.Get();
		}
	}

	// NPCs only take focus when no zone has it.
	AVillagerNPC* NearestNPC = nullptr;
	if (!Nearest)
	{
		NearbyNPCs.RemoveAll([](const TWeakObjectPtr<AVillagerNPC>& NPC)
		{
			return !NPC.IsValid();
		});
		float NearestNPCDistSq = TNumericLimits<float>::Max();
		for (const TWeakObjectPtr<AVillagerNPC>& NPC : NearbyNPCs)
		{
			const float DistSq = FVector::DistSquared(OwnerLocation, NPC->GetActorLocation());
			if (DistSq < NearestNPCDistSq)
			{
				NearestNPCDistSq = DistSq;
				NearestNPC = NPC.Get();
			}
		}
	}

	if (Nearest == FocusedZone && NearestNPC == FocusedNPC)
	{
		return; // no prompt change
	}
	FocusedZone = Nearest;
	FocusedNPC = NearestNPC;

	if (HUDWidget)
	{
		// Always vacate the prompt slot being left so zone<->NPC focus
		// transitions never strand a stale prompt on screen.
		if (FocusedZone)
		{
			HUDWidget->HideTalkPrompt();
			HUDWidget->ShowInteractPrompt(FocusedZone->GameDisplayName);
		}
		else if (FocusedNPC)
		{
			HUDWidget->HideInteractPrompt();
			HUDWidget->ShowTalkPrompt(FocusedNPC->GetVillagerName());
		}
		else
		{
			HUDWidget->HideInteractPrompt();
			HUDWidget->HideTalkPrompt();
		}
	}
	else if (GEngine)
	{
		// Debug fallback so the interact loop is testable before
		// WBP_GameHUD exists. Assign HUDWidgetClass to replace this.
		if (FocusedZone)
		{
			GEngine->AddOnScreenDebugMessage(0xE110, 600.f, FColor::Yellow,
				FString::Printf(TEXT("Press E to play %s  (Esc to quit)"),
					*FocusedZone->GameDisplayName.ToString()));
		}
		else if (FocusedNPC)
		{
			GEngine->AddOnScreenDebugMessage(0xE110, 600.f, FColor::Yellow,
				FString::Printf(TEXT("Press E to talk to %s"),
					*FocusedNPC->GetVillagerName().ToString()));
		}
		else
		{
			GEngine->RemoveOnScreenDebugMessage(0xE110);
		}
	}
}

// -------------------- NPC conversation --------------------

void UInteractionComponent::TalkToFocusedNPC()
{
	if (!FocusedNPC)
	{
		return;
	}

	FText Line;
	if (TalkingNPC == FocusedNPC)
	{
		Line = FocusedNPC->NextLine();
	}
	else
	{
		EndTalk();
		TalkingNPC = FocusedNPC;
		Line = FocusedNPC->StartTalk(GetVillageCharacter());
	}

	if (HUDWidget)
	{
		HUDWidget->ShowDialogueLine(FocusedNPC->GetVillagerName(), Line);
	}
	else if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(0xE120, 8.f, FColor::White,
			FString::Printf(TEXT("%s: \"%s\"   (E = more, Q = leave)"),
				*FocusedNPC->GetVillagerName().ToString(), *Line.ToString()));
	}
}

void UInteractionComponent::EndTalk()
{
	if (!TalkingNPC)
	{
		return;
	}
	// Clear before calling into the NPC: its EndTalk notifies us back, and
	// the TalkingNPC != NPC guard must short-circuit that reentrant call.
	AVillagerNPC* NPC = TalkingNPC;
	TalkingNPC = nullptr;
	NPC->EndTalk();

	if (HUDWidget)
	{
		HUDWidget->HideDialogue();
	}
	else if (GEngine)
	{
		GEngine->RemoveOnScreenDebugMessage(0xE120);
	}
}

void UInteractionComponent::NotifyTalkEndedByNPC(AVillagerNPC* NPC)
{
	if (TalkingNPC != NPC)
	{
		return;
	}
	TalkingNPC = nullptr;
	if (HUDWidget)
	{
		HUDWidget->HideDialogue();
	}
	else if (GEngine)
	{
		GEngine->RemoveOnScreenDebugMessage(0xE120);
	}
}

// -------------------- game start / end --------------------

void UInteractionComponent::OnInteractPressed()
{
	if (PlayerMode == EPlayerMode::InGame)
	{
		if (ActiveZone)
		{
			ActiveZone->HandleInteractPressed();
		}
	}
	else if (FocusedZone)
	{
		StartGame(FocusedZone);
	}
	else if (FocusedNPC)
	{
		TalkToFocusedNPC();
	}
}

void UInteractionComponent::OnInteractReleased()
{
	if (PlayerMode == EPlayerMode::InGame && ActiveZone)
	{
		ActiveZone->HandleInteractReleased();
	}
}

void UInteractionComponent::OnCancelPressed()
{
	if (PlayerMode == EPlayerMode::InGame)
	{
		EndActiveGame();
	}
	else
	{
		EndTalk();
	}
}

void UInteractionComponent::StartGame(AMiniGameZone* Zone)
{
	if (!Zone || PlayerMode == EPlayerMode::InGame)
	{
		return;
	}

	EndTalk(); // a game interrupts any conversation

	ActiveZone = Zone;
	PlayerMode = EPlayerMode::InGame;

	if (HUDWidget)
	{
		HUDWidget->HideInteractPrompt();
		HUDWidget->HideTalkPrompt();
	}

	// Blend to the zone's own camera component (zones set
	// bFindCameraComponentWhenViewTarget so the blend lands on it).
	if (APlayerController* PC = GetPlayerController())
	{
		PC->SetViewTargetWithBlend(Zone, CameraBlendTime, VTBlend_Cubic);
	}

	Zone->StartGame(this);
}

void UInteractionComponent::EndActiveGame()
{
	if (PlayerMode != EPlayerMode::InGame)
	{
		return;
	}

	if (ActiveZone)
	{
		ActiveZone->EndGame();
	}
	ActiveZone = nullptr;
	PlayerMode = EPlayerMode::FreeRoam;

	// Clear the focus members so UpdateFocusedZone's "no prompt change"
	// early-out cannot swallow the re-show: the player usually still stands
	// inside the zone they just left, and the prompt must come back.
	FocusedZone = nullptr;
	FocusedNPC = nullptr;

	if (APlayerController* PC = GetPlayerController())
	{
		PC->SetViewTargetWithBlend(GetOwner(), CameraBlendTime, VTBlend_Cubic);
	}
}

// -------------------- input routing --------------------

bool UInteractionComponent::RouteMoveInput(const FVector2D& Value)
{
	if (PlayerMode == EPlayerMode::InGame && ActiveZone)
	{
		ActiveZone->HandleMoveInput(Value);
		return true;
	}
	return false;
}

bool UInteractionComponent::RouteLookInput(const FVector2D& Value)
{
	if (PlayerMode == EPlayerMode::InGame && ActiveZone)
	{
		ActiveZone->HandleLookInput(Value);
		return true;
	}
	return false;
}

bool UInteractionComponent::RouteJumpInput(bool bPressed)
{
	if (PlayerMode == EPlayerMode::InGame && ActiveZone)
	{
		ActiveZone->HandleJumpInput(bPressed);
		return true;
	}
	return false;
}

bool UInteractionComponent::RouteSprintInput(bool bPressed)
{
	if (PlayerMode == EPlayerMode::InGame && ActiveZone)
	{
		ActiveZone->HandleSprintInput(bPressed);
		return true;
	}
	return false;
}

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MiniGameZone.generated.h"

class UBoxComponent;
class UCameraComponent;
class UDecalComponent;
class UGameHUDWidget;
class UInteractionComponent;
class AVillageCharacter;

/**
 * Base class for every interactive mini-game zone.
 *
 * Owns: a box trigger (editable extent), a ground decal marking the play
 * area, and a camera the player view blends to while playing. Subclasses
 * override StartGame/EndGame/TickGame plus whichever HandleXxx input hooks
 * they need — that is the entire contract, so a 4th game slots in identically.
 */
UCLASS(Abstract)
class RURAL_PARDEEP_API AMiniGameZone : public AActor
{
	GENERATED_BODY()

public:
	AMiniGameZone();

	virtual void Tick(float DeltaTime) override;
	virtual void PostInitializeComponents() override;

	/** Begin the game. Base implementation flags active + shows the HUD panel. */
	virtual void StartGame(UInteractionComponent* InInteraction);

	/** End the game. Base implementation hides the HUD panel + clears state. */
	virtual void EndGame();

	// ---- input hooks, forwarded by UInteractionComponent while this game runs ----
	virtual void HandleMoveInput(const FVector2D& Value) {}
	virtual void HandleLookInput(const FVector2D& Value) {}
	virtual void HandleInteractPressed() {}
	virtual void HandleInteractReleased() {}
	virtual void HandleJumpInput(bool bPressed) {}
	virtual void HandleSprintInput(bool bPressed) {}

	/** Shown in the "Press E to play <GameName>" prompt. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "MiniGame")
	FText GameDisplayName;

	/**
	 * Identifies this game's HUD panel; the shared UGameHUDWidget receives it
	 * in ShowGamePanel/HideGamePanel and switches its own panels accordingly.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "MiniGame")
	FName HUDPanelName;

	UFUNCTION(BlueprintPure, Category = "MiniGame")
	bool IsGameActive() const { return bGameActive; }

protected:
	/** Per-frame game logic; only called while the game is active. */
	virtual void TickGame(float DeltaTime) {}

	UFUNCTION()
	void OnTriggerBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
		UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void OnTriggerEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
		UPrimitiveComponent* OtherComp, int32 OtherBodyIndex);

	/** HUD shell owned by the interaction component (null-safe). */
	UGameHUDWidget* GetHUD() const;

	/** On-screen debug line, shown ONLY while no HUD widget is assigned —
	 *  keeps every game playable before WBP_GameHUD is authored. */
	void DebugHUD(int32 Slot, const FString& Text) const;

	AVillageCharacter* GetPlayerCharacter() const;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "MiniGame|Components")
	TObjectPtr<USceneComponent> SceneRoot;

	/** Walk-in activation trigger. Size per zone in the editor or via the placement script. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "MiniGame|Components")
	TObjectPtr<UBoxComponent> Trigger;

	/** Marks the play area on the ground. Assign a decal material in the editor. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "MiniGame|Components")
	TObjectPtr<UDecalComponent> PlayAreaDecal;

	/** View the player blends to while playing. Subclasses may move it per-tick. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "MiniGame|Components")
	TObjectPtr<UCameraComponent> GameCamera;

	/** Valid between StartGame and EndGame. */
	UPROPERTY(Transient)
	TObjectPtr<UInteractionComponent> OwningInteraction;

	bool bGameActive = false;
};

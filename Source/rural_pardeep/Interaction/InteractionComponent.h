#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "InteractionComponent.generated.h"

class AMiniGameZone;
class AVillageCharacter;
class AVillagerNPC;
class UGameHUDWidget;

UENUM(BlueprintType)
enum class EPlayerMode : uint8
{
	FreeRoam,
	InGame
};

/**
 * THE shared interaction system. Lives on AVillageCharacter.
 *
 * Zones report themselves via NotifyZoneEntered/Exited (driven by their box
 * triggers). Each tick the nearest overlapping zone becomes the "focused"
 * zone and gets a "Press E to play <GameName>" prompt. IA_Interact starts the
 * focused zone's game; IA_Cancel (or walking out of the trigger) ends it.
 *
 * While InGame, every RouteXxx call is forwarded to the active zone and
 * consumed, so the character's free-roam handlers never see it. A 4th game
 * only needs a new AMiniGameZone subclass — nothing here changes.
 */
UCLASS(ClassGroup = (Village), meta = (BlueprintSpawnableComponent))
class RURAL_PARDEEP_API UInteractionComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UInteractionComponent();

	virtual void TickComponent(float DeltaTime, ELevelTick TickType,
		FActorComponentTickFunction* ThisTickFunction) override;

	// ---- zone overlap bookkeeping (called by AMiniGameZone) ----
	void NotifyZoneEntered(AMiniGameZone* Zone);
	void NotifyZoneExited(AMiniGameZone* Zone);

	// ---- NPC overlap bookkeeping (called by AVillagerNPC) ----
	void NotifyNPCEntered(AVillagerNPC* NPC);
	void NotifyNPCExited(AVillagerNPC* NPC);

	/** The NPC ended the conversation itself (timeout / walked away). */
	void NotifyTalkEndedByNPC(AVillagerNPC* NPC);

	// ---- input entry points (called by AVillageCharacter) ----
	void OnInteractPressed();
	void OnInteractReleased();
	void OnCancelPressed();

	/** Return true if the input was consumed by an active mini-game. */
	bool RouteMoveInput(const FVector2D& Value);
	bool RouteLookInput(const FVector2D& Value);
	bool RouteJumpInput(bool bPressed);
	bool RouteSprintInput(bool bPressed);

	/** Ends the active game, blends the camera home and restores FreeRoam. */
	UFUNCTION(BlueprintCallable, Category = "Village|Interaction")
	void EndActiveGame();

	/**
	 * Creates the HUD widget if it doesn't exist yet and a player controller
	 * is available. Safe to call repeatedly — BeginPlay tries once, and the
	 * character retries on every possession (BeginPlay runs before Possess
	 * for pawns spawned after the world has begun play).
	 */
	void EnsureHUDWidget();

	UFUNCTION(BlueprintPure, Category = "Village|Interaction")
	EPlayerMode GetPlayerMode() const { return PlayerMode; }

	UFUNCTION(BlueprintPure, Category = "Village|Interaction")
	UGameHUDWidget* GetHUD() const { return HUDWidget; }

	AVillageCharacter* GetVillageCharacter() const;

	/** Widget class for the shared HUD shell (create WBP_GameHUD from UGameHUDWidget). */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Village|Interaction")
	TSubclassOf<UGameHUDWidget> HUDWidgetClass;

	/** Seconds for the camera blend into/out of a mini-game view. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Interaction", meta = (ClampMin = "0"))
	float CameraBlendTime = 0.75f;

protected:
	virtual void BeginPlay() override;

	void StartGame(AMiniGameZone* Zone);
	void UpdateFocusedZone();
	void TalkToFocusedNPC();
	void EndTalk();
	APlayerController* GetPlayerController() const;

	UPROPERTY(Transient)
	EPlayerMode PlayerMode = EPlayerMode::FreeRoam;

	/** Zones whose triggers currently contain the character. */
	TArray<TWeakObjectPtr<AMiniGameZone>> OverlappingZones;

	/** Villagers whose interact spheres currently contain the character. */
	TArray<TWeakObjectPtr<AVillagerNPC>> NearbyNPCs;

	/** Nearest overlapping zone; owns the interact prompt. */
	UPROPERTY(Transient)
	TObjectPtr<AMiniGameZone> FocusedZone;

	/** Nearest villager (only focused while no zone is). */
	UPROPERTY(Transient)
	TObjectPtr<AVillagerNPC> FocusedNPC;

	/** Villager currently in conversation with the player. */
	UPROPERTY(Transient)
	TObjectPtr<AVillagerNPC> TalkingNPC;

	/** Zone currently running a game (only valid while InGame). */
	UPROPERTY(Transient)
	TObjectPtr<AMiniGameZone> ActiveZone;

	UPROPERTY(Transient)
	TObjectPtr<UGameHUDWidget> HUDWidget;
};

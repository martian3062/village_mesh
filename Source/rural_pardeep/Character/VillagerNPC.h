#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Character/VillagerLook.h"
#include "VillagerNPC.generated.h"

class USphereComponent;
class AVillageCharacter;

UENUM(BlueprintType)
enum class EVillagerActivity : uint8
{
	Rest,          // dwell near home charpai
	Wander,        // stroll the lanes
	Work,          // out to the fields / farm
	Pray,          // visit the gurdwara / mandir
	Socialize,     // hang around the vendor cart / school gate
	TalkToPlayer   // pinned in conversation
};

/**
 * A villager with a small utility brain. Four needs (energy, faith, social,
 * work) drain over time; each tick-cycle the villager scores every activity
 * against its needs (plus a little whimsy) and walks to the matching point
 * of interest, dwelling there to refill the need. NavMesh pathing when
 * available, straight-line strolling when not — the village never freezes.
 *
 * Awareness: villagers stop and face the player when they come close, and a
 * walk-up + IA_Interact starts a conversation routed through the player's
 * UInteractionComponent (prompt/dialogue events on UGameHUDWidget, with the
 * on-screen debug fallback until the widget is designed).
 *
 * Mesh/anim are assigned on the BP child (BP_Villager); points of interest
 * and the name are stamped by the environment build script per instance.
 */
UCLASS()
class RURAL_PARDEEP_API AVillagerNPC : public ACharacter
{
	GENERATED_BODY()

public:
	AVillagerNPC();

	virtual void Tick(float DeltaTime) override;
	virtual void OnConstruction(const FTransform& Transform) override;

	/** Punjabi villager appearance (cloth colours, pagri/chunni, beard) —
	 *  stamped per instance by the dressing script. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Look")
	FVillagerLook Appearance;

	// ---- conversation API (called by UInteractionComponent) ----

	/** Enter TalkToPlayer and return the opening line. */
	FText StartTalk(AVillageCharacter* Player);

	/** Next line while already talking (cycles through DialogueLines). */
	FText NextLine();

	void EndTalk();
	bool IsTalking() const { return Activity == EVillagerActivity::TalkToPlayer; }

	UFUNCTION(BlueprintPure, Category = "Villager")
	FText GetVillagerName() const { return VillagerName; }

	// ---- identity + dialogue (stamped per instance by the build script) ----

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager")
	FText VillagerName;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Dialogue")
	TArray<FText> GreetingLines;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Dialogue")
	TArray<FText> DialogueLines;

	// ---- points of interest (world positions) ----

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|POI")
	FVector HomeSpot = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|POI")
	FVector WorkSpot = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|POI")
	FVector PraySpot = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|POI")
	FVector SocialSpot = FVector::ZeroVector;

	// ---- brain tuning ----

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Brain", meta = (ClampMin = "50"))
	float StrollSpeed = 160.f;

	/** Random offset radius around a chosen point of interest. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Brain", meta = (ClampMin = "0"))
	float ArrivalScatter = 350.f;

	/** Radius for aimless wandering around the current position. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Brain", meta = (ClampMin = "200"))
	float WanderRadius = 2500.f;

	/** Seconds spent at a destination (randomised +/- 40%). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Brain", meta = (ClampMin = "1"))
	float DwellTime = 10.f;

	/** Needs drain per second (they refill ~10x faster while dwelling). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Brain", meta = (ClampMin = "0"))
	float NeedDrainRate = 0.006f;

	/** Player distance that makes the villager stop and face them. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Brain", meta = (ClampMin = "0"))
	float AwarenessRadius = 420.f;

	/** Player distance beyond which a conversation auto-ends. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Villager|Brain", meta = (ClampMin = "0"))
	float TalkBreakRadius = 650.f;

	/** Registers the player for the talk prompt when inside. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Villager")
	TObjectPtr<USphereComponent> InteractSphere;

protected:
	virtual void BeginPlay() override;

	UFUNCTION()
	void OnSphereBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
		UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);

	UFUNCTION()
	void OnSphereEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
		UPrimitiveComponent* OtherComp, int32 OtherBodyIndex);

	void ChooseNextActivity();
	void StartMoveTo(const FVector& Destination);
	void FacePoint(const FVector& Point, float DeltaTime);
	float& NeedFor(EVillagerActivity InActivity);

	// runtime state
	EVillagerActivity Activity = EVillagerActivity::Wander;
	FVector CurrentDestination = FVector::ZeroVector;
	bool bTravelling = false;
	bool bDirectWalk = false;   // fallback when no NavMesh path exists
	float DwellRemaining = 0.f;
	float StuckTimer = 0.f;
	float TalkIdleTimer = 0.f;
	int32 LineIndex = 0;

	// needs, 0 (starving) .. 1 (satisfied)
	float Energy = 1.f;
	float Faith = 0.7f;
	float Social = 0.6f;
	float WorkSat = 0.5f;

	TWeakObjectPtr<AVillageCharacter> PlayerNearby;
};

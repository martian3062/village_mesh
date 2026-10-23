#pragma once

#include "CoreMinimal.h"
#include "MiniGames/MiniGameZone.h"
#include "KiteZone.generated.h"

class AKiteActor;

/**
 * Rooftop patang (kite) zone. The placement script builds the 2-storey
 * building with the exterior stair and drops this zone on the roof, so the
 * trigger only fires once the character has physically climbed up.
 *
 * Controls while flying:
 *   IA_Move / IA_Look .. steer (X = sideways, Y = climb/dive)
 *   IA_Jump (hold) ..... let string out          IA_Sprint (hold) .. reel in
 *   IA_Interact ........ PULL during a pech (mash or hold)
 *   IA_Cancel .......... land the kite / leave
 *
 * Pech: when the two strings cross (segment-to-segment distance under
 * StringCrossDistance) a tension contest starts. Pull input builds your
 * tension while it decays over time; the rival's rises steadily with a
 * wobble. First to TensionToWin cuts the other's string.
 */
UCLASS()
class RURAL_PARDEEP_API AKiteZone : public AMiniGameZone
{
	GENERATED_BODY()

public:
	AKiteZone();

	virtual void StartGame(UInteractionComponent* InInteraction) override;
	virtual void EndGame() override;
	virtual void HandleMoveInput(const FVector2D& Value) override;
	virtual void HandleLookInput(const FVector2D& Value) override;
	virtual void HandleInteractPressed() override;
	virtual void HandleInteractReleased() override;
	virtual void HandleJumpInput(bool bPressed) override;
	virtual void HandleSprintInput(bool bPressed) override;

	// -------- wind --------

	/** Direction the wind blows toward (normalized at use). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Wind")
	FVector WindDirection = FVector(1.f, 0.35f, 0.f);

	/** Steady wind speed, cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Wind", meta = (ClampMin = "0"))
	float WindStrength = 120.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Wind", meta = (ClampMin = "0"))
	float GustAmplitude = 60.f;

	/** Gust cycles per second. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Wind", meta = (ClampMin = "0"))
	float GustFrequency = 0.4f;

	// -------- pech (string-cutting contest) --------

	/** Strings closer than this (cm) start a contest. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Pech", meta = (ClampMin = "5"))
	float StringCrossDistance = 60.f;

	/** Tension gained per IA_Interact press (mash). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Pech", meta = (ClampMin = "0"))
	float TensionPerPress = 0.12f;

	/** Tension per second while IA_Interact is held. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Pech", meta = (ClampMin = "0"))
	float TensionHoldRate = 0.22f;

	/** Your tension decay per second (fight it by pulling!). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Pech", meta = (ClampMin = "0"))
	float TensionDecayRate = 0.10f;

	/** Rival tension per second — the true average; it wobbles ±50% around this. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Pech", meta = (ClampMin = "0"))
	float RivalTensionRate = 0.12f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Pech", meta = (ClampMin = "0.1"))
	float TensionToWin = 1.0f;

	/** Seconds until a new rival kite rises after you cut one. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Pech", meta = (ClampMin = "0"))
	float RivalRespawnDelay = 4.f;

	/** Seconds until your kite is relaunched after being cut. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Pech", meta = (ClampMin = "0"))
	float PlayerRelaunchDelay = 3.f;

	// -------- setup --------

	/** Rival flyer's rooftop position relative to this zone. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Setup")
	FVector RivalAnchorOffset = FVector(900.f, 700.f, 0.f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Setup")
	TSubclassOf<AKiteActor> PlayerKiteClass;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Setup")
	TSubclassOf<AKiteActor> RivalKiteClass;

protected:
	virtual void TickGame(float DeltaTime) override;

	AKiteActor* SpawnKite(TSubclassOf<AKiteActor> KiteClass, const FVector& InAnchor, bool bAutoPilot);
	void RelaunchPlayerKite();
	void RespawnRivalKite();
	void ResolveContest(bool bPlayerWon);
	void UpdateReelInput();
	void PushHUD();

	// -------- runtime state --------
	FVector PlayerAnchor = FVector::ZeroVector;
	FVector RivalAnchor = FVector::ZeroVector;
	FVector2D CurrentSteer = FVector2D::ZeroVector;
	float ReelInput = 0.f;
	bool bLetOutHeld = false;
	bool bReelInHeld = false;
	float ZoneTime = 0.f;

	bool bContestActive = false;
	bool bPullHeld = false;
	float PlayerTension = 0.f;
	float RivalTension = 0.f;
	int32 KitesCut = 0;

	FTimerHandle RivalRespawnTimer;
	FTimerHandle PlayerRelaunchTimer;

	UPROPERTY(Transient)
	TObjectPtr<AKiteActor> PlayerKite;

	UPROPERTY(Transient)
	TObjectPtr<AKiteActor> RivalKite;
};

#pragma once

#include "CoreMinimal.h"
#include "MiniGames/MiniGameZone.h"
#include "KanchaZone.generated.h"

class AMarbleActor;

UENUM(BlueprintType)
enum class EKanchaRule : uint8
{
	/** Authentic primary rule: strike a rival marble with yours to win it. */
	HitRivalToWin,
	/** Ring variant: rivals knocked outside the circle are won. */
	KnockOutOfRing
};

UENUM(BlueprintType)
enum class EKanchaTurnState : uint8
{
	Aiming,
	Charging,
	Rolling,
	GameOver
};

/**
 * Kancha (marbles) on a flat dirt patch inside a target ring.
 *
 * Turn loop: aim with IA_Look (over-shoulder camera orbits the shooter),
 * hold IA_Interact to charge, release to flick. The shot resolves when all
 * marbles settle (or a timeout); win rule is switchable via EKanchaRule.
 * The shooter plays on from wherever it stops, like the street game.
 */
UCLASS()
class RURAL_PARDEEP_API AKanchaZone : public AMiniGameZone
{
	GENERATED_BODY()

public:
	AKanchaZone();

	virtual void StartGame(UInteractionComponent* InInteraction) override;
	virtual void EndGame() override;
	virtual void HandleLookInput(const FVector2D& Value) override;
	virtual void HandleInteractPressed() override;
	virtual void HandleInteractReleased() override;

	/** Called by AMarbleActor on every rigid-body hit. */
	void NotifyMarbleHit(AMarbleActor* Marble, AActor* OtherActor);

	// -------- rules --------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Rules")
	EKanchaRule WinRule = EKanchaRule::HitRivalToWin;

	/** N rival marbles scattered inside the ring. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Rules", meta = (ClampMin = "1"))
	int32 RivalCount = 5;

	/** Turns before the game ends even if marbles remain. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Rules", meta = (ClampMin = "1"))
	int32 MaxTurns = 10;

	/** Target ring radius (cm) — also drives rival spawn spread and the decal. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Rules", meta = (ClampMin = "50"))
	float RingRadius = 250.f;

	// -------- marble physics (pushed into every spawned marble) --------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Physics", meta = (ClampMin = "0.001"))
	float MarbleMass = 0.03f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Physics", meta = (ClampMin = "0"))
	float MarbleFriction = 0.6f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Physics", meta = (ClampMin = "0", ClampMax = "1"))
	float MarbleRestitution = 0.2f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Physics")
	TSubclassOf<AMarbleActor> MarbleClass;

	// -------- flick feel --------

	/** Flick strength range, applied as a velocity change (cm/s). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Flick", meta = (ClampMin = "0"))
	float MinFlickSpeed = 150.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Flick", meta = (ClampMin = "0"))
	float MaxFlickSpeed = 750.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Flick", meta = (ClampMin = "0.05"))
	float ChargeRate = 1.0f;

	/** Degrees of aim yaw per input unit. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Flick", meta = (ClampMin = "0.01"))
	float AimSensitivity = 2.0f;

	/** Slight upward angle on the flick so marbles hop over grit. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Flick", meta = (ClampMin = "0", ClampMax = "45"))
	float FlickElevationDeg = 8.f;

	// -------- settle detection --------

	/** A marble slower than this (cm/s) counts as stopped. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Settle", meta = (ClampMin = "0"))
	float SettleSpeedThreshold = 8.f;

	/** All marbles must stay stopped this long before the shot resolves. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Settle", meta = (ClampMin = "0"))
	float SettleTime = 0.6f;

	/** Failsafe: resolve the shot after this many seconds regardless. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kancha|Settle", meta = (ClampMin = "1"))
	float RollTimeout = 8.f;

protected:
	virtual void TickGame(float DeltaTime) override;

	void SpawnMarbles();
	void DestroyMarbles();
	void ClaimRival(AMarbleActor* Rival);
	void ResolveShot();
	void PushHUD();

	// -------- runtime state --------
	EKanchaTurnState TurnState = EKanchaTurnState::Aiming;
	float AimYaw = 0.f;
	float ChargePower = 0.f;
	float SettleTimer = 0.f;
	float RollTimer = 0.f;
	int32 TurnsTaken = 0;
	int32 MarblesWon = 0;

	UPROPERTY(Transient)
	TObjectPtr<AMarbleActor> PlayerMarble;

	UPROPERTY(Transient)
	TArray<TObjectPtr<AMarbleActor>> RivalMarbles;
};

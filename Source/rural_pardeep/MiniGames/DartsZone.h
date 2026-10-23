#pragma once

#include "CoreMinimal.h"
#include "MiniGames/MiniGameZone.h"
#include "DartsZone.generated.h"

class ADartProjectile;
class UStaticMeshComponent;
class UDecalComponent;

UENUM(BlueprintType)
enum class EDartsMode : uint8
{
	/** Classic 501: score counts DOWN, overshooting a turn is a bust. */
	Countdown501,
	/** 3 turns of 3 darts; highest accumulated total. */
	BestOfThreeTurns
};

/** One concentric scoring ring: any impact within Radius (cm) of the board centre scores Score. */
USTRUCT(BlueprintType)
struct FDartScoreRing
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts")
	float Radius = 10.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts")
	int32 Score = 0;
};

/**
 * Courtyard darts. Zone root sits at the throwing line (oche); the board
 * hangs OcheDistance up the +X axis at regulation-ish height.
 *
 * Throw: IA_Look aims (camera reticle), hold IA_Interact to charge, release
 * to throw a gravity-arced dart. Impact distance from the board centre picks
 * the ring score.
 *
 * Scoring uses analytic concentric rings (Radius/Score pairs, editable).
 * To extend to a real 20-segment board with doubles/trebles: in ComputeScore,
 * also take atan2(LocalZ, LocalY) -> 18° segment index into the standard
 * 20,1,18,4,13,... sequence, and multiply by 2/3 when the radial distance
 * falls inside the double/treble ring bands.
 */
UCLASS()
class RURAL_PARDEEP_API ADartsZone : public AMiniGameZone
{
	GENERATED_BODY()

public:
	ADartsZone();

	virtual void StartGame(UInteractionComponent* InInteraction) override;
	virtual void EndGame() override;
	virtual void HandleLookInput(const FVector2D& Value) override;
	virtual void HandleInteractPressed() override;
	virtual void HandleInteractReleased() override;

	/** Called by ADartProjectile when it sticks into something. */
	void OnDartLanded(ADartProjectile* Dart, const FHitResult& Hit);

	/** Called by ADartProjectile if it is destroyed without ever landing
	 *  (lifespan expiry, fell out of world) so the turn cannot soft-lock. */
	void OnDartLost(ADartProjectile* Dart);

	// -------- rules --------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Rules")
	EDartsMode GameMode = EDartsMode::Countdown501;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Rules", meta = (ClampMin = "1"))
	int32 DartsPerTurn = 3;

	/** Turn count for BestOfThreeTurns mode. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Rules", meta = (ClampMin = "1"))
	int32 TotalTurns = 3;

	/** Inner bull 50, outer bull 25, then simple rings. Radii in cm, keep ascending. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Rules")
	TArray<FDartScoreRing> ScoreRings;

	// -------- throw feel --------

	/** Board centre distance from the throw line (regulation oche = 237 cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Layout", meta = (ClampMin = "100"))
	float OcheDistance = 237.f;

	/** Board centre height (regulation = 173 cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Layout", meta = (ClampMin = "50"))
	float BoardHeight = 173.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Throw", meta = (ClampMin = "0"))
	float MinThrowSpeed = 900.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Throw", meta = (ClampMin = "0"))
	float MaxThrowSpeed = 2200.f;

	/** Full charge takes 1/ChargeRate seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Throw", meta = (ClampMin = "0.05"))
	float ChargeRate = 1.2f;

	/** Degrees of aim per input unit. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Throw", meta = (ClampMin = "0.01"))
	float AimSensitivity = 1.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Throw")
	float MaxAimYaw = 25.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Throw")
	float MaxAimPitch = 20.f;

	/** Dart actor to spawn; defaults to the C++ dart, point at a BP child for custom art. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Darts|Throw")
	TSubclassOf<ADartProjectile> DartClass;

	/** Wall-mounted board. <DARTBOARD_MESH_PLACEHOLDER> — assign your Blender board. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Darts|Components")
	TObjectPtr<UStaticMeshComponent> DartboardMesh;

	/** Marked throwing line at the zone root. Assign a stripe decal material. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Darts|Components")
	TObjectPtr<UDecalComponent> ThrowLineDecal;

protected:
	virtual void TickGame(float DeltaTime) override;
	virtual void OnConstruction(const FTransform& Transform) override;

	int32 ComputeScore(const FHitResult& Hit) const;
	void BeginTurn();
	void AdvanceTurnIfNeeded();
	void FinishGame();
	void PushHUD();

	// -------- runtime state --------
	int32 Score = 0;           // 501 countdown value, or accumulated total
	int32 TurnStartScore = 0;  // for bust recovery in 501
	int32 DartsLeftInTurn = 0;
	int32 DartsInFlight = 0;   // one dart airborne at a time keeps turns honest
	int32 LastThrowScore = 0;
	int32 TurnsPlayed = 0;
	bool bGameOver = false;

	bool bCharging = false;
	float ChargePower = 0.f;
	float AimYaw = 0.f;
	float AimPitch = 0.f;

	UPROPERTY(Transient)
	TArray<TObjectPtr<ADartProjectile>> ActiveDarts;
};

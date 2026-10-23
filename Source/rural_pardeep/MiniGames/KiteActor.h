#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "KiteActor.generated.h"

class UStaticMeshComponent;

/**
 * A patang. Arcade flight model: steering + wind produce a desired velocity,
 * the position is then clamped to a sphere of radius StringLength around the
 * anchor (the flyer's hands). The rival kite runs the same model with an
 * autopilot feeding the inputs. Cut() releases the string and the kite falls.
 */
UCLASS()
class RURAL_PARDEEP_API AKiteActor : public AActor
{
	GENERATED_BODY()

public:
	AKiteActor();

	virtual void Tick(float DeltaTime) override;

	/**
	 * Advance the flight model one frame.
	 * Steer: X = sideways around the anchor, Y = climb/dive.
	 * Reel: +1 lets string out, -1 reels in, 0 holds.
	 */
	void UpdateFlight(float DeltaTime, const FVector2D& Steer, float Reel, const FVector& Wind);

	/** Cut the string — the kite tumbles away and destroys itself. */
	void Cut();

	void SetAnchor(const FVector& InAnchor) { Anchor = InAnchor; }
	void SetAutoPilot(bool bEnabled) { bAutoPilot = bEnabled; }
	void SetWind(const FVector& InWind) { CachedWind = InWind; }

	bool IsCut() const { return bCut; }
	FVector GetAnchor() const { return Anchor; }
	float GetStringLength() const { return StringLength; }

	// -------- flight tuning --------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|String", meta = (ClampMin = "100"))
	float StringLength = 900.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|String", meta = (ClampMin = "50"))
	float MinStringLength = 300.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|String", meta = (ClampMin = "100"))
	float MaxStringLength = 4000.f;

	/** cm/s of string let out / reeled in while the reel input is held. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|String", meta = (ClampMin = "0"))
	float ReelRate = 500.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Flight", meta = (ClampMin = "0"))
	float LateralSpeed = 450.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Flight", meta = (ClampMin = "0"))
	float ClimbSpeed = 400.f;

	/** How quickly velocity chases the steered direction (VInterpTo speed). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Flight", meta = (ClampMin = "0.1"))
	float Agility = 2.5f;

	/** Kite never drops below Anchor.Z + this (keeps it out of the parapet). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite|Flight", meta = (ClampMin = "0"))
	float MinAltitude = 150.f;

	/** Kite face. <KITE_MESH_PLACEHOLDER> — swap for your Blender patang. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Kite")
	TObjectPtr<UStaticMeshComponent> KiteMesh;

	/** Manjha: a thin cylinder stretched from the anchor to the kite. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Kite")
	TObjectPtr<UStaticMeshComponent> StringMesh;

	/** Paper tail ribbons trailing the kite. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Kite")
	TArray<TObjectPtr<UStaticMeshComponent>> TailPieces;

	/**
	 * Editor-placed ambience: on BeginPlay the spawn point becomes the anchor,
	 * the autopilot engages and the kite rises on its own — no zone required.
	 * The placement script drops a few of these over village rooftops.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Kite")
	bool bAmbientAutoFly = false;

protected:
	virtual void BeginPlay() override;

	void UpdateStringVisual();

	FVector Anchor = FVector::ZeroVector;
	FVector Velocity = FVector::ZeroVector;
	FVector CachedWind = FVector::ZeroVector;

	bool bAutoPilot = false;
	bool bCut = false;
	float PatrolTime = 0.f;
	float FallTime = 0.f;
	float VisualTime = 0.f;
};

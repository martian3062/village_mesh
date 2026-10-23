#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "BirdActor.generated.h"

class UStaticMeshComponent;

/**
 * A stylised bird assembled from engine basic shapes (no skeletal mesh). At
 * runtime it soars in a slow horizontal circle around its spawn point, banks
 * into the turn, bobs gently on the thermals, and flaps its wings. Purely
 * ambient sky decoration — the placement script drops a small flock over the
 * village. In the editor (no PIE) it holds a spread-wing glide pose so it still
 * reads as a bird.
 */
UCLASS()
class RURAL_PARDEEP_API ABirdActor : public AActor
{
	GENERATED_BODY()

public:
	ABirdActor();

	virtual void Tick(float DeltaTime) override;

	/** Horizontal radius of the soaring circle around the spawn point (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bird", meta = (ClampMin = "200"))
	float CircleRadius = 2200.f;

	/** Angular speed around the circle (deg/s). Sign flips the turn direction. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bird")
	float CircleSpeed = 26.f;

	/** Vertical bob amplitude (cm) and rate (Hz-ish). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bird")
	float BobAmplitude = 220.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bird")
	float BobSpeed = 0.6f;

	/** Wing-flap peak angle (deg) and rate. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bird")
	float FlapAngle = 32.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bird")
	float FlapSpeed = 3.2f;

	/** Constant bank into the circle (deg). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bird")
	float BankAngle = 16.f;

	/** Body + wing material (script-assigned; silhouette dark by default). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bird")
	TObjectPtr<UMaterialInterface> BodyMaterial;

	/** On BeginPlay the spawn point becomes the circle centre and it soars. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Bird")
	bool bAmbientAutoFly = true;

	UStaticMeshComponent* GetBody() const { return Body; }

protected:
	virtual void BeginPlay() override;

	void ApplyMaterial();

	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Body;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Head;
	UPROPERTY() TObjectPtr<USceneComponent> ShoulderL;   // flap pivot at the body
	UPROPERTY() TObjectPtr<USceneComponent> ShoulderR;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> WingL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> WingR;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Tail;

	// runtime state
	FVector Center = FVector::ZeroVector;
	float Angle = 0.f;       // deg around the circle
	float FlapPhase = 0.f;
	float BobPhase = 0.f;
	bool bSoaring = false;
};

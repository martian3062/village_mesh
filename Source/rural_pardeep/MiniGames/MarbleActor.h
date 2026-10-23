#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MarbleActor.generated.h"

class AKanchaZone;
class UStaticMeshComponent;

/**
 * One physics marble (kancha). An engine sphere with SimulatePhysics on;
 * mass/friction/restitution are pushed in by the zone via InitMarble so the
 * whole set is tuned from one place.
 */
UCLASS()
class RURAL_PARDEEP_API AMarbleActor : public AActor
{
	GENERATED_BODY()

public:
	AMarbleActor();

	/** Configure physics + ownership. Called by AKanchaZone right after spawning. */
	void InitMarble(AKanchaZone* InZone, bool bInPlayerMarble,
		float Mass, float Friction, float Restitution);

	bool IsPlayerMarble() const { return bPlayerMarble; }

	FVector GetMarbleVelocity() const;

	/** Marble radius in cm (engine sphere is scaled to match). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marble", meta = (ClampMin = "0.5"))
	float MarbleRadius = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marble", meta = (ClampMin = "0"))
	float LinearDamping = 0.4f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Marble", meta = (ClampMin = "0"))
	float AngularDamping = 0.6f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Marble")
	TObjectPtr<UStaticMeshComponent> MeshComp;

protected:
	UFUNCTION()
	void OnMarbleHit(UPrimitiveComponent* HitComponent, AActor* OtherActor,
		UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit);

	TWeakObjectPtr<AKanchaZone> OwnerZone;
	bool bPlayerMarble = false;
};

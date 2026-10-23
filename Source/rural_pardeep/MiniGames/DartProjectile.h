#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DartProjectile.generated.h"

class ADartsZone;
class UProjectileMovementComponent;
class UStaticMeshComponent;

/**
 * A thrown dart. Gravity-arced projectile that sticks into whatever it hits
 * and reports the impact back to its owning ADartsZone for scoring.
 */
UCLASS()
class RURAL_PARDEEP_API ADartProjectile : public AActor
{
	GENERATED_BODY()

public:
	ADartProjectile();

	/** Fire the dart. Velocity in cm/s; gravity is on, so it arcs. */
	void Launch(const FVector& Velocity, ADartsZone* InOwnerZone);

	/** Dart body. Default is a thin engine cylinder — swap for your Blender dart mesh. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dart")
	TObjectPtr<UStaticMeshComponent> DartMesh;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Dart")
	TObjectPtr<UProjectileMovementComponent> ProjectileMovement;

protected:
	UFUNCTION()
	void OnDartHit(UPrimitiveComponent* HitComponent, AActor* OtherActor,
		UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit);

	UFUNCTION()
	void OnDartDestroyed(AActor* DestroyedActor);

	TWeakObjectPtr<ADartsZone> OwnerZone;
	bool bStuck = false;
};

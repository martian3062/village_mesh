#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GrazingAnimal.generated.h"

class UStaticMeshComponent;

UENUM(BlueprintType)
enum class EGrazingSpecies : uint8
{
	Cow,
	Buffalo,
	Horse
};

/**
 * A free-roaming farm animal assembled from engine basic shapes (no skeletal
 * mesh needed). One class covers cows, water buffalo and horses — the species
 * property drives proportions, stance and default gait in OnConstruction, so
 * the placement script just spawns, sets Species + materials and walks away.
 *
 * Brain: Idle -> pick a point within WanderRadius of the home spot -> turn ->
 * walk (ground-snapped by line trace, obstacle probe ahead) -> graze with the
 * head dipped, tail flicking. Movement is plain actor motion — no NavMesh,
 * no CharacterMovement — so herds stay cheap.
 */
UCLASS()
class RURAL_PARDEEP_API AGrazingAnimal : public AActor
{
	GENERATED_BODY()

public:
	AGrazingAnimal();

	virtual void Tick(float DeltaTime) override;
	virtual void OnConstruction(const FTransform& Transform) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Animal")
	EGrazingSpecies Species = EGrazingSpecies::Cow;

	/** Roam radius around the spawn point (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Animal", meta = (ClampMin = "100"))
	float WanderRadius = 900.f;

	/** Walk speed (cm/s). 0 = species default (cow 55, buffalo 45, horse 95). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Animal", meta = (ClampMin = "0"))
	float WalkSpeed = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Animal", meta = (ClampMin = "1"))
	float GrazeTimeMin = 6.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Animal", meta = (ClampMin = "1"))
	float GrazeTimeMax = 16.f;

	/** Coat material — applied to body, head, legs, ears, tail (script-assigned). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Animal")
	TObjectPtr<UMaterialInterface> CoatMaterial;

	/** Detail material — horns, hooves, muzzle, mane (script-assigned). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Animal")
	TObjectPtr<UMaterialInterface> DetailMaterial;

protected:
	virtual void BeginPlay() override;

	void ApplySpeciesShape();
	void ApplyMaterials();
	float GroundZ(const FVector2D& At, float Fallback) const;
	void PickNewTarget();

	// -------- parts --------
	UPROPERTY() TObjectPtr<USceneComponent> Root;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Body;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Head;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Snout;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Neck;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> EarL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> EarR;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> HornL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> HornR;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Mane;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> Tail;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> LegFL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> LegFR;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> LegBL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> LegBR;

	// -------- runtime state --------
	enum class EAnimalState : uint8 { Idle, Turning, Walking, Grazing };
	EAnimalState State = EAnimalState::Idle;

	FVector HomeSpot = FVector::ZeroVector;
	FVector Target = FVector::ZeroVector;
	float StateTimeLeft = 2.f;
	float WalkPhase = 0.f;
	float TailPhase = 0.f;
	float HeadBasePitch = 0.f;
	float HeadBaseZ = 0.f;
	FRandomStream Rand;
};

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "VillagePhysicsProp.generated.h"

class UStaticMeshComponent;
class UPhysicalMaterial;
class AWeatherManager;

/** Chaos rigid body with aerodynamic drag and optional plane-water buoyancy.
 * Positions/velocities use cm; force inputs are converted from SI to kg cm/s^2. */
UCLASS()
class RURAL_PARDEEP_API AVillagePhysicsProp : public AActor
{
    GENERATED_BODY()
public:
    AVillagePhysicsProp();
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Physics")
    TObjectPtr<UStaticMeshComponent> Body;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Physics", meta=(ClampMin="0.1"))
    float MassKg = 12.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Physics", meta=(ClampMin="0"))
    float DragAreaSquareMeters = 0.35f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Physics")
    bool bEnableBuoyancy = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Physics")
    float WaterLevelCm = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Physics", meta=(ClampMin="0.001"))
    float DisplacedVolumeCubicMeters = 0.08f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Physics")
    TObjectPtr<AWeatherManager> Weather;
protected:
    virtual void BeginPlay() override;
    UPROPERTY(Transient)
    TObjectPtr<UPhysicalMaterial> Surface;
};

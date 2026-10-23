#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "VillageDoor.generated.h"

class UStaticMeshComponent;

/** Session state survives actor streaming; it is not a disk save or multiplayer state. */
UCLASS()
class RURAL_PARDEEP_API UVillageDoorState : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    TMap<FString, bool> OpenDoors;
};

UCLASS()
class RURAL_PARDEEP_API AVillageDoor : public AActor
{
    GENERATED_BODY()
public:
    AVillageDoor();
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(BlueprintCallable) void Toggle();
    UFUNCTION(BlueprintPure) bool IsOpen() const { return bOpen; }
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString PersistentId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float DoorWidthCm = 120.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float DoorHeightCm = 225.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bCanOpen = true;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) TObjectPtr<UStaticMeshComponent> Leaf;
private:
    bool bOpen = false;
    float CurrentAngle = 0.f;
};

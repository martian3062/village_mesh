#pragma once
#include "CoreMinimal.h"
#include "Character/VillageExplorer.h"
#include "V3/VillageAtlas.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "PardeepPlayer.generated.h"

class USpringArmComponent;
class USkeletalMeshComponent;
class UBlendSpace;
class UStaticMeshComponent;

UCLASS()
class RURAL_PARDEEP_API UPardeepAssetTools : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Village|Editor")
    static bool RebuildLocomotion(UBlendSpace* Blend);
    // Save only this generated character's loaded packages, without editor thumbnails.
    UFUNCTION(BlueprintCallable,Category="Village|Editor")
    static int32 SaveLoadedPardeepPackages(const FString& Root, bool OnlyDirty = true);
};

UCLASS()
class RURAL_PARDEEP_API APardeepPlayer : public AVillageExplorer
{
    GENERATED_BODY()
public:
    APardeepPlayer();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
    FString SurfaceName=TEXT("Village ground");
    bool HasCharacter() const {return Body!=nullptr;}
    bool IsFirstPerson() const {return bFirstPerson;}
protected:
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void ToggleView();
    void SwapShoulder();
    void ApplyView();
    void UpdateSurface();
    void CheckRuntime(float Dt);
    void AttachTurban();
    void CycleInspection();
    void UpdateInspectionCamera();
    UPROPERTY(VisibleAnywhere) TObjectPtr<USpringArmComponent> CameraBoom;
    UPROPERTY() TObjectPtr<AActor> Visual;
    UPROPERTY() TObjectPtr<USkeletalMeshComponent> Body;
    UPROPERTY() TObjectPtr<UBlendSpace> Locomotion;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Turban;
    bool bFirstPerson=false,bRightShoulder=true,bReferenceAppearance=false;
    int32 InspectionMode=0;
    int32 PortraitFaceLOD=INDEX_NONE,HandBodyLOD=INDEX_NONE;
    float SurfaceTimer=0,Elapsed=0,Travel=0,FootTravel=0;
    FVector LastPosition=FVector::ZeroVector,LastFoot=FVector::ZeroVector;
    bool bHaveFoot=false,bCheck=false,bGrounded=true,bWalkingSeen=false,bRunningSeen=false;
};

UCLASS()
class RURAL_PARDEEP_API APardeepVillageHUD : public AVillageAtlasHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};

UCLASS()
class RURAL_PARDEEP_API APardeepVillageGameMode : public AVillageAtlasGameMode
{
    GENERATED_BODY()
public:
    APardeepVillageGameMode();
};

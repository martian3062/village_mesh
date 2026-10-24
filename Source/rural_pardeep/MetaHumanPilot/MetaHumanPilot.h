#pragma once
#include "CoreMinimal.h"
#include "V3/VillageAtlas.h"
#include "MetaHumanPilot.generated.h"

class UCapsuleComponent;
class USkeletalMeshComponent;
class UAnimSequence;

// Selected explicitly through a map URL; ordinary village modes never spawn this probe.
UCLASS()
class RURAL_PARDEEP_API AMetaHumanPilotProbe : public AActor
{
    GENERATED_BODY()
public:
    AMetaHumanPilotProbe();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
private:
    void InitializePilot();
    void Finish();
    UPROPERTY() TObjectPtr<UCapsuleComponent> Capsule;
    UPROPERTY() TObjectPtr<AActor> Visual;
    UPROPERTY() TObjectPtr<USkeletalMeshComponent> Body;
    UPROPERTY() TObjectPtr<UAnimSequence> Idle;
    UPROPERTY() TObjectPtr<UAnimSequence> Walk;
    FVector Anchor=FVector::ZeroVector,LastFoot=FVector::ZeroVector;
    TArray<double> FrameTimes;
    FString Error,BlueprintPath,MovementBlocker;
    float Elapsed=0,Travel=0,FootTravel=0;
    double ReadyAt=0,StartedAt=0;
    bool bInitialized=false,bBaseline=false,bCheck=false,bWalking=false,bGrounded=true;
    bool bIdleApplied=false,bWalkApplied=false,bHaveFoot=false;
    bool bShadersDuringSamples=false;
    bool bPortraitPlaced=false;
    bool bMovementStartedPenetrating=false;
    bool bWarmupWalking=false;
    float FirstShaderSampleSeconds=-1;
    int32 MaxShaderJobsDuringSamples=0,ShaderSampleFrames=0;
    int32 Shot=0;
};

UCLASS()
class RURAL_PARDEEP_API AMetaHumanPilotGameMode : public AVillageAtlasGameMode
{
    GENERATED_BODY()
public:
    virtual void StartPlay() override;
};

#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/HUD.h"
#include "VillageExplorer.generated.h"

class UCameraComponent;
class UPhysicsHandleComponent;

/** Asset-independent first-person controller for the public world build. */
UCLASS()
class RURAL_PARDEEP_API AVillageExplorer : public ACharacter
{
    GENERATED_BODY()
public:
    AVillageExplorer();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
protected:
    float WalkingSpeed = 420.f;
    float RunningSpeed = 720.f;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void Forward(float Value);
    void Right(float Value);
    void Turn(float Value);
    void LookUp(float Value);
    void SprintOn();
    void SprintOff();
    void GrabOrRelease();
    void Throw();
    void CycleWeather();
    void AdvanceTime();
    void VisitPhysicsYard();
    void ToggleOverview();
    void VisitPilotRoom();
    TArray<FVector> PilotRoomStops;
    TArray<FVector> PilotRoomTargets;
    int32 PilotRoomIndex = 0;
    bool bAtPhysicsYard = false;
    bool bOverview = false;
    FVector OverviewReturnPosition;
    FRotator OverviewReturnRotation;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPhysicsHandleComponent> GrabHandle;
#if !UE_BUILD_SHIPPING
    float SmokeElapsed = 0.f;
    bool bSmokeChecked = false;
    bool bSmokeCaptured = false;
#endif
};

UCLASS()
class RURAL_PARDEEP_API AVillageExplorerHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};

UCLASS()
class RURAL_PARDEEP_API AVillageExplorerGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AVillageExplorerGameMode();
};

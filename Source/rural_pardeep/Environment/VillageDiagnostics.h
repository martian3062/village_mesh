#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "VillageDiagnostics.generated.h"
class FJsonObject;
class FJsonValue;
class AVillageExplorer;
class AWeatherManager;

/** Explicit development command-line runs; no automatic player movement in normal play. */
UCLASS()
class RURAL_PARDEEP_API AVillageDiagnostics : public AActor
{
    GENERATED_BODY()
public:
    AVillageDiagnostics();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
private:
    void Finish(bool bPass, const FString& Reason);
    void CaptureCamera(int32 Index);
    TSharedPtr<FJsonObject> Input;
    TArray<FVector> Route;
    TArray<double> FrameTimes;
    TArray<TSharedPtr<FJsonValue>> MemorySamples;
    UPROPERTY() TObjectPtr<AVillageExplorer> Player;
    UPROPERTY() TObjectPtr<AWeatherManager> Weather;
    FString Mode, Condition, RunId;
    int32 Index = 0;
    float Elapsed = 0, StageElapsed = 0, StuckSeconds = 0;
    bool bStarted = false, bFinished = false;
    double PreviousWallTime = 0;
    double StartedWallTime = 0, SoakStartedWallTime = 0, NextMemorySample = 0;
    int32 CompletedLegs = 0;
    float SoakMinutes = 30.f;
    FVector PreviousPosition;
    uint64 PeakMemory = 0;
};

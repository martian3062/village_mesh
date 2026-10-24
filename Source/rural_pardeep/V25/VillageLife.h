#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/Actor.h"
#include "V25/TinyNPCPolicy.h"
#include "VillageLife.generated.h"

class UStaticMeshComponent;
class UInstancedStaticMeshComponent;
class UTextRenderComponent;
class AWeatherManager;
class SWidget;
class FJsonObject;

UCLASS()
class RURAL_PARDEEP_API AVillageResident : public ACharacter
{
    GENERATED_BODY()
public:
    AVillageResident();
    virtual void Tick(float DeltaSeconds) override;
    void Dress(int32 Index,FLinearColor Color);
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Parts;
    UPROPERTY() TObjectPtr<UTextRenderComponent> Label;
    FString Identity;
    float GaitTime=0;
};

struct FV25Person
{
    FString Id,Name,Role,Outfit,Home,Work,Shelter,Target,CurrentNode,Plot;
    TArray<FString> Capabilities,Path;
    TArray<FString> RecentEvents;
    FVector Position=FVector::ZeroVector;
    FLinearColor Color=FLinearColor::White;
    float StartHour=8,EndHour=17,Fatigue=.1f,TaskProgress=0,Talkativeness=.5f,StuckSeconds=0;
    double CommitmentUntil=0,ConversationUntil=0;
    int32 Action=0,CompletedTasks=0,Visits=0;
    bool bReturning=false,bActive=false;
    TWeakObjectPtr<AVillageResident> Actor;
};

/** Runtime overlay on the frozen V2 world; enabled only by -VillageV25. */
UCLASS()
class RURAL_PARDEEP_API AVillageLifeDirector : public AActor
{
    GENERATED_BODY()
public:
    AVillageLifeDirector();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void Talk();
    void DialogueChoice(int32 Choice);
    void VisitFarm();
    void TogglePolicy();
    void AdvanceClock(){Hour=FMath::Fmod(Hour+3,24.f);}
    FString HUDStatus() const;
    static bool Enabled();
    static AVillageLifeDirector* Find(UWorld* World);
private:
    bool ReadContracts();
    void SpawnResident(FV25Person& Person,int32 Index);
    void BuildFarmAndRoads();
    void SetDestination(FV25Person& Person,const FString& Node);
    TArray<FString> FindPath(const FString& From,const FString& To) const;
    FString ClosestNode(FVector Position) const;
    void Decide(FV25Person& Person,int32 Index,const float* Logits=nullptr);
    TArray<float> Features(const FV25Person& Person) const;
    void Mask(const TArray<float>& X,TArray<bool>& Valid) const;
    int32 Baseline(const TArray<float>& X,const TArray<bool>& Valid) const;
    bool Reserve(const FString& Slot,const FString& Identity);
    void Release(const FString& Identity);
    void UpdateTractor(float DeltaSeconds);
    void UpdateDialogueWidget();
    TSharedPtr<FJsonObject> SerializeState() const;
    bool RestoreState(const TSharedPtr<FJsonObject>& State);
    void SaveState() const;
    void Diagnostics(float DeltaSeconds);
    void FinishDiagnostics(bool bPass,const FString& Reason);
    UPROPERTY() TArray<TObjectPtr<UInstancedStaticMeshComponent>> SceneParts;
    UPROPERTY() TObjectPtr<UStaticMeshComponent> Tractor;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> TractorParts;
    UPROPERTY() TObjectPtr<AWeatherManager> Weather;
    TArray<FV25Person> People;
    TMap<FString,FVector> Nodes;
    TMap<FString,TArray<FString>> Edges;
    TMap<FString,FString> Reservations;
    TArray<TSharedPtr<FJsonObject>> Parcels;
    TMap<FString,TSharedPtr<FJsonObject>> Lines;
    TSharedPtr<SWidget> DialogueWidget;
    FString DialogueText,ActiveSpeaker,SavePath;
    FTinyNPCPolicy Policy;
    TArray<float> LatestLogits;
    uint64 Generation=0;
    float Hour=13.5f,DecisionElapsed=0,SaveElapsed=0,Age=0,TractorWait=0;
    double StartedAt=0,LastTickAt=0,LatestResultAt=0;
    TArray<double> FrameMs,InferenceMs,QueueMs,GameThreadMs;
    int32 ModelCalls=0,StaleResults=0,InvalidRejected=0,CompletedLegs=0,StreamRestores=0,TractorNode=0,TractorDirection=1;
    bool bLearned=false,bNoSave=false,bCheck=false,bFinished=false,bMissingModel=false,bLastRain=false,bStreamTest=false,bSaveTest=false;
    bool bContractParity=false,bDoorTest=false,bTractorAuthorized=false;
    int32 CaptureStage=0,LastProgressMinute=0;
    double CheckSeconds=120;
    FString CheckId=TEXT("local");
};

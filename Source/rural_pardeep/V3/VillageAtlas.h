#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "Character/VillageExplorer.h"
#include "VillageAtlas.generated.h"

class UTexture2D;
class UStaticMeshComponent;
class UWorldPartitionStreamingSourceComponent;
struct FAtlasPlace
{
    FString Id,Name,Kind;
    FVector Center=FVector::ZeroVector,Arrival=FVector::ZeroVector,LookAt=FVector::ZeroVector;
};

UCLASS()
class RURAL_PARDEEP_API AVillageLivestock : public AActor
{
    GENERATED_BODY()
public:
    AVillageLivestock();
    void Initialize(const FString& Species,int32 Seed,FVector Yard);
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Parts;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Legs;
    FVector Origin,Target;
    float Age=0,Phase=0,Radius=420,Speed=35;
    int32 Identity=0;
};

UCLASS()
class RURAL_PARDEEP_API AVillageAtlasHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void DrawHUD() override;
    void ToggleMap();
    void SelectNext();
    void SelectAtCursor();
    void VisitSelected();
    void Zoom(float Direction);
    bool IsMapOpen() const {return bExpanded;}
    bool HasAtlas() const {return Atlas!=nullptr;}
    void SetExpanded(bool Value);
    TArray<FAtlasPlace> Places;
    int32 Selected=0;
private:
    FVector2D MapPoint(FVector P) const;
    UPROPERTY() TObjectPtr<UTexture2D> Atlas;
    bool bExpanded=false;
    float MapX=0,MapY=0,MapSize=300,MapSpan=36000;
    FVector MapCenter=FVector::ZeroVector;
    float MiniSpan=36000;
    float ListRowHeight=42;
};

UCLASS()
class RURAL_PARDEEP_API AVillageAtlasWorld : public AActor
{
    GENERATED_BODY()
public:
    AVillageAtlasWorld();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
private:
    UPROPERTY() TArray<TObjectPtr<AVillageLivestock>> Animals;
    UPROPERTY() TObjectPtr<UWorldPartitionStreamingSourceComponent> OverviewSource;
    TArray<FAtlasPlace> Places;
    TArray<double> FrameTimes;
    float Elapsed=0;
    int32 CheckStop=-1;
    bool bCheck=false,bPass=true,bGrounded=true;
    double Started=0;
    FVector LastAnimalPosition=FVector::ZeroVector;
    double AnimalDistance=0;
    TArray<FVector> LastAnimalPositions;
    TArray<double> AnimalTravel;
    bool bOverviewLoaded=false;
    int32 OverviewMeshChunks=0;
};

UCLASS()
class RURAL_PARDEEP_API AVillageAtlasGameMode : public AVillageExplorerGameMode
{
    GENERATED_BODY()
public:
    AVillageAtlasGameMode();
    virtual void StartPlay() override;
};

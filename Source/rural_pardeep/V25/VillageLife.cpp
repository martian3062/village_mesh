#include "V25/VillageLife.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Environment/WeatherManager.h"
#include "Environment/VillageDoor.h"
#include "EngineUtils.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Engine.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Fonts/SlateFontInfo.h"
#include "Fonts/CompositeFont.h"
#include "Fonts/FontCache.h"
#include "Styling/CoreStyle.h"
#include "HighResScreenshot.h"
#include "UnrealClient.h"

namespace {
TSharedPtr<FJsonObject> ReadJSON(const FString& Name)
{
    FString Text;TSharedPtr<FJsonObject> Object;
    if (FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("V25/Data")/Name)))
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Object);
    return Object;
}
FVector VectorJSON(const TArray<TSharedPtr<FJsonValue>>& A) { return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber()); }
TArray<TSharedPtr<FJsonValue>> JsonVector(FVector V) { return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)}; }
const TCHAR* ActionNames[]={TEXT("idle"),TEXT("travel"),TEXT("work"),TEXT("rest"),TEXT("shelter"),TEXT("greet"),TEXT("home"),TEXT("yield"),TEXT("replan")};
UStaticMesh* V25Basic(const TCHAR* Name) { return LoadObject<UStaticMesh>(nullptr,*FString::Printf(TEXT("/Engine/BasicShapes/%s.%s"),Name,Name)); }
UMaterialInterface* Surface(const TCHAR* Name) { return LoadObject<UMaterialInterface>(nullptr,*FString::Printf(TEXT("/Game/VillageMeshV2/Materials/%s.%s"),Name,Name)); }
UMaterialInstanceDynamic* Colored(UObject* Owner,FLinearColor Color)
{
    auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/VillageMeshV25/Materials/M_V25Color.M_V25Color"));
    if (!Base) Base=Surface(TEXT("M_V2_concrete"));
    auto* Mat=UMaterialInstanceDynamic::Create(Base,Owner);if (Mat) Mat->SetVectorParameterValue(TEXT("Color"),Color);return Mat;
}
}

AVillageResident::AVillageResident()
{
    PrimaryActorTick.bCanEverTick=true;GetCapsuleComponent()->InitCapsuleSize(28,88);
    GetCharacterMovement()->MaxWalkSpeed=145;GetCharacterMovement()->bOrientRotationToMovement=true;
    GetCharacterMovement()->RotationRate=FRotator(0,240,0);bUseControllerRotationYaw=false;
    GetCharacterMovement()->bRunPhysicsWithNoController=true;
    GetCharacterMovement()->MaxStepHeight=28;
    for (int i=0;i<13;++i)
    {
        auto* Part=CreateDefaultSubobject<UStaticMeshComponent>(*FString::Printf(TEXT("BodyPart%d"),i));
        Part->SetupAttachment(GetRootComponent());Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Parts.Add(Part);
    }
    Label=CreateDefaultSubobject<UTextRenderComponent>(TEXT("IdentityLabel"));Label->SetupAttachment(GetRootComponent());
    Label->SetRelativeLocation(FVector(0,0,108));Label->SetWorldSize(11);Label->SetHorizontalAlignment(EHTA_Center);
}
void AVillageResident::Dress(int32 Index,FLinearColor Color)
{
    // Original articulated prototype, explicitly not a licensed/local wardrobe substitute.
    auto* Skin=Colored(this,FLinearColor(.42f,.28f,.19f));auto* Cloth=Colored(this,Color);
    auto* Trousers=Colored(this,FLinearColor(.08f,.10f,.12f));auto* Shoes=Colored(this,FLinearColor(.035f,.03f,.025f));
    const FVector Locations[]={FVector(0,0,22),FVector(0,0,65),FVector(0,-23,18),FVector(0,23,18),FVector(0,-10,-43),FVector(0,10,-43),FVector(7,-10,-82),FVector(7,10,-82),FVector(2,0,79),FVector(0,0,-10),FVector(10,-5,68),FVector(10,5,68),FVector(12,0,62)};
    const FVector Scales[]={FVector(.37,.44,.60),FVector(.22,.20,.28),FVector(.12,.12,.56),FVector(.12,.12,.56),FVector(.17,.17,.70),FVector(.17,.17,.70),FVector(.28,.16,.11),FVector(.28,.16,.11),FVector(.22,.20,.10),FVector(.39,.45,Index%3==1?.38:.16),FVector(.025,.025,.025),FVector(.025,.025,.025),FVector(.05,.04,.07)};
    for (int i=0;i<Parts.Num();++i)
    {
        Parts[i]->SetStaticMesh(V25Basic(i==1 || i==8 || i>=10?TEXT("Sphere"):TEXT("Cylinder")));
        Parts[i]->SetRelativeLocation(Locations[i]);Parts[i]->SetRelativeScale3D(Scales[i]);
        Parts[i]->SetMaterial(0,i==1||i==12?Skin:i==4||i==5?Trousers:(i>=6&&i<=8)||i==10||i==11?Shoes:Cloth);
    }
}
void AVillageResident::Tick(float Delta)
{
    Super::Tick(Delta);const float Speed=GetVelocity().Size2D();GaitTime+=Delta*Speed*.065f;
    const float Swing=FMath::Sin(GaitTime)*FMath::Min(22.f,Speed*.15f);
    Parts[2]->SetRelativeRotation(FRotator(Swing,0,0));Parts[3]->SetRelativeRotation(FRotator(-Swing,0,0));
    Parts[4]->SetRelativeRotation(FRotator(-Swing*.65f,0,0));Parts[5]->SetRelativeRotation(FRotator(Swing*.65f,0,0));
    if (auto* Player=UGameplayStatics::GetPlayerPawn(this,0))
    {
        Label->SetVisibility(FVector::DistSquared(Player->GetActorLocation(),GetActorLocation())<1800.f*1800.f);
        Label->SetWorldRotation((Player->GetActorLocation()-Label->GetComponentLocation()).Rotation());
    }
}

AVillageLifeDirector::AVillageLifeDirector()
{
    PrimaryActorTick.bCanEverTick=true;RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("LifeRoot"));
    Tractor=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TractorBody"));Tractor->SetupAttachment(RootComponent);
    Tractor->SetCollisionProfileName(TEXT("BlockAllDynamic"));
}
bool AVillageLifeDirector::Enabled() { return FParse::Param(FCommandLine::Get(),TEXT("VillageV25")); }
AVillageLifeDirector* AVillageLifeDirector::Find(UWorld* World)
{ for (TActorIterator<AVillageLifeDirector> It(World);It;++It) return *It;return nullptr; }
void AVillageLifeDirector::BeginPlay()
{
    Super::BeginPlay();StartedAt=LastTickAt=FPlatformTime::Seconds();
    bLearned=FParse::Param(FCommandLine::Get(),TEXT("V25Learned"));bMissingModel=FParse::Param(FCommandLine::Get(),TEXT("V25MissingModel"));
    bCheck=FParse::Param(FCommandLine::Get(),TEXT("V25Check"));bNoSave=bCheck||FParse::Param(FCommandLine::Get(),TEXT("V25NoSave"));
    FParse::Value(FCommandLine::Get(),TEXT("V25Seconds="),CheckSeconds);CheckSeconds=FMath::Clamp(CheckSeconds,30.,7200.);
    FParse::Value(FCommandLine::Get(),TEXT("V25Run="),CheckId);
    for (TCHAR C:CheckId) if (!FChar::IsAlnum(C)&&C!='_'&&C!='-') { CheckId=TEXT("local");break; }
    SavePath=FPaths::ProjectSavedDir()/TEXT("VillageMeshV25/save_v1.json");
    for (TActorIterator<AWeatherManager> It(GetWorld());It;++It) { Weather=*It;Weather->bDayNightCycle=false;Weather->bAutoCycle=false;break; }
    if (!ReadContracts()) { if (bCheck) FinishDiagnostics(false,TEXT("Contracts missing or invalid"));SetActorTickEnabled(false);return; }
    if (!bNoSave)
    {
        FString Text;TSharedPtr<FJsonObject> State;
        if (IFileManager::Get().FileSize(*SavePath)<=1024*1024&&FFileHelper::LoadFileToString(Text,*SavePath)&&FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),State)) RestoreState(State);
    }
    BuildFarmAndRoads();
    for (int i=0;i<People.Num();++i) SpawnResident(People[i],i);
    Policy.Load(bMissingModel);
    UE_LOG(LogTemp,Display,TEXT("V25_START residents=%d plots=%d policy=%s error=%g"),People.Num(),Parcels.Num(),*Policy.Status,Policy.ParityError);
}

bool AVillageLifeDirector::ReadContracts()
{
    const auto Personas=ReadJSON(TEXT("personas.json")),Schedules=ReadJSON(TEXT("schedules.json")),Navigation=ReadJSON(TEXT("navigation.json")),Wardrobe=ReadJSON(TEXT("outfits.json")),Farms=ReadJSON(TEXT("parcels.geojson"));
    if (!Personas||!Schedules||!Navigation||!Wardrobe||!Farms) return false;
    for (const auto& Value:Navigation->GetArrayField(TEXT("nodes"))) { auto O=Value->AsObject();Nodes.Add(O->GetStringField(TEXT("id")),VectorJSON(O->GetArrayField(TEXT("position_cm")))); }
    for (const auto& Value:Navigation->GetArrayField(TEXT("edges"))) { auto E=Value->AsArray();FString A=E[0]->AsString(),B=E[1]->AsString();if (!Nodes.Contains(A)||!Nodes.Contains(B))return false;Edges.FindOrAdd(A).Add(B);Edges.FindOrAdd(B).Add(A); }
    TSet<FString> Ids;
    for (const auto& Value:Personas->GetArrayField(TEXT("people")))
    {
        auto O=Value->AsObject();FV25Person P;P.Id=O->GetStringField(TEXT("id"));P.Name=O->GetStringField(TEXT("name"));P.Role=O->GetStringField(TEXT("role"));
        P.Home=O->GetStringField(TEXT("home_node"));P.Work=O->GetStringField(TEXT("work_node"));P.Shelter=O->GetStringField(TEXT("shelter_node"));P.Outfit=O->GetStringField(TEXT("outfit_id"));
        O->TryGetStringField(TEXT("assigned_plot"),P.Plot);P.Talkativeness=O->GetObjectField(TEXT("preferences"))->GetNumberField(TEXT("talkativeness"));
        for (const auto& Cap:O->GetArrayField(TEXT("capabilities"))) P.Capabilities.Add(Cap->AsString());
        if (Ids.Contains(P.Id)||!Nodes.Contains(P.Home)||!Nodes.Contains(P.Work)||!Nodes.Contains(P.Shelter))return false;
        Ids.Add(P.Id);P.CurrentNode=P.Home;P.Target=P.Home;P.Position=Nodes[P.Home];
        for (const auto& Row:Schedules->GetArrayField(TEXT("schedules")))
            if (Row->AsObject()->GetStringField(TEXT("npc_id"))==P.Id)
            { auto Window=Row->AsObject()->GetArrayField(TEXT("windows"))[0]->AsObject();P.StartHour=Window->GetNumberField(TEXT("start_hour"));P.EndHour=Window->GetNumberField(TEXT("end_hour")); }
        for (const auto& Row:Wardrobe->GetArrayField(TEXT("outfits")))
            if (Row->AsObject()->GetStringField(TEXT("id"))==P.Outfit)
            { const auto& C=Row->AsObject()->GetArrayField(TEXT("color"));P.Color=FLinearColor(C[0]->AsNumber(),C[1]->AsNumber(),C[2]->AsNumber()); }
        People.Add(P);
    }
    for (const auto& V:Farms->GetArrayField(TEXT("features"))) Parcels.Add(V->AsObject()->GetObjectField(TEXT("properties")));
    FString Text;TArray<FString> Rows;
    if (FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("V25/Data/punjabi_lines.jsonl"))))
    { Text.ParseIntoArrayLines(Rows);for (const FString& Row:Rows) { TSharedPtr<FJsonObject> O;if(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Row),O))Lines.Add(O->GetStringField(TEXT("intent")),O); } }
    const auto Fixture=ReadJSON(TEXT("policy_parity.json"));bContractParity=Fixture.IsValid();
    if(Fixture)for(const auto& Row:Fixture->GetArrayField(TEXT("vectors")))
    {
        auto O=Row->AsObject();TArray<float> X;for(const auto& V:O->GetArrayField(TEXT("input")))X.Add(V->AsNumber());
        if(X.Num()!=64){bContractParity=false;break;}TArray<bool> Valid;Mask(X,Valid);const auto& Expected=O->GetArrayField(TEXT("valid_mask"));
        if(Expected.Num()!=48){bContractParity=false;break;}
        for(int i=0;i<48;++i)if(Valid[i]!=Expected[i]->AsBool())
        {bContractParity=false;UE_LOG(LogTemp,Error,TEXT("V25_MASK_PARITY action=%d cpp=%d python=%d"),i,Valid[i],Expected[i]->AsBool());}
        const int Actual=Baseline(X,Valid),ExpectedAction=O->GetIntegerField(TEXT("baseline_action"));
        if(Actual!=ExpectedAction){bContractParity=false;UE_LOG(LogTemp,Error,TEXT("V25_BASELINE_PARITY cpp=%d python=%d"),Actual,ExpectedAction);}
    }
    return People.Num()==8 && Parcels.Num()==4 && bContractParity;
}
void AVillageLifeDirector::SpawnResident(FV25Person& P,int32 Index)
{
    if (P.Actor.IsValid()) return;
    FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
    auto* Actor=GetWorld()->SpawnActor<AVillageResident>(P.Position,FRotator::ZeroRotator,Params);
    if (!Actor) return;
    Actor->Identity=P.Id;Actor->Label->SetText(FText::FromString(P.Name));Actor->Dress(FCString::Atoi(*P.Outfit.Right(2)),P.Color);P.Actor=Actor;P.bActive=true;
}
FString AVillageLifeDirector::ClosestNode(FVector P) const
{
    FString Best;double Distance=DBL_MAX;
    for (const auto& Pair:Nodes) { const double D=FVector::DistSquared2D(P,Pair.Value);if(D<Distance){Distance=D;Best=Pair.Key;} }
    return Best;
}
TArray<FString> AVillageLifeDirector::FindPath(const FString& From,const FString& To) const
{
    TArray<FString> Queue{From};TMap<FString,FString> Previous;Previous.Add(From,TEXT(""));
    for(int i=0;i<Queue.Num();++i)
    {
        if(Queue[i]==To)break;
        if(const auto* Neighbors=Edges.Find(Queue[i]))for(const auto& N:*Neighbors)if(!Previous.Contains(N)){Previous.Add(N,Queue[i]);Queue.Add(N);}
    }
    TArray<FString> Path;if(!Previous.Contains(To))return Path;
    FString At=To;while(At!=From){Path.Insert(At,0);At=Previous[At];}return Path;
}
void AVillageLifeDirector::SetDestination(FV25Person& P,const FString& Node)
{
    if(!Nodes.Contains(Node))return;
    if(P.Target==Node&&!P.Path.IsEmpty())return;
    if(P.Path.IsEmpty()&&P.CurrentNode==Node&&FVector::Dist2D(P.Position,Nodes[Node])<(Node==P.Shelter?450:130))return;
    // Rejoin the last reached graph node instead of jumping to a geometrically
    // nearby branch across a wall/field when rain interrupts a long segment.
    P.Target=Node;P.Path=FindPath(P.CurrentNode,Node);
    if(FVector::Dist2D(P.Position,Nodes[P.CurrentNode])>130)P.Path.Insert(P.CurrentNode,0);
    if(P.Path.IsEmpty()&&FVector::Dist2D(P.Position,Nodes[Node])>70)P.Path.Add(Node);
}
bool AVillageLifeDirector::Reserve(const FString& Slot,const FString& Identity)
{ if(const auto* Existing=Reservations.Find(Slot))if(*Existing!=Identity)return false;Reservations.Add(Slot,Identity);return true; }
void AVillageLifeDirector::Release(const FString& Identity)
{ for(auto It=Reservations.CreateIterator();It;++It)if(It.Value()==Identity)It.RemoveCurrent(); }

TArray<float> AVillageLifeDirector::Features(const FV25Person& P) const
{
    TArray<float> X;X.Init(0,64);X[0]=Hour/24;X[1]=Hour>6&&Hour<18;X[2]=Weather&&Weather->EnvironmentState.RainfallMmPerHour>.1f;
    X[3]=Weather?Weather->EnvironmentState.Wetness:0;X[4]=Weather?FMath::Clamp(Weather->EnvironmentState.WindMetersPerSecond.Size()/20.f,0.f,1.f):0;
    X[6]=.8f;X[8]=P.Fatigue;X[16]=Hour>=P.StartHour&&Hour<P.EndHour;X[17]=P.TaskProgress;X[18]=1;X[19]=1;
    X[20]=Age<P.ConversationUntil;X[21]=Age<P.CommitmentUntil;X[24]=Nodes.Contains(P.Shelter);X[25]=1;X[26]=1;X[27]=Age<P.ConversationUntil;
    const auto* PassageOwner=Reservations.Find(TEXT("farm_passage"));
    X[28]=PassageOwner&&*PassageOwner!=P.Id&&(!P.Path.IsEmpty()&&(P.Path[0].StartsWith(TEXT("farm"))||P.CurrentNode.StartsWith(TEXT("farm"))));
    X[29]=1;X[30]=Hour>=8.15f&&Hour<16.9f;X[31]=Nodes.Contains(P.Work);X[32]=FVector::Dist2D(P.Position,Nodes[P.Work])<130;
    X[33]=FVector::Dist2D(P.Position,Nodes[P.Home])<130;X[34]=Weather&&Weather->IsShelteredAt(P.Position);
    X[35]=FMath::Clamp(FVector::Dist2D(P.Position,Nodes[P.Work])/30000.,0.,1.);X[36]=P.StuckSeconds>8;X[37]=FMath::Clamp(FVector::Dist2D(P.Position,Nodes[P.Home])/30000.,0.,1.);
    X[38]=FVector::Dist2D(P.Position,Tractor->GetComponentLocation())<380;X[39]=1;X[40]=FMath::Min(P.Visits/20.f,1.f);
    X[46]=FMath::Min(P.CompletedTasks/20.f,1.f);X[48]=1;X[49]=X[3];X[50]=.8f;X[51]=!P.Plot.IsEmpty();X[52]=1;
    const auto* WorkOwner=Reservations.Find(TEXT("job_")+P.Work);X[53]=!WorkOwner||*WorkOwner==P.Id;X[54]=P.Capabilities.Contains(TEXT("drive"));X[55]=1;
    const TCHAR* Capabilities[]={TEXT("inspect"),TEXT("stock"),TEXT("drive"),TEXT("commute"),TEXT("carry"),TEXT("visit")};
    for(int i=0;i<6;++i)X[56+i]=P.Capabilities.Contains(Capabilities[i]);X[62]=P.Talkativeness;X[63]=.4f;return X;
}
void AVillageLifeDirector::Mask(const TArray<float>& X,TArray<bool>& M) const
{
    M.Init(false,48);M[0]=M[8]=true;M[1]=X[16]>.5&&X[48]>.5&&X[25]>.5&&X[31]>.5&&X[39]>.5&&X[32]<.5;
    M[2]=X[16]>.5&&X[48]>.5&&X[25]>.5&&X[32]>.5&&X[53]>.5;M[3]=X[26]>.5&&X[5]<.5;
    M[4]=X[24]>.5&&X[19]>.5;M[5]=X[27]>.5&&X[20]<.5&&X[5]<.5;M[6]=X[33]<.5&&X[39]>.5;M[7]=X[28]>.5||X[36]>.5||X[38]>.5;
    if(X[28]>.5||X[36]>.5)M[1]=M[2]=M[6]=false;if(X[2]>.5)M[1]=M[2]=false;
}
int32 AVillageLifeDirector::Baseline(const TArray<float>& X,const TArray<bool>& M) const
{
    TArray<int32> Order;if(X[28]>.5||X[36]>.5)Order.Add(7);if(X[2]>.5)Order.Add(4);
    if(X[16]<.5){Order.Add(6);Order.Add(0);}if(X[8]>.8)Order.Add(3);Order.Append({2,1,0,8});
    for(int A:Order)if(M[A])return A;return 0;
}
void AVillageLifeDirector::Decide(FV25Person& P,int32 Index,const float* Logits)
{
    auto X=Features(P);TArray<bool> Valid;Mask(X,Valid);int32 Action=Baseline(X,Valid);
    // Rain, occupied passages and existing commitments are execution constraints.
    if(Logits&&X[2]<.5&&X[28]<.5&&X[36]<.5)
    {
        bool Finite=true;for(int i=0;i<48;++i)Finite&=FMath::IsFinite(Logits[i]);
        if(Finite)
        {
            float Best=-FLT_MAX,Second=-FLT_MAX;int Candidate=Action;
            for(int i=0;i<48;++i)if(Valid[i]){if(Logits[i]>Best){Second=Best;Best=Logits[i];Candidate=i;}else Second=FMath::Max(Second,Logits[i]);}
            if(Best-Second>=.5f)Action=Candidate;
        }
        else ++InvalidRejected;
    }
    if(!Valid[Action]){++InvalidRejected;Action=Baseline(X,Valid);}
    if(Age<P.CommitmentUntil&&Valid[P.Action]&&X[2]<.5&&X[28]<.5&&P.Action!=0)return;
    if(P.Action!=Action){P.RecentEvents.Add(FString::Printf(TEXT("%.2f:%s"),Hour,ActionNames[Action]));if(P.RecentEvents.Num()>8)P.RecentEvents.RemoveAt(0);}
    // Preserve a moving resident's passage reservation across decision ticks.
    // Releasing it every tick lets a following resident claim the corridor and
    // immobilize the person who is already inside it.
    if(Action!=P.Action||Action==0||Action==3||Action==5||Action==7||Action==8)Release(P.Id);
    P.Action=Action;P.CommitmentUntil=Age+(Action==2?8:2);
    if(Action==1)SetDestination(P,P.Work);
    else if(Action==4)SetDestination(P,P.Shelter);
    else if(Action==6)SetDestination(P,P.Home);
    else if(Action==2)
    {
        if(!Reserve(TEXT("job_")+P.Work,P.Id)){P.Action=7;return;}
        // Work becomes valid at 130 cm, before the path follower's 65 cm
        // waypoint threshold. Record that arrival before clearing the path.
        P.Path.Empty();P.CurrentNode=P.Work;P.Target=P.Work;
    }
    else if(Action==0||Action==3||Action==5||Action==7)
    {
        P.Path.Empty();
        if(Action==0&&X[33]>.5f){P.CurrentNode=P.Home;P.Target=P.Home;}
    }
    else if(Action==8)SetDestination(P,P.Target);
}

void AVillageLifeDirector::BuildFarmAndRoads()
{
    auto MakeGroup=[&](const TCHAR* Name,UMaterialInterface* Mat,bool Collision)
    {
        auto* C=NewObject<UInstancedStaticMeshComponent>(this);C->SetupAttachment(RootComponent);C->SetStaticMesh(V25Basic(Name));C->SetMaterial(0,Mat);
        C->SetCollisionEnabled(Collision?ECollisionEnabled::QueryAndPhysics:ECollisionEnabled::NoCollision);C->SetCollisionResponseToAllChannels(ECR_Block);C->RegisterComponent();SceneParts.Add(C);return C;
    };
    auto Add=[](UInstancedStaticMeshComponent* C,FVector P,FVector Size,float Yaw=0){C->AddInstance(FTransform(FRotator(0,Yaw,0),P,Size/100),true);};
    auto* Soil=MakeGroup(TEXT("Cube"),Surface(TEXT("M_V2RoadsideSoil")),false);
    auto* Bund=MakeGroup(TEXT("Cube"),Colored(this,FLinearColor(.25f,.18f,.095f)),true);
    auto* Rice=MakeGroup(TEXT("Cylinder"),Colored(this,FLinearColor(.46f,.46f,.12f)),false);
    auto* Residue=MakeGroup(TEXT("Cube"),Colored(this,FLinearColor(.39f,.29f,.11f)),false);
    auto* Fodder=MakeGroup(TEXT("Cylinder"),Colored(this,FLinearColor(.15f,.25f,.075f)),false);
    FRandomStream Random(3062);
    for(int i=0;i<Parcels.Num();++i)
    {
        auto Ring=Parcels[i]->GetArrayField(TEXT("polygon_cm"));const float X=Ring[0]->AsArray()[0]->AsNumber(),Y=Ring[0]->AsArray()[1]->AsNumber();
        Add(Soil,FVector(X+525,Y-750,1),FVector(1050,1500,2));
        Add(Bund,FVector(X+525,Y,6),FVector(1050,20,12));Add(Bund,FVector(X+525,Y-1500,6),FVector(1050,20,12));
        Add(Bund,FVector(X,Y-750,6),FVector(20,1500,12));Add(Bund,FVector(X+1050,Y-750,6),FVector(20,1500,12));
        for(int Row=0;Row<32;++Row)for(int Col=0;Col<21;++Col)
        {
            const FVector P(X+40+Col*46+Random.FRandRange(-6,6),Y-45-Row*44,0);
            if(i==0)Add(Rice,P+FVector(0,0,36),FVector(6,6,72),Random.FRandRange(0,360));
            if(i==1)Add(Residue,P+FVector(0,0,3),FVector(30,5,4),Random.FRandRange(-30,30));
            if(i==3)Add(Fodder,P+FVector(0,0,24),FVector(12,12,48));
        }
    }
    const FString RoadNodes[]={TEXT("lane_14"),TEXT("farm_gate"),TEXT("farm_south")};
    for(int i=0;i<2;++i)
    {
        FVector A=Nodes[RoadNodes[i]],B=Nodes[RoadNodes[i+1]],D=B-A;const float Angle=D.Rotation().Yaw;
        FVector Center=(A+B)*.5;Center.Z=3;Add(Soil,Center,FVector(D.Size2D(),280,4),Angle);
        const FVector Side=FVector(-D.Y,D.X,0).GetSafeNormal();
        for(float Offset:{-65.f,65.f})Add(Residue,Center+Side*Offset+FVector(0,0,.6),FVector(D.Size2D(),32,1),Angle);
    }
    // Inferred communal shade structure; this roof is actually traced for rain shelter.
    auto* Shelter=MakeGroup(TEXT("Cube"),Surface(TEXT("M_V2_concrete")),true);
    Add(Shelter,FVector(2600,-1300,255),FVector(850,650,18));
    for(float X:{2200.f,3000.f})for(float Y:{-1590.f,-1010.f})Add(Shelter,FVector(X,Y,125),FVector(18,18,250));
    Tractor->SetStaticMesh(V25Basic(TEXT("Cube")));Tractor->SetMaterial(0,Colored(this,FLinearColor(.065f,.22f,.31f)));
    Tractor->SetWorldLocation(Nodes[TEXT("farm_south")]+FVector(300,0,-5));Tractor->SetWorldScale3D(FVector(2.5,1.6,1.0));TractorNode=2;TractorDirection=-1;
    for(int i=0;i<4;++i)
    {
        auto* Wheel=NewObject<UStaticMeshComponent>(this);Wheel->SetupAttachment(Tractor);Wheel->SetStaticMesh(V25Basic(TEXT("Cylinder")));
        Wheel->SetMaterial(0,Colored(this,FLinearColor(.025f,.025f,.025f)));Wheel->SetCollisionEnabled(ECollisionEnabled::NoCollision);Wheel->RegisterComponent();
        Wheel->SetAbsolute(false,false,true);Wheel->SetRelativeLocation(FVector(i<2?-35:35,i%2?-55:55,-35));Wheel->SetRelativeRotation(FRotator(0,0,90));
        Wheel->SetWorldScale3D(FVector(i<2?.95:.65,i<2?.95:.65,.28));TractorParts.Add(Wheel);
    }
}

void AVillageLifeDirector::UpdateTractor(float Delta)
{
    const FString N[]={TEXT("lane_14"),TEXT("farm_gate"),TEXT("farm_south")};
    if(TractorWait>0){TractorWait-=Delta;return;}
    // Operator has to reach the interaction point before the vehicle can move.
    if(People.Num()<3)return;
    if(!bTractorAuthorized)
    {
        if(People[2].CompletedTasks==0||FVector::Dist2D(People[2].Position,Nodes[TEXT("vehicle_stop")])>200||
            (Weather&&Weather->EnvironmentState.RainfallMmPerHour>.1f)){Release(TEXT("tractor"));return;}
        bTractorAuthorized=true;
    }
    if(!Reserve(TEXT("farm_passage"),TEXT("tractor")))return;
    FVector Target=Nodes[N[TractorNode]]+FVector(0,0,-5),Position=Tractor->GetComponentLocation(),D=Target-Position;D.Z=0;
    if(D.Size2D()<25)
    {
        TractorNode+=TractorDirection;
        if(TractorNode>2||TractorNode<0){TractorDirection*=-1;TractorNode=FMath::Clamp(TractorNode,0,2);Release(TEXT("tractor"));TractorWait=12;bTractorAuthorized=false;++CompletedLegs;}
        return;
    }
    for(int i=0;i<People.Num();++i)if(i!=2&&People[i].Actor.IsValid()&&FVector::Dist2D(People[i].Position,Position)<260)return;
    const float Speed=110*(Weather&&Weather->EnvironmentState.Wetness>.4?.5:1.);
    FHitResult Hit;Tractor->SetWorldLocation(Position+D.GetSafeNormal()*FMath::Min(Speed*Delta,D.Size2D()),true,&Hit);
    Tractor->SetWorldRotation(FMath::RInterpTo(Tractor->GetComponentRotation(),D.Rotation(),Delta,2));
    for(const auto& Wheel:TractorParts)Wheel->AddLocalRotation(FRotator(0,0,Speed*Delta));
}

void AVillageLifeDirector::Tick(float Delta)
{
    Super::Tick(Delta);const double TickStart=FPlatformTime::Seconds();Age+=Delta;
    const double Now=FPlatformTime::Seconds();if(bCheck&&Age>20)FrameMs.Add((Now-LastTickAt)*1000);LastTickAt=Now;
    if(bFinished||People.Num()!=8)return;
    Hour=FMath::Fmod(Hour+Delta*(bCheck?.0125f:5.f/3600.f),24.f);
    if(Weather)Weather->TimeOfDayHours=Hour;
    const bool Rain=Weather&&Weather->EnvironmentState.RainfallMmPerHour>.1f;
    for(auto& Plot:Parcels)Plot->SetStringField(TEXT("soil_visual_state"),Weather&&Weather->EnvironmentState.Wetness>.5f?TEXT("wet"):TEXT("dry"));
    if(Rain!=bLastRain){++Generation;LatestLogits.Empty();bLastRain=Rain;for(auto& P:People)P.CommitmentUntil=0;}
    FV25InferenceResult Result;
    if(Policy.Poll(Result))
    {
        if(bCheck){InferenceMs.Add((Result.FinishedAt-Result.StartedAt)*1000);QueueMs.Add((Result.StartedAt-Result.RequestedAt)*1000);}++ModelCalls;
        if(Result.bSuccess&&Result.Generation==Generation&&Now-Result.RequestedAt<1)
        { LatestLogits=MoveTemp(Result.Logits);LatestResultAt=Now; }
        else {++StaleResults;LatestLogits.Empty();}
    }
    DecisionElapsed+=Delta;
    if(DecisionElapsed>=.4f)
    {
        DecisionElapsed=0;TArray<float> Snapshot;
        for(int i=0;i<People.Num();++i)
        {
            auto& P=People[i];Snapshot.Append(Features(P));
            const float* Scores=bLearned&&LatestLogits.Num()==384&&Now-LatestResultAt<1?LatestLogits.GetData()+i*48:nullptr;
            Decide(P,i,Scores);
        }
        Policy.Submit(Snapshot,Generation);
    }
    const auto* Player=UGameplayStatics::GetPlayerPawn(this,0);
    for(int i=0;i<People.Num();++i)
    {
        auto& P=People[i];const bool Near=!Player||FVector::Dist2D(Player->GetActorLocation(),P.Position)<22000;
        if(!Near&&P.Actor.IsValid()) { P.Position=P.Actor->GetActorLocation();Release(P.Id);P.Actor->Destroy();P.Actor.Reset();P.bActive=false; }
        if(Near&&!P.Actor.IsValid()) { SpawnResident(P,i);++StreamRestores; }
        if(!P.Actor.IsValid())continue;
        auto* Actor=P.Actor.Get();const FVector Before=P.Position;P.Position=Actor->GetActorLocation();
        if(!P.Path.IsEmpty()&&FVector::Dist2D(Before,P.Position)<Delta*5)P.StuckSeconds+=Delta;else P.StuckSeconds=0;
        if(P.StuckSeconds>10){Release(P.Id);P.Path.Empty();P.Action=8;P.CommitmentUntil=Age+2;P.StuckSeconds=0;}
        if(Age<P.ConversationUntil){Actor->GetCharacterMovement()->StopMovementImmediately();if(Player)Actor->SetActorRotation((Player->GetActorLocation()-P.Position).Rotation());continue;}
        if(Player)
        {
            const FVector Heading=Player->GetLastMovementInputVector().GetSafeNormal2D();
            const FVector Separation=P.Position-Player->GetActorLocation();
            const FVector Left(-Heading.Y,Heading.X,0);const float Side=FVector::DotProduct(Separation,Left);
            if(!Heading.IsNearlyZero()&&Separation.Size2D()<220&&FVector::DotProduct(Separation,Heading)>0&&FMath::Abs(Side)<110)
            {
                // A standing task must not turn a street waypoint into a wall.
                // Yield physically to the nearer side; keep capsule collision.
                Actor->AddMovementInput(Left*(Side<0?-1.f:1.f),1);
                Release(P.Id);P.Action=7;P.CommitmentUntil=0;continue;
            }
        }
        if(!P.Path.IsEmpty())
        {
            const FString Next=P.Path[0];FVector Target=Nodes[Next];
            if(Next.StartsWith(TEXT("lane"))&&P.CurrentNode!=Next)
            {
                const FVector Heading=(Nodes[Next]-Nodes[P.CurrentNode]).GetSafeNormal2D();
                Target+=FVector(-Heading.Y,Heading.X,0)*80; // left-side pedestrian travel
            }
            if(Next==P.Shelter){Target.X+=(i%4-1.5f)*120;Target.Y+=(i/4-.5f)*150;}
            FVector Direction=Target-P.Position;Direction.Z=0;
            if(Direction.Size2D()<65)
            { P.CurrentNode=Next;P.Path.RemoveAt(0);if(P.Path.IsEmpty()){Release(P.Id);++P.Visits;} }
            else
            {
                const bool OnPassage=Next==TEXT("farm_gate")||Next==TEXT("farm_south")||P.CurrentNode==TEXT("farm_gate")||P.CurrentNode==TEXT("farm_south");
                if(OnPassage&&!Reserve(TEXT("farm_passage"),P.Id)){Actor->GetCharacterMovement()->StopMovementImmediately();continue;}
                FVector Heading=Direction.GetSafeNormal2D();
                // Yield left around another capsule rather than making both
                // participants wait forever at a graph junction or shop stop.
                for(const auto& Other:People)
                    if(Other.Id!=P.Id&&Other.Actor.IsValid())
                    {
                        const FVector Separation=Other.Position-P.Position;const float Distance=Separation.Size2D();
                        if(Distance<200&&FVector::DotProduct(Separation.GetSafeNormal2D(),Heading)>.1f)
                        {Heading=(Heading+FVector(-Heading.Y,Heading.X,0)*(2.f*(1.f-Distance/240.f))).GetSafeNormal2D();break;}
                    }
                Actor->AddMovementInput(Heading,1);
            }
        }
        else if(P.Action==2)
        {
            P.TaskProgress=FMath::Min(1.f,P.TaskProgress+Delta/12);P.Fatigue=FMath::Min(1.f,P.Fatigue+Delta*.0015f);
            if(P.TaskProgress>=1)
            {
                ++P.CompletedTasks;P.TaskProgress=0;Release(P.Id);P.CommitmentUntil=0;
                for(auto& Plot:Parcels)if(Plot->GetStringField(TEXT("plot_id"))==P.Plot)
                {Plot->SetStringField(TEXT("irrigation_state"),TEXT("checked"));Plot->SetNumberField(TEXT("last_inspection_hour"),Hour);}
            }
        }
        else if(P.Action==3)P.Fatigue=FMath::Max(.1f,P.Fatigue-Delta*.03f);
    }
    UpdateTractor(Delta);SaveElapsed+=Delta;if(SaveElapsed>30){SaveElapsed=0;SaveState();}
    if(bCheck)Diagnostics(Delta);
    if(bCheck)GameThreadMs.Add((FPlatformTime::Seconds()-TickStart)*1000);
    if(GameThreadMs.Num()>200000)GameThreadMs.RemoveAt(0,10000);
}

TSharedPtr<FJsonObject> AVillageLifeDirector::SerializeState() const
{
    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("version"),1);Root->SetStringField(TEXT("scene_date"),TEXT("2026-10-23"));Root->SetNumberField(TEXT("hour"),Hour);
    if(Weather)Root->SetNumberField(TEXT("weather_preset"),int(Weather->GetCurrentWeather()));
    TArray<TSharedPtr<FJsonValue>> Residents;
    for(const auto& P:People)
    {
        auto O=MakeShared<FJsonObject>();O->SetStringField(TEXT("id"),P.Id);O->SetStringField(TEXT("outfit"),P.Outfit);O->SetStringField(TEXT("target"),P.Target);
        O->SetArrayField(TEXT("position"),JsonVector(P.Actor.IsValid()?P.Actor->GetActorLocation():P.Position));O->SetNumberField(TEXT("fatigue"),P.Fatigue);
        O->SetNumberField(TEXT("completed_tasks"),P.CompletedTasks);O->SetNumberField(TEXT("visits"),P.Visits);O->SetNumberField(TEXT("task_progress"),P.TaskProgress);
        O->SetNumberField(TEXT("action"),P.Action);TArray<TSharedPtr<FJsonValue>> Events;for(const auto& E:P.RecentEvents)Events.Add(MakeShared<FJsonValueString>(E));O->SetArrayField(TEXT("recent_events"),Events);
        O->SetStringField(TEXT("current_node"),P.CurrentNode);O->SetNumberField(TEXT("stuck_seconds"),P.StuckSeconds);
        TArray<TSharedPtr<FJsonValue>> Path;for(const auto& Node:P.Path)Path.Add(MakeShared<FJsonValueString>(Node));O->SetArrayField(TEXT("remaining_path"),Path);
        Residents.Add(MakeShared<FJsonValueObject>(O));
    }
    Root->SetArrayField(TEXT("residents"),Residents);TArray<TSharedPtr<FJsonValue>> Plots;
    for(const auto& P:Parcels)Plots.Add(MakeShared<FJsonValueObject>(P));Root->SetArrayField(TEXT("plots"),Plots);
    auto Doors=MakeShared<FJsonObject>();for(const auto& Pair:GetWorld()->GetSubsystem<UVillageDoorState>()->OpenDoors)Doors->SetBoolField(Pair.Key,Pair.Value);Root->SetObjectField(TEXT("doors"),Doors);
    return Root;
}
bool AVillageLifeDirector::RestoreState(const TSharedPtr<FJsonObject>& Root)
{
    double Version=0,LoadedHour=0;FString Date;
    if(!Root||!Root->TryGetNumberField(TEXT("version"),Version)||Version!=1||!Root->TryGetStringField(TEXT("scene_date"),Date)||Date!=TEXT("2026-10-23")||!Root->TryGetNumberField(TEXT("hour"),LoadedHour)||!FMath::IsFinite(LoadedHour)||LoadedHour<0||LoadedHour>=24)return false;
    const TArray<TSharedPtr<FJsonValue>>* Residents=nullptr;
    if(!Root->TryGetArrayField(TEXT("residents"),Residents)||Residents->Num()!=People.Num())return false;
    auto Restored=People;TSet<FString> Seen;
    for(const auto& Value:*Residents)
    {
        const auto O=Value->AsObject();FString Id,Target,Outfit,CurrentNode;double Fatigue=0,Tasks=0,Visits=0,Progress=0,Action=0;
        const TArray<TSharedPtr<FJsonValue>>* Position=nullptr;
        if(!O||!O->TryGetStringField(TEXT("id"),Id)||Seen.Contains(Id)||!O->TryGetStringField(TEXT("target"),Target)||!Nodes.Contains(Target)||!O->TryGetStringField(TEXT("outfit"),Outfit)||!O->TryGetArrayField(TEXT("position"),Position)||Position->Num()!=3||
            !O->TryGetStringField(TEXT("current_node"),CurrentNode)||!Nodes.Contains(CurrentNode)||!O->TryGetNumberField(TEXT("fatigue"),Fatigue)||!O->TryGetNumberField(TEXT("completed_tasks"),Tasks)||!O->TryGetNumberField(TEXT("visits"),Visits)||!O->TryGetNumberField(TEXT("task_progress"),Progress)||!O->TryGetNumberField(TEXT("action"),Action))return false;
        auto* P=Restored.FindByPredicate([&](const FV25Person& Person){return Person.Id==Id;});if(!P||P->Outfit!=Outfit)return false;
        FVector V=VectorJSON(*Position);
        if(V.ContainsNaN()||V.GetAbsMax()>70000||V.Z<40||V.Z>1000||!FMath::IsFinite(Fatigue)||Fatigue<0||Fatigue>1||
            !FMath::IsFinite(Tasks)||!FMath::IsFinite(Visits)||!FMath::IsFinite(Progress)||!FMath::IsFinite(Action)||
            Tasks<0||Tasks>1000000||Visits<0||Visits>1000000||Progress<0||Progress>1||Action<0||Action>8||Action!=FMath::FloorToDouble(Action))return false;
        P->Position=V;P->Fatigue=Fatigue;P->CompletedTasks=Tasks;P->Visits=Visits;P->TaskProgress=Progress;P->Action=Action;P->Target=Target;P->CurrentNode=CurrentNode;P->Path=FindPath(CurrentNode,Target);P->CommitmentUntil=0;
        if(FVector::Dist2D(V,Nodes[CurrentNode])>130)P->Path.Insert(CurrentNode,0);
        const TArray<TSharedPtr<FJsonValue>>* Events=nullptr;P->RecentEvents.Empty();if(O->TryGetArrayField(TEXT("recent_events"),Events))for(int i=FMath::Max(0,Events->Num()-8);i<Events->Num();++i)P->RecentEvents.Add((*Events)[i]->AsString());Seen.Add(Id);
    }
    People=MoveTemp(Restored);Hour=LoadedHour;Reservations.Empty();
    double Preset=0;if(Weather&&Root->TryGetNumberField(TEXT("weather_preset"),Preset)&&Preset>=0&&Preset<=3)Weather->SetWeather(static_cast<EVillageWeather>(int(Preset)),.1f);
    const TArray<TSharedPtr<FJsonValue>>* Plots=nullptr;
    if(Root->TryGetArrayField(TEXT("plots"),Plots)&&Plots->Num()==Parcels.Num())
        for(const auto& Value:*Plots)
        {
            const auto O=Value->AsObject();FString Id,State;
            if(O&&O->TryGetStringField(TEXT("plot_id"),Id)&&O->TryGetStringField(TEXT("irrigation_state"),State)&&(State==TEXT("checked")||State==TEXT("check_due")))
                for(auto& Plot:Parcels)if(Plot->GetStringField(TEXT("plot_id"))==Id)Plot->SetStringField(TEXT("irrigation_state"),State);
        }
    const TSharedPtr<FJsonObject>* Doors=nullptr;if(Root->TryGetObjectField(TEXT("doors"),Doors))for(const auto& Pair:(*Doors)->Values)if(Pair.Value->Type==EJson::Boolean)GetWorld()->GetSubsystem<UVillageDoorState>()->OpenDoors.Add(FString(Pair.Key),Pair.Value->AsBool());
    for(TActorIterator<AVillageDoor> It(GetWorld());It;++It)
        if(It->bCanOpen&&It->IsOpen()!=GetWorld()->GetSubsystem<UVillageDoorState>()->OpenDoors.FindRef(It->PersistentId))It->Toggle();
    return true;
}
void AVillageLifeDirector::SaveState() const
{
    if(bNoSave||People.Num()!=8)return;
    FString Text;FJsonSerializer::Serialize(SerializeState().ToSharedRef(),TJsonWriterFactory<>::Create(&Text));
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(SavePath),true);
    const FString Temporary=SavePath+TEXT(".tmp");
    if(FFileHelper::SaveStringToFile(Text,*Temporary,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM))IFileManager::Get().Move(*SavePath,*Temporary,true,true);
}
void AVillageLifeDirector::EndPlay(const EEndPlayReason::Type Reason)
{
    SaveState();Reservations.Empty();
    if(DialogueWidget&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(DialogueWidget.ToSharedRef());DialogueWidget.Reset();
    Super::EndPlay(Reason);
}

void AVillageLifeDirector::Talk()
{
    auto* Player=UGameplayStatics::GetPlayerPawn(this,0);if(!Player)return;FV25Person* Nearest=nullptr;double Best=600;
    for(auto& P:People)if(P.Actor.IsValid()){double D=FVector::Dist2D(P.Position,Player->GetActorLocation());if(D<Best){Best=D;Nearest=&P;}}
    if(!Nearest){ActiveSpeaker.Empty();DialogueText=TEXT("Move within 6 m of a fictional resident to talk.");UpdateDialogueWidget();return;}
    ActiveSpeaker=Nearest->Id;Nearest->ConversationUntil=Age+15;++Nearest->Visits;DialogueChoice(1);
}
void AVillageLifeDirector::DialogueChoice(int32 Choice)
{
    auto* P=People.FindByPredicate([&](const FV25Person& V){return V.Id==ActiveSpeaker;});if(!P)return;
    if(Choice==5){P->ConversationUntil=0;ActiveSpeaker.Empty();if(DialogueWidget&&GetWorld()->GetGameViewport())GetWorld()->GetGameViewport()->RemoveViewportWidgetContent(DialogueWidget.ToSharedRef());DialogueWidget.Reset();return;}
    FString Intent=TEXT("greeting"),Detail;
    if(Choice==2){Intent=Weather&&Weather->EnvironmentState.RainfallMmPerHour>.1?TEXT("rain"):TEXT("unknown");Detail=Weather?FString::Printf(TEXT("\nCurrent scene wetness: %.0f%%"),Weather->EnvironmentState.Wetness*100):TEXT("");}
    if(Choice==3){Intent=TEXT("unknown");Detail=FString::Printf(TEXT("\nCurrent activity: %s | assigned destination: %s\nCompleted activities: %d"),ActionNames[P->Action],*P->Work,P->CompletedTasks);}
    if(Choice==4){const bool Open=Hour>=8.15f&&Hour<16.9f;Intent=Open?TEXT("unknown"):TEXT("shop_closed");Detail=Open?TEXT("\nAuthored shop schedule: open now."):TEXT("\nAuthored shop schedule: closed now.");}
    if(Choice==6)Intent=TEXT("unknown");
    if(const auto* Line=Lines.Find(Intent))
        DialogueText=P->Name+TEXT("  |  FICTIONAL RESIDENT\nDRAFT PUNJABI - local wording and pronunciation review pending\n\n")+(*Line)->GetStringField(TEXT("Gurmukhi_text"))+TEXT("\n")+(*Line)->GetStringField(TEXT("Roman_transliteration"))+TEXT("\n")+(*Line)->GetStringField(TEXT("English_gloss"))+Detail+TEXT("\n\n1 Greet   2 Weather   3 Work   4 Shop   5 Close");
    P->ConversationUntil=Age+15;UpdateDialogueWidget();
}
void AVillageLifeDirector::UpdateDialogueWidget()
{
    auto* Viewport=GetWorld()->GetGameViewport();if(!Viewport)return;
    if(DialogueWidget)Viewport->RemoveViewportWidgetContent(DialogueWidget.ToSharedRef());
    const auto Typeface=MakeShared<FCompositeFont>(FName(TEXT("Regular")),FPaths::ProjectContentDir()/TEXT("V25/Fonts/NotoSansGurmukhi.ttf"),EFontHinting::Default,EFontLoadingPolicy::LazyLoad);
    const FSlateFontInfo Font(Typeface,18);
    DialogueWidget=SNew(SBox).HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(FMargin(20,20,20,85))
        [SNew(SBorder).Padding(18).BorderImage(FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"))).BorderBackgroundColor(FLinearColor(.015f,.02f,.02f,.94f))
        [SNew(STextBlock).Text(FText::FromString(DialogueText)).Font(Font).TextShapingMethod(ETextShapingMethod::FullShaping).ColorAndOpacity(FLinearColor::White).WrapTextAt(760)]];
    Viewport->AddViewportWidgetContent(DialogueWidget.ToSharedRef(),20);
}
void AVillageLifeDirector::VisitFarm()
{
    if(auto* Player=UGameplayStatics::GetPlayerPawn(this,0)){Player->SetActorLocation(FVector(3600,-1100,100));if(Player->GetController())Player->GetController()->SetControlRotation(FRotator(-12,-135,0));}
}
void AVillageLifeDirector::TogglePolicy(){bLearned=!bLearned;++Generation;LatestLogits.Empty();}
FString AVillageLifeDirector::HUDStatus() const
{
    int Active=0,Tasks=0;for(const auto& P:People){Active+=P.Actor.IsValid();Tasks+=P.CompletedTasks;}
    return FString::Printf(TEXT("V2.5 | %02d:%02d | Residents %d/8 | Activities %d\n%s | %s\nT talk | 1-5 choices | F11 farms | F5 policy\nPrototype character art; Punjabi draft; no recorded voices"),int(Hour),int(FMath::Frac(Hour)*60),Active,Tasks,bLearned?TEXT("Experimental learned ranking"):TEXT("Deterministic schedules"),*Policy.Status);
}

void AVillageLifeDirector::Diagnostics(float Delta)
{
    if(People.Num()!=8){FinishDiagnostics(false,TEXT("Resident identity count differs"));return;}
    for(const auto& P:People)if(P.Actor.IsValid()&&(P.Position.ContainsNaN()||P.Position.Z< -100)){FinishDiagnostics(false,TEXT("Resident fell through terrain"));return;}
    for(const auto& P:People)if(P.Action==2&&P.Path.IsEmpty()&&P.CurrentNode!=P.Work){FinishDiagnostics(false,TEXT("Work arrival anchor was not committed"));return;}
    const double Wall=FPlatformTime::Seconds()-StartedAt;
    if(int(Wall/60)>LastProgressMinute)
    {
        LastProgressMinute=int(Wall/60);int Tasks=0;for(const auto& P:People)Tasks+=P.CompletedTasks;
        UE_LOG(LogTemp,Display,TEXT("V25_PROGRESS wall=%.1f tasks=%d tractor_legs=%d batches=%d"),Wall,Tasks,CompletedLegs,ModelCalls);
    }
    if(!bSaveTest&&Wall>25)
    {
        AVillageDoor* CheckedDoor=nullptr;
        for(TActorIterator<AVillageDoor> It(GetWorld());It;++It)if(It->bCanOpen){CheckedDoor=*It;if(!It->IsOpen())It->Toggle();break;}
        auto State=SerializeState();FString Text;FJsonSerializer::Serialize(State.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));
        if(CheckedDoor)CheckedDoor->Toggle();
        TSharedPtr<FJsonObject> Parsed;bSaveTest=FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Parsed)&&RestoreState(Parsed);
        bDoorTest=CheckedDoor&&CheckedDoor->IsOpen();
        if(!bSaveTest){FinishDiagnostics(false,TEXT("Save round-trip failed"));return;}
        auto Broken=MakeShared<FJsonObject>();Broken->SetNumberField(TEXT("version"),999);if(RestoreState(Broken)){FinishDiagnostics(false,TEXT("Invalid save accepted"));return;}
    }
    if(!bStreamTest&&Wall>35)
    {
        auto& P=People[0];P.Position=P.Actor->GetActorLocation();const FVector Before=P.Position;const FString Outfit=P.Outfit;
        Release(P.Id);P.Actor->Destroy();P.Actor.Reset();SpawnResident(P,0);
        bStreamTest=P.Actor.IsValid()&&P.Outfit==Outfit&&FVector::Dist2D(P.Actor->GetActorLocation(),Before)<150;
        if(!bStreamTest){FinishDiagnostics(false,TEXT("Resident unload/restore failed"));return;}++StreamRestores;
    }
    if(Weather)
    {
        const double WeatherPeriod=FParse::Param(FCommandLine::Get(),TEXT("V25Screenshots"))?60.:180.;
        const int Phase=int(Wall/WeatherPeriod)%4;
        const EVillageWeather Preset=Phase==1||Phase==2?EVillageWeather::Rain:EVillageWeather::Clear;
        if(Weather->GetCurrentWeather()!=Preset)Weather->SetWeather(Preset,1);
    }
    if(!FParse::Param(FCommandLine::Get(),TEXT("NullRHI"))&&FParse::Param(FCommandLine::Get(),TEXT("V25Screenshots")))
    {
        auto* Player=UGameplayStatics::GetPlayerPawn(this,0);
        if(CaptureStage==0&&Wall>42&&Player&&People[0].Actor.IsValid())
        {
            const FVector P=People[0].Position;Player->SetActorLocation(P+FVector(350,100,10));
            if(Player->GetController())Player->GetController()->SetControlRotation((P+FVector(0,0,40)-(Player->GetActorLocation()+FVector(0,0,70))).Rotation());
            Talk();CaptureStage=1;
        }
        if(CaptureStage==1&&Wall>46){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("VillageMeshV25/dialogue.png"),true,false);CaptureStage=2;}
        if(CaptureStage==2&&Wall>85){DialogueChoice(5);VisitFarm();CaptureStage=3;}
        if(CaptureStage==3&&Wall>90){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("VillageMeshV25/farms_rain.png"),true,false);CaptureStage=4;}
    }
    if(Wall>CheckSeconds)
    {
        int Tasks=0;for(const auto& P:People)Tasks+=P.CompletedTasks;
        const bool Pass=bSaveTest&&bStreamTest&&bDoorTest&&bContractParity&&(bMissingModel?!Policy.IsReady():Policy.IsReady())&&(bMissingModel||ModelCalls>0)&&Tasks>0;
        FinishDiagnostics(Pass,Pass?TEXT("Bounded runtime checks passed"):TEXT("Missing policy, activity completion or state evidence"));
    }
}
void AVillageLifeDirector::FinishDiagnostics(bool Pass,const FString& Reason)
{
    if(bFinished)return;bFinished=true;
    auto Percentile=[](TArray<double> Values,double P){if(Values.IsEmpty())return 0.;Values.Sort();return Values[FMath::Clamp(FMath::CeilToInt((Values.Num()-1)*P),0,Values.Num()-1)];};
    auto Report=MakeShared<FJsonObject>();Report->SetBoolField(TEXT("passed"),Pass);Report->SetStringField(TEXT("reason"),Reason);
    Report->SetStringField(TEXT("run_id"),CheckId);Report->SetBoolField(TEXT("editor_build"),WITH_EDITOR!=0);Report->SetNumberField(TEXT("wall_seconds"),FPlatformTime::Seconds()-StartedAt);
    Report->SetBoolField(TEXT("rendered"),!FParse::Param(FCommandLine::Get(),TEXT("NullRHI")));Report->SetBoolField(TEXT("learned_mode"),bLearned);Report->SetBoolField(TEXT("missing_model_test"),bMissingModel);
    Report->SetNumberField(TEXT("p95_frame_ms"),Percentile(FrameMs,.95));Report->SetNumberField(TEXT("max_frame_ms"),Percentile(FrameMs,1));Report->SetNumberField(TEXT("p95_inference_batch_ms"),Percentile(InferenceMs,.95));
    Report->SetNumberField(TEXT("p50_frame_ms"),Percentile(FrameMs,.5));Report->SetNumberField(TEXT("p99_frame_ms"),Percentile(FrameMs,.99));Report->SetNumberField(TEXT("frame_samples"),FrameMs.Num());
    Report->SetNumberField(TEXT("p95_queue_ms"),Percentile(QueueMs,.95));Report->SetNumberField(TEXT("p95_director_tick_ms"),Percentile(GameThreadMs,.95));
    Report->SetNumberField(TEXT("inference_batches"),ModelCalls);Report->SetNumberField(TEXT("stale_results_rejected"),StaleResults);Report->SetNumberField(TEXT("invalid_results_rejected"),InvalidRejected);
    Report->SetNumberField(TEXT("model_parameters"),bMissingModel?0:121520);Report->SetNumberField(TEXT("parity_max_abs_error"),Policy.ParityError);Report->SetStringField(TEXT("policy_status"),Policy.Status);
    Report->SetBoolField(TEXT("save_roundtrip"),bSaveTest);Report->SetBoolField(TEXT("resident_restore"),bStreamTest);Report->SetNumberField(TEXT("stream_restores"),StreamRestores);Report->SetNumberField(TEXT("tractor_legs"),CompletedLegs);
    Report->SetBoolField(TEXT("contract_python_cpp_parity"),bContractParity);Report->SetBoolField(TEXT("loaded_door_restore"),bDoorTest);
    Report->SetObjectField(TEXT("final_state"),SerializeState());Report->SetNumberField(TEXT("peak_process_bytes"),double(FPlatformMemory::GetStats().PeakUsedPhysical));
    const FString Folder=FPaths::ProjectSavedDir()/TEXT("VillageMeshV25");IFileManager::Get().MakeDirectory(*Folder,true);
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*(Folder/(TEXT("runtime_")+CheckId+TEXT(".json"))));
    UE_LOG(LogTemp,Display,TEXT("V25_DIAGNOSTICS pass=%d reason=%s"),Pass,*Reason);FPlatformMisc::RequestExitWithStatus(false,Pass?0:1);
}

#include "V3/VillageAtlas.h"
#include "Components/StaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/TextRenderComponent.h"
#include "Components/WorldPartitionStreamingSourceComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/Texture2D.h"
#include "Engine/Canvas.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "V25/VillageLife.h"

namespace
{
FVector ReadPoint(const TSharedPtr<FJsonObject>& J,const FString& Key)
{
    const auto& A=J->GetArrayField(Key);return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A.Num()>2?A[2]->AsNumber():0);
}
TArray<FAtlasPlace> ReadPlaces()
{
    FString Text;TSharedPtr<FJsonObject> Root;TArray<FAtlasPlace> Out;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("V3/Data/v3_world.json")))||
       !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root))return Out;
    for(const TCHAR* Key:{TEXT("landmarks"),TEXT("navigation_stops")})
    {
        if(!Root->HasField(Key))continue;
        for(const auto& Value:Root->GetArrayField(Key))
        {
        auto J=Value->AsObject();FAtlasPlace P;P.Id=J->GetStringField(TEXT("id"));P.Name=J->GetStringField(TEXT("name"));
        P.Kind=J->GetStringField(TEXT("kind"));P.Center=ReadPoint(J,TEXT("center_cm"));P.Arrival=ReadPoint(J,TEXT("arrival_cm"));
        P.LookAt=J->HasField(TEXT("look_at_cm"))?ReadPoint(J,TEXT("look_at_cm")):P.Center+FVector(0,0,180);Out.Add(P);
        }
    }
    return Out;
}
UMaterialInstanceDynamic* Color(UObject* Owner,FLinearColor C)
{
    auto* Base=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/VillageMeshV25/Materials/M_V25Color.M_V25Color"));
    auto* M=UMaterialInstanceDynamic::Create(Base,Owner);if(M)M->SetVectorParameterValue(TEXT("Color"),C);return M;
}
FLinearColor Gold(.95f,.76f,.36f),Pale(.89f,.92f,.85f),Muted(.58f,.67f,.61f),Panel(.025f,.055f,.045f,.96f);
}

AVillageLivestock::AVillageLivestock()
{
    PrimaryActorTick.bCanEverTick=true;
    auto* Capsule=CreateDefaultSubobject<UCapsuleComponent>(TEXT("BodyCollision"));SetRootComponent(Capsule);
    Capsule->InitCapsuleSize(38,65);Capsule->SetCollisionProfileName(TEXT("Pawn"));
}
void AVillageLivestock::Initialize(const FString& Species,int32 Seed,FVector Yard)
{
    Identity=Seed;Origin=Yard;Phase=Seed*.73f;Target=Origin;SetActorLocation(Origin+FVector(0,0,65));
    const bool Goat=Species==TEXT("Goat"),Bird=Species==TEXT("Hen"),Buffalo=Species==TEXT("Buffalo");
    const float S=Bird?.23f:Goat?.56f:1.f;
    auto* Capsule=Cast<UCapsuleComponent>(GetRootComponent());Capsule->SetCapsuleSize(38*S,65*S);
    SetActorLocation(Origin+FVector(0,0,65*S));Origin=GetActorLocation();Target=Origin;
    Speed=Bird?28:Goat?42:30;Radius=Bird?210:320;
    const FLinearColor Coat=Buffalo?FLinearColor(.075f,.085f,.08f):Goat?FLinearColor(.42f,.27f,.15f):Bird?FLinearColor(.68f,.48f,.25f):FLinearColor(.72f,.69f,.58f);
    auto* Main=Color(this,Coat);auto* Dark=Color(this,FLinearColor(.06f,.05f,.04f));auto* Horn=Color(this,FLinearColor(.45f,.40f,.30f));
    auto* Sphere=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    auto Part=[&](FVector P,FVector Size,UMaterialInterface* Mat)
    {
        auto* C=NewObject<UStaticMeshComponent>(this);C->SetStaticMesh(Sphere);C->SetMaterial(0,Mat);C->SetupAttachment(RootComponent);
        C->SetRelativeLocation(P*S);C->SetRelativeScale3D(Size*S/100);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->RegisterComponent();Parts.Add(C);return C;
    };
    Part(FVector(0,0,30),FVector(185,82,93),Main);
    Part(FVector(83,0,40),FVector(65,55,82),Main);
    Part(FVector(113,0,27),FVector(60,45,35),Buffalo?Dark:Main);
    for(float Side:{-1.f,1.f})
    {
        auto* Ear=Part(FVector(81,Side*37,69),FVector(52,14,19),Main);Ear->SetRelativeRotation(FRotator(0,Side*24,Side*10));
        Part(FVector(104,Side*25,57),FVector(9,4,9),Dark);
        if(!Bird){auto* H=Part(FVector(69,Side*27,97),FVector(9,12,44),Horn);H->SetRelativeRotation(FRotator(Goat?-30:15,0,Side*25));}
        for(float Front:{-1.f,1.f})
        {
            if(Bird&&Front<0)continue;
            auto* L=Part(FVector(Front*59,Side*29,-28),FVector(18,18,73),Main);Legs.Add(L);
            Part(FVector(Front*59+5,Side*29,-60),FVector(26,23,14),Dark);
        }
        if(!Buffalo&&!Goat&&!Bird)
            Part(FVector(-25,Side*39,38),FVector(72,8,56),Dark);
    }
    auto* Tail=Part(FVector(-100,0,0),FVector(8,8,75),Main);Tail->SetRelativeRotation(FRotator(-20,0,0));
    if(Bird){Part(FVector(120,0,45),FVector(45,15,15),Horn);Part(FVector(90,0,90),FVector(26,12,24),Color(this,FLinearColor(.6f,.04f,.025f)));}
}
void AVillageLivestock::Tick(float Dt)
{
    Super::Tick(Dt);Age+=Dt;const float Cycle=FMath::Fmod(Age+Phase*5,24.f);const bool Moving=Cycle<13;
    if(Moving)
    {
        const float A=Phase+Age*.085f;Target=Origin+FVector(FMath::Cos(A)*Radius,FMath::Sin(A)*Radius*.55f,0);
        FVector D=Target-GetActorLocation();D.Z=0;
        if(!D.IsNearlyZero())
        {
            SetActorRotation(FMath::RInterpTo(GetActorRotation(),D.Rotation(),Dt,2));
            FHitResult Hit;AddActorWorldOffset(D.GetSafeNormal()*FMath::Min(D.Size(),Speed*Dt),true,&Hit);
            if(Hit.bBlockingHit)Phase+=Dt*.8f;
        }
    }
    for(int32 I=0;I<Legs.Num();++I)Legs[I]->SetRelativeRotation(FRotator(Moving?FMath::Sin(Age*4+I*PI*.8f)*15:0,0,0));
}

void AVillageAtlasHUD::BeginPlay()
{
    Super::BeginPlay();Places=ReadPlaces();Atlas=LoadObject<UTexture2D>(nullptr,TEXT("/Game/VillageMeshV3/UI/T_VillageAtlas.T_VillageAtlas"));
    if(Places.Num()==10)Selected=9;
    UE_LOG(LogTemp,Display,TEXT("V3_ATLAS loaded=%d places=%d"),HasAtlas(),Places.Num());
}
void AVillageAtlasHUD::SetExpanded(bool Value)
{
    if(bExpanded==Value)return;
    bExpanded=Value;
    if(auto* PC=GetOwningPlayerController())
    {
        PC->bShowMouseCursor=Value;PC->SetIgnoreLookInput(Value);PC->SetIgnoreMoveInput(Value);
        if(Value){FInputModeGameAndUI Mode;Mode.SetHideCursorDuringCapture(false);PC->SetInputMode(Mode);}
        else{PC->ResetIgnoreLookInput();PC->ResetIgnoreMoveInput();PC->SetInputMode(FInputModeGameOnly());}
    }
}
void AVillageAtlasHUD::ToggleMap(){SetExpanded(!bExpanded);}
void AVillageAtlasHUD::SelectNext(){if(Places.Num())Selected=(Selected+1)%Places.Num();}
void AVillageAtlasHUD::Zoom(float Direction){MiniSpan=FMath::Clamp(MiniSpan-Direction*8000,16000.f,96000.f);}
FVector2D AVillageAtlasHUD::MapPoint(FVector P) const
{return FVector2D(MapX+MapSize*(.5f+(P.X-MapCenter.X)/MapSpan),MapY+MapSize*(.5f-(P.Y-MapCenter.Y)/MapSpan));}
void AVillageAtlasHUD::SelectAtCursor()
{
    if(!bExpanded||!Canvas)return;float X,Y;if(!GetOwningPlayerController()->GetMousePosition(X,Y))return;
    float Closest=24;
    for(int32 I=0;I<Places.Num();++I){const float D=FVector2D::Distance(MapPoint(Places[I].Center),FVector2D(X,Y));if(D<Closest){Closest=D;Selected=I;}}
    const float ListX=MapX+MapSize+28;
    if(X>ListX&&X<Canvas->ClipX-25&&Y>=MapY+48&&Y<MapY+48+Places.Num()*ListRowHeight)
        Selected=FMath::Clamp(int32((Y-MapY-48)/ListRowHeight),0,Places.Num()-1);
}
void AVillageAtlasHUD::VisitSelected()
{
    if(!bExpanded||!Places.IsValidIndex(Selected))return;
    auto* PC=GetOwningPlayerController();auto* Pawn=Cast<ACharacter>(PC->GetPawn());if(!Pawn)return;
    const auto& P=Places[Selected];Pawn->GetCharacterMovement()->StopMovementImmediately();
    Pawn->SetActorLocation(P.Arrival,false,nullptr,ETeleportType::TeleportPhysics);Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    PC->SetControlRotation((P.LookAt-P.Arrival-FVector(0,0,70)).Rotation());SetExpanded(false);
}
void AVillageAtlasHUD::DrawHUD()
{
    Super::DrawHUD();if(!Canvas)return;auto* PC=GetOwningPlayerController();APawn* Pawn=PC?PC->GetPawn().Get():nullptr;if(!Pawn)return;
    const FVector Pos=Pawn->GetActorLocation();const float W=Canvas->ClipX,H=Canvas->ClipY;
    DrawRect(Panel,20,20,435,74);DrawText(TEXT("PANDORI NIJJARAN"),Gold,38,30,nullptr,1.35f);
    DrawText(TEXT("Punjab  /  Village atlas  /  1.28 km mapped extent"),Pale,38,58,nullptr,.9f);
    if(!bExpanded)
    {
        DrawText(TEXT("WASD walk   Shift run   T talk   M village map"),Pale,26,H-56,nullptr,.9f);
        DrawText(TEXT("F6 weather   F7 time   F10 rooms   F11 farms   Mouse wheel map scale"),Muted,26,H-36,nullptr,.8f);
        if(auto* Life=AVillageLifeDirector::Find(GetWorld()))
        {
            FString Status,Tail;Life->HUDStatus().Split(TEXT("\n"),&Status,&Tail);Status=Status.Replace(TEXT("V2.5 | "),TEXT(""));
            DrawRect(Panel,W-395,20,375,86);DrawText(TEXT("VILLAGE LIFE"),Gold,W-380,30,nullptr,1);
            DrawText(Status,Pale,W-380,55,nullptr,.85f);DrawText(TEXT("T talk   F11 farm plots   F6 weather"),Muted,W-380,78,nullptr,.8f);
        }
        MapSize=FMath::Min(292.f,H*.34f);MapX=W-MapSize-28;MapY=H-MapSize-78;MapSpan=MiniSpan;
        const float Half=MapSpan/2;MapCenter=FVector(FMath::Clamp(Pos.X,-64000.+Half,64000.-Half),FMath::Clamp(Pos.Y,-64000.+Half,64000.-Half),0);
    }
    else
    {
        DrawRect(FLinearColor(.012f,.027f,.022f,.98f),12,105,W-24,H-126);
        MapSize=FMath::Min(H-180,W-405);MapX=34;MapY=126;MapSpan=128000;MapCenter=FVector::ZeroVector;
        ListRowHeight=FMath::Clamp((MapSize-210)/FMath::Max(1,Places.Num()),25.f,42.f);
    }
    DrawRect(Panel,MapX-6,MapY-6,MapSize+12,MapSize+42);
    if(Atlas)DrawTexture(Atlas,MapX,MapY,MapSize,MapSize,(MapCenter.X-MapSpan/2+64000)/128000,
        (64000-MapCenter.Y-MapSpan/2)/128000,MapSpan/128000,MapSpan/128000,FLinearColor::White,BLEND_Opaque);
    DrawText(TEXT("N"),Gold,MapX+MapSize/2-5,MapY+7,nullptr,1);
    const auto Inside=[&](FVector2D P){return P.X>=MapX&&P.Y>=MapY&&P.X<=MapX+MapSize&&P.Y<=MapY+MapSize;};
    for(int32 I=0;I<Places.Num();++I)
    {
        const auto P=MapPoint(Places[I].Center);if(!Inside(P))continue;
        DrawRect(I==Selected?Gold:FLinearColor(.83f,.86f,.75f),P.X-6,P.Y-6,12,12);
        if(bExpanded)DrawText(FString::FromInt(I+1),FLinearColor::Black,P.X-4,P.Y-6,nullptr,.7f);
    }
    const auto Player=MapPoint(Pos);const float Yaw=FMath::DegreesToRadians(PC->GetControlRotation().Yaw);
    const FVector2D Forward(FMath::Cos(Yaw),-FMath::Sin(Yaw)),Side(-Forward.Y,Forward.X);
    if(Inside(Player))
    {
        const auto Tip=Player+Forward*12,Left=Player-Forward*7+Side*6,Right=Player-Forward*7-Side*6;
        DrawLine(Tip.X,Tip.Y,Left.X,Left.Y,FLinearColor::White,2);DrawLine(Tip.X,Tip.Y,Right.X,Right.Y,FLinearColor::White,2);DrawLine(Left.X,Left.Y,Right.X,Right.Y,FLinearColor::White,2);
    }
    DrawText(FString::Printf(TEXT("%.0f m  |  North up  |  M %s"),MapSpan/100,bExpanded?TEXT("close"):TEXT("expand")),Pale,MapX+7,MapY+MapSize+9,nullptr,.8f);
    if(Places.IsValidIndex(Selected))
    {
        const auto& P=Places[Selected];const float Dist=FVector::Dist2D(Pos,P.Arrival)/100;
        if(!bExpanded){DrawText(P.Name+FString::Printf(TEXT("  %.0f m"),Dist),Gold,MapX,MapY-24,nullptr,.9f);}
        else
        {
            const float LX=MapX+MapSize+28;
            DrawText(TEXT("PLACES TO EXPLORE"),Gold,LX,MapY+10,nullptr,1.1f);
            for(int32 I=0;I<Places.Num();++I)
            {
                const float YY=MapY+48+I*ListRowHeight;if(I==Selected)DrawRect(FLinearColor(.16f,.22f,.15f,1),LX-8,YY-5,W-LX-30,ListRowHeight-6);
                DrawText(FString::Printf(TEXT("%d  %s"),I+1,*Places[I].Name),I==Selected?Gold:Pale,LX,YY,nullptr,1);
            }
            float Y=MapY+48+Places.Num()*ListRowHeight+18;
            DrawText(FString::Printf(TEXT("%.0f m straight-line distance"),Dist),Gold,LX,Y,nullptr,.9f);
            DrawText(TEXT("Click a marker / list row or press Tab"),Pale,LX,Y+28,nullptr,.85f);
            DrawText(TEXT("Enter: visit selected entrance"),Pale,LX,Y+51,nullptr,.85f);
            DrawText(TEXT("Public-site layouts are representative."),Muted,LX,Y+88,nullptr,.78f);
            DrawText(TEXT("Roads / footprints: OSM + Overture."),Muted,LX,Y+109,nullptr,.78f);
        }
    }
    DrawText(TEXT("Map (c) OpenStreetMap contributors / Overture Maps  |  Original inferred architecture and farming"),Muted,25,H-17,nullptr,.7f);
    if(!bExpanded)DrawRect(FLinearColor(1,1,1,.65f),W/2-2,H/2-2,4,4);
}

AVillageAtlasWorld::AVillageAtlasWorld()
{
    PrimaryActorTick.bCanEverTick=true;
    OverviewSource=CreateDefaultSubobject<UWorldPartitionStreamingSourceComponent>(TEXT("VillageOverviewStreaming"));
    FStreamingSourceShape Shape;Shape.bUseGridLoadingRange=false;Shape.Radius=180000;
    OverviewSource->Shapes.Add(Shape);OverviewSource->TargetState=EStreamingSourceTargetState::Activated;
    OverviewSource->DisableStreamingSource();
}
void AVillageAtlasWorld::BeginPlay()
{
    Super::BeginPlay();Places=ReadPlaces();bCheck=FParse::Param(FCommandLine::Get(),TEXT("V3Check"));Started=FPlatformTime::Seconds();
    auto SignAt=[&](FVector Position,const FString& Caption,float Width,float LetterSize,bool Posts)
    {
        auto* Sign=GetWorld()->SpawnActor<AActor>();auto* Root=NewObject<USceneComponent>(Sign);Sign->SetRootComponent(Root);Root->RegisterComponent();Sign->SetActorLocation(Position);
        auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
        auto* Mat=Color(Sign,FLinearColor(.06f,.18f,.15f));
        auto Box=[&](FVector Offset,FVector Size)
        {
            auto* C=NewObject<UStaticMeshComponent>(Sign);C->SetStaticMesh(Cube);C->SetMaterial(0,Mat);C->SetupAttachment(Root);
            C->SetRelativeLocation(Offset);C->SetRelativeScale3D(Size/100);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->RegisterComponent();
        };
        Box(FVector::ZeroVector,FVector(Width,20,80));
        if(Posts)for(float Side:{-1.f,1.f})Box(FVector(Side*Width*.38f,0,-75),FVector(12,12,150));
        auto* Text=NewObject<UTextRenderComponent>(Sign);Text->SetupAttachment(Root);Text->SetRelativeLocation(FVector(0,-12,0));Text->SetRelativeRotation(FRotator(0,-90,0));
        Text->SetText(FText::FromString(Caption));Text->SetWorldSize(LetterSize);Text->SetTextRenderColor(FColor(235,210,145));
        Text->SetHorizontalAlignment(EHTA_Center);Text->SetVerticalAlignment(EVRTA_TextCenter);Text->RegisterComponent();
    };
    for(const auto& P:Places)
    {
        if(P.Kind!=TEXT("residential"))SignAt(P.Arrival+FVector(520,145,50),P.Name,650,32,true);
        if(P.Kind==TEXT("market"))
        {
            const TCHAR* Names[]={TEXT("GENERAL STORE"),TEXT("CHAI & SWEETS"),TEXT("CYCLE REPAIR"),TEXT("TAILOR"),TEXT("FARM SUPPLIES")};
            for(int32 I=0;I<5;++I)SignAt(P.Center+FVector((I-2)*610,-145,390),Names[I],490,26,false);
        }
        if(P.Kind==TEXT("dairy")||P.Kind==TEXT("farm"))
        {
            const int32 Count=P.Kind==TEXT("dairy")?8:6;
            for(int32 I=0;I<Count;++I)
            {
                auto* A=GetWorld()->SpawnActor<AVillageLivestock>();
                const FString Species=P.Kind==TEXT("dairy")?(I%2?TEXT("Cow"):TEXT("Buffalo")):(I<4?TEXT("Goat"):TEXT("Hen"));
                A->Initialize(Species,Animals.Num(),P.Center+FVector((I%4-1.5f)*650,-600-(I/4)*700,10));Animals.Add(A);
            }
        }
    }
    if(Animals.Num())LastAnimalPosition=Animals[0]->GetActorLocation();
    for(const auto& A:Animals){LastAnimalPositions.Add(A->GetActorLocation());AnimalTravel.Add(0);}
    UE_LOG(LogTemp,Display,TEXT("V3_START places=%d animals=%d"),Places.Num(),Animals.Num());
}
void AVillageAtlasWorld::Tick(float Dt)
{
    Super::Tick(Dt);
    auto* PC=UGameplayStatics::GetPlayerController(GetWorld(),0);auto* Pawn=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;
    // A component works with both RuntimeHashSet and SpatialHash. The legacy
    // spatial-hash console command does not expand UE 5.8 HashSet coverage.
    if(Pawn&&Pawn->GetActorLocation().Z>10000)OverviewSource->EnableStreamingSource();
    else OverviewSource->DisableStreamingSource();
    if(!bCheck)return;Elapsed+=Dt;
    if(Elapsed>20)FrameTimes.Add(Dt*1000.);
    if(Animals.Num()){AnimalDistance+=FVector::Dist(LastAnimalPosition,Animals[0]->GetActorLocation());LastAnimalPosition=Animals[0]->GetActorLocation();}
    for(int32 I=0;I<Animals.Num();++I)
    {
        const FVector P=Animals[I]->GetActorLocation();AnimalTravel[I]+=FVector::Dist(P,LastAnimalPositions[I]);LastAnimalPositions[I]=P;
        bPass&=!P.ContainsNaN()&&FVector::Dist2D(P,Animals[I]->Origin)<=Animals[I]->Radius+80;
    }
    auto* HUD=PC?Cast<AVillageAtlasHUD>(PC->GetHUD()):nullptr;if(!Pawn||!HUD)return;
    const int32 Stage=FMath::Min(int32(Elapsed/14),Places.Num()+1);
    if(Stage!=CheckStop)
    {
        CheckStop=Stage;
        if(Stage==0)HUD->SetExpanded(true);
        else if(Stage<=Places.Num()){HUD->Selected=Stage-1;HUD->SetExpanded(true);HUD->VisitSelected();}
        else
        {
            Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Flying);Pawn->GetCharacterMovement()->StopMovementImmediately();
            Pawn->SetActorLocation(FVector(0,-35000,35000));PC->SetControlRotation(FRotator(-48,90,0));
        }
    }
    const float Local=FMath::Fmod(Elapsed,14.f);
    if(Local>10&&Local-Dt<=10)
    {
        bool Ground=Pawn->GetCharacterMovement()->IsMovingOnGround()&&Pawn->GetActorLocation().Z>-20&&Pawn->GetActorLocation().Z<300;
        if(Stage<=Places.Num()){bPass&=Ground;bGrounded&=Ground;}
        else
        {
            bOverviewLoaded=OverviewSource->IsStreamingCompleted();OverviewMeshChunks=0;
            for(TActorIterator<AStaticMeshActor> It(GetWorld());It;++It)
                if(auto* Mesh=It->GetStaticMeshComponent()->GetStaticMesh().Get())
                    if(Mesh->GetName().StartsWith(TEXT("SM_V3_")))++OverviewMeshChunks;
            bPass&=bOverviewLoaded;
            UE_LOG(LogTemp,Display,TEXT("V3_OVERVIEW streaming_complete=%d mesh_chunks=%d"),bOverviewLoaded,OverviewMeshChunks);
        }
        UE_LOG(LogTemp,Display,TEXT("V3_STOP %d ground=%d pos=%s"),Stage,Ground,*Pawn->GetActorLocation().ToString());
        const FString Dir=FPaths::ProjectSavedDir()/TEXT("VillageMeshV3");IFileManager::Get().MakeDirectory(*Dir,true);
        FScreenshotRequest::RequestScreenshot(Dir/FString::Printf(TEXT("view_%02d.png"),Stage),true,false);
    }
    if(Elapsed>(Places.Num()+2)*14)
    {
        FrameTimes.Sort();const double P95=FrameTimes.Num()?FrameTimes[FMath::Min(FrameTimes.Num()-1,int32(FrameTimes.Num()*.95f))]:0;
        TArray<TSharedPtr<FJsonValue>> Travel;bool AllMoving=true;
        for(double D:AnimalTravel){Travel.Add(MakeShared<FJsonValueNumber>(D));AllMoving&=D>50;}
        auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("passed"),bPass&&Places.Num()==10&&Animals.Num()==14&&AllMoving&&HUD->HasAtlas());
        J->SetBoolField(TEXT("atlas_loaded"),HUD->HasAtlas());
        J->SetBoolField(TEXT("overview_streaming_complete"),bOverviewLoaded);J->SetNumberField(TEXT("overview_mesh_chunks"),OverviewMeshChunks);
        J->SetArrayField(TEXT("per_animal_travel_cm"),Travel);J->SetBoolField(TEXT("all_animals_moved"),AllMoving);
        J->SetNumberField(TEXT("places"),Places.Num());J->SetNumberField(TEXT("animals"),Animals.Num());J->SetNumberField(TEXT("animal_travel_cm"),AnimalDistance);
        J->SetNumberField(TEXT("elapsed_seconds"),FPlatformTime::Seconds()-Started);J->SetNumberField(TEXT("frame_p95_ms"),P95);
        J->SetBoolField(TEXT("all_arrivals_grounded"),bGrounded);J->SetStringField(TEXT("scope"),TEXT("Rendered atlas, nine public entrances, residential lane and aerial overview; not a full village walk-through or release soak"));
        FString Out;FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Out));FFileHelper::SaveStringToFile(Out,*(FPaths::ProjectSavedDir()/TEXT("VillageMeshV3/runtime_check.json")));
        UE_LOG(LogTemp,Display,TEXT("V3_CHECK %s"),*Out);SetActorTickEnabled(false);FPlatformMisc::RequestExitWithStatus(false,J->GetBoolField(TEXT("passed"))?0:1);
    }
}
AVillageAtlasGameMode::AVillageAtlasGameMode(){HUDClass=AVillageAtlasHUD::StaticClass();}
void AVillageAtlasGameMode::StartPlay(){Super::StartPlay();GetWorld()->SpawnActor<AVillageAtlasWorld>();}

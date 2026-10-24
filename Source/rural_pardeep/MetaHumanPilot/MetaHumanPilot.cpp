#include "MetaHumanPilot/MetaHumanPilot.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#if WITH_EDITOR
#include "ShaderCompiler.h"
#endif

AMetaHumanPilotProbe::AMetaHumanPilotProbe()
{
    PrimaryActorTick.bCanEverTick=true;
    Capsule=CreateDefaultSubobject<UCapsuleComponent>(TEXT("PilotCollision"));
    SetRootComponent(Capsule);Capsule->InitCapsuleSize(34,88);
    Capsule->SetCollisionProfileName(TEXT("Pawn"));
    Capsule->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AMetaHumanPilotProbe::BeginPlay()
{
    Super::BeginPlay();
    StartedAt=FPlatformTime::Seconds();
    bBaseline=FParse::Param(FCommandLine::Get(),TEXT("MHPilotBaseline"));
    bCheck=FParse::Param(FCommandLine::Get(),TEXT("MHPilotCheck"));
}
void AMetaHumanPilotProbe::InitializePilot()
{
    auto* PC=UGameplayStatics::GetPlayerController(GetWorld(),0);
    auto* Pawn=PC?Cast<ACharacter>(PC->GetPawn()):nullptr;
    if(!Pawn)return;
    bInitialized=true;
    // The mapped Residential Lane viewpoint already used by the village atlas.
    Pawn->SetActorLocation(FVector(3748,-18128,110));
    Pawn->GetCharacterMovement()->StopMovementImmediately();
    PC->SetControlRotation(FRotator(-4,96,0));
    if(bCheck){PC->SetIgnoreMoveInput(true);PC->SetIgnoreLookInput(true);}
    Anchor=FVector(3672,-17432,88);SetActorLocation(Anchor);SetActorRotation(FRotator(0,-84,0));
    if(bBaseline){Capsule->SetCollisionEnabled(ECollisionEnabled::NoCollision);ReadyAt=FPlatformTime::Seconds();return;}
    Capsule->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    FString Text;TSharedPtr<FJsonObject> Report;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectSavedDir()/TEXT("MetaHumanPilot/assemble.json")))||
       !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Report)||!Report->GetBoolField(TEXT("passed")))
    {Error=TEXT("A successful local assembly report is required");return;}
    const auto& Blueprints=Report->GetArrayField(TEXT("assembled_blueprints"));
    if( !Blueprints.Num()){Error=TEXT("Assembly report has no actor Blueprint");return;}
    BlueprintPath=Blueprints[0]->AsString();
    if(!BlueprintPath.StartsWith(TEXT("/Game/MetaHumanPilot/Assembled/"))){Error=TEXT("Blueprint is outside pilot namespace");return;}
    auto* Class=LoadClass<AActor>(nullptr,*(BlueprintPath+TEXT("_C")));
    if(!Class){Error=TEXT("Assembled actor class could not be loaded");return;}
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Visual=GetWorld()->SpawnActor<AActor>(Class,Anchor-FVector(0,0,88),GetActorRotation(),Spawn);
    if(!Visual){Error=TEXT("Assembled actor could not be spawned");return;}
    // The probe capsule owns movement collision. The attached visual actor must
    // not obstruct its own parent capsule during swept movement.
    Visual->SetActorEnableCollision(false);Capsule->IgnoreActorWhenMoving(Visual,true);
    Visual->AttachToComponent(Capsule,FAttachmentTransformRules::KeepWorldTransform);
    // The assembled mesh faces +Y; the movement probe uses Unreal's +X.
    Visual->SetActorRelativeRotation(FRotator(0,-90,0));
    TArray<USkeletalMeshComponent*> Meshes;Visual->GetComponents(Meshes);
    for(auto* Mesh:Meshes)if(Mesh->GetName().Equals(TEXT("Body"),ESearchCase::IgnoreCase)){Body=Mesh;break;}
    if(!Body){Error=TEXT("The assembled actor has no Body skeletal component");return;}
    const FString Base=TEXT("/MetaHumanCharacter/Optional/Animation/UEFNAnimPreset/Locomotion/");
    Idle=LoadObject<UAnimSequence>(nullptr,*(Base+TEXT("AS_MH_Neutral_Stand_Idle_Loop.AS_MH_Neutral_Stand_Idle_Loop")));
    Walk=LoadObject<UAnimSequence>(nullptr,*(Base+TEXT("AS_MH_Neutral_Walk_Loop_F.AS_MH_Neutral_Walk_Loop_F")));
    if(!Idle||!Walk){Error=TEXT("Installed pilot animation clips could not be loaded");return;}
    Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    // Exercise locomotion and its visible materials before the measured pass.
    Body->PlayAnimation(Walk,true);bWarmupWalking=true;
    if(Body->GetBoneIndex(TEXT("foot_l"))==INDEX_NONE)Error=TEXT("Body is missing the foot_l test bone");
    ReadyAt=FPlatformTime::Seconds();
}
void AMetaHumanPilotProbe::Tick(float Dt)
{
    Super::Tick(Dt);Elapsed+=Dt;
    if(!bInitialized){if(Elapsed>1)InitializePilot();if(Elapsed>30){Error=TEXT("Player did not initialize");Finish();}return;}
    if(!Error.IsEmpty()){Finish();return;}
    Elapsed=float(FPlatformTime::Seconds()-ReadyAt);
#if WITH_EDITOR
    // First-run shader work is not a representative gameplay frame-time sample.
    if(Elapsed>=25&&Elapsed<65&&GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())
    {
        bShadersDuringSamples=true;++ShaderSampleFrames;
        if(FirstShaderSampleSeconds<0)FirstShaderSampleSeconds=Elapsed;
        MaxShaderJobsDuringSamples=FMath::Max(MaxShaderJobsDuringSamples,GShaderCompilingManager->GetNumRemainingJobs());
    }
    if(Elapsed<25&&GShaderCompilingManager&&GShaderCompilingManager->IsCompiling())
    {
        ReadyAt=FPlatformTime::Seconds();Elapsed=0;
        if(ReadyAt-StartedAt>600){Error=TEXT("Shaders did not settle within ten minutes");Finish();return;}
    }
#endif
    if(Elapsed>25&&Elapsed<65)FrameTimes.Add(Dt*1000.);
    if(!bBaseline)
    {
        FHitResult Floor;FCollisionQueryParams Query;Query.AddIgnoredActor(this);Query.AddIgnoredActor(Visual);
        const FVector P=GetActorLocation();
        if(GetWorld()->LineTraceSingleByChannel(Floor,P+FVector(0,0,500),P-FVector(0,0,500),ECC_Visibility,Query))
        {
            const float FloorZ=Floor.ImpactPoint.Z;
            if(Elapsed<20){Anchor.Z=FloorZ+90;SetActorLocation(FVector(P.X,P.Y,Anchor.Z));}
            else
            {
                const float SupportFootZ=FMath::Min(Body->GetSocketLocation(TEXT("foot_l")).Z,Body->GetSocketLocation(TEXT("foot_r")).Z);
                bGrounded&=FMath::Abs((P.Z-88)-FloorZ)<15&&FloorZ<200&&SupportFootZ-FloorZ>=-10&&SupportFootZ-FloorZ<=30;
            }
        }
        else if(Elapsed>20)bGrounded=false;
        if(Elapsed<20)
        {
            if(!bWarmupWalking){Body->PlayAnimation(Walk,true);bWarmupWalking=true;}
            const float Phase=Elapsed*.65f;
            SetActorRotation(FRotator(0,FMath::Cos(Phase)>=0?90:-90,0));
            SetActorLocation(Anchor+FVector(0,FMath::Sin(Phase)*100,0),true);
        }
        else if(bWarmupWalking)
        {
            bWarmupWalking=false;Body->PlayAnimation(Idle,true);
            bIdleApplied=Body->GetSingleNodeInstance()&&Body->GetSingleNodeInstance()->GetCurrentAsset()==Idle;
            SetActorLocation(Anchor);SetActorRotation(FRotator(0,-84,0));
        }
        if(Elapsed>=45&&(!bCheck||Elapsed<65)&&!bWalking)
        {
            bWalking=true;Body->PlayAnimation(Walk,true);
            bWalkApplied=Body->GetSingleNodeInstance()&&Body->GetSingleNodeInstance()->GetCurrentAsset()==Walk;
        }
        if(bWalking&&(!bCheck||Elapsed<65))
        {
            const FVector Before=GetActorLocation();
            const float Offset=FMath::Sin((Elapsed-45)*.65f)*100;
            SetActorRotation(FRotator(0,FMath::Cos((Elapsed-45)*.65f)>=0?90:-90,0));
            FHitResult Sweep;SetActorLocation(Anchor+FVector(0,Offset,0),true,&Sweep);
            if(Sweep.bBlockingHit)
            {
                MovementBlocker=Sweep.GetActor()?Sweep.GetActor()->GetName():TEXT("unknown");
                bMovementStartedPenetrating=Sweep.bStartPenetrating;
            }
            Travel+=FVector::Dist(Before,GetActorLocation());
            const FVector Foot=Body->GetSocketTransform(TEXT("foot_l"),RTS_Component).GetTranslation();
            if(bHaveFoot)FootTravel+=FVector::Dist(Foot,LastFoot);LastFoot=Foot;bHaveFoot=true;
        }
    }
    // Close appearance view after the fixed-camera measurements have ended.
    if(bCheck&&Elapsed>=65&&!bPortraitPlaced)
    {
        bPortraitPlaced=true;bWalking=false;
        if(Body&&Idle)Body->PlayAnimation(Idle,true);
        SetActorLocation(Anchor);SetActorRotation(FRotator(0,-90,0));
        if(auto* PC=UGameplayStatics::GetPlayerController(GetWorld(),0))
        {
            if(APawn* Pawn=PC->GetPawn())Pawn->SetActorLocation(Anchor+FVector(15,-120,22));
            PC->SetControlRotation(FRotator(3.3f,97.1f,0));
        }
    }
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("MetaHumanPilot");
    if(bCheck&&((Elapsed>40&&Shot==0)||(Elapsed>61&&Shot==1)||(Elapsed>70&&Shot==2)))
    {
        IFileManager::Get().MakeDirectory(*Dir,true);
        const TCHAR* Prefix=GetWorld()->WorldType==EWorldType::PIE?TEXT("pie"):bBaseline?TEXT("baseline"):TEXT("character");
        FScreenshotRequest::RequestScreenshot(Dir/FString::Printf(TEXT("%s_%s.png"),Prefix,Shot==0?TEXT("idle"):Shot==1?TEXT("walk"):TEXT("portrait")),true,false);++Shot;
    }
    if(bCheck&&Elapsed>75)Finish();
}
void AMetaHumanPilotProbe::Finish()
{
    SetActorTickEnabled(false);FrameTimes.Sort();
    double Sum=0;for(double F:FrameTimes)Sum+=F;
    auto J=MakeShared<FJsonObject>();
    if(Error.IsEmpty())
    {
        if(bShadersDuringSamples)Error=TEXT("Shader compilation overlapped measured frames");
        else if(FrameTimes.Num()<=100)Error=TEXT("Too few measured frames");
        else if(!bBaseline&&!bGrounded)Error=TEXT("Pilot feet did not remain near the street surface");
        else if(!bBaseline&&(!bIdleApplied||!bWalkApplied))Error=TEXT("Idle or walk animation was not applied");
        else if(!bBaseline&&(Travel<=50||FootTravel<=50))Error=TEXT("Insufficient actor or skeletal foot motion");
    }
    const bool Pass=Error.IsEmpty()&&!bShadersDuringSamples&&FrameTimes.Num()>100&&(bBaseline||(bGrounded&&bIdleApplied&&bWalkApplied&&Travel>50&&FootTravel>50));
    J->SetBoolField(TEXT("passed"),Pass);J->SetBoolField(TEXT("baseline"),bBaseline);J->SetStringField(TEXT("error"),Error);
    J->SetBoolField(TEXT("shader_compilation_during_samples"),bShadersDuringSamples);
    J->SetNumberField(TEXT("first_shader_sample_seconds"),FirstShaderSampleSeconds);
    J->SetNumberField(TEXT("shader_sample_frames"),ShaderSampleFrames);
    J->SetNumberField(TEXT("max_shader_jobs_during_samples"),MaxShaderJobsDuringSamples);
    const bool bPIE=GetWorld()->WorldType==EWorldType::PIE;
    J->SetStringField(TEXT("play_mode"),bPIE?TEXT("PIE"):TEXT("standalone"));
    J->SetStringField(TEXT("blueprint"),BlueprintPath);J->SetNumberField(TEXT("elapsed_seconds"),Elapsed);
    J->SetNumberField(TEXT("samples"),FrameTimes.Num());J->SetNumberField(TEXT("frame_mean_ms"),FrameTimes.Num()?Sum/FrameTimes.Num():0);
    J->SetNumberField(TEXT("frame_p95_ms"),FrameTimes.Num()?FrameTimes[FMath::Min(FrameTimes.Num()-1,int32(FrameTimes.Num()*.95))]:0);
    J->SetBoolField(TEXT("grounded"),!bBaseline&&bGrounded);J->SetBoolField(TEXT("idle_applied"),bIdleApplied);J->SetBoolField(TEXT("walk_applied"),bWalkApplied);
    J->SetNumberField(TEXT("actor_travel_cm"),Travel);J->SetNumberField(TEXT("foot_component_space_travel_cm"),FootTravel);
    J->SetStringField(TEXT("last_movement_blocker"),MovementBlocker);J->SetBoolField(TEXT("movement_started_penetrating"),bMovementStartedPenetrating);
    J->SetStringField(TEXT("scope"),TEXT("Single MetaHuman at mapped V3 Residential Lane, 25 s warmup and 40 s samples. No crowd, packaged release, long soak or custom Punjabi wardrobe claim."));
    FString Out;FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&Out));
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("MetaHumanPilot");IFileManager::Get().MakeDirectory(*Dir,true);
    FFileHelper::SaveStringToFile(Out,*(Dir/(bPIE?TEXT("runtime_pie.json"):bBaseline?TEXT("runtime_baseline.json"):TEXT("runtime_character.json"))));
    UE_LOG(LogTemp,Display,TEXT("MH_PILOT_RUNTIME %s"),*Out);
    if(bPIE)
    {
        if(Body&&Idle)Body->PlayAnimation(Idle,true);
        if(auto* PC=UGameplayStatics::GetPlayerController(GetWorld(),0)){PC->ResetIgnoreMoveInput();PC->ResetIgnoreLookInput();}
    }
    else if(bCheck)FPlatformMisc::RequestExitWithStatus(false,Pass?0:1);
}
void AMetaHumanPilotGameMode::StartPlay()
{
    Super::StartPlay();
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    GetWorld()->SpawnActor<AMetaHumanPilotProbe>(FVector::ZeroVector,FRotator::ZeroRotator,Spawn);
}

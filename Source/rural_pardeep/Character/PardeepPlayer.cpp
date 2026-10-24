#include "Character/PardeepPlayer.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/InputComponent.h"
#include "Camera/CameraComponent.h"
#include "Animation/BlendSpace.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Engine/Canvas.h"
#include "Materials/MaterialInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"

bool UPardeepAssetTools::RebuildLocomotion(UBlendSpace* Blend)
{
#if WITH_EDITOR
    if(!Blend||Blend->GetBlendSamples().Num()!=3)return false;
    Blend->ValidateSampleData();Blend->ResampleData();Blend->PostEditChange();Blend->MarkPackageDirty();
    for(float Speed:{0.f,180.f,420.f})
    {
        TArray<FBlendSampleData> Samples;int32 Index=INDEX_NONE;
        if(!Blend->GetSamplesFromBlendInput(FVector(Speed,0,0),Samples,Index,true)||Samples.IsEmpty())return false;
    }
    return true;
#else
    return false;
#endif
}

APardeepPlayer::APardeepPlayer()
{
    bUseControllerRotationYaw=false;
    WalkingSpeed=180;RunningSpeed=420;
    GetCharacterMovement()->bOrientRotationToMovement=true;
    GetCharacterMovement()->RotationRate=FRotator(0,540,0);
    GetCharacterMovement()->MaxWalkSpeed=180;
    CameraBoom=CreateDefaultSubobject<USpringArmComponent>(TEXT("ThirdPersonCameraBoom"));
    CameraBoom->SetupAttachment(GetCapsuleComponent());
    CameraBoom->TargetOffset=FVector(0,0,60);
    CameraBoom->TargetArmLength=340;
    CameraBoom->SocketOffset=FVector(0,48,8);
    CameraBoom->bUsePawnControlRotation=true;
    CameraBoom->bDoCollisionTest=true;
    CameraBoom->ProbeSize=14;
    CameraBoom->bEnableCameraLag=true;
    CameraBoom->CameraLagSpeed=12;
    Camera->SetupAttachment(CameraBoom,USpringArmComponent::SocketName);
    Camera->SetRelativeLocation(FVector::ZeroVector);
    Camera->bUsePawnControlRotation=false;
    Camera->FieldOfView=75;
}
void APardeepPlayer::BeginPlay()
{
    Super::BeginPlay();
    // A replaceable appearance slot. The existing pilot is an explicitly temporary
    // fallback until the owner selects a Pardeep reference and approves the likeness.
    const TCHAR* Path=TEXT("/Game/VillageMeshV3/Player/BP_PardeepAppearance.BP_PardeepAppearance_C");
    auto* Class=LoadClass<AActor>(nullptr,Path);
    if(!Class)Class=LoadClass<AActor>(nullptr,TEXT("/Game/MetaHumanPilot/Assembled/Manpreet/BP_Manpreet.BP_Manpreet_C"));
    if(Class)
    {
        FActorSpawnParameters Params;Params.Owner=this;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        Visual=GetWorld()->SpawnActor<AActor>(Class,GetActorLocation(),GetActorRotation(),Params);
        if(Visual)
        {
            Visual->SetActorEnableCollision(false);GetCapsuleComponent()->IgnoreActorWhenMoving(Visual,true);
            Visual->AttachToComponent(GetCapsuleComponent(),FAttachmentTransformRules::SnapToTargetNotIncludingScale);
            Visual->SetActorRelativeLocation(FVector(0,0,-88));Visual->SetActorRelativeRotation(FRotator(0,-90,0));
            TArray<USkeletalMeshComponent*> Meshes;Visual->GetComponents(Meshes);
            for(auto* Part:Meshes)if(Part->GetName().Equals(TEXT("Body"),ESearchCase::IgnoreCase)){Body=Part;break;}
            Locomotion=LoadObject<UBlendSpace>(nullptr,TEXT("/Game/VillageMeshV3/Player/BS_PlayerLocomotion.BS_PlayerLocomotion"));
            if(Body&&Locomotion){Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;Body->PlayAnimation(Locomotion,true);}
        }
    }
    bCheck=FParse::Param(FCommandLine::Get(),TEXT("PardeepCheck"));
    LastPosition=GetActorLocation();
    if(Controller)Controller->SetControlRotation(FRotator(-12,96,0));
    UE_LOG(LogTemp,Display,TEXT("PARDEEP_PLAYER body=%d blendspace=%d third_person=1 appearance=provisional"),Body!=nullptr,Locomotion!=nullptr);
}
void APardeepPlayer::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindKey(EKeys::V,IE_Pressed,this,&APardeepPlayer::ToggleView);
    Input->BindKey(EKeys::Q,IE_Pressed,this,&APardeepPlayer::SwapShoulder);
}
void APardeepPlayer::ApplyView()
{
    CameraBoom->TargetArmLength=bFirstPerson?0:340;
    CameraBoom->TargetOffset=FVector(0,0,bFirstPerson?70:60);
    if(bFirstPerson)CameraBoom->SocketOffset=FVector::ZeroVector;
    CameraBoom->bEnableCameraLag=!bFirstPerson;
    if(Visual)Visual->SetActorHiddenInGame(bFirstPerson);
    bUseControllerRotationYaw=bFirstPerson;
    GetCharacterMovement()->bOrientRotationToMovement=!bFirstPerson;
}
void APardeepPlayer::ToggleView(){bFirstPerson=!bFirstPerson;ApplyView();}
void APardeepPlayer::SwapShoulder(){bRightShoulder=!bRightShoulder;ApplyView();}
void APardeepPlayer::UpdateSurface()
{
    FHitResult Hit;FCollisionQueryParams Qry;Qry.AddIgnoredActor(this);Qry.AddIgnoredActor(Visual);Qry.bReturnPhysicalMaterial=true;
    if(GetWorld()->LineTraceSingleByChannel(Hit,GetActorLocation(),GetActorLocation()-FVector(0,0,180),ECC_Visibility,Qry))
    {
        auto* Component=Hit.GetComponent();auto* Material=Component?Component->GetMaterial(0):nullptr;
        const FString Name=Material?Material->GetName():TEXT("");
        SurfaceName=Name.Contains(TEXT("Brick"))?TEXT("Brick lane"):Name.Contains(TEXT("Paver"))?TEXT("Tile-paved lane"):
            Name.Contains(TEXT("Dirt"))||Name.Contains(TEXT("Soil"))?TEXT("Dirt / earth"):Name.Contains(TEXT("Road"))||Name.Contains(TEXT("Asphalt"))?TEXT("Asphalt road"):TEXT("Village ground");
    }
}
void APardeepPlayer::Tick(float Dt)
{
    Super::Tick(Dt);SurfaceTimer+=Dt;
    if(!bFirstPerson)CameraBoom->SocketOffset=FMath::VInterpTo(CameraBoom->SocketOffset,FVector(0,bRightShoulder?48:-48,8),Dt,10);
    if(SurfaceTimer>.25f){SurfaceTimer=0;UpdateSurface();}
    // The installed walk and run clips are authored near 1.8 and 4.2 m/s.
    if(Body&&Locomotion&&Body->GetSingleNodeInstance())Body->GetSingleNodeInstance()->SetBlendSpacePosition(FVector(GetVelocity().Size2D(),0,0));
    if(bCheck)CheckRuntime(Dt);
}
void APardeepPlayer::CheckRuntime(float Dt)
{
    Elapsed+=Dt;
    if(Elapsed<20)return;
    if(Elapsed<24){GetCharacterMovement()->MaxWalkSpeed=180;AddMovementInput(FVector(0,1,0),1);}
    else if(Elapsed<27){GetCharacterMovement()->MaxWalkSpeed=420;AddMovementInput(FVector(0,1,0),1);}
    else if(Elapsed<31){GetCharacterMovement()->MaxWalkSpeed=180;AddMovementInput(FVector(0,-1,0),1);}
    bGrounded&=GetCharacterMovement()->IsMovingOnGround();
    const float Speed=GetVelocity().Size2D();bWalkingSeen|=Speed>100&&Speed<250;bRunningSeen|=Speed>300;
    if(Elapsed>20+Dt*2)Travel+=FVector::Dist2D(GetActorLocation(),LastPosition);LastPosition=GetActorLocation();
    if(Body){const FVector Foot=Body->GetSocketTransform(TEXT("foot_l"),RTS_Component).GetTranslation();if(bHaveFoot)FootTravel+=FVector::Dist(Foot,LastFoot);LastFoot=Foot;bHaveFoot=true;}
    const FString Out=FPaths::ProjectSavedDir()/TEXT("PardeepPlayer");IFileManager::Get().MakeDirectory(*Out,true);
    if(Elapsed>23&&Elapsed-Dt<=23)FScreenshotRequest::RequestScreenshot(Out/TEXT("third_person_walk.png"),true,false);
    if(Elapsed>32&&Elapsed-Dt<=32)SwapShoulder();
    if(Elapsed>33&&Elapsed-Dt<=33)FScreenshotRequest::RequestScreenshot(Out/TEXT("third_person_idle.png"),true,false);
    if(Elapsed>35)
    {
        const bool Passed=Body&&Locomotion&&bGrounded&&bWalkingSeen&&bRunningSeen&&Travel>1200&&FootTravel>100&&CameraBoom->bDoCollisionTest;
        const FString Json=FString::Printf(TEXT("{\"passed\":%s,\"third_person\":true,\"camera_collision_enabled\":%s,\"grounded\":%s,\"walk_seen\":%s,\"run_seen\":%s,\"travel_cm\":%.2f,\"foot_motion_cm\":%.2f,\"appearance\":\"provisional existing pilot; owner reference pending\"}"),Passed?TEXT("true"):TEXT("false"),CameraBoom->bDoCollisionTest?TEXT("true"):TEXT("false"),bGrounded?TEXT("true"):TEXT("false"),bWalkingSeen?TEXT("true"):TEXT("false"),bRunningSeen?TEXT("true"):TEXT("false"),Travel,FootTravel);
        FFileHelper::SaveStringToFile(Json,*(Out/TEXT("runtime_check.json")));
        UE_LOG(LogTemp,Display,TEXT("PARDEEP_RUNTIME %s"),*Json);bCheck=false;FPlatformMisc::RequestExitWithStatus(false,Passed?0:1);
    }
}
void APardeepPlayer::EndPlay(const EEndPlayReason::Type Reason){if(Visual)Visual->Destroy();Super::EndPlay(Reason);}
void APardeepVillageHUD::DrawHUD()
{
    Super::DrawHUD();if(!Canvas||IsMapOpen())return;
    auto* Player=Cast<APardeepPlayer>(GetOwningPawn());if(!Player)return;
    const float W=Canvas->ClipX;const FLinearColor Accent(.22f,.85f,.76f),Text(.9f,.95f,.93f);
    DrawRect(FLinearColor(.018f,.045f,.045f,.9f),26,112,380,88);
    DrawText(TEXT("PARDEEP  /  APPEARANCE PREVIEW"),Accent,40,122,nullptr,.95f);
    DrawText(Player->SurfaceName+FString::Printf(TEXT("  |  %.1f km/h"),Player->GetVelocity().Size2D()*.036f),Text,40,148,nullptr,.9f);
    DrawText(TEXT("V camera view   Q swap shoulder   Space jump"),Text,40,174,nullptr,.8f);
    const float Yaw=GetOwningPlayerController()->GetControlRotation().Yaw;
    // Project axes are +X east and +Y north, unlike Unreal's conventional compass.
    const float Bearing=FMath::Fmod(450.f-Yaw,360.f);
    DrawRect(FLinearColor(.018f,.045f,.045f,.9f),W/2-85,22,170,32);
    DrawText(FString::Printf(TEXT("HEADING  %03.0f deg"),Bearing),Accent,W/2-72,28,nullptr,.85f);
}
APardeepVillageGameMode::APardeepVillageGameMode(){DefaultPawnClass=APardeepPlayer::StaticClass();HUDClass=APardeepVillageHUD::StaticClass();}

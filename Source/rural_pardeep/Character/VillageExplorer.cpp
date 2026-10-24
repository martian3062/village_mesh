#include "Character/VillageExplorer.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/Canvas.h"
#include "EngineUtils.h"
#include "Environment/WeatherManager.h"
#include "Environment/VillageDoor.h"
#include "Environment/VillageDiagnostics.h"
#include "V25/VillageLife.h"
#include "V3/VillageAtlas.h"
#include "TimerManager.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "PhysicsEngine/PhysicsHandleComponent.h"
#if !UE_BUILD_SHIPPING
#include "Environment/VillagePhysicsProp.h"
#include "Components/StaticMeshComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HighResScreenshot.h"
#include "UnrealClient.h"
#endif

AVillageExplorer::AVillageExplorer()
{
    PrimaryActorTick.bCanEverTick = true;
    GetCapsuleComponent()->InitCapsuleSize(34.f, 88.f);
    GetCharacterMovement()->MaxWalkSpeed = 420.f;
    GetCharacterMovement()->JumpZVelocity = 440.f;
    GetCharacterMovement()->AirControl = 0.2f;
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
    Camera->SetupAttachment(GetCapsuleComponent());
    Camera->SetRelativeLocation(FVector(0, 0, 70));
    Camera->bUsePawnControlRotation = true;
    Camera->FieldOfView = 85.f;
    GrabHandle = CreateDefaultSubobject<UPhysicsHandleComponent>(TEXT("GrabHandle"));
    GrabHandle->InterpolationSpeed = 12.f;
}

void AVillageExplorer::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindAxis(TEXT("VM_Forward"), this, &AVillageExplorer::Forward);
    Input->BindAxis(TEXT("VM_Right"), this, &AVillageExplorer::Right);
    Input->BindAxis(TEXT("VM_Turn"), this, &AVillageExplorer::Turn);
    Input->BindAxis(TEXT("VM_Look"), this, &AVillageExplorer::LookUp);
    Input->BindKey(EKeys::SpaceBar, IE_Pressed, this, &ACharacter::Jump);
    Input->BindKey(EKeys::SpaceBar, IE_Released, this, &ACharacter::StopJumping);
    Input->BindKey(EKeys::LeftShift, IE_Pressed, this, &AVillageExplorer::SprintOn);
    Input->BindKey(EKeys::LeftShift, IE_Released, this, &AVillageExplorer::SprintOff);
    Input->BindKey(EKeys::E, IE_Pressed, this, &AVillageExplorer::GrabOrRelease);
    Input->BindKey(EKeys::RightMouseButton, IE_Pressed, this, &AVillageExplorer::Throw);
    Input->BindKey(EKeys::F6, IE_Pressed, this, &AVillageExplorer::CycleWeather);
    Input->BindKey(EKeys::F7, IE_Pressed, this, &AVillageExplorer::AdvanceTime);
    Input->BindKey(EKeys::F8, IE_Pressed, this, &AVillageExplorer::VisitPhysicsYard);
    Input->BindKey(EKeys::F9, IE_Pressed, this, &AVillageExplorer::ToggleOverview);
    Input->BindKey(EKeys::F10, IE_Pressed, this, &AVillageExplorer::VisitPilotRoom);
    auto BindAtlas=[&](FKey Key,TFunction<void(AVillageAtlasHUD*)> Callback)
    {
        FInputKeyBinding Binding(FInputChord(Key),IE_Pressed);
        Binding.KeyDelegate.GetDelegateForManualSet().BindLambda([this,Callback]()
        {if(auto* PC=Cast<APlayerController>(Controller))if(auto* H=Cast<AVillageAtlasHUD>(PC->GetHUD()))Callback(H);});
        Input->KeyBindings.Add(MoveTemp(Binding));
    };
    BindAtlas(EKeys::M,[](AVillageAtlasHUD* H){H->ToggleMap();});
    BindAtlas(EKeys::Tab,[](AVillageAtlasHUD* H){H->SelectNext();});
    BindAtlas(EKeys::Enter,[](AVillageAtlasHUD* H){H->VisitSelected();});
    BindAtlas(EKeys::LeftMouseButton,[](AVillageAtlasHUD* H){H->SelectAtCursor();});
    BindAtlas(EKeys::MouseScrollUp,[](AVillageAtlasHUD* H){H->Zoom(1);});
    BindAtlas(EKeys::MouseScrollDown,[](AVillageAtlasHUD* H){H->Zoom(-1);});
    auto BindV25=[&](FKey Key,TFunction<void(AVillageLifeDirector*)> Callback)
    {
        FInputKeyBinding Binding(FInputChord(Key),IE_Pressed);
        Binding.KeyDelegate.GetDelegateForManualSet().BindLambda([this,Callback](){if(auto* Life=AVillageLifeDirector::Find(GetWorld()))Callback(Life);});
        Input->KeyBindings.Add(MoveTemp(Binding));
    };
    BindV25(EKeys::T,[](AVillageLifeDirector* L){L->Talk();});
    BindV25(EKeys::F11,[](AVillageLifeDirector* L){L->VisitFarm();});
    BindV25(EKeys::F5,[](AVillageLifeDirector* L){L->TogglePolicy();});
    const FKey Choices[]={EKeys::One,EKeys::Two,EKeys::Three,EKeys::Four,EKeys::Five};
    for(int i=0;i<5;++i)BindV25(Choices[i],[i](AVillageLifeDirector* L){L->DialogueChoice(i+1);});
}

void AVillageExplorer::BeginPlay()
{
    Super::BeginPlay();
    if (GetWorld()->GetMapName().Contains(TEXT("PandoriV2"))||GetWorld()->GetMapName().Contains(TEXT("PandoriV3")))
    {
        FString Text;TSharedPtr<FJsonObject> Manifest;
        if (FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Validation/pilot.json"))) &&
            FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Manifest))
        {
            for (const auto& Value : Manifest->GetArrayField(TEXT("interiors")))
            {
                const auto Space=Value->AsObject();
                const auto& Outside=Space->GetArrayField(TEXT("outside_cm"));
                const auto& Inside=Space->GetArrayField(TEXT("inside_cm"));
                PilotRoomStops.Add(FVector(Outside[0]->AsNumber(),Outside[1]->AsNumber(),Outside[2]->AsNumber()));
                PilotRoomTargets.Add(FVector(Inside[0]->AsNumber(),Inside[1]->AsNumber(),Inside[2]->AsNumber()));
            }
        }
    }
#if !UE_BUILD_SHIPPING
    const FString Arguments(FCommandLine::Get());
    if (Arguments.Contains(TEXT("-VillageV2Capture="))||Arguments.Contains(TEXT("-VillageV2Route="))||Arguments.Contains(TEXT("-VillageV2Interactions="))||Arguments.Contains(TEXT("-VillageV2Soak=")))
        GetWorldTimerManager().SetTimerForNextTick([this]() { GetWorld()->SpawnActor<AVillageDiagnostics>(); });
#endif
    if((AVillageLifeDirector::Enabled()&&GetWorld()->GetMapName().Contains(TEXT("PandoriV2")))||GetWorld()->GetMapName().Contains(TEXT("PandoriV3")))
        GetWorldTimerManager().SetTimerForNextTick([this](){GetWorld()->SpawnActor<AVillageLifeDirector>();});
}
void AVillageExplorer::Forward(float V) { const FRotator R(0,Controller?Controller->GetControlRotation().Yaw:GetActorRotation().Yaw,0);AddMovementInput(R.Vector(), V); }
void AVillageExplorer::Right(float V) { const FRotator R(0,Controller?Controller->GetControlRotation().Yaw:GetActorRotation().Yaw,0);AddMovementInput(FRotationMatrix(R).GetUnitAxis(EAxis::Y), V); }
void AVillageExplorer::Turn(float V) { AddControllerYawInput(V); }
void AVillageExplorer::LookUp(float V) { AddControllerPitchInput(V); }
void AVillageExplorer::SprintOn() { GetCharacterMovement()->MaxWalkSpeed = RunningSpeed; }
void AVillageExplorer::SprintOff() { GetCharacterMovement()->MaxWalkSpeed = WalkingSpeed; }

void AVillageExplorer::GrabOrRelease()
{
    if (GrabHandle->GetGrabbedComponent()) { GrabHandle->ReleaseComponent(); return; }
    const FVector Start = Camera->GetComponentLocation();
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageGrab), false, this);
    if (GetWorld()->LineTraceSingleByChannel(Hit, Start,
        Start + Camera->GetForwardVector() * 900.f, ECC_Visibility, Query) && FVector::Dist(Hit.ImpactPoint,GetActorLocation())<=440.f)
    {
        if (AVillageDoor* Door = Cast<AVillageDoor>(Hit.GetActor()))
        {
            Door->Toggle();
            return;
        }
        UPrimitiveComponent* Component = Hit.GetComponent();
        if (Component && Component->IsSimulatingPhysics() && Component->GetMass() <= 40.f)
            GrabHandle->GrabComponentAtLocationWithRotation(Component, NAME_None,
                Hit.ImpactPoint, Component->GetComponentRotation());
    }
}
void AVillageExplorer::Throw()
{
    UPrimitiveComponent* Component = GrabHandle->GetGrabbedComponent();
    if (!Component) return;
    GrabHandle->ReleaseComponent();
    Component->AddImpulse(Camera->GetForwardVector() * Component->GetMass() * 650.f);
}
void AVillageExplorer::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
#if !UE_BUILD_SHIPPING
    if (FParse::Param(FCommandLine::Get(), TEXT("VillageMeshSmoke")))
    {
        SmokeElapsed += DeltaSeconds;
        if (SmokeElapsed > 35.f && !bSmokeChecked)
        {
            bSmokeChecked = true;
            bool bPass = GetCharacterMovement()->IsMovingOnGround() && FMath::Abs(GetActorLocation().Z - 90.f) < 20.f;
            int32 PropCount = 0;
            for (TActorIterator<AVillagePhysicsProp> It(GetWorld()); It; ++It)
            {
                ++PropCount;
                const FVector Position = It->GetActorLocation();
                bPass &= It->Body->IsSimulatingPhysics() && !Position.ContainsNaN() && Position.Z > -10.f && Position.Z < 300.f;
                if (It->bEnableBuoyancy) bPass &= Position.Z > It->WaterLevelCm - 70.f;
            }
            int32 Instances = 0;
            for (TActorIterator<AActor> It(GetWorld()); It; ++It)
            {
                TArray<UInstancedStaticMeshComponent*> Components;
                It->GetComponents(Components);
                for (const auto* Component : Components) Instances += Component->GetInstanceCount();
            }
            bPass &= PropCount == 13 && Instances > 50;
            const FString Result = FString::Printf(TEXT("{\"passed\":%s,\"physics_props\":%d,\"pcg_instances\":%d,\"player_z_cm\":%.2f}"),
                bPass ? TEXT("true") : TEXT("false"), PropCount, Instances, GetActorLocation().Z);
            FFileHelper::SaveStringToFile(Result, *(FPaths::ProjectSavedDir() / TEXT("VillageMeshGenerated/runtime_smoke.json")));
            UE_LOG(LogTemp, Display, TEXT("VILLAGE_MESH_SMOKE %s"), *Result);
            if (!bPass) { FPlatformMisc::RequestExitWithStatus(false, 1); return; }
            if (FParse::Param(FCommandLine::Get(), TEXT("VillageMeshOverview"))) ToggleOverview();
        }
        if (SmokeElapsed > 40.f && !bSmokeCaptured)
        {
            bSmokeCaptured = true;
            const TCHAR* Name = bOverview ? TEXT("VillageMeshGenerated/overview.png") : TEXT("VillageMeshGenerated/playable.png");
            FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir() / Name, true, false);
        }
        if (SmokeElapsed > 45.f) FPlatformMisc::RequestExitWithStatus(false, 0);
    }
#endif
    if (UPrimitiveComponent* Held = GrabHandle->GetGrabbedComponent())
    {
        const FVector Start = GetActorLocation()+FVector(0,0,60);
        const FVector Target = Start + Camera->GetForwardVector() * 220.f;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageGrabTarget), false, this);
        Query.AddIgnoredActor(Held->GetOwner());
        FHitResult Hit;
        GetWorld()->LineTraceSingleByChannel(Hit, Start, Target, ECC_Visibility, Query);
        if (FVector::Dist(Held->GetComponentLocation(), Start) > 550.f)
            GrabHandle->ReleaseComponent();
        else
            GrabHandle->SetTargetLocation(Hit.bBlockingHit ? Hit.ImpactPoint + Hit.ImpactNormal * 60.f : Target);
    }
}
void AVillageExplorer::EndPlay(const EEndPlayReason::Type Reason)
{
    GrabHandle->ReleaseComponent();
    Super::EndPlay(Reason);
}
void AVillageExplorer::CycleWeather()
{
    for (TActorIterator<AWeatherManager> It(GetWorld()); It; ++It)
        It->SetWeather(static_cast<EVillageWeather>((static_cast<uint8>(It->GetCurrentWeather()) + 1) % 4));
}
void AVillageExplorer::AdvanceTime()
{
    if(auto* Life=AVillageLifeDirector::Find(GetWorld())){Life->AdvanceClock();return;}
    for (TActorIterator<AWeatherManager> It(GetWorld()); It; ++It)
        It->TimeOfDayHours = FMath::Fmod(It->TimeOfDayHours + 3.f, 24.f);
}
void AVillageExplorer::VisitPhysicsYard()
{
    if (!GetWorld()->GetMapName().Contains(TEXT("Pandori"))) return;
    if (bOverview) ToggleOverview();
    GrabHandle->ReleaseComponent();
    bAtPhysicsYard = !bAtPhysicsYard;
    SetActorLocation(bAtPhysicsYard ? FVector(-47500,-42500,100) : FVector(600,2080,100));
    GetCharacterMovement()->StopMovementImmediately();
    if (Controller) Controller->SetControlRotation(FRotator(0,bAtPhysicsYard ? 90 : 187,0));
}
void AVillageExplorer::ToggleOverview()
{
    GrabHandle->ReleaseComponent();
    bOverview = !bOverview;
    if (bOverview)
    {
        OverviewReturnPosition = GetActorLocation();
        OverviewReturnRotation = Controller ? Controller->GetControlRotation() : FRotator::ZeroRotator;
        GetCharacterMovement()->SetMovementMode(MOVE_Flying);
        SetActorLocation(FVector(0,-45000,42000));
        if (Controller)
        {
            if (APlayerController* Player = Cast<APlayerController>(Controller))
                Player->ConsoleCommand(GetWorld()->GetMapName().Contains(TEXT("PandoriV2"))
                    ? TEXT("wp.Runtime.OverrideRuntimeSpatialHashLoadingRange -grid=0 -range=30000")
                    : TEXT("wp.Runtime.OverrideRuntimeSpatialHashLoadingRange -grid=0 -range=180000"), true);
            Controller->SetControlRotation(FRotator(-50,90,0));
        }
    }
    else
    {
        SetActorLocation(OverviewReturnPosition);
        if (Controller)
        {
            Controller->SetControlRotation(OverviewReturnRotation);
            if (APlayerController* Player = Cast<APlayerController>(Controller)) Player->ConsoleCommand(TEXT("wp.Runtime.OverrideRuntimeSpatialHashLoadingRange -grid=0 -range=25600"), true);
        }
        GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    }
    GetCharacterMovement()->StopMovementImmediately();
}

void AVillageExplorer::VisitPilotRoom()
{
    if (PilotRoomStops.IsEmpty()) return;
    if (bOverview) ToggleOverview();
    GrabHandle->ReleaseComponent();
    const int32 Index=PilotRoomIndex++ % PilotRoomStops.Num();
    SetActorLocation(PilotRoomStops[Index],false,nullptr,ETeleportType::TeleportPhysics);
    GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    GetCharacterMovement()->StopMovementImmediately();
    if (Controller) Controller->SetControlRotation((PilotRoomTargets[Index]-PilotRoomStops[Index]).Rotation());
}
void AVillageExplorerHUD::DrawHUD()
{
    Super::DrawHUD();
    if (!Canvas) return;
    DrawRect(FLinearColor(0.02f, 0.03f, 0.025f, 0.65f), 24, 24, 480, 66);
    const bool bPandori = GetWorld()->GetMapName().Contains(TEXT("Pandori"));
    DrawText(GetWorld()->GetMapName().Contains(TEXT("PandoriV2")) ? TEXT("PANDORI NIJJARAN  /  V2 PILOT") : bPandori ? TEXT("PANDORI NIJJARAN  /  144102") : TEXT("VILLAGE MESH  /  OPEN WORLD"), FLinearColor(0.93f, 0.85f, 0.62f), 40, 34, nullptr, 1.2f);
    DrawText(TEXT("WASD walk  |  Shift run  |  Space jump"), FLinearColor::White, 40, 60);
    if(auto* Life=AVillageLifeDirector::Find(GetWorld()))
    {
        DrawRect(FLinearColor(.02f,.025f,.02f,.75f),Canvas->ClipX-600,24,575,112);
        DrawText(Life->HUDStatus(),FLinearColor(.92f,.89f,.73f),Canvas->ClipX-585,34,nullptr,.9f);
    }
    DrawText(TEXT("E door/grab/drop | RMB throw | F6 weather | F7 time | F8 yard | F9 overview | F10 rooms"),
        FLinearColor::White, 30, Canvas->ClipY - 50);
    if (bPandori) DrawText(TEXT("Map: (c) OpenStreetMap contributors, Overture Maps | Building sources: Microsoft / Google | ODbL / CC BY 4.0"),
        FLinearColor(0.8f,0.8f,0.8f), 30, Canvas->ClipY - 26, nullptr, 0.8f);
    DrawRect(FLinearColor(1, 1, 1, 0.65f), Canvas->ClipX * 0.5f - 2, Canvas->ClipY * 0.5f - 2, 4, 4);
}
AVillageExplorerGameMode::AVillageExplorerGameMode()
{
    DefaultPawnClass = AVillageExplorer::StaticClass();
    HUDClass = AVillageExplorerHUD::StaticClass();
}

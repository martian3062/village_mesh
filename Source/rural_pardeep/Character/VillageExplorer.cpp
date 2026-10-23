#include "Character/VillageExplorer.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/InputComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/Canvas.h"
#include "EngineUtils.h"
#include "Environment/WeatherManager.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "PhysicsEngine/PhysicsHandleComponent.h"
#if !UE_BUILD_SHIPPING
#include "Environment/VillagePhysicsProp.h"
#include "Components/StaticMeshComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
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
}
void AVillageExplorer::Forward(float V) { AddMovementInput(GetActorForwardVector(), V); }
void AVillageExplorer::Right(float V) { AddMovementInput(GetActorRightVector(), V); }
void AVillageExplorer::Turn(float V) { AddControllerYawInput(V); }
void AVillageExplorer::LookUp(float V) { AddControllerPitchInput(V); }
void AVillageExplorer::SprintOn() { GetCharacterMovement()->MaxWalkSpeed = 720.f; }
void AVillageExplorer::SprintOff() { GetCharacterMovement()->MaxWalkSpeed = 420.f; }

void AVillageExplorer::GrabOrRelease()
{
    if (GrabHandle->GetGrabbedComponent()) { GrabHandle->ReleaseComponent(); return; }
    const FVector Start = Camera->GetComponentLocation();
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageGrab), false, this);
    if (GetWorld()->LineTraceSingleByChannel(Hit, Start,
        Start + Camera->GetForwardVector() * 400.f, ECC_Visibility, Query))
    {
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
        const FVector Start = Camera->GetComponentLocation();
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
            if (APlayerController* Player = Cast<APlayerController>(Controller)) Player->ConsoleCommand(TEXT("wp.Runtime.OverrideRuntimeSpatialHashLoadingRange -grid=0 -range=180000"), true);
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
void AVillageExplorerHUD::DrawHUD()
{
    Super::DrawHUD();
    if (!Canvas) return;
    DrawRect(FLinearColor(0.02f, 0.03f, 0.025f, 0.65f), 24, 24, 480, 66);
    const bool bPandori = GetWorld()->GetMapName().Contains(TEXT("Pandori"));
    DrawText(bPandori ? TEXT("PANDORI NIJJARAN  /  144102") : TEXT("VILLAGE MESH  /  OPEN WORLD"), FLinearColor(0.93f, 0.85f, 0.62f), 40, 34, nullptr, 1.2f);
    DrawText(TEXT("WASD walk  |  Shift run  |  Space jump"), FLinearColor::White, 40, 60);
    DrawText(TEXT("E grab/drop | RMB throw | F6 weather | F7 time | F8 physics yard | F9 overview"),
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

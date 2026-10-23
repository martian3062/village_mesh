#include "Environment/VillageDiagnostics.h"
#include "Character/VillageExplorer.h"
#include "Environment/WeatherManager.h"
#include "Environment/VillageDoor.h"
#include "Camera/CameraComponent.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMemory.h"
#include "UnrealClient.h"
#include "Algo/Reverse.h"

namespace
{
FVector ReadVector(const TArray<TSharedPtr<FJsonValue>>& V)
{
    return FVector(V[0]->AsNumber(),V[1]->AsNumber(),V[2]->AsNumber());
}
}

AVillageDiagnostics::AVillageDiagnostics() { PrimaryActorTick.bCanEverTick = true; }

void AVillageDiagnostics::BeginPlay()
{
    Super::BeginPlay();
    if (FParse::Value(FCommandLine::Get(),TEXT("VillageV2Capture="),Condition)) Mode=TEXT("capture");
    else if (FParse::Value(FCommandLine::Get(),TEXT("VillageV2Route="),Condition)) Mode=TEXT("route");
    else if (FParse::Value(FCommandLine::Get(),TEXT("VillageV2Interactions="),Condition)) Mode=TEXT("interactions");
    else if (FParse::Value(FCommandLine::Get(),TEXT("VillageV2Soak="),Condition)) Mode=TEXT("soak");
    else { Destroy(); return; }
    StartedWallTime=FPlatformTime::Seconds();
    FParse::Value(FCommandLine::Get(),TEXT("VillageSoakMinutes="),SoakMinutes);
    SoakMinutes=FMath::Clamp(SoakMinutes,1.f,120.f);
    if (!FParse::Value(FCommandLine::Get(),TEXT("VillageRunId="),RunId)) RunId=TEXT("local");
    // Filenames cannot escape the evidence directory.
    for (TCHAR& Ch : RunId) if (!FChar::IsAlnum(Ch) && Ch != TEXT('_') && Ch != TEXT('-')) Ch=TEXT('_');
    if (Condition!=TEXT("daylight") && Condition!=TEXT("evening") && Condition!=TEXT("overcast") && Condition!=TEXT("rain"))
    { Finish(false,TEXT("Unknown presentation condition")); return; }
    FString Text;
    if (!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("Validation/pilot.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Input))
    { Finish(false,TEXT("Missing or invalid pilot manifest")); return; }
    Player=Cast<AVillageExplorer>(UGameplayStatics::GetPlayerPawn(this,0));
    for (TActorIterator<AWeatherManager> It(GetWorld());It;++It) { Weather=*It;break; }
    if (!Player || !Weather) { Finish(false,TEXT("Missing explorer or weather actor"));return; }
    Weather->SetPresentationCondition(FName(*Condition));
    for (const auto& Point : Input->GetObjectField(TEXT("route"))->GetArrayField(TEXT("points_cm"))) Route.Add(ReadVector(Point->AsArray()));
    PreviousWallTime=FPlatformTime::Seconds();
    IFileManager::Get().MakeDirectory(*(FPaths::ProjectSavedDir()/TEXT("VillageMeshV2")),true);
    if (Mode==TEXT("capture")) CaptureCamera(0);
}

void AVillageDiagnostics::CaptureCamera(int32 CameraIndex)
{
    const auto Camera=Input->GetArrayField(TEXT("cameras"))[CameraIndex]->AsObject();
    const FVector Position=ReadVector(Camera->GetArrayField(TEXT("position_cm")));
    Player->GetCharacterMovement()->SetMovementMode(MOVE_Flying);
    // Manifest gives eye position; the first-person camera is 70 cm above the pawn.
    Player->SetActorLocation(Position-FVector(0,0,70),false,nullptr,ETeleportType::TeleportPhysics);
    Player->GetCharacterMovement()->StopMovementImmediately();
    if (auto* View=Player->FindComponentByClass<UCameraComponent>()) View->SetFieldOfView(Camera->GetNumberField(TEXT("fov_degrees")));
    if (auto* Controller=Cast<APlayerController>(Player->GetController()))
        Controller->SetControlRotation(FRotator(Camera->GetNumberField(TEXT("pitch_degrees")),Camera->GetNumberField(TEXT("yaw_degrees")),0));
}

void AVillageDiagnostics::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (bFinished || !Player || !Input.IsValid()) return;
    Elapsed+=DeltaSeconds;StageElapsed+=DeltaSeconds;
    const double Now=FPlatformTime::Seconds();
    const double WallDelta=(Now-PreviousWallTime)*1000.;PreviousWallTime=Now;
    PeakMemory=FMath::Max(PeakMemory,FPlatformMemory::GetStats().UsedPhysical);
    if (Mode==TEXT("soak") && Now>=NextMemorySample)
    {
        auto Sample=MakeShared<FJsonObject>();
        Sample->SetNumberField(TEXT("wall_seconds"),Now-StartedWallTime);
        Sample->SetNumberField(TEXT("process_physical_bytes"),double(FPlatformMemory::GetStats().UsedPhysical));
        MemorySamples.Add(MakeShared<FJsonValueObject>(Sample));NextMemorySample=Now+60.;
    }
    if (Elapsed>20.f) FrameTimes.Add(WallDelta);
    if (Mode!=TEXT("soak") && Elapsed>240.f) { Finish(false,TEXT("Run timed out"));return; }
    if (Elapsed<20.f) return;
    if (Mode!=TEXT("soak") && Weather->bUseGeographicSun && Condition==TEXT("daylight") && Weather->EnvironmentState.SunElevationDegrees<=0.f)
    { Finish(false,TEXT("Daylight preset has a nonpositive solar elevation"));return; }
    if (Mode==TEXT("capture"))
    {
        if (bStarted)
        {
            if (StageElapsed < .5f) return;
            if (Index>=Input->GetArrayField(TEXT("cameras")).Num()) { Finish(true,TEXT("Eight fixed camera captures requested"));return; }
            CaptureCamera(Index);bStarted=false;StageElapsed=0;return;
        }
        if (StageElapsed<6.f) return;
        const FString File=FPaths::ProjectSavedDir()/TEXT("VillageMeshV2")/
            FString::Printf(TEXT("%s_%02d.png"),*Condition,Index+1);
        FScreenshotRequest::RequestScreenshot(File,true,false);
        ++Index;StageElapsed=0;
        // Change camera on a later frame so the queued screenshot uses this view.
        bStarted=true;
    }
    else if (Mode==TEXT("route") || Mode==TEXT("soak"))
    {
        if (!bStarted)
        {
            bStarted=true;Index=1;Player->SetActorLocation(Route[0],false,nullptr,ETeleportType::TeleportPhysics);
            Player->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
            PreviousPosition=Player->GetActorLocation();StageElapsed=0;
            SoakStartedWallTime=Now;
        }
        if (Mode==TEXT("soak") && Now-SoakStartedWallTime>=SoakMinutes*60.)
        { Finish(true,TEXT("Continuous route and weather soak completed"));return; }
        if (Index>=Route.Num())
        {
            if (Mode==TEXT("route")) { Finish(true,TEXT("Collision-aware walking route completed"));return; }
            ++CompletedLegs;Algo::Reverse(Route);Index=1;
            const FName Conditions[]={TEXT("daylight"),TEXT("overcast"),TEXT("rain"),TEXT("evening")};
            Weather->SetPresentationCondition(Conditions[CompletedLegs%4]);
            UE_LOG(LogTemp,Display,TEXT("VILLAGE_V2_SOAK leg=%d wall_seconds=%.1f"),CompletedLegs,Now-SoakStartedWallTime);
        }
        FVector Direction=Route[Index]-Player->GetActorLocation();Direction.Z=0;
        if (Direction.Size()<48.f) { ++Index;return; }
        if (auto* Controller=Player->GetController()) Controller->SetControlRotation(Direction.Rotation());
        Player->AddMovementInput(Direction.GetSafeNormal(),1.f,true);
        const float Moved=FVector::Dist2D(PreviousPosition,Player->GetActorLocation());
        StuckSeconds=Moved<FMath::Max(.001f,DeltaSeconds*10.f) ? StuckSeconds+DeltaSeconds : 0.f;
        PreviousPosition=Player->GetActorLocation();
        if (StuckSeconds>8.f) Finish(false,FString::Printf(TEXT("Blocked at route point %d"),Index));
        if (Player->GetActorLocation().Z< -100.f) Finish(false,TEXT("Fell below terrain"));
    }
    else if (Mode==TEXT("interactions"))
    {
        const auto& Spaces=Input->GetArrayField(TEXT("interiors"));
        if (Index>=Spaces.Num()) { Finish(true,TEXT("Three doors, entrances and shelter checks passed"));return; }
        const auto Space=Spaces[Index]->AsObject();
        if (!bStarted)
        {
            bStarted=true;StageElapsed=0;
            Player->SetActorLocation(ReadVector(Space->GetArrayField(TEXT("outside_cm"))),false,nullptr,ETeleportType::TeleportPhysics);
            return;
        }
        if (StageElapsed<4.f) return;
        AVillageDoor* Door=nullptr;
        for (TActorIterator<AVillageDoor> It(GetWorld());It;++It)
            if (It->PersistentId==Space->GetStringField(TEXT("door_id"))) { Door=*It;break; }
        if (!Door) { Finish(false,TEXT("Interior door not streamed in"));return; }
        if (StageElapsed<5.f) { if (!Door->IsOpen()) Door->Toggle(); return; }
        FVector Destination=ReadVector(Space->GetArrayField(TEXT("inside_cm")));
        FVector Direction=Destination-Player->GetActorLocation();Direction.Z=0;
        if (Direction.Size()>40.f)
        {
            Player->AddMovementInput(Direction.GetSafeNormal(),.5f,true);
            if (StageElapsed>15.f) Finish(false,TEXT("Entrance blocked by collision"));
            return;
        }
        if (!Weather->IsShelteredAt(Player->GetActorLocation())) { Finish(false,TEXT("Interior failed roof shelter test"));return; }
        if (!GetWorld()->GetSubsystem<UVillageDoorState>()->OpenDoors.FindRef(Door->PersistentId))
        { Finish(false,TEXT("Door state missing from streaming persistence store"));return; }
        ++Index;bStarted=false;StageElapsed=0;
    }
}

void AVillageDiagnostics::Finish(bool bPass,const FString& Reason)
{
    if (bFinished) return;
    bFinished=true;
    FrameTimes.Sort();
    const auto Percentile=[&](double P) { return FrameTimes.IsEmpty()?0.:FrameTimes[FMath::Clamp(FMath::CeilToInt((FrameTimes.Num()-1)*P),0,FrameTimes.Num()-1)]; };
    auto Report=MakeShared<FJsonObject>();
    Report->SetBoolField(TEXT("passed"),bPass);Report->SetStringField(TEXT("reason"),Reason);
    Report->SetStringField(TEXT("mode"),Mode);Report->SetStringField(TEXT("condition"),Condition);
    Report->SetStringField(TEXT("run_id"),RunId);Report->SetStringField(TEXT("map"),GetWorld()->GetMapName());
    Report->SetNumberField(TEXT("simulation_seconds"),Elapsed);Report->SetNumberField(TEXT("samples"),FrameTimes.Num());
    Report->SetNumberField(TEXT("wall_seconds"),FPlatformTime::Seconds()-StartedWallTime);
    if (Mode==TEXT("soak"))
    {
        Report->SetNumberField(TEXT("requested_soak_minutes"),SoakMinutes);
        Report->SetNumberField(TEXT("soak_wall_seconds"),FPlatformTime::Seconds()-SoakStartedWallTime);
        Report->SetNumberField(TEXT("completed_route_legs"),CompletedLegs);
        Report->SetArrayField(TEXT("memory_samples"),MemorySamples);
        Report->SetStringField(TEXT("weather_sequence"),TEXT("daylight, overcast, rain, evening; changes after each route leg"));
    }
    Report->SetNumberField(TEXT("median_frame_ms"),Percentile(.5));Report->SetNumberField(TEXT("p95_frame_ms"),Percentile(.95));
    Report->SetNumberField(TEXT("p99_frame_ms"),Percentile(.99));Report->SetNumberField(TEXT("max_frame_ms"),Percentile(1));
    Report->SetNumberField(TEXT("peak_process_physical_bytes"),double(PeakMemory));
    const bool bRendered = !FParse::Param(FCommandLine::Get(),TEXT("NullRHI"));
    Report->SetBoolField(TEXT("rendered"),bRendered);
    if (Mode==TEXT("route") && bRendered) Report->SetBoolField(TEXT("p95_target_met"),!FrameTimes.IsEmpty()&&Percentile(.95)<=33.3);
    else Report->SetField(TEXT("p95_target_met"),MakeShared<FJsonValueNull>());
    Report->SetNumberField(TEXT("point_index"),Index);
    if (Weather)
    {
        Report->SetNumberField(TEXT("sun_elevation_degrees"),Weather->EnvironmentState.SunElevationDegrees);
        Report->SetNumberField(TEXT("local_hour_utc_plus_5_5"),Weather->TimeOfDayHours);
        Report->SetNumberField(TEXT("wetness"),Weather->EnvironmentState.Wetness);
        Report->SetBoolField(TEXT("player_sheltered"),Weather->EnvironmentState.bPlayerSheltered);
    }
    if (Player) Report->SetArrayField(TEXT("player_position_cm"),{MakeShared<FJsonValueNumber>(Player->GetActorLocation().X),MakeShared<FJsonValueNumber>(Player->GetActorLocation().Y),MakeShared<FJsonValueNumber>(Player->GetActorLocation().Z)});
    Report->SetStringField(TEXT("measurement_scope"),TEXT("Observed frame wall time after 20 simulation-second warmup. No separate CPU/GPU timing or VRAM metric. Captures and interaction runs are not traversal benchmarks."));
    Report->SetBoolField(TEXT("editor_build"),WITH_EDITOR != 0);
    FString Text;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Text));
    const FString Folder=FPaths::ProjectSavedDir()/TEXT("VillageMeshV2");IFileManager::Get().MakeDirectory(*Folder,true);
    FFileHelper::SaveStringToFile(Text,*(Folder/(Mode+TEXT("_")+Condition+TEXT("_")+RunId+TEXT(".json"))));
    UE_LOG(LogTemp,Display,TEXT("VILLAGE_V2_DIAGNOSTICS %s"),*Text);
    FPlatformMisc::RequestExitWithStatus(false,bPass?0:1);
}

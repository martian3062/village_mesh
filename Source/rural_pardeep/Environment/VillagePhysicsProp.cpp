#include "Environment/VillagePhysicsProp.h"
#include "Environment/WeatherManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "UObject/ConstructorHelpers.h"

AVillagePhysicsProp::AVillagePhysicsProp()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PrePhysics;
    Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
    SetRootComponent(Body);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded()) Body->SetStaticMesh(Cube.Object);
    Body->SetCollisionProfileName(TEXT("PhysicsActor"));
    Body->SetSimulatePhysics(true);
    Body->SetUseCCD(true);
    Body->SetLinearDamping(0.08f);
    Body->SetAngularDamping(0.35f);
}

void AVillagePhysicsProp::BeginPlay()
{
    Super::BeginPlay();
    Body->SetMassOverrideInKg(NAME_None, FMath::Max(MassKg, 0.1f));
    Surface = NewObject<UPhysicalMaterial>(this);
    Surface->Friction = 0.65f;
    Surface->Restitution = 0.12f;
    Body->SetPhysMaterialOverride(Surface);
    if (!Weather)
        for (TActorIterator<AWeatherManager> It(GetWorld()); It; ++It) { Weather = *It; break; }
}

void AVillagePhysicsProp::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!Body->IsSimulatingPhysics()) return;
    const FVector AirVelocity = Weather ? Weather->GetWindVelocityCm() : FVector::ZeroVector;
    // Quadratic drag: 1/2 rho Cd A |v| v, in newtons, then converted to UE force.
    const FVector RelativeMps = (AirVelocity - Body->GetPhysicsLinearVelocity()) * 0.01;
    FVector Force = 0.5 * 1.225 * FMath::Max(0.f, DragAreaSquareMeters)
        * RelativeMps.Size() * RelativeMps * 100.;
    if (bEnableBuoyancy)
    {
        const FBox Bounds = Body->Bounds.GetBox();
        const float Immersion = FMath::Clamp((WaterLevelCm - Bounds.Min.Z)
            / FMath::Max(1., Bounds.Max.Z - Bounds.Min.Z), 0., 1.);
        Force.Z += 1000.f * FMath::Max(0.001f, DisplacedVolumeCubicMeters)
            * FMath::Abs(GetWorld()->GetGravityZ()) * Immersion;
        Force -= Body->GetPhysicsLinearVelocity() * Body->GetMass() * Immersion * 3.f;
    }
    // Bound extreme transient forces after teleports or editor tuning.
    Body->AddForce(Force.GetClampedToMaxSize(Body->GetMass() * 5000.));
}

#include "Environment/VillageDoor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

AVillageDoor::AVillageDoor()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Hinge"));
    Leaf = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Leaf"));
    Leaf->SetupAttachment(RootComponent);
    Leaf->SetMobility(EComponentMobility::Movable);
    Leaf->SetCollisionProfileName(TEXT("BlockAllDynamic"));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded()) Leaf->SetStaticMesh(Cube.Object);
}

void AVillageDoor::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    Leaf->SetRelativeLocation(FVector(DoorWidthCm * .5f, 0, DoorHeightCm * .5f));
    Leaf->SetRelativeScale3D(FVector(DoorWidthCm / 100.f, .06f, DoorHeightCm / 100.f));
}

void AVillageDoor::BeginPlay()
{
    Super::BeginPlay();
    if (const auto* State = GetWorld()->GetSubsystem<UVillageDoorState>())
        bOpen = bCanOpen && State->OpenDoors.FindRef(PersistentId);
    CurrentAngle = bOpen ? 95.f : 0.f;
    RootComponent->SetRelativeRotation(FRotator(0,GetActorRotation().Yaw,0));
    Leaf->SetRelativeLocation(FRotator(0,CurrentAngle,0).RotateVector(FVector(DoorWidthCm*.5f,0,DoorHeightCm*.5f)));
    Leaf->SetRelativeRotation(FRotator(0,CurrentAngle,0));
}

void AVillageDoor::Toggle()
{
    if (!bCanOpen || PersistentId.IsEmpty()) return;
    bOpen = !bOpen;
    GetWorld()->GetSubsystem<UVillageDoorState>()->OpenDoors.Add(PersistentId,bOpen);
    SetActorTickEnabled(true);
}

void AVillageDoor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    CurrentAngle = FMath::FInterpConstantTo(CurrentAngle,bOpen ? 95.f : 0.f,DeltaSeconds,95.f);
    // Rotating leaf is kinematic; keep interaction intentional and nearby.
    Leaf->SetRelativeLocation(FRotator(0,CurrentAngle,0).RotateVector(FVector(DoorWidthCm*.5f,0,DoorHeightCm*.5f)));
    Leaf->SetRelativeRotation(FRotator(0,CurrentAngle,0));
    if (FMath::IsNearlyEqual(CurrentAngle,bOpen ? 95.f : 0.f,.1f)) SetActorTickEnabled(false);
}

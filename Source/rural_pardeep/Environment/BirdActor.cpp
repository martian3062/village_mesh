#include "Environment/BirdActor.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

ABirdActor::ABirdActor()
{
	PrimaryActorTick.bCanEverTick = true;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(
		TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(
		TEXT("/Engine/BasicShapes/Cube.Cube"));
	UStaticMesh* Sphere = SphereMesh.Object;
	UStaticMesh* Cube = CubeMesh.Object;

	auto MakeMesh = [&](const TCHAR* Name, USceneComponent* Parent, UStaticMesh* Mesh)
	{
		UStaticMeshComponent* Comp = CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Comp->SetupAttachment(Parent);
		Comp->SetStaticMesh(Mesh);
		Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Comp->SetCastShadow(false);
		return Comp;
	};

	// Fuselage: an elongated sphere along +X (forward = travel direction).
	Body = MakeMesh(TEXT("Body"), Root, Sphere);
	Body->SetRelativeLocation(FVector(0.f, 0.f, 0.f));
	Body->SetRelativeScale3D(FVector(0.85f, 0.24f, 0.20f));

	// Small head sphere out front.
	Head = MakeMesh(TEXT("Head"), Root, Sphere);
	Head->SetRelativeLocation(FVector(44.f, 0.f, 4.f));
	Head->SetRelativeScale3D(FVector(0.22f, 0.20f, 0.19f));

	// Fan tail at the back.
	Tail = MakeMesh(TEXT("Tail"), Root, Cube);
	Tail->SetRelativeLocation(FVector(-50.f, 0.f, 2.f));
	Tail->SetRelativeScale3D(FVector(0.30f, 0.42f, 0.03f));

	// Wings hang off shoulder pivots at the body sides so a roll on the pivot
	// sweeps the whole wing up/down (a flap), not a see-saw about its centre.
	// Default pose: a shallow raised-dihedral glide.
	ShoulderL = CreateDefaultSubobject<USceneComponent>(TEXT("ShoulderL"));
	ShoulderL->SetupAttachment(Root);
	ShoulderL->SetRelativeLocation(FVector(0.f, -6.f, 5.f));
	ShoulderL->SetRelativeRotation(FRotator(0.f, 0.f, 10.f));   // roll: tip up

	ShoulderR = CreateDefaultSubobject<USceneComponent>(TEXT("ShoulderR"));
	ShoulderR->SetupAttachment(Root);
	ShoulderR->SetRelativeLocation(FVector(0.f, 6.f, 5.f));
	ShoulderR->SetRelativeRotation(FRotator(0.f, 0.f, -10.f));

	WingL = MakeMesh(TEXT("WingL"), ShoulderL, Cube);
	WingL->SetRelativeLocation(FVector(0.f, -48.f, 0.f));       // extends outward -Y
	WingL->SetRelativeScale3D(FVector(0.34f, 0.96f, 0.025f));   // chord X, span Y, thin Z

	WingR = MakeMesh(TEXT("WingR"), ShoulderR, Cube);
	WingR->SetRelativeLocation(FVector(0.f, 48.f, 0.f));
	WingR->SetRelativeScale3D(FVector(0.34f, 0.96f, 0.025f));
}

void ABirdActor::BeginPlay()
{
	Super::BeginPlay();
	ApplyMaterial();

	if (bAmbientAutoFly)
	{
		Center = GetActorLocation();
		// desync the flock so they don't wheel in lockstep
		const uint32 Id = GetUniqueID();
		Angle = static_cast<float>(Id % 360);
		FlapPhase = static_cast<float>(Id % 61) * 0.1f;
		BobPhase = static_cast<float>(Id % 47) * 0.13f;
		bSoaring = true;
	}
}

void ABirdActor::ApplyMaterial()
{
	if (!BodyMaterial)
	{
		return;
	}
	for (UStaticMeshComponent* Part : { Body.Get(), Head.Get(), Tail.Get(),
			WingL.Get(), WingR.Get() })
	{
		if (Part)
		{
			for (int32 i = 0; i < Part->GetNumMaterials(); ++i)
			{
				Part->SetMaterial(i, BodyMaterial);
			}
		}
	}
}

void ABirdActor::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// Wing flap runs even before soaring engages (editor safety), but only
	// when a play session is ticking us.
	FlapPhase += FlapSpeed * DeltaTime;
	const float Flap = FMath::Sin(FlapPhase) * FlapAngle;
	if (ShoulderL) { ShoulderL->SetRelativeRotation(FRotator(0.f, 0.f, 10.f + Flap)); }
	if (ShoulderR) { ShoulderR->SetRelativeRotation(FRotator(0.f, 0.f, -10.f - Flap)); }

	if (!bSoaring)
	{
		return;
	}

	Angle += CircleSpeed * DeltaTime;
	BobPhase += BobSpeed * DeltaTime;

	const float A = FMath::DegreesToRadians(Angle);
	const float Bob = FMath::Sin(BobPhase) * BobAmplitude;
	const FVector Pos = Center
		+ FVector(FMath::Cos(A), FMath::Sin(A), 0.f) * CircleRadius
		+ FVector(0.f, 0.f, Bob);
	SetActorLocation(Pos);

	// Face along travel (tangent to the circle), banked into the turn.
	const float Dir = CircleSpeed >= 0.f ? 1.f : -1.f;
	const FVector Tangent(-FMath::Sin(A) * Dir, FMath::Cos(A) * Dir, 0.f);
	FRotator Facing = Tangent.Rotation();
	Facing.Pitch = FMath::Sin(BobPhase) * 6.f;   // nose follows the bob a little
	Facing.Roll = -BankAngle * Dir;              // bank toward the circle centre
	SetActorRotation(Facing);
}

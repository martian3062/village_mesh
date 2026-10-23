#include "Environment/GrazingAnimal.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	UStaticMeshComponent* MakePart(AActor* Owner, USceneComponent* Parent,
		const TCHAR* Name, UStaticMesh* Mesh)
	{
		UStaticMeshComponent* Comp = Owner->CreateDefaultSubobject<UStaticMeshComponent>(Name);
		Comp->SetupAttachment(Parent);
		Comp->SetStaticMesh(Mesh);
		Comp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		return Comp;
	}
}

AGrazingAnimal::AGrazingAnimal()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.f;

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(
		TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(
		TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> ConeMesh(
		TEXT("/Engine/BasicShapes/Cone.Cone"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(
		TEXT("/Engine/BasicShapes/Sphere.Sphere"));

	UStaticMesh* Cube = CubeMesh.Object;
	UStaticMesh* Cylinder = CylinderMesh.Object;
	UStaticMesh* Cone = ConeMesh.Object;
	UStaticMesh* Sphere = SphereMesh.Object;

	Body  = MakePart(this, Root, TEXT("Body"), Cube);
	Head  = MakePart(this, Root, TEXT("Head"), Cube);
	Snout = MakePart(this, Head, TEXT("Snout"), Cube);
	Neck  = MakePart(this, Root, TEXT("Neck"), Cube);
	EarL  = MakePart(this, Head, TEXT("EarL"), Cube);
	EarR  = MakePart(this, Head, TEXT("EarR"), Cube);
	HornL = MakePart(this, Head, TEXT("HornL"), Cone);
	HornR = MakePart(this, Head, TEXT("HornR"), Cone);
	Mane  = MakePart(this, Root, TEXT("Mane"), Cube);
	Tail  = MakePart(this, Root, TEXT("Tail"), Cube);
	LegFL = MakePart(this, Root, TEXT("LegFL"), Cylinder);
	LegFR = MakePart(this, Root, TEXT("LegFR"), Cylinder);
	LegBL = MakePart(this, Root, TEXT("LegBL"), Cylinder);
	LegBR = MakePart(this, Root, TEXT("LegBR"), Cylinder);

	// The body block is the only collider (keeps the player from ghosting
	// through the herd) — everything else stays trace-transparent.
	Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Body->SetCollisionResponseToAllChannels(ECR_Block);
	Body->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
}

void AGrazingAnimal::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	ApplySpeciesShape();
	ApplyMaterials();
}

void AGrazingAnimal::ApplySpeciesShape()
{
	// All parts are placed so the feet touch Z=0 in actor space; the tick
	// keeps the actor origin glued to the ground trace.
	const bool bCow = Species == EGrazingSpecies::Cow;
	const bool bBuffalo = Species == EGrazingSpecies::Buffalo;
	const bool bHorse = Species == EGrazingSpecies::Horse;

	// body: length x, width y, height z (cube is 100 cm)
	const FVector BodyDim = bHorse ? FVector(1.9f, 0.58f, 0.95f)
	                     : bBuffalo ? FVector(2.1f, 0.85f, 1.15f)
	                                : FVector(1.9f, 0.72f, 1.05f);
	const float LegH = bHorse ? 1.15f : bBuffalo ? 0.85f : 0.9f;
	const float LegR = bHorse ? 0.13f : 0.19f;
	const float BodyZ = LegH * 100.f + BodyDim.Z * 50.f - 8.f; // slight leg overlap

	Body->SetRelativeLocation(FVector(0, 0, BodyZ));
	Body->SetRelativeScale3D(BodyDim);

	const float LegX = BodyDim.X * 50.f - 22.f;
	const float LegY = BodyDim.Y * 50.f - 12.f;
	const FVector LegScale(LegR, LegR, LegH);
	LegFL->SetRelativeLocation(FVector(LegX, -LegY, LegH * 50.f));
	LegFR->SetRelativeLocation(FVector(LegX, LegY, LegH * 50.f));
	LegBL->SetRelativeLocation(FVector(-LegX, -LegY, LegH * 50.f));
	LegBR->SetRelativeLocation(FVector(-LegX, LegY, LegH * 50.f));
	for (UStaticMeshComponent* Leg : { LegFL.Get(), LegFR.Get(), LegBL.Get(), LegBR.Get() })
	{
		Leg->SetRelativeScale3D(LegScale);
	}

	// neck + head
	const float NeckPitch = bHorse ? -48.f : -20.f;
	const FVector NeckScale = bHorse ? FVector(0.72f, 0.24f, 0.30f) : FVector(0.55f, 0.32f, 0.34f);
	const float FrontX = BodyDim.X * 50.f;
	Neck->SetRelativeLocation(FVector(FrontX + 8.f, 0, BodyZ + BodyDim.Z * 34.f));
	Neck->SetRelativeRotation(FRotator(NeckPitch, 0, 0));
	Neck->SetRelativeScale3D(NeckScale);

	HeadBaseZ = bHorse ? BodyZ + BodyDim.Z * 50.f + 52.f : BodyZ + BodyDim.Z * 32.f;
	const float HeadX = bHorse ? FrontX + 52.f : FrontX + 42.f;
	Head->SetRelativeLocation(FVector(HeadX, 0, HeadBaseZ));
	Head->SetRelativeScale3D(bHorse ? FVector(0.52f, 0.26f, 0.36f) : FVector(0.5f, 0.36f, 0.42f));
	HeadBasePitch = bHorse ? -18.f : -6.f;
	Head->SetRelativeRotation(FRotator(HeadBasePitch, 0, 0));

	// child parts of the head use the head's local (scaled) space
	Snout->SetRelativeLocation(FVector(62.f, 0, -16.f));
	Snout->SetRelativeScale3D(FVector(0.42f, 0.72f, 0.55f));
	EarL->SetRelativeLocation(FVector(-18.f, -56.f, 48.f));
	EarR->SetRelativeLocation(FVector(-18.f, 56.f, 48.f));
	const FVector EarScale = bHorse ? FVector(0.10f, 0.16f, 0.42f) : FVector(0.10f, 0.30f, 0.34f);
	EarL->SetRelativeScale3D(EarScale);
	EarR->SetRelativeScale3D(EarScale);
	EarL->SetRelativeRotation(FRotator(0, 0, -18.f));
	EarR->SetRelativeRotation(FRotator(0, 0, 18.f));

	// horns: cattle only — buffalo carry wide swept-back crescents
	const bool bHorns = !bHorse;
	HornL->SetVisibility(bHorns, true);
	HornR->SetVisibility(bHorns, true);
	if (bHorns)
	{
		const float HornRoll = bBuffalo ? 105.f : 55.f;
		const float HornPitch = bBuffalo ? -35.f : -10.f;
		const FVector HornScale = bBuffalo ? FVector(0.16f, 0.16f, 0.62f) : FVector(0.12f, 0.12f, 0.38f);
		HornL->SetRelativeLocation(FVector(-8.f, -42.f, 52.f));
		HornR->SetRelativeLocation(FVector(-8.f, 42.f, 52.f));
		HornL->SetRelativeRotation(FRotator(HornPitch, 0, -HornRoll));
		HornR->SetRelativeRotation(FRotator(HornPitch, 0, HornRoll));
		HornL->SetRelativeScale3D(HornScale);
		HornR->SetRelativeScale3D(HornScale);
	}

	// mane: horse only, a thin crest along the neck top
	Mane->SetVisibility(bHorse, true);
	if (bHorse)
	{
		Mane->SetRelativeLocation(FVector(FrontX + 14.f, 0, BodyZ + BodyDim.Z * 50.f + 26.f));
		Mane->SetRelativeRotation(FRotator(-48.f, 0, 0));
		Mane->SetRelativeScale3D(FVector(0.78f, 0.06f, 0.22f));
	}

	// tail
	const float BackX = -BodyDim.X * 50.f;
	Tail->SetRelativeLocation(FVector(BackX - 4.f, 0, BodyZ + BodyDim.Z * 30.f));
	Tail->SetRelativeRotation(FRotator(bHorse ? -72.f : -80.f, 0, 0));
	Tail->SetRelativeScale3D(bHorse ? FVector(0.10f, 0.14f, 0.75f) : FVector(0.07f, 0.07f, 0.68f));
}

void AGrazingAnimal::ApplyMaterials()
{
	if (CoatMaterial)
	{
		for (UStaticMeshComponent* Part : { Body.Get(), Head.Get(), Neck.Get(), Snout.Get(),
			EarL.Get(), EarR.Get(), Tail.Get(), LegFL.Get(), LegFR.Get(), LegBL.Get(), LegBR.Get() })
		{
			for (int32 i = 0; i < Part->GetNumMaterials(); ++i)
			{
				Part->SetMaterial(i, CoatMaterial);
			}
		}
	}
	if (DetailMaterial)
	{
		for (UStaticMeshComponent* Part : { HornL.Get(), HornR.Get(), Mane.Get() })
		{
			for (int32 i = 0; i < Part->GetNumMaterials(); ++i)
			{
				Part->SetMaterial(i, DetailMaterial);
			}
		}
	}
}

void AGrazingAnimal::BeginPlay()
{
	Super::BeginPlay();
	HomeSpot = GetActorLocation();
	Rand.Initialize(GetUniqueID());
	StateTimeLeft = Rand.FRandRange(0.5f, 4.f);
	TailPhase = Rand.FRandRange(0.f, 100.f);
	ApplySpeciesShape();
	ApplyMaterials();
}

float AGrazingAnimal::GroundZ(const FVector2D& At, float Fallback) const
{
	if (const UWorld* World = GetWorld())
	{
		FHitResult Hit;
		const FVector Start(At.X, At.Y, GetActorLocation().Z + 800.f);
		const FVector End(At.X, At.Y, GetActorLocation().Z - 1600.f);
		FCollisionQueryParams Params(SCENE_QUERY_STAT(AnimalGround), false, this);
		if (World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
		{
			return Hit.Location.Z;
		}
	}
	return Fallback;
}

void AGrazingAnimal::PickNewTarget()
{
	const float Angle = Rand.FRandRange(0.f, 2.f * PI);
	const float Radius = Rand.FRandRange(0.25f, 1.f) * WanderRadius;
	Target = HomeSpot + FVector(FMath::Cos(Angle) * Radius, FMath::Sin(Angle) * Radius, 0.f);
	State = EAnimalState::Turning;
}

void AGrazingAnimal::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	const float SpeciesSpeed = Species == EGrazingSpecies::Horse ? 95.f
	                         : Species == EGrazingSpecies::Buffalo ? 45.f : 55.f;
	const float Speed = WalkSpeed > 1.f ? WalkSpeed : SpeciesSpeed;

	// tail flick: lazy sine with an occasional sharper swat
	TailPhase += DeltaTime;
	const float Flick = FMath::Sin(TailPhase * 1.7f) * 14.f
		+ FMath::Sin(TailPhase * 0.23f) * FMath::Sin(TailPhase * 6.1f) * 10.f;
	FRotator TailRot = Tail->GetRelativeRotation();
	TailRot.Yaw = Flick;
	Tail->SetRelativeRotation(TailRot);

	switch (State)
	{
	case EAnimalState::Idle:
	{
		StateTimeLeft -= DeltaTime;
		// ease the head back up
		FRotator HeadRot = Head->GetRelativeRotation();
		HeadRot.Pitch = FMath::FInterpTo(HeadRot.Pitch, HeadBasePitch, DeltaTime, 3.f);
		Head->SetRelativeRotation(HeadRot);
		if (StateTimeLeft <= 0.f)
		{
			PickNewTarget();
		}
		break;
	}
	case EAnimalState::Turning:
	{
		const FVector To = Target - GetActorLocation();
		const FRotator Desired = FVector(To.X, To.Y, 0.f).Rotation();
		const FRotator Now = GetActorRotation();
		SetActorRotation(FMath::RInterpTo(Now, FRotator(0, Desired.Yaw, 0), DeltaTime, 2.2f));
		if (FMath::Abs(FMath::FindDeltaAngleDegrees(Now.Yaw, Desired.Yaw)) < 8.f)
		{
			State = EAnimalState::Walking;
		}
		break;
	}
	case EAnimalState::Walking:
	{
		const FVector Loc = GetActorLocation();
		FVector To = Target - Loc;
		To.Z = 0.f;
		if (To.Size() < 60.f)
		{
			State = EAnimalState::Grazing;
			StateTimeLeft = Rand.FRandRange(GrazeTimeMin, GrazeTimeMax);
			break;
		}

		// obstacle probe: a chest-height whisker; on hit just pick elsewhere
		const FVector Dir = To.GetSafeNormal();
		FHitResult Probe;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(AnimalProbe), false, this);
		if (GetWorld() && GetWorld()->LineTraceSingleByChannel(Probe,
			Loc + FVector(0, 0, 90.f), Loc + FVector(0, 0, 90.f) + Dir * 220.f,
			ECC_Visibility, Params))
		{
			PickNewTarget();
			break;
		}

		FVector NewLoc = Loc + Dir * Speed * DeltaTime;
		NewLoc.Z = FMath::FInterpTo(Loc.Z,
			GroundZ(FVector2D(NewLoc.X, NewLoc.Y), Loc.Z), DeltaTime, 8.f);
		SetActorLocation(NewLoc);
		SetActorRotation(FMath::RInterpTo(GetActorRotation(),
			FRotator(0, Dir.Rotation().Yaw, 0), DeltaTime, 3.f));

		// gait bob
		WalkPhase += DeltaTime * Speed * 0.10f;
		FVector BodyLoc = Body->GetRelativeLocation();
		Body->SetRelativeLocation(FVector(BodyLoc.X, BodyLoc.Y,
			BodyLoc.Z + FMath::Sin(WalkPhase) * 0.35f));
		break;
	}
	case EAnimalState::Grazing:
	{
		StateTimeLeft -= DeltaTime;
		// head down to the grass with a nibbling wobble; horses crop, cattle sweep
		const float Nibble = FMath::Sin(TailPhase * 5.3f) * 3.f;
		const float DownPitch = Species == EGrazingSpecies::Horse ? -62.f : -48.f;
		FRotator HeadRot = Head->GetRelativeRotation();
		HeadRot.Pitch = FMath::FInterpTo(HeadRot.Pitch, DownPitch + Nibble, DeltaTime, 2.5f);
		HeadRot.Yaw = FMath::Sin(TailPhase * 0.4f) * (Species == EGrazingSpecies::Horse ? 4.f : 12.f);
		Head->SetRelativeRotation(HeadRot);
		if (StateTimeLeft <= 0.f)
		{
			State = EAnimalState::Idle;
			StateTimeLeft = Rand.FRandRange(1.5f, 5.f);
		}
		break;
	}
	}
}

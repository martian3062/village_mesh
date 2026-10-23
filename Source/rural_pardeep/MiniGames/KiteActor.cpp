#include "MiniGames/KiteActor.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

AKiteActor::AKiteActor()
{
	PrimaryActorTick.bCanEverTick = true;

	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	KiteMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("KiteMesh"));
	KiteMesh->SetupAttachment(Root);

	// <KITE_MESH_PLACEHOLDER>: engine plane, yawed 45° to read as a diamond.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> PlaneMesh(
		TEXT("/Engine/BasicShapes/Plane.Plane"));
	if (PlaneMesh.Succeeded())
	{
		KiteMesh->SetStaticMesh(PlaneMesh.Object);
	}
	KiteMesh->SetRelativeScale3D(FVector(0.9f, 0.9f, 1.f));
	KiteMesh->SetRelativeRotation(FRotator(70.f, 45.f, 0.f)); // tilted into the wind
	KiteMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	// Manjha: absolute transform — it spans world space between the flyer's
	// hands and the kite, unaffected by the kite's own banking.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(
		TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	StringMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StringMesh"));
	StringMesh->SetupAttachment(Root);
	if (CylinderMesh.Succeeded())
	{
		StringMesh->SetStaticMesh(CylinderMesh.Object);
	}
	StringMesh->SetUsingAbsoluteLocation(true);
	StringMesh->SetUsingAbsoluteRotation(true);
	StringMesh->SetUsingAbsoluteScale(true);
	StringMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	StringMesh->SetCastShadow(false);

	// Tail: three ribbon planes hanging behind the kite, swayed per tick.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> TailPlane(
		TEXT("/Engine/BasicShapes/Plane.Plane"));
	for (int32 i = 0; i < 3; ++i)
	{
		UStaticMeshComponent* Piece = CreateDefaultSubobject<UStaticMeshComponent>(
			*FString::Printf(TEXT("Tail%d"), i));
		Piece->SetupAttachment(Root);
		if (TailPlane.Succeeded())
		{
			Piece->SetStaticMesh(TailPlane.Object);
		}
		Piece->SetRelativeLocation(FVector(-52.f * (i + 1), 0.f, -14.f * (i + 1)));
		Piece->SetRelativeRotation(FRotator(90.f, 0.f, 0.f));
		Piece->SetRelativeScale3D(FVector(0.30f, 0.12f, 1.f));
		Piece->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Piece->SetCastShadow(false);
		TailPieces.Add(Piece);
	}
}

void AKiteActor::BeginPlay()
{
	Super::BeginPlay();

	if (bAmbientAutoFly)
	{
		Anchor = GetActorLocation();
		bAutoPilot = true;
		if (CachedWind.IsNearlyZero())
		{
			CachedWind = FVector(110.f, 40.f, 0.f);
		}
		// Start already airborne at a believable point on the string sphere.
		const FVector Up = FVector(0.45f, 0.18f, 0.85f).GetSafeNormal();
		SetActorLocation(Anchor + Up * StringLength * 0.85f);
		PatrolTime = static_cast<float>(GetUniqueID() % 97); // desync patrols
	}
}

void AKiteActor::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// Tail ribbons flutter regardless of who is flying.
	VisualTime += DeltaTime;
	for (int32 i = 0; i < TailPieces.Num(); ++i)
	{
		if (UStaticMeshComponent* Piece = TailPieces[i])
		{
			Piece->SetRelativeRotation(FRotator(
				90.f + FMath::Sin(VisualTime * 3.1f + i * 1.1f) * 12.f,
				FMath::Sin(VisualTime * 2.2f + i * 0.7f) * 16.f,
				0.f));
		}
	}

	if (bCut)
	{
		// String gone: tumble and fall with a little drag, then clean up.
		FallTime += DeltaTime;
		Velocity += FVector(0.f, 0.f, -980.f) * DeltaTime;
		Velocity *= FMath::Max(0.f, 1.f - 0.4f * DeltaTime);
		SetActorLocation(GetActorLocation() + Velocity * DeltaTime);
		AddActorWorldRotation(FRotator(140.f * DeltaTime, 90.f * DeltaTime, 200.f * DeltaTime));

		if (FallTime > 8.f || GetActorLocation().Z < Anchor.Z - 4000.f)
		{
			Destroy();
		}
		return;
	}

	if (bAutoPilot)
	{
		// Lazy figure-eight patrol with a slow breathing reel.
		PatrolTime += DeltaTime;
		const FVector2D Steer(
			FMath::Sin(PatrolTime * 0.6f),
			0.5f * FMath::Sin(PatrolTime * 1.1f));
		const float Reel = 0.3f * FMath::Sin(PatrolTime * 0.25f);
		UpdateFlight(DeltaTime, Steer, Reel, CachedWind);
	}

	UpdateStringVisual();
}

void AKiteActor::UpdateStringVisual()
{
	if (!StringMesh || bCut)
	{
		return;
	}
	const FVector End = GetActorLocation();
	const FVector Span = End - Anchor;
	const float Length = Span.Size();
	if (Length < 10.f || Anchor.IsNearlyZero())
	{
		StringMesh->SetVisibility(false);
		return;
	}
	StringMesh->SetVisibility(true);
	StringMesh->SetWorldLocation(Anchor + Span * 0.5f);
	StringMesh->SetWorldRotation(FRotationMatrix::MakeFromZ(Span).Rotator());
	StringMesh->SetWorldScale3D(FVector(0.03f, 0.03f, Length / 100.f));
}

void AKiteActor::UpdateFlight(float DeltaTime, const FVector2D& Steer, float Reel, const FVector& Wind)
{
	if (bCut)
	{
		return;
	}

	StringLength = FMath::Clamp(StringLength + Reel * ReelRate * DeltaTime,
		MinStringLength, MaxStringLength);

	// Steering basis: sideways = horizontal tangent around the anchor,
	// climb = straight up. Wind is added raw so gusts genuinely shove the kite.
	const FVector ToKite = GetActorLocation() - Anchor;
	const FVector Radial = ToKite.GetSafeNormal();
	FVector Side = FVector::CrossProduct(FVector::UpVector, Radial);
	if (!Side.Normalize())
	{
		Side = GetActorRightVector();
	}

	const FVector DesiredVelocity =
		Side * Steer.X * LateralSpeed +
		FVector::UpVector * Steer.Y * ClimbSpeed +
		Wind;
	Velocity = FMath::VInterpTo(Velocity, DesiredVelocity, DeltaTime, Agility);

	FVector NewPos = GetActorLocation() + Velocity * DeltaTime;

	// String constraint: stay on/inside the sphere around the anchor.
	FVector Offset = NewPos - Anchor;
	if (Offset.Size() > StringLength)
	{
		NewPos = Anchor + Offset.GetSafeNormal() * StringLength;
	}
	NewPos.Z = FMath::Max(NewPos.Z, Anchor.Z + MinAltitude);

	SetActorLocation(NewPos);

	// Face along travel, banked by the sideways input.
	if (Velocity.SizeSquared() > 25.f)
	{
		FRotator Facing = Velocity.Rotation();
		Facing.Roll = FMath::Clamp(Steer.X * 30.f, -45.f, 45.f);
		SetActorRotation(FMath::RInterpTo(GetActorRotation(), Facing, DeltaTime, 4.f));
	}
}

void AKiteActor::Cut()
{
	if (!bCut)
	{
		bCut = true;
		FallTime = 0.f;
		if (StringMesh)
		{
			StringMesh->SetVisibility(false); // string snaps away
		}
	}
}

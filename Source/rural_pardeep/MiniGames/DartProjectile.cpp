#include "MiniGames/DartProjectile.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "MiniGames/DartsZone.h"
#include "UObject/ConstructorHelpers.h"

ADartProjectile::ADartProjectile()
{
	PrimaryActorTick.bCanEverTick = false;

	DartMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("DartMesh"));
	SetRootComponent(DartMesh);

	// Engine default so the game runs before any art exists; swap for your
	// Blender dart on a BP child or via ADartsZone::DartClass.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CylinderMesh(
		TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (CylinderMesh.Succeeded())
	{
		DartMesh->SetStaticMesh(CylinderMesh.Object);
	}
	// Thin 15 cm needle, laid along +X so bRotationFollowsVelocity points it.
	DartMesh->SetRelativeScale3D(FVector(0.15f, 0.02f, 0.02f));
	DartMesh->SetRelativeRotation(FRotator(-90.f, 0.f, 0.f)); // cylinder axis Z -> X

	DartMesh->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	DartMesh->SetNotifyRigidBodyCollision(true);

	ProjectileMovement = CreateDefaultSubobject<UProjectileMovementComponent>(TEXT("ProjectileMovement"));
	ProjectileMovement->bRotationFollowsVelocity = true;
	ProjectileMovement->ProjectileGravityScale = 1.f;
	ProjectileMovement->InitialSpeed = 0.f; // velocity supplied by Launch()
	ProjectileMovement->MaxSpeed = 0.f;     // unclamped
	ProjectileMovement->bShouldBounce = false;

	// Darts left in the board are cleaned up by the zone at end of turn/game.
	InitialLifeSpan = 60.f;
}

void ADartProjectile::Launch(const FVector& Velocity, ADartsZone* InOwnerZone)
{
	OwnerZone = InOwnerZone;
	DartMesh->OnComponentHit.AddDynamic(this, &ADartProjectile::OnDartHit);
	// If the dart dies without ever landing (lifespan, KillZ), the zone still
	// needs to hear about it or the turn would wait forever.
	OnDestroyed.AddDynamic(this, &ADartProjectile::OnDartDestroyed);
	ProjectileMovement->Velocity = Velocity;
	SetActorRotation(Velocity.Rotation());
}

void ADartProjectile::OnDartDestroyed(AActor* DestroyedActor)
{
	if (!bStuck && OwnerZone.IsValid())
	{
		OwnerZone->OnDartLost(this);
	}
}

void ADartProjectile::OnDartHit(UPrimitiveComponent* HitComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit)
{
	if (bStuck)
	{
		return;
	}
	bStuck = true;

	// Stick: freeze the projectile and ride whatever we hit.
	ProjectileMovement->StopMovementImmediately();
	ProjectileMovement->Deactivate();
	DartMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	if (OtherComp)
	{
		AttachToComponent(OtherComp, FAttachmentTransformRules::KeepWorldTransform);
	}

	if (OwnerZone.IsValid())
	{
		OwnerZone->OnDartLanded(this, Hit);
	}
}

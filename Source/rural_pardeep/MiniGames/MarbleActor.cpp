#include "MiniGames/MarbleActor.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "MiniGames/KanchaZone.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "UObject/ConstructorHelpers.h"

AMarbleActor::AMarbleActor()
{
	PrimaryActorTick.bCanEverTick = false;

	MeshComp = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("MeshComp"));
	SetRootComponent(MeshComp);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(
		TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (SphereMesh.Succeeded())
	{
		MeshComp->SetStaticMesh(SphereMesh.Object);
	}
	// Engine sphere is 50 cm radius at scale 1.
	MeshComp->SetRelativeScale3D(FVector(MarbleRadius / 50.f));
	MeshComp->SetCollisionProfileName(TEXT("PhysicsActor"));
	MeshComp->SetNotifyRigidBodyCollision(true);
}

void AMarbleActor::InitMarble(AKanchaZone* InZone, bool bInPlayerMarble,
	float Mass, float Friction, float Restitution)
{
	OwnerZone = InZone;
	bPlayerMarble = bInPlayerMarble;

	MeshComp->SetWorldScale3D(FVector(MarbleRadius / 50.f));
	MeshComp->SetSimulatePhysics(true);
	MeshComp->SetMassOverrideInKg(NAME_None, Mass, true);
	MeshComp->SetLinearDamping(LinearDamping);
	MeshComp->SetAngularDamping(AngularDamping);
	// Small fast spheres tunnel without continuous collision detection.
	// SetUseCCD pushes the flag to the already-created physics body; a raw
	// BodyInstance.bUseCCD write here would never reach the live particle.
	MeshComp->SetUseCCD(true);

	// Runtime physical material so friction/restitution are plain UPROPERTYs
	// on the zone instead of hand-authored assets.
	UPhysicalMaterial* PhysMat = NewObject<UPhysicalMaterial>(this);
	PhysMat->Friction = Friction;
	PhysMat->Restitution = Restitution;
	MeshComp->SetPhysMaterialOverride(PhysMat);

	MeshComp->OnComponentHit.AddDynamic(this, &AMarbleActor::OnMarbleHit);
}

FVector AMarbleActor::GetMarbleVelocity() const
{
	return MeshComp->GetPhysicsLinearVelocity();
}

void AMarbleActor::OnMarbleHit(UPrimitiveComponent* HitComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, FVector NormalImpulse, const FHitResult& Hit)
{
	if (OwnerZone.IsValid())
	{
		OwnerZone->NotifyMarbleHit(this, OtherActor);
	}
}

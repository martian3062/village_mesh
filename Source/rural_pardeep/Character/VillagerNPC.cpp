#include "Character/VillagerNPC.h"

#include "AIController.h"
#include "Character/VillageCharacter.h"
#include "Navigation/PathFollowingComponent.h" // EPathFollowingRequestResult enumerators
#include "Components/CapsuleComponent.h"
#include "Components/SphereComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Interaction/InteractionComponent.h"
#include "Kismet/GameplayStatics.h"

AVillagerNPC::AVillagerNPC()
{
	PrimaryActorTick.bCanEverTick = true;

	GetCapsuleComponent()->InitCapsuleSize(34.f, 88.f);
	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -88.f), FRotator(0.f, -90.f, 0.f));

	bUseControllerRotationYaw = false;
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = true;
	Movement->RotationRate = FRotator(0.f, 240.f, 0.f);
	Movement->MaxWalkSpeed = StrollSpeed;

	InteractSphere = CreateDefaultSubobject<USphereComponent>(TEXT("InteractSphere"));
	InteractSphere->SetupAttachment(RootComponent);
	InteractSphere->SetSphereRadius(380.f);
	InteractSphere->SetCollisionProfileName(TEXT("Trigger"));

	// Spawned villagers get an engine AAIController for NavMesh moves.
	AIControllerClass = AAIController::StaticClass();
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;

	// Default voice — the build script personalises names and can extend these.
	GreetingLines = {
		NSLOCTEXT("Villager", "Greet1", "Sat Sri Akal, ji!"),
		NSLOCTEXT("Villager", "Greet2", "Oye, you're the new face in Pandori!"),
		NSLOCTEXT("Villager", "Greet3", "Come, come — chai just boiled."),
	};
	DialogueLines = {
		NSLOCTEXT("Villager", "Line1", "The wheat came in heavy this year, waheguru di kirpa."),
		NSLOCTEXT("Villager", "Line2", "Have you tried the darts by the old courtyard wall?"),
		NSLOCTEXT("Villager", "Line3", "The boys play kancha on the school ground till dark."),
		NSLOCTEXT("Villager", "Line4", "At dusk the rooftops fill with kites. Bo kata!"),
		NSLOCTEXT("Villager", "Line5", "Langar at the gurdwara today — everyone is welcome."),
		NSLOCTEXT("Villager", "Line6", "My cousin's tractor is louder than the whole village."),
		NSLOCTEXT("Villager", "Line7", "Rain will come late this year. The pond says so."),
		NSLOCTEXT("Villager", "Line8", "Careful on the side road — the buffaloes own it."),
		NSLOCTEXT("Villager", "Line9", "You throw darts like my grandmother. She is very good."),
		NSLOCTEXT("Villager", "Line10", "The vendor's samosas? Best between here and Adampur."),
	};
}

void AVillagerNPC::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	VillagerLookUtil::Apply(this, Appearance);
}

void AVillagerNPC::BeginPlay()
{
	Super::BeginPlay();

	VillagerLookUtil::Apply(this, Appearance);
	GetCharacterMovement()->MaxWalkSpeed = StrollSpeed;
	InteractSphere->OnComponentBeginOverlap.AddDynamic(this, &AVillagerNPC::OnSphereBeginOverlap);
	InteractSphere->OnComponentEndOverlap.AddDynamic(this, &AVillagerNPC::OnSphereEndOverlap);

	// Villagers start out on different errands so the village looks lived-in.
	LineIndex = GetName().Len() % FMath::Max(1, DialogueLines.Num());
	DwellRemaining = FMath::FRandRange(0.5f, 4.f);
}

// -------------------- awareness + brain --------------------

void AVillagerNPC::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// Needs drain slowly all the time.
	Energy = FMath::Max(0.f, Energy - NeedDrainRate * DeltaTime);
	Faith = FMath::Max(0.f, Faith - NeedDrainRate * DeltaTime);
	Social = FMath::Max(0.f, Social - NeedDrainRate * DeltaTime);
	WorkSat = FMath::Max(0.f, WorkSat - NeedDrainRate * DeltaTime);

	AVillageCharacter* Player = Cast<AVillageCharacter>(
		UGameplayStatics::GetPlayerCharacter(this, 0));
	const float PlayerDist = Player
		? FVector::Dist2D(Player->GetActorLocation(), GetActorLocation())
		: TNumericLimits<float>::Max();

	// ---- conversation state ----
	if (Activity == EVillagerActivity::TalkToPlayer)
	{
		TalkIdleTimer += DeltaTime;
		if (Player)
		{
			FacePoint(Player->GetActorLocation(), DeltaTime);
		}
		if (PlayerDist > TalkBreakRadius || TalkIdleTimer > 12.f)
		{
			EndTalk();
		}
		return; // pinned while talking
	}

	// ---- polite pause: stop and face a player who walks right up ----
	if (Player && PlayerDist < AwarenessRadius)
	{
		if (AAIController* AI = Cast<AAIController>(GetController()))
		{
			AI->StopMovement();
		}
		bTravelling = false;
		FacePoint(Player->GetActorLocation(), DeltaTime);
		Social = FMath::Min(1.f, Social + 0.02f * DeltaTime);
		return;
	}

	// ---- travel / dwell / decide ----
	if (bTravelling)
	{
		if (bDirectWalk)
		{
			AddMovementInput((CurrentDestination - GetActorLocation()).GetSafeNormal2D());
		}

		const float Dist = FVector::Dist2D(GetActorLocation(), CurrentDestination);
		StuckTimer = (GetVelocity().Size2D() < 20.f) ? StuckTimer + DeltaTime : 0.f;

		if (Dist < 180.f || StuckTimer > 6.f)
		{
			bTravelling = false;
			bDirectWalk = false;
			DwellRemaining = DwellTime * FMath::FRandRange(0.6f, 1.4f);
		}
	}
	else
	{
		DwellRemaining -= DeltaTime;
		// Dwelling refills the need that brought us here.
		NeedFor(Activity) = FMath::Min(1.f, NeedFor(Activity) + 10.f * NeedDrainRate * DeltaTime);

		if (DwellRemaining <= 0.f)
		{
			ChooseNextActivity();
		}
	}
}

float& AVillagerNPC::NeedFor(EVillagerActivity InActivity)
{
	switch (InActivity)
	{
	case EVillagerActivity::Rest: return Energy;
	case EVillagerActivity::Work: return WorkSat;
	case EVillagerActivity::Pray: return Faith;
	case EVillagerActivity::Socialize: return Social;
	default: return Social; // Wander counts lightly as social air
	}
}

void AVillagerNPC::ChooseNextActivity()
{
	// Utility scores: how badly each need wants attention, plus whimsy.
	TArray<TPair<EVillagerActivity, float>> Scores = {
		{ EVillagerActivity::Rest,      (1.f - Energy) + FMath::FRandRange(0.f, 0.2f) },
		{ EVillagerActivity::Work,      (1.f - WorkSat) + FMath::FRandRange(0.f, 0.2f) },
		{ EVillagerActivity::Pray,      (1.f - Faith) + FMath::FRandRange(0.f, 0.2f) },
		{ EVillagerActivity::Socialize, (1.f - Social) + FMath::FRandRange(0.f, 0.2f) },
		{ EVillagerActivity::Wander,    0.35f + FMath::FRandRange(0.f, 0.3f) },
	};
	Scores.Sort([](const TPair<EVillagerActivity, float>& A, const TPair<EVillagerActivity, float>& B)
	{
		return A.Value > B.Value;
	});
	Activity = Scores[0].Key;

	FVector Target;
	switch (Activity)
	{
	case EVillagerActivity::Rest:      Target = HomeSpot; break;
	case EVillagerActivity::Work:      Target = WorkSpot; break;
	case EVillagerActivity::Pray:      Target = PraySpot; break;
	case EVillagerActivity::Socialize: Target = SocialSpot; break;
	default:
		Target = GetActorLocation() + FVector(
			FMath::FRandRange(-WanderRadius, WanderRadius),
			FMath::FRandRange(-WanderRadius, WanderRadius), 0.f);
		break;
	}

	// Unstamped POIs (zero vector) degrade gracefully into a wander.
	if (Target.IsNearlyZero())
	{
		Target = GetActorLocation() + FVector(
			FMath::FRandRange(-WanderRadius, WanderRadius),
			FMath::FRandRange(-WanderRadius, WanderRadius), 0.f);
	}

	Target += FVector(FMath::FRandRange(-ArrivalScatter, ArrivalScatter),
		FMath::FRandRange(-ArrivalScatter, ArrivalScatter), 0.f);
	StartMoveTo(Target);
}

void AVillagerNPC::StartMoveTo(const FVector& Destination)
{
	CurrentDestination = Destination;
	bTravelling = true;
	bDirectWalk = false;
	StuckTimer = 0.f;

	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		const EPathFollowingRequestResult::Type Result =
			AI->MoveToLocation(Destination, 120.f, true, true, true);
		if (Result == EPathFollowingRequestResult::Failed)
		{
			bDirectWalk = true; // no NavMesh here — stroll straight instead
		}
	}
	else
	{
		bDirectWalk = true;
	}
}

void AVillagerNPC::FacePoint(const FVector& Point, float DeltaTime)
{
	FRotator Look = (Point - GetActorLocation()).Rotation();
	Look.Pitch = 0.f;
	Look.Roll = 0.f;
	SetActorRotation(FMath::RInterpTo(GetActorRotation(), Look, DeltaTime, 5.f));
}

// -------------------- conversation --------------------

FText AVillagerNPC::StartTalk(AVillageCharacter* Player)
{
	Activity = EVillagerActivity::TalkToPlayer;
	PlayerNearby = Player;
	bTravelling = false;
	TalkIdleTimer = 0.f;
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		AI->StopMovement();
	}
	Social = FMath::Min(1.f, Social + 0.25f);

	if (GreetingLines.Num() > 0)
	{
		return GreetingLines[FMath::RandRange(0, GreetingLines.Num() - 1)];
	}
	return NextLine();
}

FText AVillagerNPC::NextLine()
{
	TalkIdleTimer = 0.f;
	if (DialogueLines.Num() == 0)
	{
		return NSLOCTEXT("Villager", "NoLines", "...");
	}
	const FText Line = DialogueLines[LineIndex % DialogueLines.Num()];
	LineIndex++;
	return Line;
}

void AVillagerNPC::EndTalk()
{
	if (Activity == EVillagerActivity::TalkToPlayer)
	{
		Activity = EVillagerActivity::Wander;
		DwellRemaining = FMath::FRandRange(1.f, 3.f);

		// The villager may end the chat itself (timeout / player wandered
		// off) — the interaction system must drop its side too, or the
		// dialogue UI stays open on a walking NPC.
		if (AVillageCharacter* Player = PlayerNearby.Get())
		{
			if (UInteractionComponent* Interaction = Player->GetInteractionComponent())
			{
				Interaction->NotifyTalkEndedByNPC(this);
			}
		}
		PlayerNearby = nullptr;
	}
}

// -------------------- prompt registration --------------------

void AVillagerNPC::OnSphereBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (const AVillageCharacter* Player = Cast<AVillageCharacter>(OtherActor))
	{
		if (UInteractionComponent* Interaction = Player->GetInteractionComponent())
		{
			Interaction->NotifyNPCEntered(this);
		}
	}
}

void AVillagerNPC::OnSphereEndOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor,
	UPrimitiveComponent* OtherComp, int32 OtherBodyIndex)
{
	if (const AVillageCharacter* Player = Cast<AVillageCharacter>(OtherActor))
	{
		if (UInteractionComponent* Interaction = Player->GetInteractionComponent())
		{
			Interaction->NotifyNPCExited(this);
		}
	}
}

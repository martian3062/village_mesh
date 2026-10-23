#include "Character/VillageCharacter.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"
#include "Interaction/InteractionComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"
#include "PhysicalMaterials/PhysicalMaterial.h"

AVillageCharacter::AVillageCharacter()
{
	PrimaryActorTick.bCanEverTick = true;

	GetCapsuleComponent()->InitCapsuleSize(35.f, 90.f);

	// Rotate the character toward movement, not toward the camera.
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->bOrientRotationToMovement = true;
	Movement->RotationRate = FRotator(0.f, 500.f, 0.f);
	Movement->MaxWalkSpeed = WalkSpeed;
	Movement->JumpZVelocity = JumpZVelocityOverride;
	Movement->AirControl = AirControlOverride;
	Movement->MinAnalogWalkSpeed = 20.f;
	Movement->BrakingDecelerationWalking = 2000.f;

	// <PLAYER_MESH_PLACEHOLDER>: assign the skeletal mesh + anim class on the BP
	// child. Offsets below fit a standard UE mannequin-sized mesh.
	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -90.f), FRotator(0.f, -90.f, 0.f));

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 400.f;
	CameraBoom->bUsePawnControlRotation = true;

	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;

	InteractionComponent = CreateDefaultSubobject<UInteractionComponent>(TEXT("InteractionComponent"));

	// SurfaceType1/2 = "Dirt"/"Dust" (named in DefaultEngine.ini).
	DustSurfaceTypes.Add(SurfaceType1);
	DustSurfaceTypes.Add(SurfaceType2);
}

void AVillageCharacter::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	VillagerLookUtil::Apply(this, Appearance);
}

void AVillageCharacter::BeginPlay()
{
	Super::BeginPlay();

	VillagerLookUtil::Apply(this, Appearance);
	ApplyMovementSettings();
}

void AVillageCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// Stride-synthesised footsteps (see bAutoFootsteps in the header).
	if (bAutoFootsteps && GetCharacterMovement()->IsMovingOnGround())
	{
		const float Speed2D = GetVelocity().Size2D();
		if (Speed2D > 80.f)
		{
			DistanceSinceFootstep += Speed2D * DeltaTime;
			if (DistanceSinceFootstep >= AutoFootstepStride)
			{
				DistanceSinceFootstep = 0.f;
				OnFootstep();
			}
		}
		else
		{
			DistanceSinceFootstep = 0.f;
		}
	}
}

void AVillageCharacter::NotifyControllerChanged()
{
	Super::NotifyControllerChanged();

	// Runs on every possession (initial spawn, respawn, seamless travel).
	// BeginPlay is too early: pawns spawned after the world begins play get
	// BeginPlay before the controller is assigned.
	if (InteractionComponent)
	{
		InteractionComponent->EnsureHUDWidget(); // same ordering hazard as input
	}
	if (APlayerController* PC = Cast<APlayerController>(Controller))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Subsystem =
			ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			if (VillageMappingContext && !Subsystem->HasMappingContext(VillageMappingContext))
			{
				Subsystem->AddMappingContext(VillageMappingContext, 0);
			}
		}
	}
}

void AVillageCharacter::ApplyMovementSettings()
{
	UCharacterMovementComponent* Movement = GetCharacterMovement();
	Movement->MaxWalkSpeed = WalkSpeed;
	Movement->JumpZVelocity = JumpZVelocityOverride;
	Movement->AirControl = AirControlOverride;
}

void AVillageCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);

	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	if (!Input)
	{
		UE_LOG(LogTemp, Error,
			TEXT("VillageCharacter: expected an EnhancedInputComponent. Check Project Settings > Input default classes."));
		return;
	}

	if (MoveAction)
	{
		Input->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AVillageCharacter::Move);
	}
	if (LookAction)
	{
		Input->BindAction(LookAction, ETriggerEvent::Triggered, this, &AVillageCharacter::Look);
	}
	if (JumpAction)
	{
		Input->BindAction(JumpAction, ETriggerEvent::Started, this, &AVillageCharacter::JumpPressed);
		Input->BindAction(JumpAction, ETriggerEvent::Completed, this, &AVillageCharacter::JumpReleased);
	}
	if (SprintAction)
	{
		Input->BindAction(SprintAction, ETriggerEvent::Started, this, &AVillageCharacter::SprintPressed);
		Input->BindAction(SprintAction, ETriggerEvent::Completed, this, &AVillageCharacter::SprintReleased);
	}
	if (InteractAction)
	{
		Input->BindAction(InteractAction, ETriggerEvent::Started, this, &AVillageCharacter::InteractPressed);
		Input->BindAction(InteractAction, ETriggerEvent::Completed, this, &AVillageCharacter::InteractReleased);
	}
	if (CancelAction)
	{
		Input->BindAction(CancelAction, ETriggerEvent::Started, this, &AVillageCharacter::CancelPressed);
	}
}

// -------------------- input handlers --------------------
// Each handler offers the input to the interaction system first; a zone that
// is running a game consumes it. FreeRoam falls through to locomotion.

void AVillageCharacter::Move(const FInputActionValue& Value)
{
	const FVector2D MoveVector = Value.Get<FVector2D>();

	if (InteractionComponent->RouteMoveInput(MoveVector))
	{
		return;
	}

	if (Controller)
	{
		const FRotator YawRotation(0.f, Controller->GetControlRotation().Yaw, 0.f);
		const FVector Forward = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::X);
		const FVector Right = FRotationMatrix(YawRotation).GetUnitAxis(EAxis::Y);
		AddMovementInput(Forward, MoveVector.Y);
		AddMovementInput(Right, MoveVector.X);
	}
}

void AVillageCharacter::Look(const FInputActionValue& Value)
{
	const FVector2D LookVector = Value.Get<FVector2D>();

	if (InteractionComponent->RouteLookInput(LookVector))
	{
		return;
	}

	AddControllerYawInput(LookVector.X);
	AddControllerPitchInput(LookVector.Y);
}

void AVillageCharacter::JumpPressed(const FInputActionValue& Value)
{
	if (!InteractionComponent->RouteJumpInput(true))
	{
		Jump();
	}
}

void AVillageCharacter::JumpReleased(const FInputActionValue& Value)
{
	if (!InteractionComponent->RouteJumpInput(false))
	{
		StopJumping();
	}
}

void AVillageCharacter::SprintPressed(const FInputActionValue& Value)
{
	if (!InteractionComponent->RouteSprintInput(true))
	{
		GetCharacterMovement()->MaxWalkSpeed = SprintSpeed;
	}
}

void AVillageCharacter::SprintReleased(const FInputActionValue& Value)
{
	InteractionComponent->RouteSprintInput(false);
	// Reset unconditionally: a mini-game may consume the release (kite reel),
	// which would otherwise leave sprint speed latched after the game ends.
	GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
}

void AVillageCharacter::InteractPressed(const FInputActionValue& Value)
{
	InteractionComponent->OnInteractPressed();
}

void AVillageCharacter::InteractReleased(const FInputActionValue& Value)
{
	InteractionComponent->OnInteractReleased();
}

void AVillageCharacter::CancelPressed(const FInputActionValue& Value)
{
	InteractionComponent->OnCancelPressed();
}

// -------------------- footsteps --------------------

void AVillageCharacter::OnFootstep()
{
	const FVector Start = GetActorLocation();
	const FVector End = Start - FVector(0.f, 0.f,
		GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + FootstepTraceDistance);

	FCollisionQueryParams Params(SCENE_QUERY_STAT(FootstepTrace), /*bTraceComplex*/ false, this);
	Params.bReturnPhysicalMaterial = true;

	FHitResult Hit;
	if (!GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
	{
		return;
	}

	const EPhysicalSurface Surface = UPhysicalMaterial::DetermineSurfaceType(Hit.PhysMaterial.Get());
	const bool bDusty = DustSurfaceTypes.Num() == 0 || DustSurfaceTypes.Contains(Surface);

	if (bDusty && FootstepDustSystem)
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(
			this, FootstepDustSystem, Hit.ImpactPoint, Hit.ImpactNormal.Rotation());
	}
}

void AVillageCharacter::PlayGameMontage(UAnimMontage* Montage)
{
	if (Montage)
	{
		PlayAnimMontage(Montage);
	}
}

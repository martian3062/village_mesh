#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Chaos/ChaosEngineInterface.h" // EPhysicalSurface
#include "Character/VillagerLook.h"
#include "VillageCharacter.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UInputMappingContext;
class UInputAction;
class UInteractionComponent;
class UNiagaraSystem;
class UAnimMontage;
struct FInputActionValue;

/**
 * Third-person player character for the village.
 *
 * Mesh/anim assets are NOT set here — assign them on a Blueprint child
 * (BP_VillageCharacter): skeletal mesh = <PLAYER_MESH_PLACEHOLDER>,
 * anim class = your ABP (idle/walk/run come from there).
 *
 * All mini-game input is routed through the InteractionComponent: while a game
 * is active the zone consumes Move/Look/Jump/Sprint/Interact, otherwise this
 * class does normal locomotion. Adding a 4th game needs zero changes here.
 */
UCLASS()
class RURAL_PARDEEP_API AVillageCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AVillageCharacter();

	virtual void Tick(float DeltaTime) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;
	virtual void OnConstruction(const FTransform& Transform) override;

	/** The player's own Punjabi look (defaults set by the dressing script).
	 *  Named Appearance — this class already has a Look() input handler. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Look")
	FVillagerLook Appearance;

	/**
	 * Call from a footstep AnimNotify (manual hookup — see WIRING_CHECKLIST.md).
	 * Traces down, reads the physical material, and puffs dust on dirt/dust surfaces.
	 */
	UFUNCTION(BlueprintCallable, Category = "Village|Footsteps")
	void OnFootstep();

	UFUNCTION(BlueprintPure, Category = "Village")
	UInteractionComponent* GetInteractionComponent() const { return InteractionComponent; }

	/** Plays a montage if it has been assigned; safe to call with null. */
	void PlayGameMontage(UAnimMontage* Montage);

	// -------- Movement tuning --------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Movement", meta = (ClampMin = "0"))
	float WalkSpeed = 400.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Movement", meta = (ClampMin = "0"))
	float SprintSpeed = 650.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Movement", meta = (ClampMin = "0"))
	float JumpZVelocityOverride = 500.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Movement", meta = (ClampMin = "0", ClampMax = "1"))
	float AirControlOverride = 0.3f;

	// -------- Per-game montages (<ANIM_PLACEHOLDER> — assign in BP child) --------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Animation")
	TObjectPtr<UAnimMontage> DartThrowMontage;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Animation")
	TObjectPtr<UAnimMontage> MarbleFlickMontage;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Animation")
	TObjectPtr<UAnimMontage> KitePullMontage;

	// -------- Footstep dust --------

	/** Niagara system spawned at the foot on dusty surfaces. <DUST_NS_PLACEHOLDER> */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Footsteps")
	TObjectPtr<UNiagaraSystem> FootstepDustSystem;

	/**
	 * Surfaces that produce dust. Defaults to SurfaceType1/2 which
	 * DefaultEngine.ini names "Dirt"/"Dust". Empty array = puff on ANY surface
	 * (handy before physical materials are authored).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Footsteps")
	TArray<TEnumAsByte<EPhysicalSurface>> DustSurfaceTypes;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Footsteps", meta = (ClampMin = "0"))
	float FootstepTraceDistance = 150.f;

	/**
	 * Synthesise footsteps from distance travelled on the ground, so dust
	 * works with any anim set and zero notify wiring. Turn OFF once
	 * UFootstepNotify markers are hand-placed on the locomotion sequences.
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Footsteps")
	bool bAutoFootsteps = true;

	/** Centimetres travelled between synthesised footsteps. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Village|Footsteps",
		meta = (ClampMin = "50", EditCondition = "bAutoFootsteps"))
	float AutoFootstepStride = 180.f;

	// -------- Enhanced Input assets (assign in BP child — see checklist) --------

	/** IMC_Village */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Village|Input")
	TObjectPtr<UInputMappingContext> VillageMappingContext;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Village|Input")
	TObjectPtr<UInputAction> MoveAction;      // IA_Move    (Axis2D, WASD / left stick)

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Village|Input")
	TObjectPtr<UInputAction> LookAction;      // IA_Look    (Axis2D, mouse / right stick)

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Village|Input")
	TObjectPtr<UInputAction> JumpAction;      // IA_Jump    (Digital, Space)

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Village|Input")
	TObjectPtr<UInputAction> SprintAction;    // IA_Sprint  (Digital, LShift, hold)

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Village|Input")
	TObjectPtr<UInputAction> InteractAction;  // IA_Interact (Digital, E)

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Village|Input")
	TObjectPtr<UInputAction> CancelAction;    // IA_Cancel  (Digital, Esc)

protected:
	virtual void BeginPlay() override;
	virtual void NotifyControllerChanged() override;

	void Move(const FInputActionValue& Value);
	void Look(const FInputActionValue& Value);
	void JumpPressed(const FInputActionValue& Value);
	void JumpReleased(const FInputActionValue& Value);
	void SprintPressed(const FInputActionValue& Value);
	void SprintReleased(const FInputActionValue& Value);
	void InteractPressed(const FInputActionValue& Value);
	void InteractReleased(const FInputActionValue& Value);
	void CancelPressed(const FInputActionValue& Value);

	/** Pushes the movement UPROPERTYs above into CharacterMovement. */
	void ApplyMovementSettings();

	/** Ground distance accumulated toward the next synthesised footstep. */
	float DistanceSinceFootstep = 0.f;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Village|Components")
	TObjectPtr<USpringArmComponent> CameraBoom;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Village|Components")
	TObjectPtr<UCameraComponent> FollowCamera;

	/** THE shared interaction system — every mini-game routes through this. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Village|Components")
	TObjectPtr<UInteractionComponent> InteractionComponent;
};

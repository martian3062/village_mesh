#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WeatherManager.generated.h"

class ADirectionalLight;
class AExponentialHeightFog;
class UMaterialInstanceDynamic;
class UMaterialParameterCollection;
class UNiagaraComponent;
class UNiagaraSystem;
class UStaticMesh;
class UStaticMeshComponent;
class UCurveVector;

UENUM(BlueprintType)
enum class EVillageWeather : uint8
{
	Clear,
	Overcast,
	Rain,
	Storm
};

/** Blend targets for one weather state. Scales apply to the level's baseline
 *  sun/fog captured at BeginPlay, so profiles survive lighting re-tunes. */
USTRUCT(BlueprintType)
struct FWeatherProfile
{
	GENERATED_BODY()

	/** Multiplier on the directional light's baseline intensity. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0"))
	float SunScale = 1.f;

	/** Multiplier on the height fog's baseline density. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0"))
	float FogScale = 1.f;

	/** 0..1 -> MPC_Weather "WindIntensity" (tree sway amplitude). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0", ClampMax = "1"))
	float WindIntensity = 0.15f;

	/** 0..1 -> MPC_Weather "Wetness" (ground darkening etc.). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0", ClampMax = "1"))
	float Wetness = 0.f;

	/** 0..1 rain FX strength; > 0 activates the rain component. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0", ClampMax = "1"))
	float RainAmount = 0.f;
};

/**
 * Village weather: cycles Clear/Overcast/Rain/Storm with smooth blends.
 *
 * Drives (all optional — missing pieces are skipped, nothing crashes):
 *  - the level's directional light intensity (baseline captured at BeginPlay),
 *  - exponential height fog density,
 *  - MPC_Weather scalars "WindIntensity"/"Wetness" + vector "WindDirection"
 *    (tree/foliage sway materials read these for real-time gust response),
 *  - a rain Niagara component that follows the player,
 *  - lightning flashes during storms.
 *
 * Sun/fog/MPC references auto-resolve at BeginPlay when left unset. Place one
 * per level (the build script labels it VG_Weather). SetWeather() is
 * BlueprintCallable for scripted moments; bAutoCycle does the rest.
 */
UCLASS()
class RURAL_PARDEEP_API AWeatherManager : public AActor
{
	GENERATED_BODY()

public:
	AWeatherManager();

	virtual void Tick(float DeltaTime) override;

	UFUNCTION(BlueprintCallable, Category = "Weather")
	void SetWeather(EVillageWeather NewWeather, float BlendSeconds = 8.f);

	UFUNCTION(BlueprintPure, Category = "Weather")
	EVillageWeather GetCurrentWeather() const { return CurrentWeather; }

	UFUNCTION(BlueprintPure, Category = "Weather")
	FVector GetWindVelocityCm() const { return CurrentWindVelocity; }

	/** Optional vector curve exported from The Well. Dimensionless, art-directed
	 *  velocity samples; not a solver or a validated local weather forecast. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Wind")
	TObjectPtr<UCurveVector> WellWindCurve;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Wind", meta = (ClampMin = "0"))
	float WindSpeedCmPerSecond = 700.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Daylight")
	bool bDayNightCycle = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Daylight", meta = (ClampMin = "0", ClampMax = "24"))
	float TimeOfDayHours = 16.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Daylight", meta = (ClampMin = "1"))
	float DayLengthMinutes = 40.f;

	// -------- cycling --------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
	bool bAutoCycle = true;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "5"))
	float MinStateSeconds = 90.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "10"))
	float MaxStateSeconds = 240.f;

	/** Seconds a normal auto-cycle transition takes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0.1"))
	float DefaultBlendSeconds = 10.f;

	// -------- per-state profiles --------

	// Profile defaults are assigned in the constructor (USTRUCT + positional
	// brace-init is fragile under UHT).
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Profiles")
	FWeatherProfile ClearProfile;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Profiles")
	FWeatherProfile OvercastProfile;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Profiles")
	FWeatherProfile RainProfile;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Profiles")
	FWeatherProfile StormProfile;

	// -------- driven scene pieces (auto-found at BeginPlay when unset) --------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Scene")
	TObjectPtr<ADirectionalLight> SunLight;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Scene")
	TObjectPtr<AExponentialHeightFog> HeightFog;

	/** Defaults to /Game/Village/MPC_Weather when left unset. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Scene")
	TObjectPtr<UMaterialParameterCollection> WeatherMPC;

	/** Rain particle system; the rain component follows the player pawn. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Scene")
	TObjectPtr<UNiagaraSystem> RainSystem;

	/** Fallback/additional rain visual: an open cylinder with a panning
	 *  streak material, wrapped around the player. Both are assigned by the
	 *  build script (engine Cylinder + M_VGRainStreaks). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Scene")
	TObjectPtr<UStaticMesh> RainShellMesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Scene")
	TObjectPtr<UMaterialInterface> RainShellMaterial;

	/** World-space wind direction pushed into MPC_Weather once at BeginPlay. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Scene")
	FVector WindDirection = FVector(1.f, 0.35f, 0.f);

	// -------- storm lightning --------

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Lightning", meta = (ClampMin = "1"))
	float LightningMinInterval = 4.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Lightning", meta = (ClampMin = "2"))
	float LightningMaxInterval = 14.f;

	/** Sun intensity multiplier at the peak of a flash. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather|Lightning", meta = (ClampMin = "1"))
	float LightningBoost = 6.f;

protected:
	virtual void BeginPlay() override;

	const FWeatherProfile& ProfileFor(EVillageWeather Weather) const;
	EVillageWeather PickNextWeather() const;
	void ApplyProfile(const FWeatherProfile& Profile, float LightningAlpha);
	static FWeatherProfile LerpProfiles(const FWeatherProfile& A, const FWeatherProfile& B, float Alpha);

	UPROPERTY(Transient)
	TObjectPtr<UNiagaraComponent> RainComponent;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> RainShellComponent;

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInstanceDynamic> RainShellDMI;

	// runtime state
	EVillageWeather CurrentWeather = EVillageWeather::Clear;
	FWeatherProfile BlendFrom;
	FWeatherProfile BlendTo;
	float BlendElapsed = 0.f;
	float BlendDuration = 0.f;
	float TimeToNextCycle = 0.f;
	float NextFlashIn = 0.f;
	float FlashTimeLeft = 0.f;
	float BaseSunIntensity = 10.f;
	float BaseFogDensity = 0.02f;
	float WindTime = 0.f;
	FVector CurrentWindVelocity = FVector::ZeroVector;
	TArray<float> WellSampleTimes;
	TArray<FVector> WellSampleVectors;
};

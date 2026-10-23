#include "Environment/WeatherManager.h"

#include "Components/ExponentialHeightFogComponent.h"
#include "Components/LightComponent.h"
#include "Curves/CurveVector.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialParameterCollection.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "SunPosition.h"

namespace
{
	const FName WindIntensityParam(TEXT("WindIntensity"));
	const FName WetnessParam(TEXT("Wetness"));
	const FName WindDirectionParam(TEXT("WindDirection"));
	const TCHAR* DefaultMPCPath = TEXT("/Game/Village/MPC_Weather.MPC_Weather");
}

AWeatherManager::AWeatherManager()
{
	PrimaryActorTick.bCanEverTick = true;

	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));

	RainComponent = CreateDefaultSubobject<UNiagaraComponent>(TEXT("RainComponent"));
	RainComponent->SetupAttachment(RootComponent);
	RainComponent->SetAutoActivate(false);
	// The component chases the player pawn, not this actor's transform.
	RainComponent->SetAbsolute(true, true, true);

	RainShellComponent = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RainShell"));
	RainShellComponent->SetupAttachment(RootComponent);
	RainShellComponent->SetAbsolute(true, true, true);
	RainShellComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	RainShellComponent->SetCastShadow(false);
	RainShellComponent->SetVisibility(false);

	// Clear = the level's authored look; everything else darkens/thickens it.
	ClearProfile.SunScale = 1.f;    ClearProfile.FogScale = 1.f;
	ClearProfile.WindIntensity = 0.15f; ClearProfile.Wetness = 0.f;  ClearProfile.RainAmount = 0.f;
	OvercastProfile.SunScale = 0.45f; OvercastProfile.FogScale = 2.5f;
	OvercastProfile.WindIntensity = 0.35f; OvercastProfile.Wetness = 0.1f; OvercastProfile.RainAmount = 0.f;
	RainProfile.SunScale = 0.30f;   RainProfile.FogScale = 4.f;
	RainProfile.WindIntensity = 0.55f; RainProfile.Wetness = 0.8f;   RainProfile.RainAmount = 0.6f;
	StormProfile.SunScale = 0.18f;  StormProfile.FogScale = 6.f;
	StormProfile.WindIntensity = 1.f;  StormProfile.Wetness = 1.f;   StormProfile.RainAmount = 1.f;
}

void AWeatherManager::BeginPlay()
{
	Super::BeginPlay();
	TArray<FString> Rows;
	if (FFileHelper::LoadFileToStringArray(Rows, *(FPaths::ProjectContentDir() / TEXT("Well/wind.csv"))))
	{
		bool bValid = Rows.Num() >= 3 && Rows.Num() <= 4097 && Rows[0] == TEXT("time,x,y,z");
		for (int32 I = 1; bValid && I < Rows.Num(); ++I)
		{
			TArray<FString> Cells;
			Rows[I].ParseIntoArray(Cells, TEXT(","), false);
			float T = 0.f, X = 0.f, Y = 0.f, Z = 0.f;
			bValid = Cells.Num() == 4 && LexTryParseString(T, *Cells[0]) && LexTryParseString(X, *Cells[1])
				&& LexTryParseString(Y, *Cells[2]) && LexTryParseString(Z, *Cells[3]);
			bValid = bValid && FMath::IsFinite(T) && FMath::IsFinite(X) && FMath::IsFinite(Y)
				&& FMath::IsFinite(Z) && T >= 0.f && FVector(X, Y, Z).Size() <= 2.f
				&& (WellSampleTimes.IsEmpty() || T > WellSampleTimes.Last());
			if (bValid) { WellSampleTimes.Add(T); WellSampleVectors.Add(FVector(X, Y, Z)); }
		}
		if (!bValid) { WellSampleTimes.Reset(); WellSampleVectors.Reset(); }
		UE_LOG(LogTemp, Display, TEXT("Village Well wind: %d validated samples"), WellSampleTimes.Num());
	}

	// Resolve unset scene references from the level.
	if (!SunLight)
	{
		for (TActorIterator<ADirectionalLight> It(GetWorld()); It; ++It)
		{
			SunLight = *It;
			break;
		}
	}
	if (!HeightFog)
	{
		for (TActorIterator<AExponentialHeightFog> It(GetWorld()); It; ++It)
		{
			HeightFog = *It;
			break;
		}
	}
	if (!WeatherMPC)
	{
		WeatherMPC = LoadObject<UMaterialParameterCollection>(nullptr, DefaultMPCPath);
	}

	// Baselines: profiles scale these, so the level's authored look = Clear.
	if (SunLight && SunLight->GetLightComponent())
	{
		BaseSunIntensity = SunLight->GetLightComponent()->Intensity;
	}
	if (HeightFog && HeightFog->GetComponent())
	{
		BaseFogDensity = FMath::Max(HeightFog->GetComponent()->FogDensity, 0.005f);
	}

	if (WeatherMPC)
	{
		UKismetMaterialLibrary::SetVectorParameterValue(this, WeatherMPC, WindDirectionParam,
			FLinearColor(WindDirection.X, WindDirection.Y, WindDirection.Z, 0.f));
	}
	if (RainSystem)
	{
		RainComponent->SetAsset(RainSystem);
	}
	if (RainShellMesh)
	{
		RainShellComponent->SetStaticMesh(RainShellMesh);
		RainShellComponent->SetWorldScale3D(FVector(16.f, 16.f, 24.f));
		if (RainShellMaterial)
		{
			RainShellDMI = UMaterialInstanceDynamic::Create(RainShellMaterial, this);
			RainShellComponent->SetMaterial(0, RainShellDMI);
		}
	}

	// Start firmly in Clear with no blend.
	CurrentWeather = EVillageWeather::Clear;
	BlendFrom = BlendTo = ProfileFor(CurrentWeather);
	BlendElapsed = BlendDuration = 0.f;
	TimeToNextCycle = FMath::FRandRange(MinStateSeconds, MaxStateSeconds);
	ApplyProfile(BlendTo, 0.f);
}

const FWeatherProfile& AWeatherManager::ProfileFor(EVillageWeather Weather) const
{
	switch (Weather)
	{
	case EVillageWeather::Overcast: return OvercastProfile;
	case EVillageWeather::Rain:     return RainProfile;
	case EVillageWeather::Storm:    return StormProfile;
	default:                        return ClearProfile;
	}
}

EVillageWeather AWeatherManager::PickNextWeather() const
{
	// Weighted draw, never repeating the current state.
	struct FChoice { EVillageWeather Weather; float Weight; };
	const FChoice Choices[] =
	{
		{ EVillageWeather::Clear,    0.40f },
		{ EVillageWeather::Overcast, 0.30f },
		{ EVillageWeather::Rain,     0.20f },
		{ EVillageWeather::Storm,    0.10f },
	};

	float Total = 0.f;
	for (const FChoice& C : Choices)
	{
		if (C.Weather != CurrentWeather)
		{
			Total += C.Weight;
		}
	}
	float Roll = FMath::FRandRange(0.f, Total);
	for (const FChoice& C : Choices)
	{
		if (C.Weather == CurrentWeather)
		{
			continue;
		}
		Roll -= C.Weight;
		if (Roll <= 0.f)
		{
			return C.Weather;
		}
	}
	return EVillageWeather::Clear;
}

void AWeatherManager::SetWeather(EVillageWeather NewWeather, float BlendSeconds)
{
	// Freeze the current blended values as the new starting point so a
	// mid-blend change never pops.
	const float Alpha = BlendDuration > 0.f
		? FMath::Clamp(BlendElapsed / BlendDuration, 0.f, 1.f) : 1.f;
	BlendFrom = LerpProfiles(BlendFrom, BlendTo, Alpha);

	CurrentWeather = NewWeather;
	BlendTo = ProfileFor(NewWeather);
	BlendElapsed = 0.f;
	BlendDuration = FMath::Max(BlendSeconds, 0.1f);
	NextFlashIn = FMath::FRandRange(LightningMinInterval, LightningMaxInterval);
}

FWeatherProfile AWeatherManager::LerpProfiles(const FWeatherProfile& A, const FWeatherProfile& B, float Alpha)
{
	FWeatherProfile Out;
	Out.SunScale = FMath::Lerp(A.SunScale, B.SunScale, Alpha);
	Out.FogScale = FMath::Lerp(A.FogScale, B.FogScale, Alpha);
	Out.WindIntensity = FMath::Lerp(A.WindIntensity, B.WindIntensity, Alpha);
	Out.Wetness = FMath::Lerp(A.Wetness, B.Wetness, Alpha);
	Out.RainAmount = FMath::Lerp(A.RainAmount, B.RainAmount, Alpha);
	return Out;
}

void AWeatherManager::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);
	WindTime += DeltaTime;
	if (bDayNightCycle)
	{
		TimeOfDayHours = FMath::Fmod(TimeOfDayHours + DeltaTime * 24.f / (FMath::Max(1.f, DayLengthMinutes) * 60.f), 24.f);
		if (SunLight && !bUseGeographicSun) SunLight->SetActorRotation(FRotator((TimeOfDayHours - 6.f) * -15.f, -35.f, 0.f));
	}
	SunUpdateElapsed += DeltaTime;
	if (bUseGeographicSun && SunLight && SunUpdateElapsed >= .25f)
	{
		SunUpdateElapsed = 0.f;
		FSunPositionData Sun;
		const int32 Seconds = FMath::FloorToInt(TimeOfDayHours * 3600.f);
		USunPositionFunctionLibrary::GetSunPosition(Latitude,Longitude,UtcOffsetHours,false,
			CalendarYear,CalendarMonth,CalendarDay,Seconds/3600,(Seconds/60)%60,Seconds%60,Sun);
		// UE 5.8 SunPosition returns its light-rotation elevation with a +180 offset
		// (223.08 at this site's 13:30 test). Convert to physical elevation once.
		EnvironmentState.SunElevationDegrees = Sun.CorrectedElevation - 180.f;
		// Solar azimuth is clockwise from north. X=east/Y=north; light points away from sun.
		SunLight->SetActorRotation(FRotator(-EnvironmentState.SunElevationDegrees,270.f-Sun.Azimuth,0.f));
	}

	// ---- auto cycle ----
	if (bAutoCycle)
	{
		TimeToNextCycle -= DeltaTime;
		if (TimeToNextCycle <= 0.f)
		{
			TimeToNextCycle = FMath::FRandRange(MinStateSeconds, MaxStateSeconds);
			SetWeather(PickNextWeather(), DefaultBlendSeconds);
		}
	}

	// ---- blend ----
	float Alpha = 1.f;
	if (BlendDuration > 0.f && BlendElapsed < BlendDuration)
	{
		BlendElapsed += DeltaTime;
		Alpha = FMath::Clamp(BlendElapsed / BlendDuration, 0.f, 1.f);
	}
	const FWeatherProfile Current = LerpProfiles(BlendFrom, BlendTo, Alpha);
	FVector Direction = WindDirection.GetSafeNormal();
	float Gust = 0.8f + 0.13f * FMath::Sin(WindTime * 0.37f) + 0.07f * FMath::Sin(WindTime * 1.13f);
	if (WellWindCurve)
	{
		float Start, End;
		WellWindCurve->GetTimeRange(Start, End);
		const float CurveTime = End > Start ? Start + FMath::Fmod(WindTime, End - Start) : Start;
		Direction = WellWindCurve->GetVectorValue(CurveTime).GetClampedToMaxSize(2.f);
		Gust = 1.f;
	}
	else if (WellSampleTimes.Num() >= 2)
	{
		const float T = WellSampleTimes[0] + FMath::Fmod(WindTime, WellSampleTimes.Last() - WellSampleTimes[0]);
		int32 Next = 1;
		while (Next < WellSampleTimes.Num() - 1 && WellSampleTimes[Next] < T) ++Next;
		const float A = (T - WellSampleTimes[Next - 1]) / (WellSampleTimes[Next] - WellSampleTimes[Next - 1]);
		Direction = FMath::Lerp(WellSampleVectors[Next - 1], WellSampleVectors[Next], A);
		Gust = 1.f;
	}
	CurrentWindVelocity = Direction * WindSpeedCmPerSecond * Current.WindIntensity * Gust;
	EnvironmentState.WindMetersPerSecond = CurrentWindVelocity * .01f;
	EnvironmentState.RainfallMmPerHour = Current.RainAmount * 18.f;
	EnvironmentState.Cloudiness = 1.f - Current.SunScale;
	if (bUseV2Environment)
	{
		const float Target = Current.RainAmount > .01f ? Current.Wetness : 0.f;
		const float Duration = Target > EnvironmentState.Wetness ? WettingSeconds : DryingSeconds;
		EnvironmentState.Wetness = FMath::FInterpConstantTo(EnvironmentState.Wetness,Target,DeltaTime,1.f/FMath::Max(1.f,Duration));
	}
	else EnvironmentState.Wetness = Current.Wetness;
	if (WeatherMPC)
	{
		const FVector UnitWind = CurrentWindVelocity.GetSafeNormal();
		UKismetMaterialLibrary::SetVectorParameterValue(this, WeatherMPC, WindDirectionParam,
			FLinearColor(UnitWind.X, UnitWind.Y, UnitWind.Z, 0.f));
	}

	// ---- storm lightning ----
	float LightningAlpha = 0.f;
	if (CurrentWeather == EVillageWeather::Storm)
	{
		if (FlashTimeLeft > 0.f)
		{
			FlashTimeLeft -= DeltaTime;
			LightningAlpha = FMath::Max(FlashTimeLeft / 0.18f, 0.f);
		}
		else
		{
			NextFlashIn -= DeltaTime;
			if (NextFlashIn <= 0.f)
			{
				FlashTimeLeft = 0.18f;
				NextFlashIn = FMath::FRandRange(LightningMinInterval, LightningMaxInterval);
			}
		}
	}
	else
	{
		FlashTimeLeft = 0.f;
	}

	ApplyProfile(Current, LightningAlpha);

	// ---- rain follows the player ----
	const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	EnvironmentState.bPlayerSheltered = bUseV2Environment && Pawn && IsShelteredAt(Pawn->GetActorLocation());
	const bool bRaining = Current.RainAmount > 0.01f && !EnvironmentState.bPlayerSheltered;

	if (bRaining && RainComponent->GetAsset())
	{
		if (Pawn)
		{
			RainComponent->SetWorldLocation(Pawn->GetActorLocation() + FVector(0.f, 0.f, 900.f));
		}
		if (!RainComponent->IsActive())
		{
			RainComponent->Activate();
		}
		// Best-effort user parameter; silently ignored if the system lacks it.
		RainComponent->SetVariableFloat(TEXT("User.RainAmount"), Current.RainAmount);
	}
	else if (RainComponent->IsActive())
	{
		RainComponent->Deactivate();
	}

	if (RainShellComponent->GetStaticMesh())
	{
		RainShellComponent->SetVisibility(bRaining);
		if (bRaining)
		{
			if (Pawn)
			{
				RainShellComponent->SetWorldLocation(Pawn->GetActorLocation());
			}
			if (RainShellDMI)
			{
				RainShellDMI->SetScalarParameterValue(TEXT("RainAmount"), Current.RainAmount);
			}
		}
	}
}

void AWeatherManager::ApplyProfile(const FWeatherProfile& Profile, float LightningAlpha)
{
	if (SunLight && SunLight->GetLightComponent())
	{
		const float Boost = FMath::Lerp(1.f, LightningBoost, LightningAlpha);
		const float Daylight = bUseGeographicSun ? FMath::Clamp(FMath::Sin(FMath::DegreesToRadians(EnvironmentState.SunElevationDegrees))*1.3f,0.f,1.f) : bDayNightCycle
			? FMath::Max(0.f, FMath::Sin((TimeOfDayHours - 6.f) * PI / 12.f)) : 1.f;
		SunLight->GetLightComponent()->SetIntensity(BaseSunIntensity * Profile.SunScale * Boost * Daylight);
	}
	if (HeightFog && HeightFog->GetComponent())
	{
		HeightFog->GetComponent()->SetFogDensity(BaseFogDensity * Profile.FogScale);
	}
	if (WeatherMPC)
	{
		UKismetMaterialLibrary::SetScalarParameterValue(this, WeatherMPC, WindIntensityParam, Profile.WindIntensity);
		UKismetMaterialLibrary::SetScalarParameterValue(this, WeatherMPC, WetnessParam, EnvironmentState.Wetness);
	}
}

bool AWeatherManager::IsShelteredAt(FVector Position) const
{
	FHitResult Hit;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(VillageRainShelter),false,this);
	if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this,0)) Params.AddIgnoredActor(Pawn);
	return GetWorld()->LineTraceSingleByChannel(Hit,Position+FVector(0,0,60),Position+FVector(0,0,3000),ECC_Visibility,Params);
}

void AWeatherManager::SetPresentationCondition(FName Condition)
{
	bAutoCycle = false;
	bDayNightCycle = false;
	TimeOfDayHours = Condition == TEXT("evening") ? 17.5f : 13.5f;
	const EVillageWeather Preset = Condition == TEXT("rain") ? EVillageWeather::Rain
		: Condition == TEXT("overcast") ? EVillageWeather::Overcast : EVillageWeather::Clear;
	SetWeather(Preset,.1f);
	SunUpdateElapsed = 1.f;
}

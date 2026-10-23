#include "Environment/RoadSpline.h"

#include "Components/SplineComponent.h"

ARoadSpline::ARoadSpline()
{
	PrimaryActorTick.bCanEverTick = false;

	Spline = CreateDefaultSubobject<USplineComponent>(TEXT("Spline"));
	SetRootComponent(Spline);
}

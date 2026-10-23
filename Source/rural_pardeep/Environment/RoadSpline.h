#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RoadSpline.generated.h"

class USplineComponent;

/**
 * A dirt-road centreline. The environment build script spawns these, feeds
 * the spline points, and lays visual road segments along them; the mini-game
 * placement script reads them back to keep zones clear of roads.
 */
UCLASS()
class RURAL_PARDEEP_API ARoadSpline : public AActor
{
	GENERATED_BODY()

public:
	ARoadSpline();

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Road")
	TObjectPtr<USplineComponent> Spline;
};

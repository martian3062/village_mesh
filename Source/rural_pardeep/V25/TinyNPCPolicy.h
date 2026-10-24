#pragma once
#include "CoreMinimal.h"
#include "Async/Future.h"
#include "NNERuntimeCPU.h"

struct FV25InferenceResult
{
    TArray<float> Logits;
    uint64 Generation=0;
    double RequestedAt=0, StartedAt=0, FinishedAt=0;
    bool bSuccess=false;
};

/** One worker-owned instance, one bounded batch, no UObject access on worker. */
class FTinyNPCPolicy
{
public:
    bool Load(bool MissingAssetTest=false);
    bool Submit(const TArray<float>& Features,uint64 Generation);
    bool Poll(FV25InferenceResult& Result);
    bool IsReady() const { return Instance.IsValid(); }
    bool IsBusy() const { return Future.IsValid(); }
    double ParityError=0;
    FString Status=TEXT("not loaded");
private:
    TSharedPtr<UE::NNE::IModelInstanceCPU> Instance;
    TFuture<FV25InferenceResult> Future;
};

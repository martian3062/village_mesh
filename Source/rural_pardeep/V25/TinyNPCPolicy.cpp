#include "V25/TinyNPCPolicy.h"
#include "NNE.h"
#include "NNEModelData.h"
#include "Async/Async.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

bool FTinyNPCPolicy::Load(bool MissingAssetTest)
{
    const auto Runtime=UE::NNE::GetRuntime<INNERuntimeCPU>(TEXT("NNERuntimeORTCpu"));
    if (!Runtime.IsValid()) { Status=TEXT("CPU runtime missing; rules fallback");return false; }
    auto* Data=LoadObject<UNNEModelData>(nullptr,MissingAssetTest?TEXT("/Game/VillageMeshV25/Models/intentionally_missing.intentionally_missing"):TEXT("/Game/VillageMeshV25/Models/npc_policy_v1.npc_policy_v1"));
    if (!Data || Runtime->CanCreateModelCPU(Data)!=UE::NNE::EResultStatus::Ok)
    { Status=TEXT("model unavailable; rules fallback");return false; }
    const auto Model=Runtime->CreateModelCPU(Data);
    if (!Model.IsValid()) { Status=TEXT("model creation failed");return false; }
    Instance=Model->CreateModelInstanceCPU();
    const uint32 Dims[]={1,64};
    const UE::NNE::FTensorShape Shape=UE::NNE::FTensorShape::Make(Dims);
    if (!Instance.IsValid() || Instance->SetInputTensorShapes(MakeArrayView(&Shape,1))!=UE::NNE::EResultStatus::Ok)
    { Instance.Reset();Status=TEXT("invalid model shape");return false; }
    const auto Output=Instance->GetOutputTensorShapes();
    if (Output.Num()!=1 || Output[0].Volume()!=48) { Instance.Reset();Status=TEXT("invalid output shape");return false; }
    FString Text;TSharedPtr<FJsonObject> Parity;
    if (!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("V25/Data/policy_parity.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Parity))
    { Instance.Reset();Status=TEXT("parity fixture missing");return false; }
    for (const auto& Row:Parity->GetArrayField(TEXT("vectors")))
    {
        const auto Object=Row->AsObject();const auto& Input=Object->GetArrayField(TEXT("input"));const auto& Expected=Object->GetArrayField(TEXT("output"));
        if (Input.Num()!=64 || Expected.Num()!=48) { Instance.Reset();Status=TEXT("invalid parity fixture");return false; }
        float X[64],Y[48];for (int i=0;i<64;++i) X[i]=Input[i]->AsNumber();
        const UE::NNE::FTensorBindingCPU In{X,sizeof(X)},Out{Y,sizeof(Y)};
        if (Instance->RunSync(MakeArrayView(&In,1),MakeArrayView(&Out,1))!=UE::NNE::EResultStatus::Ok)
        { Instance.Reset();Status=TEXT("CPU inference failed");return false; }
        for (int i=0;i<48;++i)
        {
            if (!FMath::IsFinite(Y[i])) { Instance.Reset();Status=TEXT("nonfinite model output");return false; }
            ParityError=FMath::Max(ParityError,FMath::Abs(double(Y[i])-Expected[i]->AsNumber()));
        }
    }
    if (ParityError>.0001) { Instance.Reset();Status=TEXT("Unreal/ONNX parity failed");return false; }
    Status=TEXT("ORT CPU ready; 121520 parameters");return true;
}

bool FTinyNPCPolicy::Submit(const TArray<float>& Features,uint64 Generation)
{
    if (!Instance.IsValid() || Future.IsValid() || Features.Num()!=8*64) return false;
    for (float Value:Features) if (!FMath::IsFinite(Value) || Value<0 || Value>1) return false;
    const auto OwnedInstance=Instance;const double Request=FPlatformTime::Seconds();
    Future=Async(EAsyncExecution::ThreadPool,[OwnedInstance,Input=Features,Generation,Request]() mutable
    {
        FV25InferenceResult Result;Result.Generation=Generation;Result.RequestedAt=Request;Result.StartedAt=FPlatformTime::Seconds();
        Result.Logits.SetNumZeroed(8*48);Result.bSuccess=true;
        for (int i=0;i<8;++i)
        {
            UE::NNE::FTensorBindingCPU In{Input.GetData()+64*i,64*sizeof(float)},Out{Result.Logits.GetData()+48*i,48*sizeof(float)};
            if (OwnedInstance->RunSync(MakeArrayView(&In,1),MakeArrayView(&Out,1))!=UE::NNE::EResultStatus::Ok) { Result.bSuccess=false;break; }
        }
        for (float Value:Result.Logits) Result.bSuccess &= FMath::IsFinite(Value);
        Result.FinishedAt=FPlatformTime::Seconds();return Result;
    });
    return true;
}
bool FTinyNPCPolicy::Poll(FV25InferenceResult& Result)
{
    if (!Future.IsValid() || !Future.IsReady()) return false;
    Result=Future.Get();Future=TFuture<FV25InferenceResult>();return true;
}

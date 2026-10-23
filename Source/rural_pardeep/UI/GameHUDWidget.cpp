#include "UI/GameHUDWidget.h"

#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/ProgressBar.h"
#include "Components/SizeBox.h"
#include "Components/Spacer.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/Texture2D.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Styling/CoreStyle.h"

namespace
{
	// Warm village palette.
	const FLinearColor PanelTint(0.020f, 0.014f, 0.008f, 0.82f);   // dark earthen brown
	const FLinearColor KeycapTint(0.85f, 0.72f, 0.38f, 0.95f);     // brass key
	const FLinearColor KeycapTextTint(0.10f, 0.07f, 0.02f, 1.f);
	const FLinearColor AccentTint(0.96f, 0.69f, 0.20f, 1.f);       // saffron
	const FLinearColor BodyTint(0.94f, 0.92f, 0.87f, 1.f);         // warm white
	const FLinearColor DimTint(0.75f, 0.71f, 0.62f, 0.9f);
	const FLinearColor GoodTint(0.35f, 0.75f, 0.30f, 1.f);
	const FLinearColor BadTint(0.85f, 0.22f, 0.12f, 1.f);

	FSlateBrush MakeRoundedBrush(float CornerRadius, const FLinearColor& Tint)
	{
		FSlateBrush Brush;
		Brush.DrawAs = ESlateBrushDrawType::RoundedBox;
		Brush.TintColor = FSlateColor(Tint);
		Brush.OutlineSettings.RoundingType = ESlateBrushRoundingType::FixedRadius;
		Brush.OutlineSettings.CornerRadii = FVector4(CornerRadius, CornerRadius, CornerRadius, CornerRadius);
		Brush.OutlineSettings.Color = FSlateColor(FLinearColor(1.f, 0.85f, 0.55f, 0.10f));
		Brush.OutlineSettings.Width = 1.0f;
		return Brush;
	}
}

// ====================== lifecycle ======================

void UGameHUDWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();
	BuildTree();
	// Pure state display: never intercept clicks meant for the game viewport.
	SetVisibility(ESlateVisibility::HitTestInvisible);
}

void UGameHUDWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	if (StatusTimeLeft > 0.f && StatusText)
	{
		StatusTimeLeft -= InDeltaTime;
		const float Alpha = FMath::Clamp(StatusTimeLeft / FMath::Max(StatusFadeTime, 0.05f), 0.f, 1.f);
		StatusText->SetRenderOpacity(Alpha);
		if (StatusTimeLeft <= 0.f)
		{
			StatusText->SetVisibility(ESlateVisibility::Collapsed);
		}
	}

	UpdateMinimap();
}

// ====================== tree construction ======================

void UGameHUDWidget::BuildTree()
{
	// A Blueprint child with its own designed hierarchy wins — its designer
	// tree (and its event overrides) fully replace the native visuals.
	if (!WidgetTree || WidgetTree->RootWidget)
	{
		return;
	}

	UCanvasPanel* Canvas = WidgetTree->ConstructWidget<UCanvasPanel>(
		UCanvasPanel::StaticClass(), TEXT("RootCanvas"));
	WidgetTree->RootWidget = Canvas;

	BuildPrompt(Canvas);
	BuildDialoguePanel(Canvas);
	BuildMeters(Canvas);
	BuildStatusBanner(Canvas);
	BuildGamePanels(Canvas);
	BuildMinimap(Canvas);

	bNativeTreeBuilt = true;
}

UTextBlock* UGameHUDWidget::MakeText(const FText& InText, int32 Size,
	const FLinearColor& Color, bool bBold, FName WidgetName)
{
	UTextBlock* Text = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), WidgetName);
	Text->SetText(InText);
	Text->SetFont(FCoreStyle::GetDefaultFontStyle(bBold ? "Bold" : "Regular", Size));
	Text->SetColorAndOpacity(FSlateColor(Color));
	Text->SetShadowOffset(FVector2D(1.f, 1.5f));
	Text->SetShadowColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.6f));
	return Text;
}

UBorder* UGameHUDWidget::MakePanelBorder(float CornerRadius, const FLinearColor& Tint,
	const FMargin& InPadding)
{
	UBorder* Border = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass());
	Border->SetBrush(MakeRoundedBrush(CornerRadius, Tint));
	Border->SetPadding(InPadding);
	Border->SetHorizontalAlignment(HAlign_Center);
	Border->SetVerticalAlignment(VAlign_Center);
	return Border;
}

UTextBlock* UGameHUDWidget::AddStatRow(UVerticalBox* Panel, const FText& Label)
{
	UHorizontalBox* Row = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());

	UTextBlock* LabelText = MakeText(Label, 13, DimTint, /*bBold*/ false);
	UHorizontalBoxSlot* LabelSlot = Row->AddChildToHorizontalBox(LabelText);
	LabelSlot->SetVerticalAlignment(VAlign_Center);

	USpacer* Gap = WidgetTree->ConstructWidget<USpacer>(USpacer::StaticClass());
	Gap->SetSize(FVector2D(18.f, 1.f));
	UHorizontalBoxSlot* GapSlot = Row->AddChildToHorizontalBox(Gap);
	GapSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));

	UTextBlock* ValueText = MakeText(FText::FromString(TEXT("-")), 19, BodyTint);
	UHorizontalBoxSlot* ValueSlot = Row->AddChildToHorizontalBox(ValueText);
	ValueSlot->SetVerticalAlignment(VAlign_Center);

	UVerticalBoxSlot* RowSlot = Panel->AddChildToVerticalBox(Row);
	RowSlot->SetPadding(FMargin(0.f, 3.f));
	return ValueText;
}

void UGameHUDWidget::BuildPrompt(UCanvasPanel* Canvas)
{
	UHorizontalBox* Line = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());

	UTextBlock* Press = MakeText(NSLOCTEXT("HUD", "PromptPress", "Press"), 17, BodyTint, false);
	UHorizontalBoxSlot* PressSlot = Line->AddChildToHorizontalBox(Press);
	PressSlot->SetVerticalAlignment(VAlign_Center);

	UBorder* Keycap = MakePanelBorder(5.f, KeycapTint, FMargin(9.f, 2.f));
	Keycap->SetContent(MakeText(NSLOCTEXT("HUD", "PromptKeyE", "E"), 16, KeycapTextTint));
	UHorizontalBoxSlot* KeySlot = Line->AddChildToHorizontalBox(Keycap);
	KeySlot->SetPadding(FMargin(7.f, 0.f));
	KeySlot->SetVerticalAlignment(VAlign_Center);

	PromptSuffixText = MakeText(FText::GetEmpty(), 17, BodyTint, false, TEXT("PromptSuffix"));
	UHorizontalBoxSlot* SuffixSlot = Line->AddChildToHorizontalBox(PromptSuffixText);
	SuffixSlot->SetVerticalAlignment(VAlign_Center);

	PromptBorder = MakePanelBorder(9.f, PanelTint, FMargin(16.f, 9.f));
	PromptBorder->SetContent(Line);
	PromptBorder->SetVisibility(ESlateVisibility::Collapsed);

	UCanvasPanelSlot* CanvasSlot = Canvas->AddChildToCanvas(PromptBorder);
	CanvasSlot->SetAnchors(FAnchors(0.5f, 1.f));
	CanvasSlot->SetAlignment(FVector2D(0.5f, 1.f));
	CanvasSlot->SetPosition(FVector2D(0.f, -130.f));
	CanvasSlot->SetAutoSize(true);
}

void UGameHUDWidget::BuildDialoguePanel(UCanvasPanel* Canvas)
{
	UVerticalBox* Box = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());

	DialogueSpeakerText = MakeText(FText::GetEmpty(), 19, AccentTint, true, TEXT("DialogueSpeaker"));
	Box->AddChildToVerticalBox(DialogueSpeakerText);

	DialogueLineText = MakeText(FText::GetEmpty(), 17, BodyTint, false, TEXT("DialogueLine"));
	DialogueLineText->SetAutoWrapText(true);
	UVerticalBoxSlot* LineSlot = Box->AddChildToVerticalBox(DialogueLineText);
	LineSlot->SetPadding(FMargin(0.f, 7.f, 0.f, 9.f));

	UTextBlock* Hint = MakeText(
		NSLOCTEXT("HUD", "DialogueHint", "E — continue      Q — leave"), 12, DimTint, false);
	Box->AddChildToVerticalBox(Hint);

	USizeBox* Width = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	Width->SetWidthOverride(660.f);
	Width->SetContent(Box);

	DialogueBorder = MakePanelBorder(11.f, PanelTint, FMargin(20.f, 14.f));
	DialogueBorder->SetHorizontalAlignment(HAlign_Fill);
	DialogueBorder->SetContent(Width);
	DialogueBorder->SetVisibility(ESlateVisibility::Collapsed);

	UCanvasPanelSlot* CanvasSlot = Canvas->AddChildToCanvas(DialogueBorder);
	CanvasSlot->SetAnchors(FAnchors(0.5f, 1.f));
	CanvasSlot->SetAlignment(FVector2D(0.5f, 1.f));
	CanvasSlot->SetPosition(FVector2D(0.f, -70.f));
	CanvasSlot->SetAutoSize(true);
}

void UGameHUDWidget::BuildMeters(UCanvasPanel* Canvas)
{
	// ---- shared power / charge meter ----
	{
		UVerticalBox* Box = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());

		UTextBlock* Label = MakeText(NSLOCTEXT("HUD", "PowerLabel", "POWER"), 11, DimTint);
		UVerticalBoxSlot* LabelSlot = Box->AddChildToVerticalBox(Label);
		LabelSlot->SetHorizontalAlignment(HAlign_Center);
		LabelSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 3.f));

		PowerBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("PowerBar"));
		PowerBar->SetPercent(0.f);
		PowerBar->SetFillColorAndOpacity(GoodTint);
		USizeBox* BarHeight = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
		BarHeight->SetHeightOverride(17.f);
		BarHeight->SetContent(PowerBar);
		Box->AddChildToVerticalBox(BarHeight);

		PowerMeterBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("PowerMeterBox"));
		PowerMeterBox->SetWidthOverride(330.f);
		PowerMeterBox->SetContent(Box);
		PowerMeterBox->SetVisibility(ESlateVisibility::Collapsed);

		UCanvasPanelSlot* CanvasSlot = Canvas->AddChildToCanvas(PowerMeterBox);
		CanvasSlot->SetAnchors(FAnchors(0.5f, 1.f));
		CanvasSlot->SetAlignment(FVector2D(0.5f, 1.f));
		CanvasSlot->SetPosition(FVector2D(0.f, -215.f));
		CanvasSlot->SetAutoSize(true);
	}

	// ---- kite pech (string contest) meter ----
	{
		UVerticalBox* Box = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());

		UTextBlock* Label = MakeText(
			NSLOCTEXT("HUD", "PechLabel", "PECH!  mash E to cut their string"), 13, AccentTint);
		UVerticalBoxSlot* LabelSlot = Box->AddChildToVerticalBox(Label);
		LabelSlot->SetHorizontalAlignment(HAlign_Center);
		LabelSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 3.f));

		ContestBar = WidgetTree->ConstructWidget<UProgressBar>(UProgressBar::StaticClass(), TEXT("ContestBar"));
		ContestBar->SetPercent(0.5f);
		ContestBar->SetFillColorAndOpacity(AccentTint);
		USizeBox* BarHeight = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
		BarHeight->SetHeightOverride(15.f);
		BarHeight->SetContent(ContestBar);
		Box->AddChildToVerticalBox(BarHeight);

		UHorizontalBox* Ends = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass());
		UTextBlock* Lose = MakeText(NSLOCTEXT("HUD", "PechLose", "cut"), 11, DimTint, false);
		Ends->AddChildToHorizontalBox(Lose);
		USpacer* Gap = WidgetTree->ConstructWidget<USpacer>(USpacer::StaticClass());
		UHorizontalBoxSlot* GapSlot = Ends->AddChildToHorizontalBox(Gap);
		GapSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));
		UTextBlock* Win = MakeText(NSLOCTEXT("HUD", "PechWin", "bo kata!"), 11, DimTint, false);
		Ends->AddChildToHorizontalBox(Win);
		UVerticalBoxSlot* EndsSlot = Box->AddChildToVerticalBox(Ends);
		EndsSlot->SetPadding(FMargin(2.f, 2.f, 2.f, 0.f));

		ContestBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("ContestBox"));
		ContestBox->SetWidthOverride(400.f);
		ContestBox->SetContent(Box);
		ContestBox->SetVisibility(ESlateVisibility::Collapsed);

		UCanvasPanelSlot* CanvasSlot = Canvas->AddChildToCanvas(ContestBox);
		CanvasSlot->SetAnchors(FAnchors(0.5f, 1.f));
		CanvasSlot->SetAlignment(FVector2D(0.5f, 1.f));
		CanvasSlot->SetPosition(FVector2D(0.f, -290.f));
		CanvasSlot->SetAutoSize(true);
	}

	// ---- centre-screen crosshair (darts aiming) ----
	CrosshairText = MakeText(FText::FromString(TEXT("+")), 30,
		FLinearColor(1.f, 1.f, 1.f, 0.8f), false, TEXT("Crosshair"));
	CrosshairText->SetVisibility(ESlateVisibility::Collapsed);
	UCanvasPanelSlot* CrossSlot = Canvas->AddChildToCanvas(CrosshairText);
	CrossSlot->SetAnchors(FAnchors(0.5f, 0.5f));
	CrossSlot->SetAlignment(FVector2D(0.5f, 0.5f));
	CrossSlot->SetPosition(FVector2D(0.f, 0.f));
	CrossSlot->SetAutoSize(true);
}

void UGameHUDWidget::BuildStatusBanner(UCanvasPanel* Canvas)
{
	StatusText = MakeText(FText::GetEmpty(), 34, AccentTint, true, TEXT("StatusBanner"));
	StatusText->SetShadowOffset(FVector2D(2.f, 2.5f));
	StatusText->SetShadowColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.75f));
	StatusText->SetVisibility(ESlateVisibility::Collapsed);

	UCanvasPanelSlot* CanvasSlot = Canvas->AddChildToCanvas(StatusText);
	CanvasSlot->SetAnchors(FAnchors(0.5f, 0.30f));
	CanvasSlot->SetAlignment(FVector2D(0.5f, 0.5f));
	CanvasSlot->SetPosition(FVector2D(0.f, 0.f));
	CanvasSlot->SetAutoSize(true);
}

void UGameHUDWidget::BuildGamePanels(UCanvasPanel* Canvas)
{
	UVerticalBox* Stack = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());

	struct FPanelSpec
	{
		FName Name;
		FText Title;
		TFunction<void(UGameHUDWidget&, UVerticalBox*)> AddRows;
	};
	const FPanelSpec Specs[] =
	{
		{ TEXT("Darts"), NSLOCTEXT("HUD", "DartsTitle", "DARTS · 501"),
			[](UGameHUDWidget& W, UVerticalBox* P)
			{
				W.DartsScoreText = W.AddStatRow(P, NSLOCTEXT("HUD", "DartsScore", "Score"));
				W.DartsLeftText = W.AddStatRow(P, NSLOCTEXT("HUD", "DartsLeft", "Darts left"));
				W.DartsLastText = W.AddStatRow(P, NSLOCTEXT("HUD", "DartsLast", "Last throw"));
			} },
		{ TEXT("Kancha"), NSLOCTEXT("HUD", "KanchaTitle", "KANCHA"),
			[](UGameHUDWidget& W, UVerticalBox* P)
			{
				W.KanchaRemainingText = W.AddStatRow(P, NSLOCTEXT("HUD", "KanchaRing", "Marbles in ring"));
				W.KanchaWonText = W.AddStatRow(P, NSLOCTEXT("HUD", "KanchaWonLbl", "Marbles won"));
			} },
		{ TEXT("Kite"), NSLOCTEXT("HUD", "KiteTitle", "PATANG"),
			[](UGameHUDWidget& W, UVerticalBox* P)
			{
				W.KiteAltitudeText = W.AddStatRow(P, NSLOCTEXT("HUD", "KiteAlt", "Altitude"));
				W.KiteStringText = W.AddStatRow(P, NSLOCTEXT("HUD", "KiteString", "String out"));
				W.KiteCutText = W.AddStatRow(P, NSLOCTEXT("HUD", "KiteCuts", "Kites cut"));
			} },
	};

	for (const FPanelSpec& Spec : Specs)
	{
		UVerticalBox* Panel = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());

		UTextBlock* Title = MakeText(Spec.Title, 16, AccentTint);
		UVerticalBoxSlot* TitleSlot = Panel->AddChildToVerticalBox(Title);
		TitleSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 6.f));
		TitleSlot->SetHorizontalAlignment(HAlign_Center);

		Spec.AddRows(*this, Panel);

		USizeBox* Width = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
		Width->SetWidthOverride(250.f);
		Width->SetContent(Panel);

		UBorder* Border = MakePanelBorder(10.f, PanelTint, FMargin(16.f, 12.f));
		Border->SetHorizontalAlignment(HAlign_Fill);
		Border->SetContent(Width);
		Border->SetVisibility(ESlateVisibility::Collapsed);

		Stack->AddChildToVerticalBox(Border);
		GamePanels.Add(Spec.Name, Border);
	}

	UCanvasPanelSlot* CanvasSlot = Canvas->AddChildToCanvas(Stack);
	CanvasSlot->SetAnchors(FAnchors(1.f, 0.f));
	CanvasSlot->SetAlignment(FVector2D(1.f, 0.f));
	CanvasSlot->SetPosition(FVector2D(-28.f, 28.f));
	CanvasSlot->SetAutoSize(true);
}

// ====================== minimap ======================

void UGameHUDWidget::BuildMinimap(UCanvasPanel* Canvas)
{
	const float S = MinimapSizePx;

	// fixed-size canvas so the marker can be placed in exact pixels
	MinimapCanvas = WidgetTree->ConstructWidget<UCanvasPanel>(
		UCanvasPanel::StaticClass(), TEXT("MinimapCanvas"));

	// map image (or a flat-green fallback if the texture isn't imported yet)
	UImage* MapImage = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("MinimapMap"));
	FSlateBrush MapBrush;
	MapBrush.ImageSize = FVector2D(S, S);
	UTexture2D* MapTex = MinimapTexturePath.IsEmpty()
		? nullptr
		: LoadObject<UTexture2D>(nullptr, *MinimapTexturePath);
	if (MapTex)
	{
		MapBrush.SetResourceObject(MapTex);
		MapBrush.DrawAs = ESlateBrushDrawType::Image;
	}
	else
	{
		MapBrush.DrawAs = ESlateBrushDrawType::RoundedBox;
		MapBrush.TintColor = FSlateColor(FLinearColor(0.16f, 0.28f, 0.12f, 1.f));
		MapBrush.OutlineSettings.RoundingType = ESlateBrushRoundingType::FixedRadius;
		MapBrush.OutlineSettings.CornerRadii = FVector4(6, 6, 6, 6);
	}
	MapImage->SetBrush(MapBrush);
	UCanvasPanelSlot* MapSlot = MinimapCanvas->AddChildToCanvas(MapImage);
	MapSlot->SetAnchors(FAnchors(0.f, 0.f, 1.f, 1.f));
	MapSlot->SetOffsets(FMargin(0.f));

	// facing needle (thin bar, points up at 0°) then the player dot on top
	MinimapPlayerNeedle = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("MinimapNeedle"));
	{
		FSlateBrush B;
		B.ImageSize = FVector2D(4.f, 18.f);
		B.DrawAs = ESlateBrushDrawType::RoundedBox;
		B.TintColor = FSlateColor(FLinearColor(1.f, 0.95f, 0.55f, 1.f));
		B.OutlineSettings.RoundingType = ESlateBrushRoundingType::FixedRadius;
		B.OutlineSettings.CornerRadii = FVector4(2, 2, 2, 2);
		MinimapPlayerNeedle->SetBrush(B);
	}
	UCanvasPanelSlot* NeedleSlot = MinimapCanvas->AddChildToCanvas(MinimapPlayerNeedle);
	NeedleSlot->SetAnchors(FAnchors(0.f, 0.f));
	NeedleSlot->SetAlignment(FVector2D(0.5f, 0.5f));
	NeedleSlot->SetAutoSize(true);
	NeedleSlot->SetPosition(FVector2D(S * 0.5f, S * 0.5f));

	MinimapPlayerDot = WidgetTree->ConstructWidget<UImage>(UImage::StaticClass(), TEXT("MinimapDot"));
	{
		FSlateBrush B;
		B.ImageSize = FVector2D(12.f, 12.f);
		B.DrawAs = ESlateBrushDrawType::RoundedBox;
		B.TintColor = FSlateColor(FLinearColor(0.98f, 0.52f, 0.11f, 1.f)); // saffron
		B.OutlineSettings.RoundingType = ESlateBrushRoundingType::HalfHeightRadius;
		B.OutlineSettings.Color = FSlateColor(FLinearColor(0.10f, 0.07f, 0.02f, 1.f));
		B.OutlineSettings.Width = 1.5f;
		MinimapPlayerDot->SetBrush(B);
	}
	UCanvasPanelSlot* DotSlot = MinimapCanvas->AddChildToCanvas(MinimapPlayerDot);
	DotSlot->SetAnchors(FAnchors(0.f, 0.f));
	DotSlot->SetAlignment(FVector2D(0.5f, 0.5f));
	DotSlot->SetAutoSize(true);
	DotSlot->SetPosition(FVector2D(S * 0.5f, S * 0.5f));

	// lock the square size
	USizeBox* Square = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass());
	Square->SetWidthOverride(S);
	Square->SetHeightOverride(S);
	Square->SetContent(MinimapCanvas);

	// title + map in a framed panel
	UVerticalBox* Stack = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass());
	UTextBlock* Title = MakeText(NSLOCTEXT("HUD", "MinimapTitle", "Pandori Nijjaran"), 13, AccentTint);
	UVerticalBoxSlot* TitleSlot = Stack->AddChildToVerticalBox(Title);
	TitleSlot->SetHorizontalAlignment(HAlign_Center);
	TitleSlot->SetPadding(FMargin(0.f, 0.f, 0.f, 5.f));
	Stack->AddChildToVerticalBox(Square);

	UBorder* Frame = MakePanelBorder(9.f, PanelTint, FMargin(9.f, 8.f));
	Frame->SetContent(Stack);

	UCanvasPanelSlot* FrameSlot = Canvas->AddChildToCanvas(Frame);
	FrameSlot->SetAnchors(FAnchors(0.f, 1.f));         // bottom-left
	FrameSlot->SetAlignment(FVector2D(0.f, 1.f));
	FrameSlot->SetPosition(FVector2D(24.f, -24.f));
	FrameSlot->SetAutoSize(true);
}

void UGameHUDWidget::UpdateMinimap()
{
	if (!MinimapPlayerDot || !MinimapCanvas)
	{
		return;
	}
	APawn* Pawn = GetOwningPlayerPawn();
	if (!Pawn)
	{
		return;
	}
	const FVector Loc = Pawn->GetActorLocation();
	const float Half = FMath::Max(MinimapWorldHalfExtent, 1.f);
	const float S = MinimapSizePx;

	// world -> map pixels: +X right, +Y down, centred on MinimapWorldCentre
	const float U = FMath::Clamp((Loc.X - MinimapWorldCentre.X) / (2.f * Half) + 0.5f, 0.f, 1.f);
	const float V = FMath::Clamp((Loc.Y - MinimapWorldCentre.Y) / (2.f * Half) + 0.5f, 0.f, 1.f);
	const FVector2D Px(U * S, V * S);

	if (UCanvasPanelSlot* DotSlot = Cast<UCanvasPanelSlot>(MinimapPlayerDot->Slot))
	{
		DotSlot->SetPosition(Px);
	}
	if (MinimapPlayerNeedle)
	{
		if (UCanvasPanelSlot* NeedleSlot = Cast<UCanvasPanelSlot>(MinimapPlayerNeedle->Slot))
		{
			NeedleSlot->SetPosition(Px);
		}
		// view yaw drives facing. The needle points up (-Y) at 0°; world +X maps
		// to screen-right and world +Y to screen-down, so +90° aligns them.
		float Yaw = Pawn->GetActorRotation().Yaw;
		if (APlayerController* PC = GetOwningPlayer())
		{
			Yaw = PC->GetControlRotation().Yaw;
		}
		MinimapPlayerNeedle->SetRenderTransformAngle(Yaw + 90.f);
	}
}

// ====================== prompt & dialogue ======================

void UGameHUDWidget::RefreshPromptVisibility()
{
	if (PromptBorder)
	{
		PromptBorder->SetVisibility(bPromptWanted && !bDialogueVisible
			? ESlateVisibility::HitTestInvisible
			: ESlateVisibility::Collapsed);
	}
}

void UGameHUDWidget::ShowInteractPrompt_Implementation(const FText& GameName)
{
	if (!bNativeTreeBuilt) { return; }
	PromptSuffixText->SetText(FText::Format(
		NSLOCTEXT("HUD", "PromptPlayFmt", "to play {0}"), GameName));
	bPromptWanted = true;
	RefreshPromptVisibility();
}

void UGameHUDWidget::ShowTalkPrompt_Implementation(const FText& VillagerName)
{
	if (!bNativeTreeBuilt) { return; }
	PromptSuffixText->SetText(FText::Format(
		NSLOCTEXT("HUD", "PromptTalkFmt", "to talk to {0}"), VillagerName));
	bPromptWanted = true;
	RefreshPromptVisibility();
}

void UGameHUDWidget::HideInteractPrompt_Implementation()
{
	if (!bNativeTreeBuilt) { return; }
	bPromptWanted = false;
	RefreshPromptVisibility();
}

void UGameHUDWidget::HideTalkPrompt_Implementation()
{
	// One shared prompt widget serves both zone and NPC prompts; the
	// interaction component always re-shows the survivor after a hide.
	HideInteractPrompt_Implementation();
}

void UGameHUDWidget::ShowDialogueLine_Implementation(const FText& SpeakerName, const FText& Line)
{
	if (!bNativeTreeBuilt) { return; }
	DialogueSpeakerText->SetText(SpeakerName);
	DialogueLineText->SetText(Line);
	DialogueBorder->SetVisibility(ESlateVisibility::HitTestInvisible);
	bDialogueVisible = true;
	RefreshPromptVisibility(); // prompt yields to the dialogue box
}

void UGameHUDWidget::HideDialogue_Implementation()
{
	if (!bNativeTreeBuilt) { return; }
	DialogueBorder->SetVisibility(ESlateVisibility::Collapsed);
	bDialogueVisible = false;
	RefreshPromptVisibility(); // prompt returns if focus is unchanged
}

// ====================== panels & meters ======================

void UGameHUDWidget::ShowGamePanel_Implementation(FName PanelName)
{
	if (!bNativeTreeBuilt) { return; }
	for (const TPair<FName, TObjectPtr<UBorder>>& Pair : GamePanels)
	{
		Pair.Value->SetVisibility(Pair.Key == PanelName
			? ESlateVisibility::HitTestInvisible
			: ESlateVisibility::Collapsed);
	}
	if (!GamePanels.Contains(PanelName))
	{
		UE_LOG(LogTemp, Warning,
			TEXT("GameHUDWidget: no panel named '%s' — add one in BuildGamePanels."),
			*PanelName.ToString());
	}
	if (CrosshairText)
	{
		// Darts aims at screen centre; the other games have world-space aims.
		CrosshairText->SetVisibility(PanelName == TEXT("Darts")
			? ESlateVisibility::HitTestInvisible
			: ESlateVisibility::Collapsed);
	}
}

void UGameHUDWidget::HideGamePanel_Implementation(FName PanelName)
{
	if (!bNativeTreeBuilt) { return; }
	if (const TObjectPtr<UBorder>* Panel = GamePanels.Find(PanelName))
	{
		(*Panel)->SetVisibility(ESlateVisibility::Collapsed);
	}
	if (CrosshairText)
	{
		CrosshairText->SetVisibility(ESlateVisibility::Collapsed);
	}
	if (ContestBox)
	{
		ContestBox->SetVisibility(ESlateVisibility::Collapsed);
	}
}

void UGameHUDWidget::UpdatePowerMeter_Implementation(float Power01, bool bVisible)
{
	if (!bNativeTreeBuilt) { return; }
	PowerMeterBox->SetVisibility(bVisible
		? ESlateVisibility::HitTestInvisible
		: ESlateVisibility::Collapsed);
	if (bVisible)
	{
		const float P = FMath::Clamp(Power01, 0.f, 1.f);
		PowerBar->SetPercent(P);
		// green -> saffron -> red as the throw charges up
		const FLinearColor Fill = P < 0.5f
			? FMath::Lerp(GoodTint, AccentTint, P * 2.f)
			: FMath::Lerp(AccentTint, BadTint, (P - 0.5f) * 2.f);
		PowerBar->SetFillColorAndOpacity(Fill);
	}
}

void UGameHUDWidget::UpdateDartsHUD_Implementation(int32 Score, int32 DartsLeftThisTurn, int32 LastThrowScore)
{
	if (!bNativeTreeBuilt) { return; }
	DartsScoreText->SetText(FText::AsNumber(Score));

	FString Pips;
	for (int32 i = 0; i < DartsLeftThisTurn; ++i)
	{
		Pips += TEXT("● ");   // one dot per dart remaining
	}
	DartsLeftText->SetText(Pips.IsEmpty()
		? NSLOCTEXT("HUD", "DartsNone", "—")
		: FText::FromString(Pips.TrimEnd()));

	DartsLastText->SetText(FText::AsNumber(LastThrowScore));
}

void UGameHUDWidget::UpdateKanchaHUD_Implementation(int32 MarblesRemaining, int32 MarblesWon)
{
	if (!bNativeTreeBuilt) { return; }
	KanchaRemainingText->SetText(FText::AsNumber(MarblesRemaining));
	KanchaWonText->SetText(FText::AsNumber(MarblesWon));
}

void UGameHUDWidget::UpdateKiteHUD_Implementation(float AltitudeCm, float StringLengthCm,
	int32 KitesCut, float ContestMeter01, bool bContestActive)
{
	if (!bNativeTreeBuilt) { return; }
	KiteAltitudeText->SetText(FText::FromString(
		FString::Printf(TEXT("%.0f m"), AltitudeCm / 100.f)));
	KiteStringText->SetText(FText::FromString(
		FString::Printf(TEXT("%.0f m"), StringLengthCm / 100.f)));
	KiteCutText->SetText(FText::AsNumber(KitesCut));

	ContestBox->SetVisibility(bContestActive
		? ESlateVisibility::HitTestInvisible
		: ESlateVisibility::Collapsed);
	if (bContestActive)
	{
		const float M = FMath::Clamp(ContestMeter01, 0.f, 1.f);
		ContestBar->SetPercent(M);
		ContestBar->SetFillColorAndOpacity(M >= 0.5f
			? FMath::Lerp(AccentTint, GoodTint, (M - 0.5f) * 2.f)
			: FMath::Lerp(BadTint, AccentTint, M * 2.f));
	}
}

void UGameHUDWidget::ShowStatusMessage_Implementation(const FText& Message)
{
	if (!bNativeTreeBuilt) { return; }
	StatusText->SetText(Message);
	StatusText->SetRenderOpacity(1.f);
	StatusText->SetVisibility(ESlateVisibility::HitTestInvisible);
	StatusTimeLeft = StatusHoldTime + StatusFadeTime;
}

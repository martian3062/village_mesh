#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "GameHUDWidget.generated.h"

class UBorder;
class UCanvasPanel;
class UImage;
class UProgressBar;
class USizeBox;
class UTextBlock;
class UVerticalBox;

/**
 * Shared HUD shell: interact/talk prompt, NPC dialogue box, a shared power
 * meter, a transient status banner, and one stats panel per mini-game
 * (switched by the PanelName passed to ShowGamePanel/HideGamePanel).
 *
 * The whole widget tree is built in C++ (NativeOnInitialized), so the class
 * works as-is with no UMG design pass — UInteractionComponent defaults its
 * HUDWidgetClass to this class. Every event is a BlueprintNativeEvent: C++
 * pushes state, and a Blueprint child (WBP_GameHUD) may override any event to
 * restyle the visuals. If the child authors its own designer tree, the C++
 * tree is skipped entirely (BuildTree only runs when no root widget exists).
 *
 * Add one Update event + one panel per new game.
 */
UCLASS(Blueprintable)
class RURAL_PARDEEP_API UGameHUDWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	/** Show "Press E to play <GameName>". */
	UFUNCTION(BlueprintNativeEvent, Category = "HUD")
	void ShowInteractPrompt(const FText& GameName);

	/** Show "Press E to talk to <VillagerName>". */
	UFUNCTION(BlueprintNativeEvent, Category = "HUD|Dialogue")
	void ShowTalkPrompt(const FText& VillagerName);

	UFUNCTION(BlueprintNativeEvent, Category = "HUD|Dialogue")
	void HideTalkPrompt();

	/** A villager speaks. E advances, Q/Esc or walking away ends. */
	UFUNCTION(BlueprintNativeEvent, Category = "HUD|Dialogue")
	void ShowDialogueLine(const FText& SpeakerName, const FText& Line);

	UFUNCTION(BlueprintNativeEvent, Category = "HUD|Dialogue")
	void HideDialogue();

	UFUNCTION(BlueprintNativeEvent, Category = "HUD")
	void HideInteractPrompt();

	/** PanelName matches AMiniGameZone::HUDPanelName ("Darts", "Kancha", "Kite"). */
	UFUNCTION(BlueprintNativeEvent, Category = "HUD")
	void ShowGamePanel(FName PanelName);

	UFUNCTION(BlueprintNativeEvent, Category = "HUD")
	void HideGamePanel(FName PanelName);

	/** Shared charge meter (darts throw / kancha flick). Power01 in [0,1]. */
	UFUNCTION(BlueprintNativeEvent, Category = "HUD")
	void UpdatePowerMeter(float Power01, bool bVisible);

	/** Darts: running total (501 countdown or accumulated), darts left this turn, last throw. */
	UFUNCTION(BlueprintNativeEvent, Category = "HUD|Darts")
	void UpdateDartsHUD(int32 Score, int32 DartsLeftThisTurn, int32 LastThrowScore);

	UFUNCTION(BlueprintNativeEvent, Category = "HUD|Kancha")
	void UpdateKanchaHUD(int32 MarblesRemaining, int32 MarblesWon);

	/** Kite: AltitudeCm/StringLengthCm are centimetres — shown as metres. */
	UFUNCTION(BlueprintNativeEvent, Category = "HUD|Kite")
	void UpdateKiteHUD(float AltitudeCm, float StringLengthCm, int32 KitesCut,
		float ContestMeter01, bool bContestActive);

	/** Transient status line ("BUST!", "Marble won!", "Kite cut!"). */
	UFUNCTION(BlueprintNativeEvent, Category = "HUD")
	void ShowStatusMessage(const FText& Message);

	// -------- status banner timing --------

	/** Seconds the status banner holds at full opacity. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HUD|Style", meta = (ClampMin = "0"))
	float StatusHoldTime = 1.7f;

	/** Seconds the status banner takes to fade out after the hold. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HUD|Style", meta = (ClampMin = "0.05"))
	float StatusFadeTime = 0.9f;

	// -------- minimap --------

	/** World cm from the map centre to each edge of the minimap. The map
	 *  texture must be drawn to the same extent so the marker lands on roads. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HUD|Minimap", meta = (ClampMin = "1000"))
	float MinimapWorldHalfExtent = 60000.f;

	/** World-space centre the map is drawn around (village origin). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HUD|Minimap")
	FVector2D MinimapWorldCentre = FVector2D(0.f, 0.f);

	/** On-screen size of the square minimap (px). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HUD|Minimap", meta = (ClampMin = "80"))
	float MinimapSizePx = 250.f;

	/** Content path of the map texture drawn by build_greenworld/import_village_map. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "HUD|Minimap")
	FString MinimapTexturePath = TEXT("/Game/Village/Map/T_VillageMap.T_VillageMap");

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

	// ---- native implementations (Blueprint children may override the events) ----
	virtual void ShowInteractPrompt_Implementation(const FText& GameName);
	virtual void ShowTalkPrompt_Implementation(const FText& VillagerName);
	virtual void HideTalkPrompt_Implementation();
	virtual void ShowDialogueLine_Implementation(const FText& SpeakerName, const FText& Line);
	virtual void HideDialogue_Implementation();
	virtual void HideInteractPrompt_Implementation();
	virtual void ShowGamePanel_Implementation(FName PanelName);
	virtual void HideGamePanel_Implementation(FName PanelName);
	virtual void UpdatePowerMeter_Implementation(float Power01, bool bVisible);
	virtual void UpdateDartsHUD_Implementation(int32 Score, int32 DartsLeftThisTurn, int32 LastThrowScore);
	virtual void UpdateKanchaHUD_Implementation(int32 MarblesRemaining, int32 MarblesWon);
	virtual void UpdateKiteHUD_Implementation(float AltitudeCm, float StringLengthCm, int32 KitesCut,
		float ContestMeter01, bool bContestActive);
	virtual void ShowStatusMessage_Implementation(const FText& Message);

	// ---- C++ widget tree construction ----

	/** Builds the whole tree. No-op if the (Blueprint) tree already has a root. */
	void BuildTree();

	UTextBlock* MakeText(const FText& InText, int32 Size, const FLinearColor& Color,
		bool bBold = true, FName WidgetName = NAME_None);
	UBorder* MakePanelBorder(float CornerRadius, const FLinearColor& Tint, const FMargin& InPadding);
	/** "label ........ value" row inside a panel; returns the value text block. */
	UTextBlock* AddStatRow(UVerticalBox* Panel, const FText& Label);
	/** Bottom-centre prompt: "Press [E] <suffix>". */
	void BuildPrompt(UCanvasPanel* Canvas);
	void BuildDialoguePanel(UCanvasPanel* Canvas);
	void BuildMeters(UCanvasPanel* Canvas);
	void BuildStatusBanner(UCanvasPanel* Canvas);
	void BuildGamePanels(UCanvasPanel* Canvas);
	/** Bottom-left village minimap (map texture + live player marker). */
	void BuildMinimap(UCanvasPanel* Canvas);
	/** Per-frame: move the player marker to the pawn's mapped position + facing. */
	void UpdateMinimap();

	/** Prompt is suppressed (not forgotten) while the dialogue box is open. */
	void RefreshPromptVisibility();

	// ---- widget refs (all owned by the WidgetTree; refs for updates only) ----

	UPROPERTY(Transient) TObjectPtr<UBorder> PromptBorder;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> PromptSuffixText;
	UPROPERTY(Transient) TObjectPtr<UBorder> DialogueBorder;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> DialogueSpeakerText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> DialogueLineText;
	UPROPERTY(Transient) TObjectPtr<USizeBox> PowerMeterBox;
	UPROPERTY(Transient) TObjectPtr<UProgressBar> PowerBar;
	UPROPERTY(Transient) TObjectPtr<USizeBox> ContestBox;
	UPROPERTY(Transient) TObjectPtr<UProgressBar> ContestBar;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> CrosshairText;

	UPROPERTY(Transient) TObjectPtr<UTextBlock> DartsScoreText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> DartsLeftText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> DartsLastText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> KanchaRemainingText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> KanchaWonText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> KiteAltitudeText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> KiteStringText;
	UPROPERTY(Transient) TObjectPtr<UTextBlock> KiteCutText;

	UPROPERTY(Transient) TMap<FName, TObjectPtr<UBorder>> GamePanels;

	UPROPERTY(Transient) TObjectPtr<UCanvasPanel> MinimapCanvas;
	UPROPERTY(Transient) TObjectPtr<UImage> MinimapPlayerDot;
	UPROPERTY(Transient) TObjectPtr<UImage> MinimapPlayerNeedle;

	// ---- runtime state ----
	bool bPromptWanted = false;
	bool bDialogueVisible = false;
	float StatusTimeLeft = 0.f;
	/** True once BuildTree constructed the C++ tree (native impls need it). */
	bool bNativeTreeBuilt = false;
};

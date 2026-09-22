using System.Collections.Generic;
using RIMAPI.Models;
using UnityEngine;
using Verse;

namespace RIMAPI.UI
{
    public class AnnouncementWindow : Window
    {
        private readonly string _text;
        private readonly float _duration;
        private readonly Color _color;
        private readonly float _scale;
        private readonly bool _panel;
        private readonly bool _compact;
        private readonly List<OverlayBarDto> _bars;
        private readonly float _startTime;

        public override Vector2 InitialSize => new Vector2(Verse.UI.screenWidth, Verse.UI.screenHeight);
        protected override float Margin => 0f;

        public AnnouncementWindow(
            string text,
            float duration,
            string colorHex,
            float scale,
            bool panel = false,
            bool compact = true,
            List<OverlayBarDto> bars = null)
        {
            _text = text ?? string.Empty;
            _duration = duration;
            _scale = scale;
            _panel = panel;
            _compact = compact;
            _bars = bars ?? new List<OverlayBarDto>();
            _startTime = Time.realtimeSinceStartup;

            if (!ColorUtility.TryParseHtmlString(colorHex, out _color))
                _color = Color.white;

            this.layer = WindowLayer.Super;
            this.closeOnClickedOutside = false;
            this.doCloseButton = false;
            this.doCloseX = false;
            this.absorbInputAroundWindow = false;
            this.shadowAlpha = 0f;
            this.forcePause = false;
            this.preventCameraMotion = false;
        }

        // --- THE FIX ---
        // By overriding this and NOT calling base.WindowOnGUI(), 
        // we skip the default background texture drawing entirely.
        public override void WindowOnGUI()
        {
            // Just call our contents method directly
            this.DoWindowContents(this.windowRect);
        }

        public override void DoWindowContents(Rect inRect)
        {
            if (Time.realtimeSinceStartup - _startTime > _duration)
            {
                this.Close();
                return;
            }

            // Save state
            Color oldColor = GUI.color;
            Matrix4x4 oldMatrix = GUI.matrix;
            GameFont oldFont = Text.Font;
            TextAnchor oldAnchor = Text.Anchor;

            Text.Font = _panel ? (_compact ? GameFont.Tiny : GameFont.Small) : GameFont.Medium;
            Text.Anchor = _panel ? TextAnchor.UpperLeft : TextAnchor.MiddleCenter;

            // Apply style
            GUI.color = _color;
            if (_panel)
            {
                float width = Mathf.Min(_compact ? 430f : 560f, Verse.UI.screenWidth - 40f);
                float contentWidth = width - 24f;
                float textHeight = Mathf.Max(24f, Text.CalcHeight(_text, contentWidth));
                float labelHeight = _compact ? 19f : 22f;
                float trackHeight = _compact ? 5f : 7f;
                float rowStride = labelHeight + trackHeight + 7f;
                float barsHeight = _bars.Count > 0 ? _bars.Count * rowStride + 8f : 0f;
                float desiredHeight = 24f + textHeight + barsHeight;
                float height = Mathf.Min(
                    Mathf.Max(_compact ? 118f : 180f, desiredHeight),
                    Mathf.Min(_compact ? 330f : 470f, Verse.UI.screenHeight - 110f)
                );
                Rect panelRect = new Rect(18f, 86f, width, height);
                GUI.color = Color.white;
                Widgets.DrawBoxSolid(panelRect, new Color(0.035f, 0.045f, 0.055f, 0.88f));
                Widgets.DrawBox(panelRect, 1);
                Rect inner = panelRect.ContractedBy(12f);
                GUI.color = _color;
                Widgets.Label(new Rect(inner.x, inner.y, inner.width, textHeight), _text);

                float y = inner.y + textHeight + 8f;
                Color selectedYellow = new Color(1f, 0.78f, 0.22f, 1f);
                Color quietYellow = new Color(0.78f, 0.62f, 0.24f, 0.82f);
                foreach (OverlayBarDto bar in _bars)
                {
                    if (y + rowStride > panelRect.yMax - 8f) break;
                    float value = Mathf.Clamp01(bar.Value);
                    string label = string.IsNullOrEmpty(bar.Label) ? "—" : bar.Label;
                    string percentage = (value * 100f).ToString("0.0") + "%";
                    Rect labelRect = new Rect(inner.x, y, inner.width - 66f, labelHeight);
                    Rect percentageRect = new Rect(inner.xMax - 62f, y, 62f, labelHeight);

                    // Keep the labels above the fill so white text never disappears into yellow.
                    // A small shadow plus a second sub-pixel pass gives RimWorld's font more weight.
                    Text.Font = GameFont.Small;
                    Text.Anchor = TextAnchor.MiddleLeft;
                    GUI.color = new Color(0f, 0f, 0f, 0.9f);
                    Widgets.Label(new Rect(labelRect.x + 1f, labelRect.y + 1f, labelRect.width, labelRect.height), label);
                    Text.Anchor = TextAnchor.MiddleRight;
                    Widgets.Label(new Rect(percentageRect.x + 1f, percentageRect.y + 1f, percentageRect.width, percentageRect.height), percentage);
                    GUI.color = Color.white;
                    Text.Anchor = TextAnchor.MiddleLeft;
                    Widgets.Label(labelRect, label);
                    Widgets.Label(new Rect(labelRect.x + 0.45f, labelRect.y, labelRect.width, labelRect.height), label);
                    Text.Anchor = TextAnchor.MiddleRight;
                    Widgets.Label(percentageRect, percentage);
                    Widgets.Label(new Rect(percentageRect.x + 0.45f, percentageRect.y, percentageRect.width, percentageRect.height), percentage);

                    Rect track = new Rect(inner.x, y + labelHeight + 2f, inner.width, trackHeight);
                    GUI.color = Color.white;
                    Widgets.DrawBoxSolid(track, new Color(0.11f, 0.12f, 0.15f, 0.96f));
                    Color fill = bar.Selected ? selectedYellow : quietYellow;
                    // The fill uses the model's probability directly; alternatives are never equalized.
                    Widgets.DrawBoxSolid(new Rect(track.x, track.y, track.width * value, track.height), fill);
                    y += rowStride;
                }
            }
            else
            {
                Vector2 pivot = new Vector2(Verse.UI.screenWidth / 2f, Verse.UI.screenHeight / 2f);
                GUIUtility.ScaleAroundPivot(new Vector2(_scale, _scale), pivot);
                Widgets.Label(inRect, _text);
            }

            // Restore state
            GUI.matrix = oldMatrix;
            GUI.color = oldColor;
            Text.Font = oldFont;
            Text.Anchor = oldAnchor;
        }
    }
}

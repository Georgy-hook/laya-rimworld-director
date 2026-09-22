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

            Text.Font = _panel ? (_compact ? GameFont.Tiny : GameFont.Small) : GameFont.Medium;
            Text.Anchor = _panel ? TextAnchor.UpperLeft : TextAnchor.MiddleCenter;

            // Save state
            Color oldColor = GUI.color;
            Matrix4x4 oldMatrix = GUI.matrix;

            // Apply style
            GUI.color = _color;
            if (_panel)
            {
                float width = Mathf.Min(_compact ? 430f : 560f, Verse.UI.screenWidth - 40f);
                float contentWidth = width - 24f;
                float textHeight = Mathf.Max(24f, Text.CalcHeight(_text, contentWidth));
                float barsHeight = _bars.Count > 0 ? _bars.Count * (_compact ? 24f : 28f) + 8f : 0f;
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
                float rowHeight = _compact ? 20f : 24f;
                Color selectedYellow = new Color(1f, 0.78f, 0.22f, 1f);
                Color quietYellow = new Color(0.78f, 0.62f, 0.24f, 0.82f);
                foreach (OverlayBarDto bar in _bars)
                {
                    if (y + rowHeight > panelRect.yMax - 8f) break;
                    float value = Mathf.Clamp01(bar.Value);
                    Rect track = new Rect(inner.x, y, inner.width, rowHeight);
                    GUI.color = Color.white;
                    Widgets.DrawBoxSolid(track, new Color(0.11f, 0.12f, 0.15f, 0.96f));
                    Color fill = bar.Selected ? selectedYellow : quietYellow;
                    Widgets.DrawBoxSolid(new Rect(track.x, track.y, track.width * value, track.height), fill);
                    GUI.color = Color.white;
                    Text.Anchor = TextAnchor.MiddleLeft;
                    string label = string.IsNullOrEmpty(bar.Label) ? "—" : bar.Label;
                    Widgets.Label(new Rect(track.x + 6f, track.y, track.width - 58f, track.height), label);
                    Text.Anchor = TextAnchor.MiddleRight;
                    Widgets.Label(new Rect(track.x + track.width - 54f, track.y, 48f, track.height), (value * 100f).ToString("0.0") + "%");
                    y += rowHeight + 4f;
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
            Text.Anchor = TextAnchor.UpperLeft;
        }
    }
}

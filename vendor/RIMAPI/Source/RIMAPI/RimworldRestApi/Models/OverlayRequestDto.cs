using System.Collections.Generic;

namespace RIMAPI.Models
{
    public class OverlayBarDto
    {
        public string Label { get; set; }
        public float Value { get; set; }
        public bool Selected { get; set; }
    }

    public class OverlayRequestDto
    {
        public string Text { get; set; }
        public float Duration { get; set; } = 3.0f; // Seconds
        public string Color { get; set; } = "#FFFFFF"; // Hex code
        public float Scale { get; set; } = 2.0f; // Text size multiplier
        public bool Panel { get; set; } = false;
        public bool Compact { get; set; } = true;
        public List<OverlayBarDto> Bars { get; set; } = new List<OverlayBarDto>();
    }
}

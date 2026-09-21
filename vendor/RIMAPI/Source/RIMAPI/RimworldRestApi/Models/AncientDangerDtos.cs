namespace RIMAPI.Models
{
    public class AncientDangerStateDto
    {
        public int MapId { get; set; }
        public bool Detected { get; set; }
        public bool Sealed { get; set; }
        public int DetectedTick { get; set; }
        public string Notice { get; set; }
        public PositionDto Position { get; set; }
        public int? OpeningTargetThingId { get; set; }
        public PositionDto OpeningTargetPosition { get; set; }
        public bool CanOpen { get; set; }
    }

    public class OpenAncientDangerRequestDto
    {
        public int MapId { get; set; }
    }
}

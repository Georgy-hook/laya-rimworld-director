namespace RIMAPI.Models
{
    public class DesignateRequestDto
    {
        public int MapId { get; set; }
        public string Type { get; set; } // Mine, Deconstruct, Harvest, Hunt, Home, Clear-Home
        public PositionDto PointA { get; set; }
        public PositionDto PointB { get; set; }
    }
}

using RIMAPI.Core;
using RIMAPI.Models;

namespace RIMAPI.Services
{
    public interface IBuilderService
    {
        ApiResult<BlueprintDto> CopyArea(CopyAreaRequestDto request);
        ApiResult PasteArea(PasteAreaRequestDto request);
        ApiResult PlaceBlueprints(PasteAreaRequestDto request);
        ApiResult<CheckZoneResultDto> CheckZone(CheckZoneRequestDto request);
        ApiResult<ConstructionProjectsDto> GetConstructionProjects(int mapId);
        ApiResult PrioritizeConstruction(PrioritizeConstructionRequestDto request);
    }
}

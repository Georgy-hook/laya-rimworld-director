using System.Net;
using System.Threading.Tasks;
using RIMAPI.Core;
using RIMAPI.Helpers;
using RIMAPI.Http;
using RIMAPI.Models;

namespace RIMAPI.Controllers
{
    public class BuildingCatalogController
    {
        [Get("/api/v1/buildings/catalog")]
        [EndpointMetadata("List every currently loaded player-buildable building, including modded defs, costs, research, size and functional metadata")]
        public async Task GetBuildingCatalog(HttpListenerContext context)
        {
            await context.SendJsonResponse(ApiResult<System.Collections.Generic.List<BuildingCatalogDto>>.Ok(BuildingCatalogHelper.GetCatalog()));
        }

        [Get("/api/v1/colony/royalty")]
        [EndpointMetadata("Get colonist royal titles and their current bedroom/throne-room requirements")]
        public async Task GetRoyaltyContext(HttpListenerContext context)
        {
            await context.SendJsonResponse(ApiResult<RoyaltyContextDto>.Ok(BuildingCatalogHelper.GetRoyaltyContext()));
        }
    }
}

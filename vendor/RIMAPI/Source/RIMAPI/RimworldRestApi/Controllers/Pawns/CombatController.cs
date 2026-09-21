using System.Net;
using System.Threading.Tasks;
using RIMAPI.Core;
using RIMAPI.Http;
using RIMAPI.Services;

namespace RIMAPI.Controllers
{
    public class CombatController
    {
        private readonly ICombatService _combatService;

        public CombatController(ICombatService combatService)
        {
            _combatService = combatService;
        }

        [Get("/api/v1/combat/state")]
        [EndpointMetadata("Get combat-ready colonists and hostile pawns with target IDs")]
        public async Task GetCombatState(HttpListenerContext context)
        {
            var mapId = RequestParser.GetMapId(context);
            var result = _combatService.GetCombatState(mapId);
            await context.SendJsonResponse(result);
        }
    }
}

using System.Net;
using System.Threading.Tasks;
using RIMAPI.Core;
using RIMAPI.Http;
using RIMAPI.Models;
using RIMAPI.Services;
using RIMAPI.Helpers;

namespace RIMAPI.Controllers
{
    public class GameEventsController
    {
        private readonly IIncidentService _incidentService;

        public GameEventsController(IIncidentService incidentService)
        {
            _incidentService = incidentService;
        }

        [Get("/api/v1/quests")]
        public async Task GetQuestsData(HttpListenerContext context)
        {
            var mapId = RequestParser.GetMapId(context);
            var result = _incidentService.GetQuestsData(mapId);
            await context.SendJsonResponse(result);
        }

        [Get("/api/v1/incidents")]
        [EndpointMetadata("Get map incidents")]
        public async Task GetIncidentsData(HttpListenerContext context)
        {
            var mapId = RequestParser.GetMapId(context);
            var result = _incidentService.GetIncidentsData(mapId);
            await context.SendJsonResponse(result);
        }

        [Get("/api/v1/lords")]
        [EndpointMetadata("Get lords on map (AI raid managing objects)")]
        public async Task GetLordsData(HttpListenerContext context)
        {
            var mapId = RequestParser.GetMapId(context);
            var result = _incidentService.GetLordsData(mapId);
            await context.SendJsonResponse(result);
        }

        [Post("/api/v1/incident/trigger")]
        [EndpointMetadata("Trigger game incident")]
        public async Task TriggerIncident(HttpListenerContext context)
        {
            var requestData = await context.Request.ReadBodyAsync<TriggerIncidentRequestDto>();
            var result = _incidentService.TriggerIncident(requestData);
            await context.SendJsonResponse(result);
        }

        [Get("/api/v1/incidents/top")]
        public async Task GetIncidentsTopChance(HttpListenerContext context)
        {
            var result = _incidentService.GetTopIncidents();
            await context.SendJsonResponse(result);
        }

        [Get("/api/v1/incident/chance")]
        public async Task GetIncidentChance(HttpListenerContext context)
        {
            var requestData = await context.Request.ReadBodyAsync<IncidentChanceRequestDto>();
            var result = _incidentService.GetIncidentChance(requestData);
            await context.SendJsonResponse(result);
        }

        [Get("/api/v1/events/catalog")]
        [EndpointMetadata("List every loaded vanilla, DLC and mod incident definition")]
        public async Task GetEventCatalog(HttpListenerContext context)
        {
            await context.SendJsonResponse(GameEventAutomationHelper.GetCatalog());
        }

        [Get("/api/v1/events/context")]
        [EndpointMetadata("Get recent incidents, active conditions, quests, letters, kidnapped pawns and live traders")]
        public async Task GetEventContext(HttpListenerContext context)
        {
            var mapId = RequestParser.GetMapId(context);
            await context.SendJsonResponse(GameEventAutomationHelper.GetContext(mapId));
        }

        [Post("/api/v1/quest/accept")]
        [EndpointMetadata("Accept a selected live quest through the normal quest system")]
        public async Task AcceptQuest(HttpListenerContext context)
        {
            var body = await context.Request.ReadBodyAsync<QuestActionRequestDto>();
            await context.SendJsonResponse(GameEventAutomationHelper.AcceptQuest(body));
        }
    }
}

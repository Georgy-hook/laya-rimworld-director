using System;
using System.Linq;
using RIMAPI.Core;
using RIMAPI.Models;
using RimWorld;
using Verse;
using UnityEngine;

namespace RIMAPI.Helpers
{
    public static class BuilderAutomationHelper
    {
        public static ApiResult InstallMinified(InstallMinifiedRequestDto request)
        {
            try
            {
                Map map = MapHelper.GetMapByID(request.MapId);
                if (map == null) return ApiResult.Fail($"Map {request.MapId} not found.");
                if (request.Position == null) return ApiResult.Fail("Position is required.");
                MinifiedThing thing = map.listerThings.ThingsInGroup(ThingRequestGroup.HaulableEver)
                    .OfType<MinifiedThing>().FirstOrDefault(t => t.thingIDNumber == request.ThingId);
                if (thing?.InnerThing == null) return ApiResult.Fail("The selected minified building was not found.");
                if (thing.InnerThing.def.installBlueprintDef == null)
                    return ApiResult.Fail("The selected object cannot be installed.");
                IntVec3 cell = new IntVec3(request.Position.X, 0, request.Position.Z);
                Rot4 rotation = new Rot4(request.Rotation);
                if (!cell.InBounds(map)) return ApiResult.Fail("Installation cell is outside the map.");
                Room requestedRoom = cell.GetRoom(map);
                AcceptanceReport report = GenConstruct.CanPlaceBlueprintAt(thing.InnerThing.def, cell, rotation, map, false, null, thing);
                if (!report.Accepted)
                {
                    foreach (IntVec3 candidate in GenRadial.RadialCellsAround(cell, 6f, true))
                    {
                        if (!candidate.InBounds(map) || candidate.GetRoom(map) != requestedRoom) continue;
                        AcceptanceReport candidateReport = GenConstruct.CanPlaceBlueprintAt(thing.InnerThing.def, candidate, rotation, map, false, null, thing);
                        if (!candidateReport.Accepted) continue;
                        cell = candidate;
                        report = candidateReport;
                        break;
                    }
                }
                if (!report.Accepted) return ApiResult.Fail(report.Reason.NullOrEmpty() ? "The object cannot be installed there." : report.Reason);
                GenConstruct.PlaceBlueprintForInstall(thing, cell, map, rotation, Faction.OfPlayer);
                return ApiResult.Ok();
            }
            catch (Exception ex)
            {
                LogApi.Error($"Install minified error: {ex}");
                return ApiResult.Fail(ex.Message);
            }
        }

        public static ApiResult ConfigureStorageBuildings(ConfigureStorageBuildingsRequestDto request)
        {
            try
            {
                Map map = MapHelper.GetMapByID(request.MapId);
                if (map == null) return ApiResult.Fail($"Map {request.MapId} not found.");
                var ids = new System.Collections.Generic.HashSet<int>(request.BuildingIds ?? new System.Collections.Generic.List<int>());
                var storages = map.listerBuildings.allBuildingsColonist
                    .OfType<Building_Storage>().Where(b => ids.Contains(b.thingIDNumber)).ToList();
                if (storages.Count == 0) return ApiResult.Fail("No completed storage buildings matched the request.");
                foreach (Building_Storage storage in storages)
                {
                    StorageSettings settings = storage.GetStoreSettings();
                    foreach (ThingDef thingDef in DefDatabase<ThingDef>.AllDefs)
                        settings.filter.SetAllow(thingDef, false);
                    foreach (string defName in request.AllowedItemDefs ?? new System.Collections.Generic.List<string>())
                    {
                        ThingDef thingDef = DefDatabase<ThingDef>.GetNamedSilentFail(defName);
                        if (thingDef != null) settings.filter.SetAllow(thingDef, true);
                    }
                    foreach (string categoryName in request.AllowedItemCategories ?? new System.Collections.Generic.List<string>())
                    {
                        ThingCategoryDef category = DefDatabase<ThingCategoryDef>.GetNamedSilentFail(categoryName);
                        if (category == null) continue;
                        foreach (ThingDef thingDef in category.DescendantThingDefs)
                            settings.filter.SetAllow(thingDef, true);
                    }
                    settings.Priority = (StoragePriority)Mathf.Clamp(request.Priority, 0, 5);
                    storage.Notify_SettingsChanged();
                }
                return ApiResult.Ok();
            }
            catch (Exception ex)
            {
                LogApi.Error($"Configure storage buildings error: {ex}");
                return ApiResult.Fail(ex.Message);
            }
        }
    }
}

using System;
using System.Collections.Generic;
using System.Linq;
using RIMAPI.Core;
using RIMAPI.Models;
using RimWorld;
using RimWorld.Planet;
using Verse;

namespace RIMAPI.Helpers
{
    /// <summary>
    /// Remembers the legitimate proximity warning emitted by RimWorld. Hidden
    /// shrine contents are never returned to the client; only the warning cell
    /// and an ordinary wall which the player could designate are exposed.
    /// </summary>
    public static class AncientDangerAutomationHelper
    {
        private sealed class Detection
        {
            public int MapId;
            public int Tick;
            public string Notice;
            public IntVec3 Cell;
        }

        private static readonly Dictionary<int, Detection> Detections = new Dictionary<int, Detection>();

        public static void Observe(string text, LookTargets lookTargets)
        {
            if (string.IsNullOrEmpty(text) ||
                (text.IndexOf("ancient danger", StringComparison.OrdinalIgnoreCase) < 0 &&
                 text.IndexOf("ancient wall", StringComparison.OrdinalIgnoreCase) < 0))
                return;
            GlobalTargetInfo target = lookTargets != null ? lookTargets.PrimaryTarget : GlobalTargetInfo.Invalid;
            Map map = target.Thing?.Map ?? Find.CurrentMap;
            if (map == null) return;
            IntVec3 cell = target.Thing != null ? target.Thing.Position : target.Cell;
            if (!cell.IsValid) cell = map.Center;
            Detections[map.uniqueID] = new Detection
            {
                MapId = map.uniqueID,
                Tick = Find.TickManager?.TicksGame ?? 0,
                Notice = text,
                Cell = cell,
            };
        }

        public static ApiResult<AncientDangerStateDto> GetState(int mapId)
        {
            Map map = MapHelper.GetMapByID(mapId);
            if (map == null) return ApiResult<AncientDangerStateDto>.Fail($"Map {mapId} not found.");
            Detection detection;
            if (!Detections.TryGetValue(mapId, out detection))
                ObserveExistingLetters(map);
            Detections.TryGetValue(mapId, out detection);
            if (detection == null)
                return ApiResult<AncientDangerStateDto>.Ok(new AncientDangerStateDto { MapId = mapId });

            Thing casket = FindClosestCasket(map, detection.Cell);
            bool isSealed = casket != null && casket.Position.Fogged(map);
            Thing wall = isSealed ? FindOpeningWall(map, detection.Cell, casket) : null;
            return ApiResult<AncientDangerStateDto>.Ok(new AncientDangerStateDto
            {
                MapId = mapId,
                Detected = true,
                Sealed = isSealed,
                DetectedTick = detection.Tick,
                Notice = detection.Notice,
                Position = ToPosition(detection.Cell),
                OpeningTargetThingId = wall?.thingIDNumber,
                OpeningTargetPosition = wall == null ? null : ToPosition(wall.Position),
                CanOpen = wall != null,
            });
        }

        public static ApiResult Open(OpenAncientDangerRequestDto request)
        {
            Map map = MapHelper.GetMapByID(request.MapId);
            if (map == null) return ApiResult.Fail($"Map {request.MapId} not found.");
            Detection detection;
            if (!Detections.TryGetValue(request.MapId, out detection))
                return ApiResult.Fail("No Ancient Danger proximity warning has been observed on this map.");
            Thing casket = FindClosestCasket(map, detection.Cell);
            Thing wall = FindOpeningWall(map, detection.Cell, casket);
            if (wall == null) return ApiResult.Fail("No sealed shrine wall can be safely identified from the warning location.");
            if (wall.Faction == Faction.OfPlayer)
                return ApiResult.Fail("The candidate wall belongs to the colony; refusing to demolish it.");
            Designation existing = map.designationManager.DesignationOn(wall, DesignationDefOf.Deconstruct);
            if (existing == null)
                map.designationManager.AddDesignation(new Designation(wall, DesignationDefOf.Deconstruct));
            Messages.Message("Laya: Ancient Danger opening designated. Colonists will use the normal deconstruction job.", wall,
                MessageTypeDefOf.CautionInput, false);
            return ApiResult.Ok();
        }

        private static void ObserveExistingLetters(Map map)
        {
            if (Find.Archive != null)
            {
                foreach (IArchivable archived in Find.Archive.ArchivablesListForReading)
                {
                    Message message = archived as Message;
                    if (message == null || message.text.IndexOf("ancient danger", StringComparison.OrdinalIgnoreCase) < 0)
                    {
                        // The localized warning body does not necessarily repeat the English label.
                        if (message == null || message.text.IndexOf("ancient wall", StringComparison.OrdinalIgnoreCase) < 0)
                            continue;
                    }
                    Observe("Ancient danger: " + message.text, message.lookTargets);
                    if (Detections.ContainsKey(map.uniqueID)) return;
                }
            }
            if (Find.LetterStack == null) return;
            foreach (Letter letter in Find.LetterStack.LettersListForReading)
            {
                string text = letter.Label.ToString();
                if (text.IndexOf("ancient danger", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    Observe(text, letter.lookTargets);
                    if (Detections.ContainsKey(map.uniqueID)) return;
                }
            }
        }

        private static Thing FindClosestCasket(Map map, IntVec3 around)
        {
            return map.listerThings.AllThings
                .Where(t => t.def != null && t.def.defName == "AncientCryptosleepCasket")
                .OrderBy(t => t.Position.DistanceToSquared(around))
                .FirstOrDefault();
        }

        private static Thing FindOpeningWall(Map map, IntVec3 warningCell, Thing casket)
        {
            var buildings = map.listerBuildings.allBuildingsNonColonist
                .Where(b => b.def == ThingDefOf.Wall && b.Faction != Faction.OfPlayer)
                .ToList();
            if (casket != null)
            {
                Thing casketWall = buildings
                    .Where(b => b.Position.DistanceToSquared(casket.Position) <= 225)
                    .OrderBy(b => b.Position.DistanceToSquared(casket.Position))
                    .FirstOrDefault();
                if (casketWall != null) return casketWall;
            }
            return buildings
                .Where(b => b.Position.DistanceToSquared(warningCell) <= 64)
                .OrderBy(b => b.Position.DistanceToSquared(warningCell))
                .FirstOrDefault();
        }

        private static PositionDto ToPosition(IntVec3 cell)
        {
            return new PositionDto { X = cell.x, Y = cell.y, Z = cell.z };
        }
    }
}

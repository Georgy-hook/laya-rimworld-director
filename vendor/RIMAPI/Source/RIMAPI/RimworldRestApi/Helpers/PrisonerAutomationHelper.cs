using System;
using System.Collections.Generic;
using System.Linq;
using RIMAPI.Core;
using RIMAPI.Models;
using RimWorld;
using Verse;
using Verse.AI;

namespace RIMAPI.Helpers
{
    public static class PrisonerAutomationHelper
    {
        private static readonly Dictionary<int, string> PendingPolicies = new Dictionary<int, string>();

        public static ApiResult StartCapture(PrisonerCaptureRequestDto request)
        {
            try
            {
                Map map = MapHelper.GetMapByID(request.MapId);
                if (map == null) return ApiResult.Fail($"Map {request.MapId} not found.");
                Pawn target = PawnHelper.FindPawnById(request.PrisonerPawnId);
                if (target == null || target.Map != map || target.Dead || !target.Downed)
                    return ApiResult.Fail("The selected downed pawn is unavailable.");
                if (!target.HostileTo(Faction.OfPlayer))
                    return ApiResult.Fail("The selected pawn is not a hostile capture target.");

                CellRect rect = CellRect.FromLimits(
                    new IntVec3(request.PointA.X, 0, request.PointA.Z),
                    new IntVec3(request.PointB.X, 0, request.PointB.Z));
                List<Building_Bed> beds = map.listerBuildings.allBuildingsColonist
                    .OfType<Building_Bed>()
                    .Where(b => rect.Contains(b.Position) && !b.Destroyed && !b.Medical)
                    .ToList();
                foreach (Building_Bed bed in beds) bed.ForPrisoners = true;
                Building_Bed prisonBed = beds.FirstOrDefault(b => b.AnyUnoccupiedSleepingSlot && Building_Bed.RoomCanBePrisonCell(b.GetRoom()));
                if (prisonBed == null)
                    return ApiResult.Fail("No completed, enclosed and unoccupied prison bed exists in the planned prison.");

                Pawn captor = map.mapPawns.FreeColonistsSpawned
                    .Where(p => !p.Downed && !p.Dead && !p.InMentalState)
                    .OrderByDescending(p => p.health.summaryHealth.SummaryHealthPercent)
                    .ThenByDescending(p => p.skills?.GetSkill(SkillDefOf.Medicine)?.Level ?? 0)
                    .FirstOrDefault();
                if (captor == null) return ApiResult.Fail("No healthy colonist can capture the prisoner.");

                JobDef captureDef = DefDatabase<JobDef>.GetNamedSilentFail("Capture");
                if (captureDef == null) return ApiResult.Fail("The normal Capture job is unavailable.");
                Job job = JobMaker.MakeJob(captureDef, target, prisonBed);
                if (!captor.jobs.TryTakeOrderedJob(job))
                    return ApiResult.Fail("The selected colonist could not accept the Capture job.");

                PendingPolicies[target.thingIDNumber] = NormalizePolicy(request.Policy);
                Messages.Message($"Laya: {captor.LabelShortCap} is capturing {target.LabelShortCap}.", target,
                    MessageTypeDefOf.NeutralEvent, false);
                return ApiResult.Ok();
            }
            catch (Exception ex)
            {
                LogApi.Error($"Prisoner capture failed: {ex}");
                return ApiResult.Fail(ex.Message);
            }
        }

        public static ApiResult SetPolicy(PrisonerPolicyRequestDto request)
        {
            Pawn pawn = PawnHelper.FindPawnById(request.PrisonerPawnId);
            if (pawn == null || !pawn.IsPrisonerOfColony)
                return ApiResult.Fail("The selected pawn is not a colony prisoner.");
            ApplyPolicy(pawn, NormalizePolicy(request.Policy));
            return ApiResult.Ok();
        }

        public static ApiResult ConfigureBeds(BedConfigureRequestDto request)
        {
            Map map = MapHelper.GetMapByID(request.MapId);
            if (map == null) return ApiResult.Fail($"Map {request.MapId} not found.");
            CellRect rect = CellRect.FromLimits(
                new IntVec3(request.PointA.X, 0, request.PointA.Z),
                new IntVec3(request.PointB.X, 0, request.PointB.Z));
            List<Building_Bed> beds = map.listerBuildings.allBuildingsColonist
                .OfType<Building_Bed>().Where(b => rect.Contains(b.Position) && !b.Destroyed).ToList();
            foreach (Building_Bed bed in beds)
            {
                bed.Medical = request.Medical;
                bed.ForPrisoners = request.ForPrisoners;
            }
            return beds.Count == 0
                ? ApiResult.Fail("No completed beds exist in the requested area yet.")
                : ApiResult.Ok();
        }

        public static void ProcessPendingPolicies()
        {
            if (PendingPolicies.Count == 0) return;
            foreach (var pair in PendingPolicies.ToList())
            {
                Pawn pawn = PawnHelper.FindPawnById(pair.Key);
                if (pawn == null || pawn.Dead)
                {
                    PendingPolicies.Remove(pair.Key);
                    continue;
                }
                if (!pawn.IsPrisonerOfColony) continue;
                ApplyPolicy(pawn, pair.Value);
                PendingPolicies.Remove(pair.Key);
            }
        }

        private static string NormalizePolicy(string policy)
        {
            string value = (policy ?? "recruit").Trim().ToLowerInvariant();
            return value == "release" || value == "sell" ? value : "recruit";
        }

        private static void ApplyPolicy(Pawn pawn, string policy)
        {
            if (policy == "release")
                pawn.guest.SetExclusiveInteraction(PrisonerInteractionModeDefOf.Release);
            else if (policy == "sell")
                pawn.guest.SetNoInteraction();
            else
                pawn.guest.SetExclusiveInteraction(PrisonerInteractionModeDefOf.AttemptRecruit);
        }
    }
}

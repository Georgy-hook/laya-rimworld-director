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
    public static class CombatTacticsHelper
    {
        private static readonly HashSet<string> PositioningTactics = new HashSet<string>
        {
            "hold_cover", "firing_line", "spread_out", "kite", "staggered_retreat",
            "melee_block", "door_defense", "killbox_hold", "fallback_line", "wide_flank",
            "pincer", "counter_snipe", "smoke_advance", "siege_harass", "drop_pod_encircle",
            "infestation_choke", "cluster_poke", "intercept_kidnapper", "covered_rescue",
            "fire_retreat"
        };

        public static ApiResult<CombatTacticResponseDto> Apply(CombatTacticRequestDto request)
        {
            try
            {
                Map map = MapHelper.GetMapByID(request.MapId);
                if (map == null)
                    return ApiResult<CombatTacticResponseDto>.Fail($"Map {request.MapId} not found.");
                string tactic = (request.Tactic ?? "").Trim().ToLowerInvariant();
                if (tactic == "stand_down")
                {
                    foreach (Pawn pawn in map.mapPawns.FreeColonistsSpawned.Where(p => p.drafter?.Drafted == true))
                        pawn.drafter.Drafted = false;
                    return ApiResult<CombatTacticResponseDto>.Ok(new CombatTacticResponseDto { Tactic = tactic });
                }

                List<Pawn> fighters = map.mapPawns.FreeColonistsSpawned
                    .Where(p => request.FighterIds.Contains(p.thingIDNumber) && !p.Dead && !p.Downed
                        && !p.InMentalState && p.health.summaryHealth.SummaryHealthPercent >= 0.60f)
                    .ToList();
                if (fighters.Count == 0)
                    return ApiResult<CombatTacticResponseDto>.Fail("No selected healthy fighter is available on this map.");
                Pawn target = request.TargetPawnId.HasValue
                    ? map.mapPawns.AllPawnsSpawned.FirstOrDefault(p => p.thingIDNumber == request.TargetPawnId.Value && !p.Dead)
                    : map.mapPawns.AllPawnsSpawned
                        .Where(p => !p.Dead && p.HostileTo(Faction.OfPlayer))
                        .OrderBy(p => fighters.Min(f => f.Position.DistanceToSquared(p.Position)))
                        .FirstOrDefault();
                var result = new CombatTacticResponseDto
                {
                    Tactic = tactic,
                    TargetPawnId = target?.thingIDNumber,
                };

                foreach (Pawn pawn in fighters)
                {
                    if (pawn.drafter != null)
                    {
                        pawn.drafter.Drafted = true;
                        result.DraftedPawnIds.Add(pawn.thingIDNumber);
                    }
                }

                if (!string.IsNullOrEmpty(request.AbilityDefName) && request.PsycasterPawnId.HasValue)
                {
                    Pawn caster = fighters.FirstOrDefault(p => p.thingIDNumber == request.PsycasterPawnId.Value);
                    Pawn abilityTarget = request.AbilityTargetPawnId.HasValue
                        ? map.mapPawns.AllPawnsSpawned.FirstOrDefault(p => p.thingIDNumber == request.AbilityTargetPawnId.Value)
                        : target;
                    IntVec3? targetCell = request.AbilityTargetPosition == null
                        ? (IntVec3?)null
                        : new IntVec3(request.AbilityTargetPosition.X, 0, request.AbilityTargetPosition.Z);
                    ApiResult<bool> cast = PsychicAutomationHelper.QueuePsycast(caster, request.AbilityDefName, abilityTarget, targetCell);
                    result.PsycastQueued = cast.Success;
                    result.Psycast = request.AbilityDefName;
                    if (!cast.Success)
                        result.Notes.AddRange(cast.Errors);
                }

                if (target == null)
                {
                    result.Notes.Add("No living hostile target remains; fighters were drafted but no attack was issued.");
                    return ApiResult<CombatTacticResponseDto>.Ok(result);
                }

                Building defense = FindDefense(map, request.DefenseBuildingId, tactic, target.Position);
                if (PositioningTactics.Contains(tactic))
                {
                    List<Pawn> ordered = fighters
                        .OrderByDescending(p => IsRanged(p) ? p.skills?.GetSkill(SkillDefOf.Shooting)?.Level ?? 0 : p.skills?.GetSkill(SkillDefOf.Melee)?.Level ?? 0)
                        .ToList();
                    for (int i = 0; i < ordered.Count; i++)
                    {
                        Pawn pawn = ordered[i];
                        IntVec3 desired = DesiredCell(pawn, target, defense, tactic, i, ordered.Count);
                        IntVec3 safe;
                        if (TryFindTrapFreeCell(pawn, desired, target.Position, tactic, out safe))
                        {
                            Job move = JobMaker.MakeJob(JobDefOf.Goto, safe);
                            move.playerForced = true;
                            if (pawn.jobs.TryTakeOrderedJob(move))
                                result.PositionedPawnIds.Add(pawn.thingIDNumber);
                        }
                        else
                        {
                            result.Notes.Add($"No trap-free reachable position was found for {pawn.LabelShortCap}; current position retained.");
                        }
                    }
                    if (result.PositionedPawnIds.Count > 0)
                        return ApiResult<CombatTacticResponseDto>.Ok(result);
                }

                bool meleeRush = tactic == "rush_ranged" || tactic == "melee_block";
                foreach (Pawn pawn in fighters)
                {
                    bool ranged = IsRanged(pawn) && !meleeRush;
                    JobDef jobDef = ranged ? JobDefOf.AttackStatic : JobDefOf.AttackMelee;
                    Job attack = JobMaker.MakeJob(jobDef, target);
                    attack.playerForced = true;
                    if (pawn.jobs.TryTakeOrderedJob(attack))
                        result.AttackingPawnIds.Add(pawn.thingIDNumber);
                }
                return ApiResult<CombatTacticResponseDto>.Ok(result);
            }
            catch (Exception ex)
            {
                LogApi.Error($"Combat tactic failed: {ex}");
                return ApiResult<CombatTacticResponseDto>.Fail(ex.Message);
            }
        }

        private static bool IsRanged(Pawn pawn)
        {
            return pawn?.equipment?.Primary?.def?.IsRangedWeapon ?? false;
        }

        private static Building FindDefense(Map map, int? requestedId, string tactic, IntVec3 target)
        {
            IEnumerable<Building> candidates = map.listerBuildings.allBuildingsColonist
                .Where(b => b != null && !b.Destroyed && !(b is Building_Trap));
            if (requestedId.HasValue)
            {
                Building exact = candidates.FirstOrDefault(b => b.thingIDNumber == requestedId.Value);
                if (exact != null) return exact;
            }
            string[] preferred = tactic == "melee_block" || tactic == "door_defense" || tactic == "infestation_choke"
                ? new[] { "door", "wall" }
                : tactic == "killbox_hold"
                    ? new[] { "barricade", "sandbag", "turret", "wall" }
                    : tactic == "fallback_line" || tactic == "fire_retreat"
                        ? new[] { "barricade", "sandbag", "door", "wall" }
                        : new[] { "barricade", "sandbag", "wall", "shelf", "turret" };
            return candidates
                .Where(b => preferred.Any(token => (b.def.defName + " " + b.Label).ToLowerInvariant().Contains(token)))
                .OrderBy(b => b.Position.DistanceToSquared(target))
                .FirstOrDefault();
        }

        private static IntVec3 DesiredCell(Pawn pawn, Pawn target, Building defense, string tactic, int index, int count)
        {
            IntVec3 baseCell = defense?.Position ?? pawn.Position;
            int dx = Math.Sign(baseCell.x - target.Position.x);
            int dz = Math.Sign(baseCell.z - target.Position.z);
            if (dx == 0 && dz == 0) dx = 1;
            int sideX = -dz;
            int sideZ = dx;
            int spacing = tactic == "spread_out" || tactic == "drop_pod_encircle" ? 3 : 1;
            int centered = index - count / 2;

            if (tactic == "kite" || tactic == "staggered_retreat" || tactic == "fire_retreat")
                return new IntVec3(pawn.Position.x + dx * 8 + sideX * centered, 0, pawn.Position.z + dz * 8 + sideZ * centered);
            if (tactic == "wide_flank" || tactic == "pincer")
            {
                int side = (index % 2 == 0 ? -1 : 1) * Math.Max(7, 3 + count);
                return new IntVec3(target.Position.x + dx * 14 + sideX * side, 0, target.Position.z + dz * 14 + sideZ * side);
            }
            if (tactic == "drop_pod_encircle")
            {
                IntVec3[] ring = { IntVec3.North, IntVec3.East, IntVec3.South, IntVec3.West, IntVec3.NorthEast, IntVec3.SouthWest };
                IntVec3 offset = ring[index % ring.Length] * 7;
                return target.Position + offset;
            }
            int depth = tactic == "melee_block" || tactic == "door_defense" || tactic == "infestation_choke" ? 1 : 2;
            return new IntVec3(baseCell.x + dx * depth + sideX * centered * spacing, 0, baseCell.z + dz * depth + sideZ * centered * spacing);
        }

        private static bool TryFindTrapFreeCell(Pawn pawn, IntVec3 desired, IntVec3 hostile, string tactic, out IntVec3 result)
        {
            Map map = pawn.Map;
            bool melee = tactic == "melee_block" || tactic == "door_defense" || tactic == "rush_ranged" || tactic == "infestation_choke";
            IEnumerable<IntVec3> candidates = GenRadial.RadialCellsAround(desired, 7f, true)
                .Where(cell => cell.InBounds(map) && cell.Standable(map) && !cell.Fogged(map)
                    && !cell.ContainsStaticFire(map) && !HasFriendlyTrap(cell, map)
                    && !cell.GetThingList(map).OfType<Pawn>().Any())
                .OrderBy(cell => cell.DistanceToSquared(desired));
            foreach (IntVec3 cell in candidates)
            {
                if (!melee && cell.DistanceToSquared(hostile) < 36)
                    continue;
                PawnPath path = map.pathFinder.FindPathNow(pawn.Position, cell, pawn, null, PathEndMode.OnCell);
                bool valid = path.Found && path.NodesReversed.All(node => !HasFriendlyTrap(node, map));
                path.ReleaseToPool();
                if (!valid) continue;
                result = cell;
                return true;
            }
            result = IntVec3.Invalid;
            return false;
        }

        private static bool HasFriendlyTrap(IntVec3 cell, Map map)
        {
            return cell.GetThingList(map).Any(t => t is Building_Trap && t.Faction == Faction.OfPlayer);
        }
    }
}

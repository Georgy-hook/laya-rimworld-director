using System;
using System.Collections.Generic;
using System.Linq;
using RIMAPI.Core;
using RIMAPI.Helpers;
using RIMAPI.Models;
using RimWorld;
using Verse;

namespace RIMAPI.Services
{
    public class CombatService : ICombatService
    {
        public ApiResult<CombatStateDto> GetCombatState(int mapId)
        {
            try
            {
                var map = MapHelper.GetMapByID(mapId);
                if (map == null)
                {
                    return ApiResult<CombatStateDto>.Fail($"Map not found: {mapId}");
                }

                var colonists = map.mapPawns.FreeColonistsSpawned
                    .Where(p => p != null && !p.Dead)
                    .ToList();
                var hostiles = map.mapPawns.AllPawnsSpawned
                    .Where(p => p != null && !p.Dead && p.HostileTo(Faction.OfPlayer))
                    .ToList();
                var prisoners = map.mapPawns.PrisonersOfColony
                    .Where(p => p != null && !p.Dead)
                    .ToList();
                var weapons = map.listerThings.AllThings
                    .Where(t => t != null && t.Spawned && !t.Destroyed && t.def != null
                        && t.def.IsWeapon && t.def.weaponTags != null && t.def.weaponTags.Count > 0)
                    .Select(t => new CombatWeaponDto
                    {
                        Id = t.thingIDNumber,
                        DefName = t.def.defName,
                        Label = t.LabelShortCap,
                        IsRanged = t.def.IsRangedWeapon,
                        IsForbidden = t.IsForbidden(Faction.OfPlayer),
                        MarketValue = t.MarketValue,
                        Position = new PositionDto
                        {
                            X = t.Position.x,
                            Y = t.Position.y,
                            Z = t.Position.z,
                        },
                    })
                    .OrderByDescending(w => w.MarketValue)
                    .ToList();

                var result = new CombatStateDto
                {
                    MapId = map.uniqueID,
                    GameTick = Find.TickManager?.TicksGame ?? 0,
                    Colonists = colonists.Select(p => ToCombatPawn(p, false, hostiles)).ToList(),
                    Hostiles = hostiles.Select(p => ToCombatPawn(p, true, colonists)).ToList(),
                    Prisoners = prisoners.Select(p => ToCombatPawn(p, false, colonists)).ToList(),
                    AvailableWeapons = weapons,
                };
                return ApiResult<CombatStateDto>.Ok(result);
            }
            catch (Exception ex)
            {
                LogApi.Error($"Combat state error: {ex}");
                return ApiResult<CombatStateDto>.Fail(ex.Message);
            }
        }

        private static CombatPawnDto ToCombatPawn(Pawn pawn, bool hostile, List<Pawn> opponents)
        {
            var primary = pawn.equipment?.Primary;
            var shooting = pawn.skills?.GetSkill(SkillDefOf.Shooting);
            var melee = pawn.skills?.GetSkill(SkillDefOf.Melee);
            var faction = pawn.Faction;
            var distance = 0f;
            if (opponents != null && opponents.Count > 0)
            {
                distance = opponents.Min(other => (float)Math.Sqrt(
                    pawn.Position.DistanceToSquared(other.Position)));
            }

            return new CombatPawnDto
            {
                Id = pawn.thingIDNumber,
                Name = pawn.Name?.ToStringShort ?? pawn.LabelShortCap,
                KindDef = pawn.kindDef?.defName,
                Faction = pawn.Faction?.def?.defName,
                IsColonist = pawn.IsColonist,
                IsHostile = hostile,
                IsDrafted = pawn.drafter?.Drafted ?? false,
                IsDowned = pawn.Downed,
                IsDead = pawn.Dead,
                Health = pawn.health?.summaryHealth?.SummaryHealthPercent ?? 0f,
                Position = new PositionDto
                {
                    X = pawn.Position.x,
                    Y = pawn.Position.y,
                    Z = pawn.Position.z,
                },
                ShootingSkill = shooting?.Level ?? 0,
                MeleeSkill = melee?.Level ?? 0,
                WeaponDef = primary?.def?.defName,
                WeaponLabel = primary?.LabelShortCap,
                HasRangedWeapon = primary?.def?.IsRangedWeapon ?? false,
                CurrentJob = pawn.CurJobDef?.defName,
                DistanceToNearestOpponent = distance,
                Gender = pawn.gender.ToString(),
                BiologicalAge = pawn.ageTracker?.AgeBiologicalYears ?? 0,
                BleedingRate = pawn.health?.hediffSet?.BleedRateTotal ?? 0f,
                Consciousness = pawn.health?.capacities?.GetLevel(PawnCapacityDefOf.Consciousness) ?? 0f,
                Moving = pawn.health?.capacities?.GetLevel(PawnCapacityDefOf.Moving) ?? 0f,
                Manipulation = pawn.health?.capacities?.GetLevel(PawnCapacityDefOf.Manipulation) ?? 0f,
                Sight = pawn.health?.capacities?.GetLevel(PawnCapacityDefOf.Sight) ?? 0f,
                Pain = pawn.health?.hediffSet?.PainTotal ?? 0f,
                MarketValue = pawn.MarketValue,
                SocialSkill = pawn.skills?.GetSkill(SkillDefOf.Social)?.Level ?? 0,
                MedicineSkill = pawn.skills?.GetSkill(SkillDefOf.Medicine)?.Level ?? 0,
                ConstructionSkill = pawn.skills?.GetSkill(SkillDefOf.Construction)?.Level ?? 0,
                AnimalsSkill = pawn.skills?.GetSkill(SkillDefOf.Animals)?.Level ?? 0,
                IntellectualSkill = pawn.skills?.GetSkill(SkillDefOf.Intellectual)?.Level ?? 0,
                CookingSkill = pawn.skills?.GetSkill(SkillDefOf.Cooking)?.Level ?? 0,
                Recruitable = !pawn.IsPrisoner || (pawn.guest?.Recruitable ?? true),
                FactionPermanentEnemy = faction?.def?.permanentEnemy ?? false,
                FactionCanGiveGoodwill = faction != null && faction != Faction.OfPlayer && faction.CanEverGiveGoodwillRewards,
                FactionGoodwill = faction != null && faction != Faction.OfPlayer ? faction.PlayerGoodwill : 0,
                Traits = pawn.story?.traits?.allTraits?.Select(t => t.LabelCap).Take(8).ToList() ?? new List<string>(),
                TopSkills = pawn.skills?.skills?.OrderByDescending(s => s.Level)
                    .Take(5).Select(s => $"{s.def.label}:{s.Level}").ToList() ?? new List<string>(),
                HealthConditions = pawn.health?.hediffSet?.hediffs?
                    .Where(h => h.Visible)
                    .Select(h => $"{h.def.defName}:{h.Part?.def?.defName ?? "whole body"}")
                    .Take(12).ToList() ?? new List<string>(),
            };
        }
    }
}

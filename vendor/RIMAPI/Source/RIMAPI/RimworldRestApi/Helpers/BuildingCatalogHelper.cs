using System;
using System.Collections.Generic;
using System.Linq;
using RIMAPI.Models;
using RimWorld;
using Verse;

namespace RIMAPI.Helpers
{
    public static class BuildingCatalogHelper
    {
        public static List<BuildingCatalogDto> GetCatalog()
        {
            return DefDatabase<ThingDef>.AllDefsListForReading
                .Where(def => def != null
                    && def.category == ThingCategory.Building
                    && def.designationCategory != null
                    && !string.IsNullOrEmpty(def.defName))
                .Select(def => new BuildingCatalogDto
                {
                    DefName = def.defName,
                    Label = def.LabelCap,
                    Description = def.description,
                    DesignationCategory = def.designationCategory?.defName,
                    ResearchPrerequisites = def.researchPrerequisites?
                        .Where(project => project != null)
                        .Select(project => project.defName).ToList() ?? new List<string>(),
                    AvailableNow = def.researchPrerequisites == null
                        || def.researchPrerequisites.All(project => project == null || project.IsFinished),
                    CostList = def.costList?.Where(cost => cost?.thingDef != null)
                        .Select(cost => new ThingCostDto
                        {
                            ThingDef = cost.thingDef.defName,
                            Count = cost.count,
                        }).ToList() ?? new List<ThingCostDto>(),
                    CostStuffCount = def.costStuffCount,
                    StuffCategories = def.stuffCategories?
                        .Where(category => category != null)
                        .Select(category => category.defName).ToList() ?? new List<string>(),
                    SizeX = def.size.x,
                    SizeZ = def.size.z,
                    IsWorkTable = def.IsWorkTable,
                    IsBed = def.IsBed,
                    RequiresPower = def.comps?.Any(comp => comp?.compClass == typeof(CompPowerTrader)) ?? false,
                    LightRadius = def.comps?.OfType<CompProperties_Glower>()
                        .Select(comp => comp.glowRadius).DefaultIfEmpty(0f).Max() ?? 0f,
                    BuildingTags = def.building?.buildingTags?.ToList() ?? new List<string>(),
                    RecipeSkills = def.AllRecipes?
                        .Where(recipe => recipe?.workSkill != null)
                        .Select(recipe => recipe.workSkill.defName).Distinct().ToList() ?? new List<string>(),
                })
                .OrderBy(def => def.DesignationCategory)
                .ThenBy(def => def.Label)
                .ToList();
        }

        public static RoyaltyContextDto GetRoyaltyContext()
        {
            var result = new RoyaltyContextDto { Active = ModsConfig.RoyaltyActive };
            if (!result.Active)
                return result;

            foreach (var pawn in PawnsFinder.AllMaps_FreeColonists.Where(pawn => pawn?.royalty != null))
            {
                var title = pawn.royalty.MostSeniorTitle;
                if (title?.def == null)
                    continue;
                result.Colonists.Add(new RoyalPawnContextDto
                {
                    PawnId = pawn.thingIDNumber,
                    PawnName = pawn.LabelShort,
                    TitleDefName = title.def.defName,
                    TitleLabel = title.Label,
                    Seniority = title.def.seniority,
                    RequiresThroneRoom = pawn.royalty.CanRequireThroneroom(),
                    HasUnmetThroneRoomRequirements = pawn.royalty.AnyUnmetThroneroomRequirements(),
                    RequiresBedroom = pawn.royalty.CanRequireBedroom(),
                    HasUnmetBedroomRequirements = pawn.royalty.AnyUnmetBedroomRequirements(),
                    MinimumThroneRoomImpressiveness = title.def.MinThroneRoomImpressiveness,
                    MinimumThroneRoomArea = title.def.throneRoomRequirements?
                        .OfType<RoomRequirement_Area>().Select(requirement => requirement.area)
                        .DefaultIfEmpty(0).Max() ?? 0,
                    ThroneRoomRequirementTypes = title.def.throneRoomRequirements?
                        .Where(requirement => requirement != null)
                        .Select(requirement => requirement.GetType().Name).ToList() ?? new List<string>(),
                    ThroneRoomRequirements = title.def.throneRoomRequirements?
                        .Where(requirement => requirement != null)
                        .Select(DescribeRoomRequirement).ToList() ?? new List<string>(),
                });
            }
            return result;
        }

        private static string DescribeRoomRequirement(RoomRequirement requirement)
        {
            if (requirement is RoomRequirement_Area area)
                return $"minimum area {area.area}";
            if (requirement is RoomRequirement_Impressiveness impressiveness)
                return $"minimum impressiveness {impressiveness.impressiveness}";
            if (requirement is RoomRequirement_ThingCount thingCount)
                return $"{thingCount.thingDef?.defName ?? "building"} x{thingCount.count}";
            if (requirement is RoomRequirement_Thing thing)
                return thing.thingDef?.defName ?? requirement.GetType().Name;
            if (requirement is RoomRequirement_ThingAnyOfCount anyCount)
                return $"one of [{string.Join(",", anyCount.things?.Where(def => def != null).Select(def => def.defName) ?? Enumerable.Empty<string>())}] x{anyCount.count}";
            if (requirement is RoomRequirement_ThingAnyOf anyOf)
                return $"one of [{string.Join(",", anyOf.things?.Where(def => def != null).Select(def => def.defName) ?? Enumerable.Empty<string>())}]";
            if (requirement is RoomRequirement_AllThingsAreGlowing glowing)
                return $"all {glowing.thingDef?.defName ?? "required buildings"} glowing";
            if (requirement is RoomRequirement_TerrainWithTags terrain)
                return $"terrain tags [{string.Join(",", terrain.tags ?? new List<string>())}]";
            if (requirement is RoomRequirement_ForbiddenBuildings forbidden)
                return $"forbid building tags [{string.Join(",", forbidden.buildingTags ?? new List<string>())}]";
            return requirement.GetType().Name;
        }
    }
}

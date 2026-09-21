using System;
using System.Collections.Generic;
using System.Linq;
using RIMAPI.Core;
using RIMAPI.Models;
using RimWorld;
using RimWorld.Planet;
using UnityEngine;
using Verse;

namespace RIMAPI.Helpers
{
    public static class CaravanAutomationHelper
    {
        private class PendingRoute
        {
            public HashSet<int> PawnIds;
            public HashSet<int> PrisonerIds;
            public int SettlementId;
            public bool Raid;
        }

        private class PendingPrisonerSale
        {
            public HashSet<int> PrisonerIds;
            public int SettlementId;
        }

        private static readonly List<PendingRoute> PendingRoutes = new List<PendingRoute>();
        private static readonly List<PendingPrisonerSale> PendingPrisonerSales = new List<PendingPrisonerSale>();

        public static void ProcessPendingRoutes()
        {
            if (Current.Game == null || Find.WorldObjects == null) return;
            for (int i = PendingRoutes.Count - 1; i >= 0; i--)
            {
                PendingRoute pending = PendingRoutes[i];
                Caravan caravan = Find.WorldObjects.Caravans.FirstOrDefault(c => c.Faction == Faction.OfPlayer
                    && c.PawnsListForReading.Any(p => pending.PawnIds.Contains(p.thingIDNumber)));
                Settlement settlement = Find.WorldObjects.Settlements.FirstOrDefault(s => s.ID == pending.SettlementId);
                if (caravan == null || settlement == null) continue;
                CaravanArrivalAction arrival = pending.Raid
                    ? (CaravanArrivalAction)new CaravanArrivalAction_AttackSettlement(settlement)
                    : new CaravanArrivalAction_Trade(settlement);
                caravan.pather.StartPath(settlement.Tile, arrival, true);
                if (!pending.Raid && pending.PrisonerIds != null && pending.PrisonerIds.Count > 0)
                {
                    PendingPrisonerSales.Add(new PendingPrisonerSale
                    {
                        PrisonerIds = new HashSet<int>(pending.PrisonerIds),
                        SettlementId = pending.SettlementId
                    });
                }
                PendingRoutes.RemoveAt(i);
            }
            ProcessPendingPrisonerSales();
        }

        private static void ProcessPendingPrisonerSales()
        {
            if (!TradeSession.Active || TradeSession.giftMode || TradeSession.deal == null
                || TradeSession.playerNegotiator == null || !(TradeSession.trader is Settlement settlement))
                return;

            Caravan caravan = TradeSession.playerNegotiator.GetCaravan();
            if (caravan == null) return;
            PendingPrisonerSale pending = PendingPrisonerSales.FirstOrDefault(s => s.SettlementId == settlement.ID
                && caravan.PawnsListForReading.Any(p => s.PrisonerIds.Contains(p.thingIDNumber)));
            if (pending == null) return;

            List<Tradeable> selected = TradeSession.deal.AllTradeables
                .Where(t => t.TraderWillTrade && t.thingsColony.OfType<Pawn>()
                    .Any(p => pending.PrisonerIds.Contains(p.thingIDNumber)))
                .ToList();
            if (selected.Count == 0)
            {
                Messages.Message("Laya: this settlement will not buy the selected prisoner.", MessageTypeDefOf.RejectInput, false);
                PendingPrisonerSales.Remove(pending);
                return;
            }

            foreach (Tradeable tradeable in selected)
            {
                int count = tradeable.thingsColony.OfType<Pawn>()
                    .Count(p => pending.PrisonerIds.Contains(p.thingIDNumber));
                tradeable.ForceToDestination(count);
            }
            TradeSession.deal.UpdateCurrencyCount();
            if (!TradeSession.deal.DoesTraderHaveEnoughSilver())
            {
                foreach (Tradeable tradeable in selected) tradeable.ForceTo(0);
                TradeSession.deal.UpdateCurrencyCount();
                Messages.Message("Laya: the trader cannot afford the selected prisoner; no sale was made.", MessageTypeDefOf.RejectInput, false);
                PendingPrisonerSales.Remove(pending);
                return;
            }

            if (TradeSession.deal.TryExecute(out bool actuallyTraded) && actuallyTraded)
            {
                caravan.RecacheInventory();
                Messages.Message("Laya: selected prisoner sold through the normal trade system at " + settlement.LabelCap + ".",
                    MessageTypeDefOf.PositiveEvent, false);
                PendingPrisonerSales.Remove(pending);
                Dialog_Trade dialog = Find.WindowStack.WindowOfType<Dialog_Trade>();
                dialog?.Close(false);
                TradeSession.Close();
            }
        }

        public static ApiResult<List<TradeDestinationDto>> GetTradeDestinations(int mapId)
        {
            try
            {
                Map map = MapHelper.GetMapByID(mapId);
                if (map == null)
                    return ApiResult<List<TradeDestinationDto>>.Fail($"Map {mapId} not found.");
                var result = Find.WorldObjects.Settlements
                    .Where(s => s.Faction != null && s.Faction != Faction.OfPlayer && !s.Faction.def.permanentEnemy)
                    .Select(s => new TradeDestinationDto
                    {
                        SettlementId = s.ID,
                        Name = s.LabelCap,
                        Tile = s.Tile,
                        FactionName = s.Faction.Name,
                        FactionDef = s.Faction.def.defName,
                        Relation = s.Faction.PlayerRelationKind.ToString(),
                        Goodwill = s.Faction.PlayerGoodwill,
                        ApproximateDistanceTiles = Find.WorldGrid.ApproxDistanceInTiles(map.Tile, s.Tile),
                        CanTradeNow = !s.Faction.HostileTo(Faction.OfPlayer) && s.Visitable && s.CanTradeNow,
                        EverVisited = s.EverVisited,
                        StockKnowledgeMayBeStale = s.EverVisited && s.RestockedSinceLastVisit,
                        TraderKind = s.TraderKind?.defName,
                        WillBuyHumanlikePrisoners = s.TraderKind != null
                            && DefDatabase<ThingDef>.GetNamedSilentFail("Human") is ThingDef human
                            && s.TraderKind.WillTrade(human),
                        KnownStock = s.EverVisited
                            ? s.Goods.Where(t => !(t is Pawn)).Take(80).Select(t => new KnownTradeItemDto
                            {
                                DefName = t.def.defName,
                                Label = t.LabelCap,
                                Count = t.stackCount,
                                MarketValue = t.MarketValue,
                                EstimatedBuyPrice = t.MarketValue * 1.4f,
                                EstimatedSellPrice = t.MarketValue * 0.6f
                            }).ToList()
                            : null
                    })
                    .OrderBy(s => s.ApproximateDistanceTiles)
                    .ToList();
                return ApiResult<List<TradeDestinationDto>>.Ok(result);
            }
            catch (Exception ex)
            {
                return ApiResult<List<TradeDestinationDto>>.Fail(ex.Message);
            }
        }

        public static ApiResult<StartTradeCaravanResponseDto> StartTradeCaravan(StartTradeCaravanRequestDto request)
        {
            try
            {
                Map map = MapHelper.GetMapByID(request.MapId);
                if (map == null)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail($"Map {request.MapId} not found.");
                if (GenHostility.AnyHostileActiveThreatToPlayer(map))
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("A trade caravan cannot leave during an active threat.");
                if (Find.WorldObjects.Caravans.Any(c => c.Faction == Faction.OfPlayer))
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("A player caravan is already active.");

                var healthy = map.mapPawns.FreeColonistsSpawned
                    .Where(p => !p.Downed && !p.InMentalState && p.health.summaryHealth.SummaryHealthPercent >= 0.80f)
                    .ToList();
                int available = healthy.Count - Math.Max(2, request.MinimumHomeDefenders);
                if (available <= 0)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("Not enough healthy colonists to keep the requested defenders at home.");

                var destination = Find.WorldObjects.Settlements.FirstOrDefault(s => s.ID == request.DestinationSettlementId);
                if (destination == null)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("The selected settlement does not exist.");
                if (destination.Faction == null || destination.Faction == Faction.OfPlayer
                    || destination.Faction.HostileTo(Faction.OfPlayer) || destination.Faction.def.permanentEnemy
                    || !destination.Visitable || !destination.CanTradeNow)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("The selected settlement is not currently a safe trading destination.");

                var pawns = healthy
                    .OrderByDescending(p => p.skills.GetSkill(SkillDefOf.Social).Level * 3 + p.skills.GetSkill(SkillDefOf.Shooting).Level)
                    .Take(Math.Min(2, available))
                    .ToList();
                if (pawns.Count == 0)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("No safe caravan negotiator is available.");
                var requestedPrisoners = new HashSet<int>(request.PrisonerIds ?? new List<int>());
                var salePrisoners = map.mapPawns.PrisonersOfColony
                    .Where(p => requestedPrisoners.Contains(p.thingIDNumber) && !p.Dead && !p.Downed
                        && p.health.summaryHealth.SummaryHealthPercent >= 0.70f)
                    .ToList();
                if (salePrisoners.Count > 0 && salePrisoners.Any(p => !destination.TraderKind.WillTrade(p.def)))
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("The selected settlement does not buy humanlike prisoners.");

                List<Thing> items = CaravanFormingUtility.AllReachableColonyItems(map);
                int totalFood = items.Where(IsTravelFood).Sum(t => t.stackCount);
                int totalMedicine = items.Where(IsMedicine).Sum(t => t.stackCount);
                int takeFood = Math.Min(Math.Max(8, pawns.Count * 10), Math.Max(0, totalFood - request.MinimumFoodAtHome));
                int takeMedicine = Math.Min(pawns.Count * 2, Math.Max(0, totalMedicine - request.MinimumMedicineAtHome));
                if (takeFood < Math.Max(6, pawns.Count * 6))
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("Not enough shelf-stable travel food while preserving the home reserve.");

                var transferables = new List<TransferableOneWay>();
                int foodAdded = AddByPredicate(transferables, items, IsTravelFood, takeFood);
                AddByPredicate(transferables, items, IsMedicine, takeMedicine);
                var reservedTravelStacks = new HashSet<Thing>(transferables.SelectMany(t => t.things));

                float goodsValue = salePrisoners.Sum(p => p.MarketValue);
                float goodsMass = 0f;
                int goodsStacks = 0;
                float massLimit = Math.Max(20f, pawns.Count * 28f);
                foreach (Thing thing in items.Where(t => !reservedTravelStacks.Contains(t) && IsSaleGood(t, request.SaleCategories)).OrderByDescending(t => t.MarketValue / Math.Max(0.05f, t.GetStatValue(StatDefOf.Mass))))
                {
                    if (goodsValue >= 2500f || goodsMass >= massLimit)
                        break;
                    float unitMass = Math.Max(0.01f, thing.GetStatValue(StatDefOf.Mass));
                    int count = Math.Min(thing.stackCount, Math.Max(0, Mathf.FloorToInt((massLimit - goodsMass) / unitMass)));
                    if (count <= 0)
                        continue;
                    AddTransferable(transferables, thing, count);
                    goodsMass += unitMass * count;
                    goodsValue += thing.MarketValue * count;
                    goodsStacks++;
                }
                if (goodsValue < 250f)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("No safe surplus trade goods worth at least 250 silver are ready.");

                PlanetTile startingTile = CaravanExitMapUtility.BestExitTileToGoTo(destination.Tile, map);
                if (!startingTile.Valid)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("No valid map exit toward the destination was found.");
                IntVec3 root = pawns.Aggregate(IntVec3.Zero, (sum, pawn) => sum + pawn.Position) / pawns.Count;
                if (!RCellFinder.TryFindClosestEdgeCellTo(root, map, out IntVec3 exitSpot))
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("No reachable caravan exit spot was found.");
                if (!RCellFinder.TryFindRandomSpotJustOutsideColony(exitSpot, map, out IntVec3 meetingPoint))
                    meetingPoint = root;

                var caravanPawns = pawns.Concat(salePrisoners).ToList();
                CaravanFormingUtility.StartFormingCaravan(
                    caravanPawns, new List<Pawn>(), Faction.OfPlayer, transferables,
                    meetingPoint, exitSpot, startingTile, destination.Tile);
                PendingRoutes.Add(new PendingRoute
                {
                    PawnIds = new HashSet<int>(caravanPawns.Select(p => p.thingIDNumber)),
                    PrisonerIds = new HashSet<int>(salePrisoners.Select(p => p.thingIDNumber)),
                    SettlementId = destination.ID,
                    Raid = false
                });
                Messages.Message("Laya: trade caravan is gathering supplies for " + destination.LabelCap + ".", pawns[0], MessageTypeDefOf.PositiveEvent, false);
                return ApiResult<StartTradeCaravanResponseDto>.Ok(new StartTradeCaravanResponseDto
                {
                    Status = "forming",
                    DestinationSettlementId = destination.ID,
                    DestinationName = destination.LabelCap,
                    DestinationTile = destination.Tile,
                    PawnCount = pawns.Count,
                    GoodsStacks = goodsStacks,
                    FoodCount = foodAdded,
                    ApproximateGoodsValue = goodsValue,
                    PrisonerCount = salePrisoners.Count,
                    PurchasePriorities = request.PurchasePriorities ?? new List<string>()
                });
            }
            catch (Exception ex)
            {
                LogApi.Error($"Trade caravan automation failed: {ex}");
                return ApiResult<StartTradeCaravanResponseDto>.Fail(ex.Message);
            }
        }

        public static ApiResult<List<RaidDestinationDto>> GetRaidDestinations(int mapId)
        {
            try
            {
                Map map = MapHelper.GetMapByID(mapId);
                if (map == null) return ApiResult<List<RaidDestinationDto>>.Fail($"Map {mapId} not found.");
                float threatPoints = Math.Max(500f, StorytellerUtility.DefaultThreatPointsNow(map) * 1.5f);
                var results = new List<RaidDestinationDto>();
                foreach (Settlement settlement in Find.WorldObjects.Settlements.Where(s => s.Faction != null && s.Faction != Faction.OfPlayer && s.Attackable))
                {
                    var options = (settlement.Faction.def.pawnGroupMakers ?? new List<PawnGroupMaker>())
                        .Where(m => m.kindDef == PawnGroupKindDefOf.Combat)
                        .SelectMany(m => m.options ?? new List<PawnGenOption>())
                        .Where(o => o.kind != null)
                        .ToList();
                    float avgPower = options.Count == 0 ? 80f : options.Average(o => Math.Max(20f, o.kind.combatPower));
                    int defenders = Mathf.Clamp(Mathf.RoundToInt(threatPoints / avgPower), 3, 30);
                    var kinds = options.OrderByDescending(o => o.selectionWeight).Select(o => o.kind).Distinct().Take(8).ToList();
                    string tech = settlement.Faction.def.techLevel.ToString();
                    var loot = new List<string> { "silver", "food", "medicine", "weapons" };
                    if (settlement.Faction.def.techLevel >= TechLevel.Industrial)
                        loot.AddRange(new[] { "components", "industrial armor" });
                    else
                        loot.AddRange(new[] { "animals", "leather", "herbal medicine" });
                    results.Add(new RaidDestinationDto
                    {
                        SettlementId = settlement.ID,
                        Name = settlement.LabelCap,
                        Tile = settlement.Tile,
                        FactionName = settlement.Faction.Name,
                        Relation = settlement.Faction.PlayerRelationKind.ToString(),
                        Goodwill = settlement.Faction.PlayerGoodwill,
                        TechLevel = tech,
                        ApproximateDistanceTiles = Find.WorldGrid.ApproxDistanceInTiles(map.Tile, settlement.Tile),
                        EstimatedDefendersMin = Math.Max(2, Mathf.RoundToInt(defenders * 0.7f)),
                        EstimatedDefendersMax = Mathf.RoundToInt(defenders * 1.4f),
                        LikelyPawnKinds = kinds.Select(k => k.label ?? k.defName).ToList(),
                        LikelyWeaponTags = kinds.SelectMany(k => k.weaponTags ?? new List<string>()).Distinct().Take(12).ToList(),
                        LikelyApparelTags = kinds.SelectMany(k => k.apparelTags ?? new List<string>()).Distinct().Take(12).ToList(),
                        PossibleLoot = loot.Distinct().ToList(),
                        EstimatedLootValue = Mathf.Round(threatPoints * (settlement.Faction.def.techLevel >= TechLevel.Industrial ? 1.5f : 1.0f)),
                        WouldStartWar = !settlement.Faction.HostileTo(Faction.OfPlayer)
                    });
                }
                return ApiResult<List<RaidDestinationDto>>.Ok(results.OrderBy(r => r.ApproximateDistanceTiles).ToList());
            }
            catch (Exception ex)
            {
                return ApiResult<List<RaidDestinationDto>>.Fail(ex.Message);
            }
        }

        public static ApiResult<StartTradeCaravanResponseDto> StartRaidCaravan(StartRaidCaravanRequestDto request)
        {
            try
            {
                Map map = MapHelper.GetMapByID(request.MapId);
                if (map == null) return ApiResult<StartTradeCaravanResponseDto>.Fail($"Map {request.MapId} not found.");
                if (GenHostility.AnyHostileActiveThreatToPlayer(map))
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("A raid expedition cannot leave during an active threat.");
                Settlement destination = Find.WorldObjects.Settlements.FirstOrDefault(s => s.ID == request.DestinationSettlementId);
                if (destination == null || !destination.Attackable)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("The selected raid target is unavailable.");
                if (!destination.Faction.HostileTo(Faction.OfPlayer) && !request.AllowStartingWar)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("This target is not hostile and the plan did not explicitly accept starting a war.");
                var healthy = map.mapPawns.FreeColonistsSpawned
                    .Where(p => !p.Downed && !p.InMentalState && p.health.summaryHealth.SummaryHealthPercent >= 0.85f)
                    .OrderByDescending(p => p.skills.GetSkill(SkillDefOf.Shooting).Level + p.skills.GetSkill(SkillDefOf.Melee).Level)
                    .ToList();
                int sendCount = Math.Min(5, healthy.Count - Math.Max(2, request.MinimumHomeDefenders));
                if (sendCount < 3)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("At least three healthy fighters are required after preserving home defenders.");
                var pawns = healthy.Take(sendCount).ToList();
                List<Thing> items = CaravanFormingUtility.AllReachableColonyItems(map);
                int totalFood = items.Where(IsTravelFood).Sum(t => t.stackCount);
                int totalMedicine = items.Where(IsMedicine).Sum(t => t.stackCount);
                int takeFood = Math.Min(sendCount * 12, Math.Max(0, totalFood - request.MinimumFoodAtHome));
                int takeMedicine = Math.Min(sendCount * 3, Math.Max(0, totalMedicine - request.MinimumMedicineAtHome));
                if (takeFood < sendCount * 8 || takeMedicine < sendCount)
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("The expedition lacks safe food or medicine reserves.");
                var transferables = new List<TransferableOneWay>();
                int foodAdded = AddByPredicate(transferables, items, IsTravelFood, takeFood);
                AddByPredicate(transferables, items, IsMedicine, takeMedicine);
                PlanetTile startingTile = CaravanExitMapUtility.BestExitTileToGoTo(destination.Tile, map);
                if (!startingTile.Valid) return ApiResult<StartTradeCaravanResponseDto>.Fail("No valid exit toward the target was found.");
                IntVec3 root = pawns.Aggregate(IntVec3.Zero, (sum, pawn) => sum + pawn.Position) / pawns.Count;
                if (!RCellFinder.TryFindClosestEdgeCellTo(root, map, out IntVec3 exitSpot))
                    return ApiResult<StartTradeCaravanResponseDto>.Fail("No reachable caravan exit was found.");
                if (!RCellFinder.TryFindRandomSpotJustOutsideColony(exitSpot, map, out IntVec3 meetingPoint)) meetingPoint = root;
                CaravanFormingUtility.StartFormingCaravan(pawns, new List<Pawn>(), Faction.OfPlayer, transferables, meetingPoint, exitSpot, startingTile, destination.Tile);
                PendingRoutes.Add(new PendingRoute
                {
                    PawnIds = new HashSet<int>(pawns.Select(p => p.thingIDNumber)),
                    PrisonerIds = new HashSet<int>(),
                    SettlementId = destination.ID,
                    Raid = true
                });
                return ApiResult<StartTradeCaravanResponseDto>.Ok(new StartTradeCaravanResponseDto
                {
                    Status = "forming raid expedition",
                    DestinationSettlementId = destination.ID,
                    DestinationName = destination.LabelCap,
                    DestinationTile = destination.Tile,
                    PawnCount = pawns.Count,
                    FoodCount = foodAdded
                });
            }
            catch (Exception ex)
            {
                LogApi.Error($"Raid caravan automation failed: {ex}");
                return ApiResult<StartTradeCaravanResponseDto>.Fail(ex.Message);
            }
        }

        private static int AddByPredicate(List<TransferableOneWay> result, List<Thing> source, Func<Thing, bool> predicate, int wanted)
        {
            int added = 0;
            foreach (Thing thing in source.Where(predicate).OrderByDescending(t => t.stackCount))
            {
                int count = Math.Min(thing.stackCount, wanted - added);
                if (count <= 0) break;
                AddTransferable(result, thing, count);
                added += count;
            }
            return added;
        }

        private static void AddTransferable(List<TransferableOneWay> result, Thing thing, int count)
        {
            var transferable = new TransferableOneWay();
            transferable.things.Add(thing);
            transferable.AdjustTo(count);
            result.Add(transferable);
        }

        private static bool IsTravelFood(Thing thing)
        {
            return !thing.IsForbidden(Faction.OfPlayer) && (thing.def.defName == "MealSurvivalPack" || thing.def.defName == "Pemmican");
        }

        private static bool IsMedicine(Thing thing)
        {
            return !thing.IsForbidden(Faction.OfPlayer) && thing.def.thingCategories != null
                && thing.def.thingCategories.Any(c => c.defName == "Medicine");
        }

        private static bool IsSaleGood(Thing thing, List<string> requested)
        {
            if (thing.IsForbidden(Faction.OfPlayer) || thing.MarketValue <= 5f || IsMedicine(thing))
                return false;
            string name = thing.def.defName;
            IEnumerable<string> selectedCategories = requested == null || requested.Count == 0
                ? (IEnumerable<string>)new[] { "drugs", "apparel", "art", "animal_products", "chemfuel", "precious", "beer", "travel_food", "raw_food" }
                : requested;
            var categories = new HashSet<string>(selectedCategories, StringComparer.OrdinalIgnoreCase);
            bool drugs = name == "Flake" || name == "Yayo" || name == "SmokeleafJoint";
            bool apparel = thing.def.thingCategories != null && thing.def.thingCategories.Any(c => c.defName.Contains("Apparel"));
            bool art = name.Contains("Sculpture");
            bool animal = name.Contains("Wool") || name.Contains("Leather") || name.Contains("Milk");
            bool fuel = name == "Chemfuel";
            bool precious = name == "Gold" || name == "Jade";
            bool beer = name == "Beer";
            bool caravanFood = name == "MealSurvivalPack" || name == "Pemmican";
            bool rawFood = name == "RawCorn" || name == "RawRice" || name == "RawPotatoes" || name == "AgaveFruit" || name == "Berries";
            return (categories.Contains("drugs") && drugs)
                || (categories.Contains("apparel") && apparel)
                || (categories.Contains("art") && art)
                || (categories.Contains("animal_products") && animal)
                || (categories.Contains("chemfuel") && fuel)
                || (categories.Contains("precious") && precious)
                || (categories.Contains("beer") && beer)
                || (categories.Contains("travel_food") && caravanFood)
                || (categories.Contains("raw_food") && rawFood);
        }
    }
}

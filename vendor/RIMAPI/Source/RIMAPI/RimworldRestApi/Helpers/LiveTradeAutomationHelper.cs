using System;
using System.Collections.Generic;
using System.Linq;
using HarmonyLib;
using RIMAPI.Core;
using RIMAPI.Models;
using RimWorld;
using Verse;

namespace RIMAPI.Helpers
{
    public static class LiveTradeAutomationHelper
    {
        public static ApiResult<List<LiveTraderDto>> GetOpportunities(int mapId)
        {
            try
            {
                Map map = MapHelper.GetMapByID(mapId);
                if (map == null) return ApiResult<List<LiveTraderDto>>.Fail($"Map {mapId} not found.");
                Pawn negotiator = BestNegotiator(map);
                bool hasConsole = map.listerBuildings.allBuildingsColonist.Any(b =>
                    b.def?.defName == "CommsConsole" && (b.TryGetComp<CompPowerTrader>()?.PowerOn ?? true));
                bool hasBeacon = map.listerBuildings.allBuildingsColonist.Any(b =>
                    b.def?.defName == "OrbitalTradeBeacon" && (b.TryGetComp<CompPowerTrader>()?.PowerOn ?? true));
                var result = new List<LiveTraderDto>();

                List<PassingShip> passing = Traverse.Create(map.passingShipManager)
                    .Field("passingShips").GetValue<List<PassingShip>>() ?? new List<PassingShip>();
                foreach (TradeShip ship in passing.OfType<TradeShip>().Where(s => !s.Departed && s.CanTradeNow))
                {
                    int ticks = Traverse.Create(ship).Field("ticksUntilDeparture").GetValue<int>();
                    int loadId = Traverse.Create(ship).Field("loadID").GetValue<int>();
                    result.Add(ToDto(
                        $"ship:{loadId}", ship.TraderName, ship.TraderKind, ship.Faction, true, null,
                        ticks, negotiator, hasConsole, hasBeacon, ship.Goods));
                }

                foreach (Pawn trader in map.mapPawns.AllPawnsSpawned.Where(p =>
                    p != null && !p.Dead && !p.Downed && p.TraderKind != null && p.CanTradeNow
                    && !p.HostileTo(Faction.OfPlayer)))
                {
                    result.Add(ToDto(
                        $"pawn:{trader.thingIDNumber}", trader.TraderName, trader.TraderKind, trader.Faction,
                        false, trader.thingIDNumber, 0, negotiator, hasConsole, hasBeacon,
                        trader.Goods));
                }
                return ApiResult<List<LiveTraderDto>>.Ok(result);
            }
            catch (Exception ex)
            {
                return ApiResult<List<LiveTraderDto>>.Fail(ex.Message);
            }
        }

        public static ApiResult<LiveTradeResponseDto> Execute(LiveTradeRequestDto request)
        {
            try
            {
                Map map = MapHelper.GetMapByID(request.MapId);
                if (map == null) return ApiResult<LiveTradeResponseDto>.Fail($"Map {request.MapId} not found.");
                if (GenHostility.AnyHostileActiveThreatToPlayer(map))
                    return ApiResult<LiveTradeResponseDto>.Fail("Trading is blocked during an active hostile threat.");
                Pawn negotiator = BestNegotiator(map);
                if (negotiator == null)
                    return ApiResult<LiveTradeResponseDto>.Fail("No conscious colonist capable of Social work can negotiate.");
                ITrader trader = ResolveTrader(map, request.TraderId);
                if (trader == null || !trader.CanTradeNow)
                    return ApiResult<LiveTradeResponseDto>.Fail("The selected trader is no longer available.");
                if (trader is TradeShip)
                {
                    bool console = map.listerBuildings.allBuildingsColonist.Any(b => b.def?.defName == "CommsConsole"
                        && (b.TryGetComp<CompPowerTrader>()?.PowerOn ?? true));
                    bool beacon = map.listerBuildings.allBuildingsColonist.Any(b => b.def?.defName == "OrbitalTradeBeacon"
                        && (b.TryGetComp<CompPowerTrader>()?.PowerOn ?? true));
                    if (!console || !beacon)
                        return ApiResult<LiveTradeResponseDto>.Fail("Orbital trade requires a powered comms console and orbital trade beacon.");
                }

                if (TradeSession.Active) TradeSession.Close();
                TradeSession.SetupWith(trader, negotiator, false);
                TradeDeal deal = TradeSession.deal;
                var response = new LiveTradeResponseDto
                {
                    TraderId = request.TraderId,
                    TraderName = trader.TraderName,
                    Negotiator = negotiator.LabelShortCap,
                };

                var saleCategories = new HashSet<string>((request.SaleCategories ?? new List<string>()).Select(s => s.ToLowerInvariant()));
                foreach (Tradeable row in deal.AllTradeables.Where(t => t.TraderWillTrade && t.CountHeldBy(Transactor.Colony) > 0))
                {
                    int surplus = SafeSaleCount(row, map, saleCategories);
                    if (surplus <= 0) continue;
                    row.ForceToDestination(surplus);
                    response.SoldUnits += surplus;
                    float price = row.GetPriceFor(TradeAction.PlayerSells);
                    response.ApproximateSaleValue += price * surplus;
                    response.Sold.Add($"{row.Label} x{surplus}");
                }
                deal.UpdateCurrencyCount();
                if (!deal.DoesTraderHaveEnoughSilver())
                {
                    foreach (Tradeable row in deal.AllTradeables.Where(t => t.CountToTransfer > 0)) row.ForceTo(0);
                    response.Sold.Clear();
                    response.SoldUnits = 0;
                    response.ApproximateSaleValue = 0;
                    deal.UpdateCurrencyCount();
                }

                float spend = 0f;
                foreach (string priority in request.PurchasePriorities ?? new List<string>())
                {
                    foreach (Tradeable row in deal.AllTradeables
                        .Where(t => t.TraderWillTrade && t.CountHeldBy(Transactor.Trader) > 0 && MatchesPriority(t, priority))
                        .OrderBy(t => t.GetPriceFor(TradeAction.PlayerBuys)))
                    {
                        float unitPrice = Math.Max(0.01f, row.GetPriceFor(TradeAction.PlayerBuys));
                        int affordable = Math.Max(0, (int)Math.Floor((request.MaximumSpend - spend) / unitPrice));
                        int wanted = Math.Min(row.CountHeldBy(Transactor.Trader), PurchaseTarget(priority, row));
                        int count = Math.Min(affordable, wanted);
                        if (count <= 0) continue;
                        row.ForceToSource(count);
                        deal.UpdateCurrencyCount();
                        Tradeable currency = deal.CurrencyTradeable;
                        if (currency != null && currency.CountPostDealFor(Transactor.Colony) < request.MinimumSilverReserve)
                        {
                            row.ForceTo(0);
                            deal.UpdateCurrencyCount();
                            continue;
                        }
                        spend += unitPrice * count;
                        response.BoughtUnits += count;
                        response.ApproximatePurchaseValue += unitPrice * count;
                        response.Bought.Add($"{row.Label} x{count}");
                    }
                }

                if (response.SoldUnits == 0 && response.BoughtUnits == 0)
                {
                    TradeSession.Close();
                    return ApiResult<LiveTradeResponseDto>.Fail("No safe requested trade matched this trader's stock and budget.");
                }
                if (!deal.DoesTraderHaveEnoughSilver())
                {
                    TradeSession.Close();
                    return ApiResult<LiveTradeResponseDto>.Fail("The trader cannot afford the selected sale.");
                }
                response.Executed = deal.TryExecute(out bool actuallyTraded) && actuallyTraded;
                TradeSession.Close();
                if (!response.Executed)
                    return ApiResult<LiveTradeResponseDto>.Fail("The normal trade deal rejected the transaction.");
                Messages.Message("Laya completed a normal trade with " + trader.TraderName + ".", MessageTypeDefOf.PositiveEvent, false);
                return ApiResult<LiveTradeResponseDto>.Ok(response);
            }
            catch (Exception ex)
            {
                if (TradeSession.Active) TradeSession.Close();
                LogApi.Error($"Live trade automation failed: {ex}");
                return ApiResult<LiveTradeResponseDto>.Fail(ex.Message);
            }
        }

        private static LiveTraderDto ToDto(string id, string name, TraderKindDef kind, Faction faction,
            bool orbital, int? pawnId, int ticks, Pawn negotiator, bool console, bool beacon, IEnumerable<Thing> stock)
        {
            return new LiveTraderDto
            {
                Id = id,
                Name = name,
                TraderKind = kind?.defName,
                Faction = faction?.Name,
                Orbital = orbital,
                PawnId = pawnId,
                TicksUntilDeparture = ticks,
                BestNegotiatorPawnId = negotiator?.thingIDNumber ?? 0,
                BestNegotiatorName = negotiator?.LabelShortCap,
                NegotiatorSocialSkill = negotiator?.skills?.GetSkill(SkillDefOf.Social)?.Level ?? 0,
                HasPoweredCommsConsole = console,
                HasPoweredOrbitalBeacon = beacon,
                Stock = (stock ?? Enumerable.Empty<Thing>()).Where(t => t?.def != null).Take(120).Select(t => new LiveTradeItemDto
                {
                    DefName = t.def.defName,
                    Label = t.LabelCap,
                    Count = t.stackCount,
                    MarketValue = t.MarketValue,
                    Humanlike = t is Pawn human && human.RaceProps.Humanlike,
                    Animal = t is Pawn animal && animal.RaceProps.Animal,
                    Health = t is Pawn patient ? patient.health?.summaryHealth?.SummaryHealthPercent ?? 0f : 1f,
                    Skills = t is Pawn recruit && recruit.RaceProps.Humanlike && recruit.skills != null
                        ? recruit.skills.skills.OrderByDescending(skill => skill.Level)
                            .Take(5).Select(skill => $"{skill.def.defName}:{skill.Level}:{skill.passion}").ToList()
                        : new List<string>(),
                    Categories = t.def.thingCategories?.Select(c => c.defName).ToList() ?? new List<string>(),
                }).ToList(),
            };
        }

        private static Pawn BestNegotiator(Map map)
        {
            return map.mapPawns.FreeColonistsSpawned
                .Where(p => !p.Dead && !p.Downed && !p.InMentalState && p.health.capacities.CanBeAwake
                    && p.skills != null && !p.WorkTypeIsDisabled(WorkTypeDefOf.Warden))
                .OrderByDescending(p => p.GetStatValue(StatDefOf.TradePriceImprovement))
                .ThenByDescending(p => p.skills.GetSkill(SkillDefOf.Social).Level)
                .FirstOrDefault();
        }

        private static ITrader ResolveTrader(Map map, string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            string[] parts = id.Split(':');
            if (parts.Length != 2 || !int.TryParse(parts[1], out int numeric)) return null;
            if (parts[0] == "pawn")
                return map.mapPawns.AllPawnsSpawned.FirstOrDefault(p => p.thingIDNumber == numeric && p.TraderKind != null);
            if (parts[0] == "ship")
            {
                List<PassingShip> passing = Traverse.Create(map.passingShipManager).Field("passingShips").GetValue<List<PassingShip>>();
                return passing?.OfType<TradeShip>().FirstOrDefault(s => Traverse.Create(s).Field("loadID").GetValue<int>() == numeric);
            }
            return null;
        }

        private static int SafeSaleCount(Tradeable row, Map map, HashSet<string> categories)
        {
            if (categories.Count == 0 || row.ThingDef == null || row.IsCurrency) return 0;
            string text = (row.ThingDef.defName + " " + row.Label + " "
                + string.Join(" ", row.ThingDef.thingCategories?.Select(c => c.defName) ?? Enumerable.Empty<string>())).ToLowerInvariant();
            bool selected = categories.Any(category =>
                (category == "drugs" && new[] { "flake", "yayo", "smokeleafjoint", "beer", "ambrosia" }
                    .Any(text.Contains))
                || (category == "animals" && row.ThingDef.race?.Animal == true)
                || (category == "food" && (text.Contains("food") || text.Contains("meal")
                    || text.Contains("rice") || text.Contains("corn") || text.Contains("potato")))
                || (category == "art" && text.Contains("sculpture"))
                || (category == "apparel" && row.ThingDef.IsApparel)
                || (category == "weapons" && row.ThingDef.IsWeapon)
                || (category == "leather" && (text.Contains("leather") || text.Contains("wool")
                    || text.Contains("cloth")))
                || (category == "gold" && (text.Contains("gold") || text.Contains("jade"))));
            if (!selected) return 0;
            int total = row.CountHeldBy(Transactor.Colony);
            int reserve = 0;
            if (text.Contains("food") || text.Contains("meal") || text.Contains("meat")) reserve = Math.Max(20, map.mapPawns.FreeColonistsSpawnedCount * 18);
            else if (text.Contains("medicine")) reserve = 12;
            else if (text.Contains("component")) reserve = text.Contains("advanced") ? 4 : 12;
            else if (text.Contains("steel")) reserve = 350;
            else if (text.Contains("wood")) reserve = 250;
            else if (row.ThingDef.IsWeapon) reserve = 1;
            else if (row.ThingDef.race?.Animal == true) reserve = 2;
            return Math.Max(0, total - reserve);
        }

        private static bool MatchesPriority(Tradeable row, string priority)
        {
            if (row.ThingDef == null) return false;
            string wanted = (priority ?? "").ToLowerInvariant().Replace("_", "");
            string text = (row.ThingDef.defName + row.Label + string.Join("", row.ThingDef.thingCategories?.Select(c => c.defName) ?? Enumerable.Empty<string>())).ToLowerInvariant().Replace("_", "");
            if (wanted == "advancedcomponents") return text.Contains("componentadvanced");
            if (wanted == "components") return text.Contains("component") && !text.Contains("advanced");
            if (wanted == "medicine") return text.Contains("medicine") || text.Contains("neutroamine");
            if (wanted == "slaves") return row.ThingDef.race?.Humanlike == true;
            if (wanted == "livestock") return row.ThingDef.race?.Animal == true;
            if (wanted == "food") return text.Contains("food") || text.Contains("meal");
            if (wanted == "weapons") return row.ThingDef.IsWeapon;
            if (wanted == "armor") return text.Contains("armor") || text.Contains("helmet") || text.Contains("vest");
            return text.Contains(wanted);
        }

        private static int PurchaseTarget(string priority, Tradeable row)
        {
            string value = (priority ?? "").ToLowerInvariant();
            if (value.Contains("medicine") || value.Contains("component")) return 20;
            if (value.Contains("food")) return 50;
            if (value.Contains("slaves") || value.Contains("livestock")) return 1;
            if (row.ThingDef?.IsWeapon == true || value.Contains("armor")) return 2;
            return 10;
        }
    }
}

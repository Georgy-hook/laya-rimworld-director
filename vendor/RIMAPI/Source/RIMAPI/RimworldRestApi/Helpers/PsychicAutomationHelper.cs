using System;
using System.Collections.Generic;
using System.Linq;
using RIMAPI.Core;
using RIMAPI.Models;
using RimWorld;
using Verse;

namespace RIMAPI.Helpers
{
    public static class PsychicAutomationHelper
    {
        public static List<PsycastDto> GetPsycasts(Pawn pawn)
        {
            if (pawn?.abilities?.AllAbilitiesForReading == null)
                return new List<PsycastDto>();
            return pawn.abilities.AllAbilitiesForReading
                .Where(a => a?.def != null && a.def.IsPsycast)
                .Select(a =>
                {
                    AcceptanceReport report = a.CanCast;
                    return new PsycastDto
                    {
                        DefName = a.def.defName,
                        Label = a.def.LabelCap,
                        Description = a.def.description,
                        Level = a.def.level,
                        IsPsycast = a.def.IsPsycast,
                        Hostile = a.def.hostile || a.def.ai_IsOffensive,
                        TargetRequired = a.def.targetRequired,
                        CanCast = report.Accepted,
                        DisabledReason = report.Accepted ? null : report.Reason,
                        Range = a.verb?.verbProps?.range ?? 0f,
                        EffectRadius = a.def.EffectRadius,
                        PsyfocusCost = a.def.PsyfocusCost,
                        EntropyGain = a.def.EntropyGain,
                        CooldownTicksRemaining = a.CooldownTicksRemaining,
                        RemainingCharges = a.UsesCharges ? a.RemainingCharges : -1,
                        Mod = a.def.modContentPack?.Name,
                    };
                })
                .OrderBy(a => a.Level)
                .ThenBy(a => a.Label)
                .ToList();
        }

        public static ApiResult<bool> QueuePsycast(
            Pawn caster,
            string abilityDefName,
            Pawn targetPawn,
            IntVec3? targetCell)
        {
            try
            {
                if (caster == null || caster.Dead || caster.Downed)
                    return ApiResult<bool>.Fail("The selected psycaster is unavailable.");
                Ability ability = caster.abilities?.AllAbilitiesForReading
                    ?.FirstOrDefault(a => a?.def?.defName == abilityDefName && a.def.IsPsycast);
                if (ability == null)
                    return ApiResult<bool>.Fail($"Psycast {abilityDefName} is not known by this pawn.");
                AcceptanceReport castReport = ability.CanCast;
                if (!castReport.Accepted)
                    return ApiResult<bool>.Fail(castReport.Reason ?? "The psycast cannot be used now.");

                LocalTargetInfo target = targetPawn != null
                    ? (LocalTargetInfo)targetPawn
                    : targetCell.HasValue ? (LocalTargetInfo)targetCell.Value : (LocalTargetInfo)caster;
                if (ability.def.targetRequired && !ability.CanApplyOn(target))
                    return ApiResult<bool>.Fail("The selected target is invalid for this psycast.");

                Pawn_PsychicEntropyTracker entropy = caster.psychicEntropy;
                float focusCost = ability.FinalPsyfocusCost(target);
                if (entropy != null)
                {
                    if (entropy.CurrentPsyfocus + 0.0001f < focusCost)
                        return ApiResult<bool>.Fail("Insufficient psyfocus for the selected psycast.");
                    if (entropy.WouldOverflowEntropy(ability.def.EntropyGain))
                        return ApiResult<bool>.Fail("The psycast would exceed the safe neural heat limit.");
                }

                if (caster.drafter != null && ability.def.disableGizmoWhileUndrafted)
                    caster.drafter.Drafted = true;
                ability.QueueCastingJob(target, target);
                return ApiResult<bool>.Ok(true);
            }
            catch (Exception ex)
            {
                return ApiResult<bool>.Fail(ex.Message);
            }
        }
    }
}

using System;
using System.Linq;
using RIMAPI.Core;
using RIMAPI.Helpers;
using RIMAPI.Models;
using RimWorld;
using Verse;
using Verse.AI;

namespace RIMAPI.Services
{
    public class PawnJobService : IPawnJobService
    {
        public PawnJobService() { }

        public ApiResult AssignJob(PawnJobRequestDto request)
        {
            try
            {
                Pawn pawn = PawnHelper.FindPawnById(request.PawnId);
                if (pawn == null)
                {
                    return ApiResult.Fail($"Pawn not found: {request.PawnId}");
                }

                JobDef jobDef = DefDatabase<JobDef>.GetNamedSilentFail(request.JobDef);
                if (jobDef == null)
                {
                    return ApiResult.Fail($"JobDef not found: {request.JobDef}");
                }

                LocalTargetInfo target = LocalTargetInfo.Invalid;

                if (request.TargetThingId.HasValue)
                {
                    Thing thing = null;
                    foreach (Map map in Find.Maps)
                    {
                        thing = map.listerThings.AllThings
                            .FirstOrDefault(t => t.thingIDNumber == request.TargetThingId.Value);
                        if (thing != null) break;
                    }
                    if (thing == null)
                    {
                        return ApiResult.Fail($"Target thing not found: {request.TargetThingId}");
                    }
                    target = thing;
                }
                else if (request.TargetPosition != null)
                {
                    target = new IntVec3(
                        request.TargetPosition.X, 0, request.TargetPosition.Z);
                }

                Job job;
                if (request.TargetThingIdB.HasValue)
                {
                    Thing thingB = null;
                    foreach (Map map in Find.Maps)
                    {
                        thingB = map.listerThings.AllThings
                            .FirstOrDefault(t => t.thingIDNumber == request.TargetThingIdB.Value);
                        if (thingB != null) break;
                    }
                    if (thingB == null)
                    {
                        return ApiResult.Fail($"Secondary target thing not found: {request.TargetThingIdB}");
                    }
                    job = JobMaker.MakeJob(jobDef, target, thingB);
                }
                else
                {
                    job = JobMaker.MakeJob(jobDef, target);
                }
                bool success = pawn.jobs.TryTakeOrderedJob(job);
                if (!success)
                {
                    return ApiResult.Fail($"Pawn {request.PawnId} could not accept job {request.JobDef}");
                }
                return ApiResult.Ok();
            }
            catch (Exception ex)
            {
                return ApiResult.Fail(ex.Message);
            }
        }

        public ApiResult AssignTendJob(MedicalTendRequestDto request)
        {
            try
            {
                Pawn patient = PawnHelper.FindPawnById(request.PatientPawnId);
                if (patient == null)
                {
                    return ApiResult.Fail($"Patient pawn not found: {request.PatientPawnId}");
                }

                Pawn doctor;
                if (request.DoctorPawnId.HasValue)
                {
                    doctor = PawnHelper.FindPawnById(request.DoctorPawnId.Value);
                    if (doctor == null)
                    {
                        return ApiResult.Fail($"Doctor pawn not found: {request.DoctorPawnId}");
                    }
                }
                else
                {
                    // Find the best available doctor on the same map
                    doctor = patient.Map?.mapPawns.FreeColonists
                        .Where(p => p != patient && !p.Downed && !p.Dead)
                        .OrderByDescending(p => p.skills?.GetSkill(SkillDefOf.Medicine)?.Level ?? 0)
                        .FirstOrDefault();

                    if (doctor == null)
                    {
                        return ApiResult.Fail("No available doctor found on the map");
                    }
                }

                bool success = PawnHelper.AssignTendJob(doctor, patient);
                if (!success)
                {
                    return ApiResult.Fail("Doctor could not accept tend job");
                }
                return ApiResult.Ok();
            }
            catch (Exception ex)
            {
                return ApiResult.Fail(ex.Message);
            }
        }

        public ApiResult AssignBedRest(MedicalBedRestRequestDto request)
        {
            try
            {
                Pawn patient = PawnHelper.FindPawnById(request.PatientPawnId);
                if (patient == null)
                {
                    return ApiResult.Fail($"Patient pawn not found: {request.PatientPawnId}");
                }

                Building_Bed bed = null;
                if (request.BedBuildingId.HasValue)
                {
                    Building building = BuildingHelper.FindBuildingByID(request.BedBuildingId.Value);
                    bed = building as Building_Bed;
                    if (bed == null)
                    {
                        return ApiResult.Fail($"Bed not found: {request.BedBuildingId}");
                    }
                }

                bool success = PawnHelper.AssignBedRest(patient, bed);
                if (!success)
                {
                    return ApiResult.Fail("Patient could not be assigned to bed rest");
                }
                return ApiResult.Ok();
            }
            catch (Exception ex)
            {
                return ApiResult.Fail(ex.Message);
            }
        }

        public ApiResult AssignFeedJob(MedicalFeedRequestDto request)
        {
            try
            {
                Pawn patient = PawnHelper.FindPawnById(request.PatientPawnId);
                if (patient == null)
                {
                    return ApiResult.Fail($"Patient pawn not found: {request.PatientPawnId}");
                }

                Pawn feeder = request.FeederPawnId.HasValue
                    ? PawnHelper.FindPawnById(request.FeederPawnId.Value)
                    : patient.Map?.mapPawns.FreeColonists
                        .Where(p => p != patient && !p.Downed && !p.Dead)
                        .OrderByDescending(p => p.skills?.GetSkill(SkillDefOf.Medicine)?.Level ?? 0)
                        .FirstOrDefault();
                if (feeder == null)
                {
                    return ApiResult.Fail("No available feeder found on the map");
                }

                WorkGiverDef giverDef = DefDatabase<WorkGiverDef>.GetNamedSilentFail(
                    patient.RaceProps?.Animal == true ? "DoctorFeedAnimals" : "FeedPatient"
                );
                WorkGiver_Scanner scanner = giverDef?.Worker as WorkGiver_Scanner;
                Job job = scanner?.JobOnThing(feeder, patient, true);
                if (job == null && patient.RaceProps?.Animal == true)
                {
                    giverDef = DefDatabase<WorkGiverDef>.GetNamedSilentFail("HandlingFeedPatientAnimals");
                    scanner = giverDef?.Worker as WorkGiver_Scanner;
                    job = scanner?.JobOnThing(feeder, patient, true);
                }
                if (job == null)
                {
                    return ApiResult.Fail("No valid patient-feeding job could be created");
                }
                if (!feeder.jobs.TryTakeOrderedJob(job))
                {
                    return ApiResult.Fail("Feeder could not accept the patient-feeding job");
                }
                return ApiResult.Ok();
            }
            catch (Exception ex)
            {
                return ApiResult.Fail(ex.Message);
            }
        }
    }
}

using System.Collections.Generic;

namespace RIMAPI.Models
{
    public class CombatStateDto
    {
        public int MapId { get; set; }
        public int GameTick { get; set; }
        public List<CombatPawnDto> Colonists { get; set; } = new List<CombatPawnDto>();
        public List<CombatPawnDto> Hostiles { get; set; } = new List<CombatPawnDto>();
        public List<CombatPawnDto> Prisoners { get; set; } = new List<CombatPawnDto>();
        public List<CombatWeaponDto> AvailableWeapons { get; set; } = new List<CombatWeaponDto>();
    }

    public class CombatPawnDto
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string KindDef { get; set; }
        public string Faction { get; set; }
        public bool IsColonist { get; set; }
        public bool IsHostile { get; set; }
        public bool IsDrafted { get; set; }
        public bool IsDowned { get; set; }
        public bool IsDead { get; set; }
        public float Health { get; set; }
        public PositionDto Position { get; set; }
        public int ShootingSkill { get; set; }
        public int MeleeSkill { get; set; }
        public string WeaponDef { get; set; }
        public string WeaponLabel { get; set; }
        public bool HasRangedWeapon { get; set; }
        public string CurrentJob { get; set; }
        public float DistanceToNearestOpponent { get; set; }
        public string Gender { get; set; }
        public int BiologicalAge { get; set; }
        public float BleedingRate { get; set; }
        public float Consciousness { get; set; }
        public float Moving { get; set; }
        public float Manipulation { get; set; }
        public float Sight { get; set; }
        public float Pain { get; set; }
        public float MarketValue { get; set; }
        public int SocialSkill { get; set; }
        public int MedicineSkill { get; set; }
        public int ConstructionSkill { get; set; }
        public int AnimalsSkill { get; set; }
        public int IntellectualSkill { get; set; }
        public int CookingSkill { get; set; }
        public bool Recruitable { get; set; }
        public bool FactionPermanentEnemy { get; set; }
        public bool FactionCanGiveGoodwill { get; set; }
        public int FactionGoodwill { get; set; }
        public List<string> Traits { get; set; } = new List<string>();
        public List<string> TopSkills { get; set; } = new List<string>();
        public List<string> HealthConditions { get; set; } = new List<string>();
    }

    public class CombatWeaponDto
    {
        public int Id { get; set; }
        public string DefName { get; set; }
        public string Label { get; set; }
        public bool IsRanged { get; set; }
        public bool IsForbidden { get; set; }
        public float MarketValue { get; set; }
        public PositionDto Position { get; set; }
    }
}

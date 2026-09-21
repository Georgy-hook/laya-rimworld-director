using RIMAPI.Core;
using RIMAPI.Models;

namespace RIMAPI.Services
{
    public interface ICombatService
    {
        ApiResult<CombatStateDto> GetCombatState(int mapId);
    }
}

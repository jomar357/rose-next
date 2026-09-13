#pragma once

// Tiny table/record adapters exercise the production accumulation helper without
// booting the game server or requiring a developer's private data directory.
namespace ItemBonusFixtures {
enum { AT_MAX = 120, AT_MONEY = 40, AT_WEIGHT = 27 };
enum { EQUIP_IDX_FACE_ITEM, EQUIP_IDX_HELMET, EQUIP_IDX_ARMOR, EQUIP_IDX_KNAPSACK,
    EQUIP_IDX_GAUNTLET, EQUIP_IDX_BOOTS, EQUIP_IDX_WEAPON_R, EQUIP_IDX_WEAPON_L,
    EQUIP_IDX_NECKLACE, EQUIP_IDX_RING, EQUIP_IDX_EARRING, EQUIP_COUNT };
enum { ITEM_TYPE_FACE_ITEM, ITEM_TYPE_HELMET, ITEM_TYPE_ARMOR, ITEM_TYPE_KNAPSACK,
    ITEM_TYPE_GAUNTLET, ITEM_TYPE_BOOTS, ITEM_TYPE_WEAPON, ITEM_TYPE_SUBWPN,
    ITEM_TYPE_JEWEL, ITEM_TYPE_RIDE_PART, TYPE_COUNT, MAX_RIDING_PART = 5 };
struct BonusRow { short ability[2] = {}, value[2] = {}, required_union[2] = {}; };
inline BonusRow items[TYPE_COUNT][8], gems[8];
struct tagITEM {
    int no = 0, life = 0, gem = 0;
    bool appraised = false, socket = false;
    int GetItemNO() { return no; }
    int GetLife() { return life; }
    int GetGemNO() { return gem; }
    bool IsAppraisal() { return appraised; }
    bool HasSocket() { return socket; }
};
#define GEMITEM_ADD_DATA_TYPE(I, C) gems[I].ability[C]
#define GEMITEM_ADD_DATA_VALUE(I, C) gems[I].value[C]
#define ITEM_NEED_UNION(T, I, C) items[T][I].required_union[C]
#define ITEM_ADD_DATA_TYPE(T, I, C) items[T][I].ability[C]
#define ITEM_ADD_DATA_VALUE(T, I, C) items[T][I].value[C]
#include "../../sho_gameserver/src/mounted_item_bonuses.h"
#undef GEMITEM_ADD_DATA_TYPE
#undef GEMITEM_ADD_DATA_VALUE
#undef ITEM_NEED_UNION
#undef ITEM_ADD_DATA_TYPE
#undef ITEM_ADD_DATA_VALUE

inline void run() {
    int values[AT_MAX] = {};
    tagITEM equip[EQUIP_COUNT] = {}, riding[MAX_RIDING_PART] = {};
    equip[EQUIP_IDX_ARMOR] = {1, 100};
    items[ITEM_TYPE_ARMOR][1] = {{10, AT_WEIGHT}, {50, 80}, {0, 0}};
    riding[0] = {1, 100, 1, true, false};
    items[ITEM_TYPE_RIDE_PART][1] = {{10, 11}, {7, 9}, {0, 2}};
    gems[1] = {{10, 12}, {3, 4}, {0, 0}};
    values[53] = 13; // learned passive, outside the equipment reset range
    accumulate_equipment_bonuses(equip, riding, 1, values, true);
    expect(values[10] == 10 && values[11] == 0 && values[12] == 4,
        "mounted part bonuses and appraised gems, normal stat bonus removed");
    expect(values[AT_WEIGHT] == 80 && values[53] == 13, "weight and learned passives retained");
    expect(riding[0].life == 100 && equip[EQUIP_IDX_ARMOR].life == 100, "bonus input items unchanged");
    std::fill(values, values + AT_MAX, 0);
    riding[0].appraised = false;
    accumulate_equipment_bonuses(equip, riding, 2, values, true);
    expect(values[10] == 7 && values[11] == 9 && values[12] == 0,
        "union eligibility and hidden gem exclusion");
    std::fill(values, values + AT_MAX, 0);
    riding[0].socket = true;
    accumulate_equipment_bonuses(equip, riding, 2, values, true);
    expect(values[10] == 10 && values[12] == 4, "socket gems apply without appraisal");
    std::fill(values, values + AT_MAX, 0);
    riding[0].life = 0;
    accumulate_equipment_bonuses(equip, riding, 2, values, true);
    expect(values[10] == 0 && values[12] == 0, "broken or fuel-exhausted parts lose bonuses");
    std::fill(values, values + AT_MAX, 0);
    accumulate_equipment_bonuses(equip, riding, 2, values, false);
    expect(values[10] == 50 && values[AT_WEIGHT] == 80, "on-foot accumulation unchanged");
}
} // namespace ItemBonusFixtures

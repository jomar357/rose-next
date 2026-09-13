#pragma once

// Caller provides value storage. Shared by live ability updates and the preview;
// tagITEM is copied because the legacy accessors are not const-qualified.
inline void accumulate_item_bonuses(tagITEM item, short type, int user_union, int* values) {
    if (item.GetItemNO() < 1 || item.GetLife() < 1)
        return;
    if (item.GetGemNO() && (item.IsAppraisal() || item.HasSocket())) {
        for (int i = 0; i < 2; ++i) {
            const short ability = GEMITEM_ADD_DATA_TYPE(item.GetGemNO(), i);
            if (ability >= 0 && ability < AT_MAX)
                values[ability] += static_cast<short>(GEMITEM_ADD_DATA_VALUE(item.GetGemNO(), i));
        }
    }
    for (int i = 0; i < 2; ++i) {
        const short required_union = ITEM_NEED_UNION(type, item.GetItemNO(), i);
        if (required_union && required_union != user_union)
            continue;
        const short ability = ITEM_ADD_DATA_TYPE(type, item.GetItemNO(), i);
        if (ability >= 0 && ability < AT_MAX)
            values[ability] += static_cast<short>(ITEM_ADD_DATA_VALUE(type, item.GetItemNO(), i));
    }
}

inline void accumulate_equipment_bonuses(const tagITEM* equipment, const tagITEM* riding,
    int user_union, int* values, bool mounted) {
    const short slots[] = {EQUIP_IDX_FACE_ITEM, EQUIP_IDX_HELMET, EQUIP_IDX_ARMOR,
        EQUIP_IDX_KNAPSACK, EQUIP_IDX_GAUNTLET, EQUIP_IDX_BOOTS, EQUIP_IDX_WEAPON_R,
        EQUIP_IDX_WEAPON_L, EQUIP_IDX_NECKLACE, EQUIP_IDX_RING, EQUIP_IDX_EARRING};
    const short types[] = {ITEM_TYPE_FACE_ITEM, ITEM_TYPE_HELMET, ITEM_TYPE_ARMOR,
        ITEM_TYPE_KNAPSACK, ITEM_TYPE_GAUNTLET, ITEM_TYPE_BOOTS, ITEM_TYPE_WEAPON,
        ITEM_TYPE_SUBWPN, ITEM_TYPE_JEWEL, ITEM_TYPE_JEWEL, ITEM_TYPE_JEWEL};
    for (int i = 0; i < sizeof(slots) / sizeof(slots[0]); ++i)
        accumulate_item_bonuses(equipment[slots[i]], types[i], user_union, values);
    if (mounted) {
        const int weight = values[AT_WEIGHT];
        std::fill(values, values + AT_MONEY, 0);
        values[AT_WEIGHT] = weight;
        for (int i = 0; i < MAX_RIDING_PART; ++i)
            accumulate_item_bonuses(riding[i], ITEM_TYPE_RIDE_PART, user_union, values);
    }
}

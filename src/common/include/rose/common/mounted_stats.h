#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace Rose::Tuning {

enum Field : uint8_t {
    Type = 1, Defence = 2, Resistance = 4, Fuel = 8,
    Speed = 16, Attack = 32, AttackSpeed = 64
};

// These helpers retain the server's float expressions and intermediate short
// conversions. They are also used by the live mounted-stat paths.
inline int attack_power(int level, int con, int weapon, int bonus) {
    return level * 3 + con + weapon + bonus;
}

inline int attack_speed(int weapon_speed, int bonus) {
    return static_cast<int>(std::floor(1500.f / (weapon_speed + 5))) + bonus;
}

inline float move_speed(bool working, int legs, int engine, int bonus, bool overweight) {
    float speed = working ? legs * engine / 10.f : 200.f;
    speed += bonus;
    if (overweight && speed > 300.f)
        speed = 300.f;
    return speed;
}

inline short defence(int armour, int grades, int str, int level, int bonus) {
    return static_cast<short>(static_cast<int>(
        (armour + grades + (str + 5) * 0.35f + (level + 15) * 0.7f) * 0.8f) + bonus);
}

inline short resistance(int armour, int grades, int intelligence, int level, int bonus) {
    short value = static_cast<short>(static_cast<int>(
        armour + grades + (intelligence + 5) * 0.6f + (level + 15) * 0.8f));
    return static_cast<short>(value + bonus);
}

inline short passive(short value, int flat, short rate) {
    return static_cast<short>(value + flat + static_cast<short>(value * rate / 100.f));
}

inline int fuel_after_mount(int life, int cost, bool driving) {
    return driving ? life : (life > cost ? life - cost : 0);
}

inline short weight_capacity(int level, int str, int bonus, int flat, short rate) {
    short value = static_cast<short>(1100 + level * 5 + str * 6);
    value = static_cast<short>(value + bonus);
    return passive(value, flat, rate);
}

// Table lookups and effect filtering happen at the server boundary. No world
// object, mutable inventory, network connection, or global state enters here.
struct MountedStatsInput {
    uint8_t vehicle_type = 0; // 1 cart, 2 castle gear
    bool complete = false;
    bool engine_present = false;
    bool weapon_present = false;
    bool engine_working = false;
    bool legs_working = false;
    bool overweight = false;
    bool base_overweight = false; // weight bracket at the initial ability update
    int level = 0, str = 0, intelligence = 0, con = 0;
    int armour_def = 0, grade_def = 0, armour_res = 0, grade_res = 0;
    int bonus_def = 0, bonus_res = 0, bonus_attack = 0;
    int bonus_speed = 0, bonus_attack_speed = 0;
    int passive_def = 0, passive_res = 0, shield_def = 0;
    short passive_def_rate = 0, passive_res_rate = 0, shield_def_rate = 0;
    int engine_speed = 0, legs_speed = 0, weapon_attack = 0, weapon_speed = 0;
    int fuel_cost = 0;
    int adjust_def = 0, adjust_res = 0, adjust_speed = 0;
    int adjust_attack = 0, adjust_attack_speed = 0;
    int server_attack = 0, server_attack_speed = 0;
};

struct MountedStatsResult {
    uint8_t vehicle_type = 0, valid_fields = 0;
    int defence = 0, resistance = 0, fuel = 0, speed = 0;
    uint32_t attack = 0;
    int attack_speed = 0;
};

inline MountedStatsResult calculate(const MountedStatsInput& in) {
    MountedStatsResult out;
    out.vehicle_type = in.vehicle_type;
    if (!in.vehicle_type)
        return out;
    out.valid_fields = Type;
    if (in.engine_present) {
        out.valid_fields |= Fuel;
        out.fuel = in.fuel_cost;
    }
    if (!in.complete)
        return out;
    out.valid_fields |= Defence | Resistance | Speed;
    short def = defence(in.armour_def, in.grade_def, in.str, in.level, in.bonus_def);
    def = passive(def, in.passive_def, in.passive_def_rate);
    def = passive(def, in.shield_def, in.shield_def_rate);
    short res = resistance(in.armour_res, in.grade_res, in.intelligence, in.level, in.bonus_res);
    res = passive(res, in.passive_res, in.passive_res_rate);
    out.defence = (std::max)(10, def + in.adjust_def);
    out.resistance = (std::max)(10, res + in.adjust_res);
    const int base_speed = static_cast<int>(std::floor(move_speed(
        in.engine_working && in.legs_working, in.legs_speed, in.engine_speed,
        in.bonus_speed, in.base_overweight)));
    out.speed = static_cast<uint16_t>(base_speed + in.adjust_speed);
    if (in.overweight && out.speed > 300)
        out.speed = 300;
    if (in.weapon_present && in.weapon_speed + 5 > 0) {
        out.valid_fields |= Attack | AttackSpeed;
        out.attack = static_cast<uint32_t>(attack_power(in.level, in.con,
            in.weapon_attack, in.bonus_attack) + in.adjust_attack) + in.server_attack;
        // The live path stores base speed in uint16_t, then adds effects and
        // server configuration through two uint16_t-returning accessors.
        out.attack_speed = static_cast<uint16_t>(static_cast<uint16_t>(
            attack_speed(in.weapon_speed, in.bonus_attack_speed)) + in.adjust_attack_speed);
        out.attack_speed = static_cast<uint16_t>(out.attack_speed + in.server_attack_speed);
    }
    return out;
}

} // namespace Rose::Tuning

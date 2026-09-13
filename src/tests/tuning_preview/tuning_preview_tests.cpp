#include "rose/common/tuning_preview_cache.h"
#include "rose/network/packets/packet_data_generated.h"

#include <cstdlib>
#include <cstring>
#include <iostream>

using namespace Rose::Tuning;

void expect(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAILED: " << message << '\n';
        std::exit(1);
    }
}

#include "item_bonus_fixtures.h"

MountedStatsInput fixture() {
    MountedStatsInput in;
    in.vehicle_type = 1;
    in.complete = in.engine_present = in.weapon_present = true;
    in.engine_working = in.legs_working = true;
    in.level = 100;
    in.str = 100; in.intelligence = 50; in.con = 80;
    in.armour_def = 200; in.grade_def = 15;
    in.armour_res = 100; in.grade_res = 10;
    in.bonus_def = 20; in.bonus_res = 5;
    in.weapon_attack = 200; in.bonus_attack = 30;
    in.weapon_speed = 10; in.bonus_attack_speed = 12;
    in.engine_speed = 120; in.legs_speed = 60; in.bonus_speed = 25;
    in.fuel_cost = 3;
    return in;
}

// Independent pre-extraction expressions, including the legacy short stores.
// Sweep rounding boundaries rather than merely asserting our helpers agree.
void legacy_formula_regressions() {
    for (int level : {1, 50, 100, 199, 240}) {
        for (int attribute : {0, 1, 49, 100, 299, 300, 437}) {
            for (int grade : {0, 1, 17, 100}) {
                auto in = fixture();
                in.level = level; in.str = in.intelligence = in.con = attribute;
                in.grade_def = in.grade_res = grade;
                in.passive_def = 7; in.passive_def_rate = 23;
                in.shield_def = 9; in.shield_def_rate = 11;
                in.passive_res = 3; in.passive_res_rate = 37;
                const auto before = in;
                const auto out = calculate(in);
                short def = (int)((200 + grade + (attribute + 5) * 0.35f
                    + (level + 15) * 0.7f) * 0.8f) + 20;
                def += 7 + (short)(def * 23 / 100.f);
                def += 9 + (short)(def * 11 / 100.f);
                short res = (int)(100 + grade + (attribute + 5) * 0.6f + (level + 15) * 0.8f);
                res += 5;
                res += 3 + (short)(res * 37 / 100.f);
                expect(out.defence == def && out.resistance == res, "legacy DEF/RES parity");
                expect(out.attack == level * 3 + attribute + 200 + 30, "legacy mounted ATK parity");
                short capacity = 1100 + level * 5 + attribute * 6;
                capacity += 80;
                short weight_passive = 13 + (short)(capacity * 17 / 100.f);
                capacity += weight_passive;
                expect(weight_capacity(level, attribute, 80, 13, 17) == capacity,
                    "legacy carrying capacity parity");
                expect(std::memcmp(&in, &before, sizeof(in)) == 0, "calculator leaves input unchanged");
            }
        }
    }
    for (int weapon = 0; weapon < 100; ++weapon) {
        auto in = fixture(); in.weapon_speed = weapon;
        expect(calculate(in).attack_speed == (int)std::floor(1500.f / (weapon + 5)) + 12,
            "reciprocal ASPD rounding");
    }
}

void scenarios() {
    auto in = fixture();
    auto out = calculate(in);
    expect(out.valid_fields == 127 && out.attack == 610 && out.speed == 745
        && out.attack_speed == 112 && out.fuel == 3, "complete cart");
    in.vehicle_type = 2;
    expect(calculate(in).vehicle_type == 2 && calculate(in).attack == 610, "castle gear");
    in.adjust_def = -10000; in.adjust_res = -10000;
    expect(calculate(in).defence == 10 && calculate(in).resistance == 10, "surviving debuff minimums");
    in.adjust_attack = 24; in.server_attack = 37;
    in.adjust_attack_speed = -7; in.server_attack_speed = 15;
    in.adjust_speed = 80;
    expect(calculate(in).attack == 671 && calculate(in).attack_speed == 120
        && calculate(in).speed == 825, "surviving effects and server bonuses");
    in.overweight = true;
    expect(calculate(in).speed == 300, "weight cap after effects");
    in.base_overweight = true;
    in.overweight = false;
    expect(calculate(in).speed == 380, "initial weight cap retained when final bracket drops");
    in.base_overweight = false;
    expect(weight_capacity(100, 100, 80, 0, 0) == 2280,
        "mounted capacity uses mounted STR and retained weight bonuses");
    in.overweight = false; in.adjust_speed = 0; in.engine_working = false;
    expect(calculate(in).speed == 225, "empty engine uses gameplay fallback");
    in.engine_working = true; in.legs_working = false;
    expect(calculate(in).speed == 225, "broken legs use gameplay fallback");
    in.legs_working = true; in.legs_speed = 63; in.engine_speed = 113;
    expect(calculate(in).speed == 736, "fractional engine/leg speed is floored");
    in.weapon_present = false;
    expect(calculate(in).valid_fields == 31, "unarmed transport retains non-attack fields");
    in.complete = false;
    expect(calculate(in).valid_fields == (Type | Fuel), "incomplete assembly");
    in.engine_present = false;
    expect(calculate(in).valid_fields == Type, "missing engine");
    in.vehicle_type = 0;
    expect(calculate(in).valid_fields == 0, "missing or unsupported body");
    expect(fuel_after_mount(5, 3, false) == 2 && fuel_after_mount(3, 3, false) == 0
        && fuel_after_mount(0, 3, false) == 0 && fuel_after_mount(5, 3, true) == 5,
        "mount deduction once, empty fuel and exhaustion boundary");
}

void cache_ordering() {
    PreviewRequestGate gate;
    uint32_t ready = 0;
    gate.submit(1);
    expect(gate.take(1000, ready) && ready == 1, "server accepts first request");
    gate.submit(2);
    expect(!gate.take(1490, ready), "server enforces 500ms even with early arrival");
    expect(gate.take(1500, ready) && ready == 2, "early request is deferred, not dropped");
    expect(!gate.take(2000, ready), "server does not calculate without a request");
    PreviewCache cache;
    const auto value = calculate(fixture());
    expect(cache.request(0) == 0, "closed panel never polls");
    cache.set_active(true);
    const auto first = cache.request(0);
    expect(first && !cache.request(500), "one outstanding request");
    cache.invalidate(); // equipment changes while the reply is in flight
    cache.accept(first, value);
    expect(!cache.result.valid_fields, "stale equipment reply rejected");
    expect(!cache.request(499), "two requests per second limit");
    const auto second = cache.request(500);
    cache.accept(first, value);
    expect(!cache.result.valid_fields && !cache.request(600), "old sequence cannot complete new request");
    cache.accept(second, value);
    expect(cache.result.attack == 610, "current reply accepted");
    const auto third = cache.request(1000);
    expect(third && !cache.request(2999), "wait for timeout");
    const auto fourth = cache.request(3000);
    expect(fourth && !cache.result.valid_fields, "timeout expires values and retries");
    cache.set_active(false);
    cache.accept(fourth, value);
    expect(!cache.result.valid_fields && !cache.request(3500), "hidden panel rejects reply");
    cache.set_active(true);
    const auto fifth = cache.request(3500);
    cache.set_active(false); cache.invalidate(); cache.set_active(true); // zone/character reset
    cache.accept(fifth, value);
    expect(!cache.result.valid_fields, "zone transition rejects old response");
}

void packets() {
    namespace P = Rose::Network::Packets;
    static_assert(static_cast<int>(P::PacketType::DamageEvent) == 8, "existing wire IDs unchanged");
    flatbuffers::FlatBufferBuilder builder;
    auto request = P::CreateTuningPreviewRequest(builder, 1234);
    auto data = P::CreatePacketData(builder, P::PacketType::TuningPreviewRequest, request.Union());
    builder.Finish(data);
    flatbuffers::Verifier verifier(builder.GetBufferPointer(), builder.GetSize());
    expect(P::VerifyPacketDataBuffer(verifier), "request verifies");
    expect(P::GetPacketData(builder.GetBufferPointer())->data_as_TuningPreviewRequest()->sequence() == 1234,
        "request round-trip");
    builder.Clear();
    auto response = P::CreateTuningPreviewResponse(builder, 1234, 2, 127, 123, 456, 3, 745, 610, 112);
    data = P::CreatePacketData(builder, P::PacketType::TuningPreviewResponse, response.Union());
    builder.Finish(data);
    flatbuffers::Verifier verifier2(builder.GetBufferPointer(), builder.GetSize());
    expect(P::VerifyPacketDataBuffer(verifier2), "response verifies");
    auto read = P::GetPacketData(builder.GetBufferPointer())->data_as_TuningPreviewResponse();
    expect(read->vehicle_type() == 2 && read->attack_power() == 610 && read->sequence() == 1234,
        "response round-trip");
    flatbuffers::Verifier truncated(builder.GetBufferPointer(), 8);
    expect(!P::VerifyPacketDataBuffer(truncated), "truncated response rejected");
}

int main() {
    ItemBonusFixtures::run();
    legacy_formula_regressions();
    scenarios();
    cache_ordering();
    packets();
    std::cout << "Tuning preview tests passed\n";
}

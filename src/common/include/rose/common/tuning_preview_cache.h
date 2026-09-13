#pragma once

#include "rose/common/mounted_stats.h"

namespace Rose::Tuning {

// Queue an early request until the next allowed calculation. Dropping it would
// turn ordinary network/tick jitter into a two-second client timeout.
class PreviewRequestGate {
public:
    void submit(uint32_t value) { sequence = value; pending = true; }
    bool take(uint64_t now, uint32_t& value) {
        if (!pending || (has_run && now - last_run < 500))
            return false;
        value = sequence;
        pending = false;
        has_run = true;
        last_run = now;
        return true;
    }
private:
    uint32_t sequence = 0;
    uint64_t last_run = 0;
    bool pending = false, has_run = false;
};

// Independent of the UI/network so ordering and timeout behavior can be tested.
class PreviewCache {
public:
    MountedStatsResult result;

    void invalidate() {
        ++generation;
        result = {};
    }

    void set_active(bool value) {
        if (active != value) {
            active = value;
            invalidate();
        }
    }

    uint32_t request(uint64_t now) {
        if (pending && now - sent_at >= 2000) {
            pending = 0;
            invalidate();
        }
        if (!active || pending || (has_sent && now - sent_at < 500))
            return 0;
        if (++sequence == 0)
            ++sequence;
        pending = sequence;
        pending_generation = generation;
        sent_at = now;
        has_sent = true;
        return sequence;
    }

    void accept(uint32_t reply_sequence, const MountedStatsResult& value) {
        if (!pending || reply_sequence != pending)
            return;
        pending = 0;
        if (active && pending_generation == generation)
            result = value;
    }

private:
    bool active = false, has_sent = false;
    uint32_t sequence = 0, pending = 0;
    uint64_t generation = 0, pending_generation = 0, sent_at = 0;
};

} // namespace Rose::Tuning

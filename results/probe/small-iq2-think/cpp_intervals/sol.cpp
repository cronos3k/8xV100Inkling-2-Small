#include <bitset>
#include <cstdio>
#include <cstdint>
#include <vector>
#include <utility>
#include <algorithm>

#include <algorithm>
#include <iterator>
#include <map>
#include <utility>
#include <vector>

class IntervalSet {
public:
    void add(int lo, int hi) {
        if (lo >= hi) return;

        int newLo = lo;
        int newHi = hi;

        auto it = intervals_.lower_bound(lo);
        if (it != intervals_.begin()) {
            auto pit = std::prev(it);
            if (pit->second >= lo) {
                newLo = pit->first;
                newHi = std::max(newHi, pit->second);
                intervals_.erase(pit);
            }
        }

        while (it != intervals_.end() && it->first <= newHi) {
            newHi = std::max(newHi, it->second);
            it = intervals_.erase(it);
        }

        intervals_[newLo] = newHi;
    }

    void remove(int lo, int hi) {
        if (lo >= hi) return;

        auto it = intervals_.lower_bound(lo);
        if (it != intervals_.begin()) {
            auto pit = std::prev(it);
            if (pit->second > lo) {
                int leftLo = pit->first;
                int rightHi = pit->second;
                intervals_.erase(pit);
                if (leftLo < lo) intervals_[leftLo] = lo;
                if (hi < rightHi) intervals_[hi] = rightHi;
            }
        }

        it = intervals_.lower_bound(lo);
        while (it != intervals_.end() && it->first < hi) {
            if (it->second <= hi) {
                it = intervals_.erase(it);
            } else {
                int rightHi = it->second;
                intervals_.erase(it);
                intervals_[hi] = rightHi;
                break;
            }
        }
    }

    bool contains(int x) const {
        auto it = intervals_.upper_bound(x);
        if (it == intervals_.begin()) return false;
        --it;
        return x < it->second;
    }

    std::vector<std::pair<int, int>> intervals() const {
        std::vector<std::pair<int, int>> result;
        result.reserve(intervals_.size());
        for (const auto& [lo, hi] : intervals_) {
            result.emplace_back(lo, hi);
        }
        return result;
    }

private:
    std::map<int, int> intervals_;
};


int main() {
    IntervalSet s; std::bitset<300> b; uint32_t x = 12345;
    auto rnd = [&]() { x = x * 1664525u + 1013904223u; return (int)((x >> 16) % 300); };
    for (int it = 0; it < 6000; ++it) {
        int lo = rnd(), hi = std::min(300, lo + rnd() % 14); bool add = (rnd() % 5) < 3;
        if (it % 97 == 0) { lo = rnd(); hi = lo - 3; }
        if (add) { s.add(lo, hi); for (int i = lo; i < hi; ++i) b[i] = 1; }
        else { s.remove(lo, hi); for (int i = lo; i < hi; ++i) b[i] = 0; }
        std::vector<std::pair<int,int>> want;
        for (int i = 0; i < 300;) { if (b[i]) { int j = i; while (j < 300 && b[j]) ++j; want.push_back({i, j}); i = j; } else ++i; }
        if (s.intervals() != want) { std::printf("MISMATCH after operation %d\n", it); return 1; }
        int q = rnd();
        if (s.contains(q) != (bool)b[q]) { std::printf("contains() wrong after operation %d\n", it); return 1; }
    }
    std::puts("ALL-OK");
    return 0;
}

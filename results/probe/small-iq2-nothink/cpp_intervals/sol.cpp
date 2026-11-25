#include <bitset>
#include <cstdio>
#include <cstdint>
#include <vector>
#include <utility>
#include <algorithm>

#include <map>
#include <vector>
#include <utility>
#include <algorithm>

class IntervalSet {
public:
    void add(int lo, int hi) {
        if (lo >= hi) return;

        // Find the first interval that could overlap or touch [lo, hi).
        // An interval [a, b) with b < lo cannot touch/overlap; b == lo touches.
        auto it = intervals_.lower_bound(lo);
        if (it != intervals_.begin()) {
            auto prev = std::prev(it);
            if (prev->second >= lo) {
                it = prev;
            }
        }

        int newLo = lo, newHi = hi;
        while (it != intervals_.end() && it->first <= newHi) {
            newLo = std::min(newLo, it->first);
            newHi = std::max(newHi, it->second);
            it = intervals_.erase(it);
        }
        intervals_[newLo] = newHi;
    }

    void remove(int lo, int hi) {
        if (lo >= hi) return;

        auto it = intervals_.lower_bound(lo);
        if (it != intervals_.begin()) {
            auto prev = std::prev(it);
            if (prev->second > lo) {
                it = prev;
            }
        }

        std::vector<std::pair<int,int>> toInsert;
        while (it != intervals_.end() && it->first < hi) {
            int a = it->first, b = it->second;
            if (a < lo) toInsert.emplace_back(a, lo);
            if (b > hi) toInsert.emplace_back(hi, b);
            it = intervals_.erase(it);
        }
        for (auto& p : toInsert) {
            intervals_[p.first] = p.second;
        }
    }

    bool contains(int x) const {
        auto it = intervals_.upper_bound(x);
        if (it == intervals_.begin()) return false;
        --it;
        return x < it->second;
    }

    std::vector<std::pair<int,int>> intervals() const {
        return std::vector<std::pair<int,int>>(intervals_.begin(), intervals_.end());
    }

private:
    // key = lo, value = hi; intervals are disjoint and non-touching
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

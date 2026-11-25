```cpp
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
```
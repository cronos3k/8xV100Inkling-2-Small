```cpp
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
```
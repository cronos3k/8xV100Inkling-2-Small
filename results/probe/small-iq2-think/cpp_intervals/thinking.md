We need answer with one C++ code block only. Need implement IntervalSet C++17. Need think carefully.

Requirements:
- class IntervalSet holding set of integers as disjoint half-open intervals [lo, hi).
- add(int lo,int hi): insert all integers in [lo,hi). remove similarly. Both do nothing when lo>=hi.
- contains(int x) const.
- intervals() const returns vector<pair<int,int>> ascending, disjoint, maximal (touching merged).
- Use std::map internally.
- Include headers needed, no main.

Need produce robust implementation. Need consider int overflow? Intervals [lo,hi) with int lo<hi. Operations may create hi? We don't add hi+1 except maybe merging. Need avoid overflow. Use map<int,int> mapping lo -> hi, disjoint non-touching? We can maintain invariant: intervals in map are disjoint and non-adjacent? If we always merge touching on add/remove, map can store maximal intervals. Simpler: maintain map<int,int> intervals_; invariant: keys lo, values hi, lo<hi, intervals disjoint and not touching (next.lo > prev.hi). Then add: if lo>=hi return. Need merge all intervals intersecting or touching [lo,hi). Algorithm:
void add(int lo,int hi) {
 if (lo>=hi) return;
 int newLo=lo, newHi=hi;
 auto it = intervals_.lower_bound(lo); // first with key >= lo
 // Need include interval with key < lo that may overlap/touch: if it != begin, prev = std::prev(it); if prev->second >= lo? For half-open and touching merge if prev.hi >= lo (since [prev.lo, prev.hi) touches [lo,hi) if prev.hi == lo). Actually if prev.hi >= lo, merge. If prev.hi < lo no.
 if (it != intervals_.begin()) {
   auto pit = std::prev(it);
   if (pit->second >= lo) { newLo = pit->first; newHi = std::max(newHi, pit->second); intervals_.erase(pit); }
 }
 // Now erase all intervals with key < newHi? Need iterate from it (original lower_bound) but after erasing pit, it remains valid? Erasing pit (before it) does not invalidate it. Good.
 while (it != intervals_.end() && it->first <= newHi) { // if it->first == newHi, touching, merge. Since half-open [it.lo,it.hi) touches [newLo,newHi) if it.lo == newHi. Use <=.
   newHi = std::max(newHi, it->second);
   it = intervals_.erase(it);
 }
 intervals_[newLo] = newHi;
}
But careful: after erasing pit and setting newLo=pit->first, it points to first interval with key >= lo. There could be intervals with key < lo but > newLo? No newLo <= lo. Intervals with key between newLo and lo? pit was immediate predecessor of lower_bound(lo), so no keys in [newLo, lo) except pit erased. Good.
However while condition it->first <= newHi merges touching. If it->first == newHi, merge. Good. But what about interval with key < newHi but after pit? all included.
Potential issue: if pit->second >= lo, we erase pit and set newLo=pit->first. But there might be another interval before pit that touches pit? Invariant says no touching, so no.
Remove: Need erase all integers in [lo,hi). Algorithm:
if (lo>=hi) return;
// Handle interval starting before lo and ending after lo: split left part.
auto it = intervals_.lower_bound(lo);
if (it != intervals_.begin()) {
  auto pit = std::prev(it);
  if (pit->second > lo) { // overlaps [lo,hi)
     int leftLo=pit->first, leftHi=lo; // keep [leftLo, lo)
     int rightLo=hi, rightHi=pit->second; // keep [hi, pit->second) if hi < pit->second
     intervals_.erase(pit);
     if (leftLo < leftHi) intervals_[leftLo]=leftHi; // leftLo<lo by pit->first<lo? pit key < lo yes.
     if (rightLo < rightHi) intervals_[rightLo]=rightHi; // but inserting rightLo=hi maybe before it? Need handle carefully.
  }
}
// Now erase/trim intervals fully or partially inside [lo,hi).
it = intervals_.lower_bound(lo); // recompute? Or use original it? We may have inserted rightLo=hi which could be >= lo and before original it? Need recompute to be safe.
while (it != intervals_.end() && it->first < hi) {
  if (it->second <= hi) { it = intervals_.erase(it); }
  else { // it->second > hi, keep right tail [hi, it->second)
     int rightLo=hi, rightHi=it->second;
     intervals_.erase(it);
     intervals_[rightLo]=rightHi; // inserting at hi; but we're iterating? We can break after because no more intervals with first < hi? Actually after erasing it and inserting [hi,rightHi), there may be subsequent intervals with first < hi? No subsequent first > it->first. If it->first < hi and it->second > hi, the tail starts at hi, and any following interval starts >= it->second? Invariant non-touching: next.first >= it->second? Actually disjoint non-touching means next.first > it->second. If it->second > hi, next.first > it->second > hi, so no more with first < hi. We can break. But if we insert [hi,rightHi), then loop condition it->first < hi false if we set it to end? Simpler handle in loop and break.
  }
}
Need also handle case where pit overlaps and right tail [hi,pit->second) inserted before processing intervals starting at lo. If we insert right tail at hi, then recompute lower_bound(lo) and while it->first < hi will not include tail at hi (since < hi false). Good. But if hi <= pit->second, tail [hi,pit->second) remains. Good. If hi >= pit->second, no tail. Left part [pit->first, lo) remains. Good.
But subtle: When pit->second > lo, we erase pit and insert left and maybe right. If we insert right [hi,pit->second) before recomputing, and hi could be <= lo? no hi>lo. It's fine. But if right tail inserted and then lower_bound(lo) returns first >= lo. If there was an interval starting exactly at lo, it remains. Good.
Then while loop: it = intervals_.lower_bound(lo). while (it != end && it->first < hi): if it->second <= hi erase; else { int rightHi=it->second; intervals_.erase(it); intervals_[hi]=rightHi; break; } But inserting [hi,rightHi) while there may already be an interval at hi? Invariant before removal: no touching. Could there be an interval starting at hi? If it->second > hi and next interval starts at it->second (or >), not at hi. Since it->second > hi, next.first > it->second > hi. No existing key hi. But what if it->first < hi and it->second > hi, after erasing it and inserting [hi,rightHi), okay. If there was right tail from pit inserted at hi earlier, and now another interval it with first<hi and second>hi? Can that happen? Suppose pit [0,10), remove [2,5). pit overlaps, left [0,2), right [5,10) inserted. Then recompute lower_bound(2): intervals [0,2), [5,10), maybe others. while it->first<5: [0,2) first 0<5, second 2<=5 erase? Wait! This is wrong: after handling pit, we inserted left [0,2). Then recompute lower_bound(lo=2), not lower_bound(0). I said it = intervals_.lower_bound(lo), so [0,2) not included. Good. If I mistakenly used lower_bound(lo), fine.
But in remove, after pit handling, if we insert right tail [hi,pit->second), then lower_bound(lo) won't include it. Good.
However, there is a subtle bug: In pit handling, if pit->second > lo, we erase pit and insert left [pit->first, lo) and right [hi, pit->second) if hi < pit->second. But if hi < pit->second, right tail starts at hi. Then later while loop with lower_bound(lo) and it->first < hi won't touch right tail. Good. If hi >= pit->second, no right tail. Good.
But what about intervals that start before lo and end after hi (pit->second > hi): left [pit->first,lo), right [hi,pit->second). Good.
What about interval with key == lo? lower_bound(lo) returns it; pit is before. If pit overlaps, we handle. Then recompute. Good.
Need ensure after removal, invariant non-touching holds. We may insert left [pit->first,lo) and right [hi,pit->second). Could left touch an earlier interval? Invariant before: pit was predecessor of lower_bound(lo), and no touching before. After erasing pit and inserting left [pit->first,lo), could it touch previous interval? Previous interval ends <= pit->first? Invariant non-touching: prev.second < pit->first? Actually disjoint non-touching means prev.second < pit->first? For half-open, touching if prev.second == pit->first. Invariant no touching means prev.second < pit->first? Wait if prev.second == pit->first they'd be merged, so invariant prev.second < pit->first? No, disjoint intervals can have gap; if prev.second < pit->first. If prev.second == pit->first, merged. So prev.second < pit->first. Left [pit->first,lo) starts at pit->first, so prev.second < pit->first, no touch. Good. Could left touch right? left ends lo, right starts hi, lo<hi gap. Good. Could right [hi,pit->second) touch an existing interval starting at hi? Before removal, after erasing pit, could there be an interval starting at hi? Invariant no touching with pit: next interval after pit starts > pit->second? Actually if pit [a,b), next starts >= b? No touching means next.first > b? Wait touching if next.first == b. Invariant no touching means next.first > b? For half-open, if next.first == b, they'd be merged into [a,next.second). So invariant next.first > b? That seems too strong: disjoint intervals [0,5) and [5,10) touch and would be merged, so not allowed. Thus next.first > b? If next.first == b, merged; if next.first < b overlap; so next.first > b? Actually if next.first == b, they are adjacent; maximal invariant forbids. So next.first > b? No, if next.first == b, it's not > b. It must be > b? That would mean gap at least 1 integer? For integer intervals, [0,5) and [6,10) have gap [5,6). But [0,5) and [5,10) are touching and merged. So yes invariant next.first > prev.second? Wait if prev.second=5 and next.first=6, next.first > prev.second. If next.first=5, equal, merged. So invariant next.first > prev.second? That can't be right for [0,5) and [5,10) merged to [0,10). For [0,5) and [6,10), next.first=6 > 5. There is no integer 5 in first, integer 5 in second? Actually [6,10) starts at 6, integer 5 not in any. Gap. Good. But what about [0,5) and [5,10) would be merged, so not stored. Thus invariant next.first > prev.second? If next.first == prev.second, merged; if next.first < prev.second overlap. So next.first > prev.second. But for integer intervals, next.first == prev.second + 1 means there is a gap of one integer? Example [0,5) contains 0..4, [6,10) contains 6..9, integer 5 missing. next.first=6 > prev.second=5. Yes.
But hold on: half-open intervals [0,5) and [5,10) are touching and merged. [0,5) and [6,10) are not touching? They are separated by integer 5? Actually [0,5) ends at 5 exclusive, [6,10) starts at 6, so integer 5 is not included. There is a gap. Good.
But in add algorithm, while it->first <= newHi merges if it->first == newHi (touching) and also if it->first < newHi (overlap). Good.
In remove, after erasing pit and inserting right [hi,pit->second), could right touch next interval? next.first > pit->second (invariant), right ends pit->second, so next.first > right.second, no touch. Good. Could right touch an interval starting at hi inserted by while loop? We don't insert in while if it->second>hi? We do insert [hi,it->second) after erasing it. But if right tail from pit already inserted at hi, then while loop lower_bound(lo) won't see it (first==hi not <hi). But could there be another interval it with first<hi and second>hi after pit handling? Let's examine. Suppose pit [0,100), remove [10,20). pit overlaps, left [0,10), right [20,100) inserted. Recompute lower_bound(10): intervals [0,10), [20,100), maybe others. while it->first<20: [0,10) first 0<20, second 10<=20 -> erase! Wait lower_bound(lo=10) returns first >=10, so [0,10) not included. Good. If there is interval [15,25), it->first=15<20, second=25>20 -> erase and insert [20,25). But there is already right tail [20,100) from pit! Inserting [20,25) would duplicate key 20. Can this happen? Let's see: pit [0,100) overlaps remove [10,20). We erase pit and insert left [0,10) and right [20,100). But if there was an interval [15,25) before removal, it would overlap pit [0,100), impossible. So no. Good.
But after pit handling, if hi < pit->second, we insert right [hi,pit->second). Then while loop lower_bound(lo) with it->first < hi. Could there be an interval with first < hi and second > hi that was not pit? It would overlap pit? If it starts after pit->first and before hi, and pit [pit->first,pit->second) with pit->second>hi, then it overlaps pit, impossible. If it starts before pit->first? no. So safe.
However, in remove, after pit handling, we recompute it = intervals_.lower_bound(lo). But we may have inserted left [pit->first,lo) with first<lo; lower_bound(lo) skips. Good. We may have inserted right [hi,pit->second) with first==hi; while condition it->first<hi skips. Good.
Then while loop: if it->first < hi. If it->second <= hi erase. Else (it->second > hi): erase it and insert [hi,it->second). But if we already inserted right tail [hi,pit->second) from pit, can this happen? As argued no. But what if pit did not overlap (pit->second <= lo), and there is interval it with first<hi and second>hi. Then inserting [hi,it->second) is fine; no existing key hi because invariant next.first > it->second? Wait if it->second>hi, next.first > it->second > hi, so no key hi. Good. If it->first == hi? while condition false. Good.
But in the else branch, after erasing it and inserting [hi,it->second), we should break because no more intervals with first<hi. Actually there could be subsequent intervals with first<hi? No, subsequent first > it->first; but could be < hi? Suppose it->first=5, hi=10, it->second=20. Subsequent interval starts >20 (invariant), so not <10. If it->second<=hi we erase and continue; subsequent could have first<hi. If it->second>hi, subsequent starts > it->second > hi, so break. Good.
Alternatively, simpler remove algorithm: collect intervals to erase/split. But above okay.
Need contains(int x) const: auto it = intervals_.upper_bound(x); if (it == begin) return false; --it; return x < it->second; (since it->first <= x). Or lower_bound(x+1)? Avoid overflow x+1 if x==INT_MAX. Use upper_bound(x). If it != begin, prev. Good.
intervals() const: vector<pair<int,int>> res; res.reserve(intervals_.size()); for (auto& [lo,hi] : intervals_) res.emplace_back(lo,hi); return res; Since invariant maximal, just copy. Need include <map>, <vector>, <utility>, <algorithm>, <iterator> maybe. Use std::max. Include <algorithm>. <utility> for pair. <vector>. <map>. <iterator> for std::prev? std::prev is in <iterator>. Could use auto pit = it; --pit; but if it==begin check. Use std::prev with <iterator>. Include <iterator>.
Need ensure add invariant after operations. Let's test mentally.
Initial empty. add(1,3): newLo=1,newHi=3; it=lower_bound(1)=end; pit none; while none; insert [1,3). add(3,5): newLo=3,newHi=5; it=lower_bound(3)=end; pit=prev(end)=[1,3), pit->second=3>=3 -> newLo=1,newHi=max(5,3)=5, erase pit. it still end? We erased pit, it was end, okay. while none; insert [1,5). Good.
add(2,4) to [1,5): newLo=2,newHi=4; it=lower_bound(2)=end (since key1<2); pit=[1,5), pit->second=5>=2 -> newLo=1,newHi=max(4,5)=5 erase pit; insert [1,5). Good.
add(6,7) to [1,5): it=lower_bound(6)=end; pit=[1,5), pit->second=5>=6? false; while none; insert [6,7). Now map [1,5),[6,7). Are they touching? 5<6 gap integer5? Wait [1,5) contains 1..4, [6,7) contains 6, integer5 missing. Not touching. Good. If add(5,6): newLo=5,newHi=6; it=lower_bound(5)=end; pit=[1,5), pit->second=5>=5 -> newLo=1,newHi=max(6,5)=6 erase pit; it=end; while none; insert [1,6). Good. If map [1,5),[6,7), add(5,6): it=lower_bound(5)=[6,7) (first key>=5). pit=[1,5), pit->second=5>=5 -> newLo=1,newHi=max(6,5)=6 erase pit. it still [6,7). while it->first=6 <= newHi=6 -> newHi=max(6,7)=7 erase it. insert [1,7). Good.
Remove test: map [1,10). remove(3,5): it=lower_bound(3)=end? key1<3 so lower_bound(3)=end (since only key1). pit=[1,10), pit->second=10>3 -> left [1,3), right [5,10) insert. erase pit. recompute it=lower_bound(3): intervals [1,3),[5,10); lower_bound(3) returns [5,10) (first>=3). while it->first<5? [5,10) first5<5 false. Done. Map [1,3),[5,10). Good.
Remove(0,20) from [1,10): it=lower_bound(0)=[1,10)? key1>=0 yes. pit none (it==begin). recompute same. while it->first<20: it->second=10<=20 erase. Map empty. Good.
Remove(5,15) from [1,10): it=lower_bound(5)=end? key1<5 so end. pit=[1,10), pit->second=10>5 -> left [1,5), right [15,10)? hi=15, pit->second=10, hi<pit->second false, so no right. erase pit. recompute lower_bound(5): [1,5) first1<5? lower_bound(5) returns end? first>=5 none ([1,5) key1<5). while none. Map [1,5). Good.
Remove(5,7) from [1,10): pit=[1,10), left [1,5), right [7,10). recompute lower_bound(5): intervals [1,5),[7,10); lower_bound(5) returns [7,10) (first>=5). while it->first<7? 7<7 false. Map [1,5),[7,10). Good.
Remove(0,5) from [1,10): it=lower_bound(0)=[1,10) (begin). pit none. recompute it=[1,10). while it->first<5: it->second=10<=5? false; else erase it insert [5,10). Map [5,10). Good.
Remove(5,10) from [1,10): it=lower_bound(5)=end? key1<5 end. pit=[1,10), pit->second=10>5 -> left [1,5), right hi=10<pit->second? false. erase pit. recompute lower_bound(5): [1,5) key1<5 so end. while none. Map [1,5). Good.
Remove(3,7) from [1,5),[8,10): it=lower_bound(3)=[8,10)? key1<3, key8>=3 yes. pit=[1,5), pit->second=5>3 -> left [1,3), right [7,5)? hi=7<pit->second=5 false. erase pit. recompute lower_bound(3): intervals [1,3),[8,10); lower_bound(3) returns [8,10). while it->first<7? 8<7 false. Map [1,3),[8,10). Good. But what about interval [4,6) overlapping remove [3,7)? It would be in map with pit? Let's test map [1,10) only. Fine.
More complex: map [1,3),[5,7),[9,11). remove(2,10). it=lower_bound(2)=[5,7)? key1<2, key5>=2. pit=[1,3), pit->second=3>2 -> left [1,2), right [10,3)? hi=10<pit->second=3 false. erase pit. recompute lower_bound(2): intervals [1,2),[5,7),[9,11); lower_bound(2) returns [5,7). while it->first<10: [5,7) second7<=10 erase; it=[9,11); first9<10 second11<=10? false; else erase [9,11), insert [10,11); break. Map [1,2),[10,11). Good.
Remove(2,6) from [1,10): pit=[1,10), left [1,2), right [6,10). recompute lower_bound(2): [1,2),[6,10); lower_bound(2) returns [6,10) (first>=2). while it->first<6? 6<6 false. Map [1,2),[6,10). Good.
Remove(2,6) from [1,4),[6,10): it=lower_bound(2)=[6,10)? key1<2, key6>=2. pit=[1,4), pit->second=4>2 -> left [1,2), right [6,4)? hi=6<pit->second=4 false. erase pit. recompute lower_bound(2): [1,2),[6,10); lower_bound(2) returns [6,10). while it->first<6? false. Map [1,2),[6,10). Good. Note [1,2) and [6,10) gap.
Remove(2,6) from [1,4),[5,10): it=lower_bound(2)=[5,10)? key1<2, key5>=2. pit=[1,4), pit->second=4>2 -> left [1,2), right [6,4)? false. erase pit. recompute lower_bound(2): [1,2),[5,10); lower_bound(2) returns [5,10). while it->first<6: [5,10) second10<=6? false; else erase [5,10), insert [6,10); break. Map [1,2),[6,10). Good.
Remove(2,6) from [1,4),[4,10) impossible touching. Good.
Potential issue in add: after erasing pit, it may be invalidated? std::map erase(iterator) invalidates only erased iterator; it remains valid. Good.
Potential issue in add while: it->first <= newHi. Suppose it->first == newHi and it->second < newHi? impossible since it->second>it->first=newHi, so it->second>newHi. newHi=max. Good.
Need maybe maintain invariant that intervals are maximal. add merges touching. remove can create adjacent intervals? Example map [1,5),[6,10) (gap integer5). remove(5,6) (empty? lo=5,hi=6 removes integer5). It doesn't affect intervals. Map remains [1,5),[6,10), gap integer5 removed? Actually integer5 was not in any interval; removing it does nothing. Good. remove can create touching intervals? Suppose map [1,3),[5,7) with gap [3,5). remove(3,5) does nothing (no integers in gap). Map remains [1,3),[5,7), still not touching? They are separated by gap [3,5), but after removing nothing, gap remains. Good. remove can split an interval into left and right with gap [lo,hi) removed; left ends lo, right starts hi, gap remains. No touching. remove can erase middle intervals; remaining intervals separated by removed gap. No touching. Good.
But wait: remove can make two intervals touching if it removes a gap? It only removes integers, cannot fill gap. It can remove an interval that was separating? Intervals are disjoint; removing one interval leaves gap, not merge. It cannot merge intervals. Good.
Need maybe add can create touching with existing intervals not adjacent? It merges all overlapping/touching. Good.
Need consider integer overflow in contains upper_bound(x) no overflow. In add/remove no x+1. Good.
Need maybe use int64_t internally? Requirement int. Use int.
Need produce exactly one code block and nothing else. No explanation. Need include class definition. Could include `#include <map>` etc. Need not write main. Should we make class with private map and public methods. Yes.
Need ensure `intervals()` returns `std::vector<std::pair<int,int>>`. Use `std::pair<int,int>`.
Need maybe `const` methods. `contains` const, `intervals` const.
Need maybe default constructor. Not required but class with map default. Fine.
Need maybe `add` and `remove` handle lo>=hi. Yes.
Let's craft code:
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
                int leftHi = lo;
                int rightLo = hi;
                int rightHi = pit->second;
                intervals_.erase(pit);
                if (leftLo < leftHi) intervals_[leftLo] = leftHi;
                if (rightLo < rightHi) intervals_[rightLo] = rightHi;
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
    std::vector<std::pair<int,int>> intervals() const {
        std::vector<std::pair<int,int>> result;
        result.reserve(intervals_.size());
        for (const auto& [lo, hi] : intervals_) result.emplace_back(lo, hi);
        return result;
    }
private:
    std::map<int,int> intervals_;
};

Need double-check remove pit handling with `it` after erasing pit. We don't use it after; recompute. Good. But in pit handling, if pit->second > lo, we erase pit. If `it` was `intervals_.begin()`? We check it != begin, so pit exists. Good. If pit->second > lo but pit->first == lo? impossible pit key < lo. leftLo<leftHi yes. If pit->second == lo? no overlap (touching? [pit.first,lo) and [lo,hi) touch; but invariant would have merged? Wait pit->second == lo means pit interval ends exactly at lo. In remove, pit->second > lo false, so we don't split. But pit [a,lo) and remove [lo,hi) are adjacent; removing [lo,hi) doesn't affect pit. Good. In add, pit->second >= lo merges touching. Good.
Potential subtle bug in remove: Suppose pit->second > lo and hi < pit->second. We insert right [hi,pit->second). Then recompute it=lower_bound(lo). But there may be an interval with first == lo that was after pit. It remains. Good. While it->first<hi processes intervals starting before hi. It will not process right [hi,...) because first==hi. Good. But what if there is an interval with first < hi and second > hi that is the same as right? no.
Potential subtle bug: In remove, after pit handling and recompute, while loop may erase an interval with first < hi and second <= hi. If that interval is left [pit->first,lo)? first<lo, lower_bound(lo) skips. Good. If left inserted with first<lo but lower_bound(lo) returns first>=lo, skip. Good.
Potential subtle bug: In remove, if pit->second > lo and hi < pit->second, we insert right [hi,pit->second). Then while loop lower_bound(lo) might return an interval with first < hi that is actually right? no first==hi. Good.
Potential subtle bug: In remove, if pit->second > lo and hi >= pit->second, no right. But there may be intervals after pit with first < hi. while handles. Good.
Potential subtle bug: In remove, if pit->second > lo and hi < pit->second, we insert right [hi,pit->second). But what if there is already an interval starting at hi after pit? Invariant next.first > pit->second? Wait if pit [a,b), next.first > b? Actually no touching means next.first > b? Let's re-evaluate invariant precisely. For half-open intervals, [a,b) and [c,d) with c >= b are disjoint. If c == b, they are touching and should be merged. So invariant c > b? If c == b, merged; if c < b overlap. Thus c > b. But for integer intervals, c == b+? If c == b, merged; if c == b+1, there is a gap integer b? Example [0,5) and [6,10): c=6 > b=5. Yes. So next.first > pit->second. If hi < pit->second, right [hi,pit->second) ends at pit->second; next.first > pit->second, so no existing key hi (hi<pit->second<next.first). Good. If hi == pit->second, no right. If hi > pit->second, no right. Good.
But wait invariant next.first > prev.second means there is always at least one integer gap? For integer intervals, if prev.second=5 and next.first=6, integer5 is not in either. Yes. But what about [0,5) and [5,10) merged; [0,5) and [6,10) gap integer5. Good. However, is it possible to have [0,5) and [5,10) not merged but disjoint? They are not disjoint? They are disjoint as sets (no common integer) but touching; requirement maximal merges touching. So invariant forbids. Good.
But hold on: half-open intervals [0,5) and [5,10) are disjoint (no common elements) but touching; maximal requires merge. So invariant next.first > prev.second? If next.first == prev.second, they'd be merged. If next.first == prev.second + 1, there is a gap of one integer? Actually [0,5) contains 0-4, [6,10) contains 6-9, integer5 missing. Yes. So invariant next.first > prev.second. But what about [0,5) and [5,10) if not merged would have next.first == prev.second, not >. So invariant next.first > prev.second. This means stored intervals are separated by at least one integer. Is that necessary? Maximal only forbids touching (next.first == prev.second) and overlapping. It allows next.first == prev.second + 1 (gap one integer). Yes.
But wait, for integer intervals, [0,5) and [5,10) are touching; [0,5) and [6,10) are not touching but there is no integer between? There is integer5 not in either. Good.
Now, add algorithm with invariant next.first > prev.second: while it->first <= newHi merges if it->first == newHi (touching) or <. Good. After merging, newHi may become >= next.first. Good.
Need maybe in add, after erasing pit, `it` could be equal to `intervals_.end()` and pit erased; fine. If pit->second >= lo, newLo=pit->first. But what if there is an interval before pit that touches pit? invariant no. Good.
Potential issue: In add, if pit->second >= lo, we erase pit and set newLo=pit->first. But if pit->second < lo? no. If pit->second == lo, merge touching. Good.
Potential issue: In add, after erasing pit, `it` still points to first interval with key >= lo. But if pit->second >= lo and pit->first < lo, there might be intervals with key in [pit->first, lo) other than pit? No, pit was immediate predecessor of lower_bound(lo), so no keys in [pit->first, lo) except pit. Good.
Need maybe use `std::max` with int. Good.
Need maybe include `<cstddef>`? no.
Need final answer exactly one code block. No extra text. Ensure code block contains only code. Use ```cpp ... ```. That's one code block. Good.
Need not include main. Good.
Let's consider if `intervals()` should return maximal intervals even if internal invariant somehow broken. It relies on invariant. Fine.
Let's test with brute force mentally maybe. Could there be a bug in remove when pit overlaps and right tail inserted, then while loop erases left? lower_bound(lo) skips left. Good.
Let's do a more systematic verification of remove with a scenario where pit overlaps and hi < pit->second, and there is an interval starting at hi? We argued impossible due to invariant next.first > pit->second. But after erasing pit and inserting right [hi,pit->second), could right touch an existing interval starting at pit->second? Invariant next.first > pit->second, so no. Could right touch an existing interval starting at hi? no. Good.
Scenario where pit overlaps and hi >= pit->second, and there is an interval starting exactly at pit->second? Invariant forbids (would be touching). So after removing [lo,hi) with hi>=pit->second, the next interval starts > pit->second. If hi == pit->second, next.first > hi, so no touching with removed gap? We don't insert right. Good. If hi > pit->second, next.first > pit->second but could be < hi? Example pit [0,10), next [11,20) (invariant next.first>10). remove [5,15). pit overlaps, hi=15>=pit->second=10, no right. recompute lower_bound(5): intervals [0,10) erased? Wait we erased pit and inserted left [0,5). next [11,20) remains. lower_bound(5) returns [11,20) (first>=5). while it->first<15: [11,20) second20<=15? false; else erase [11,20), insert [15,20); break. Map [0,5),[15,20). Good. If next [10,20) would be touching pit, impossible. If next [12,20), remove [5,15): left [0,5), next [12,20) partially removed, right [15,20). Good.
Scenario where pit overlaps and hi < pit->second, and next interval starts at pit->second+? right [hi,pit->second), next.first>pit->second, gap. Good.
Now, one subtle point: In remove, when pit overlaps and hi < pit->second, we insert right [hi,pit->second) before the while loop. Then while loop lower_bound(lo) returns first >= lo. Suppose there is an interval with first == lo (after pit) and second <= hi; it will be erased. Good. Suppose there is an interval with first == lo and second > hi; it will be split, inserting [hi,it->second). But we already inserted right [hi,pit->second) from pit. Can this happen? It would overlap pit? Let's construct: pit [0,100), remove [10,20), hi=20<pit->second=100. We insert right [20,100). There cannot be another interval [10,30) because overlaps pit. So no. Good.
But what if pit does not overlap (pit->second <= lo), and there is interval it with first<hi and second>hi; we insert [hi,it->second). Could there already be right tail from pit? no pit doesn't overlap. Could there be an existing interval starting at hi? invariant next.first > it->second > hi, so no. Good.
Potential issue: In remove while else branch, we insert [hi,it->second) and break. But what if there is an existing interval starting at hi inserted earlier in the same while loop? We break immediately after inserting, so no. Could there be an existing interval starting at hi from pit handling? We argued no. Good.
Need maybe in remove, after pit handling, if we inserted right [hi,pit->second), and then while loop else branch inserts [hi,it->second) for another interval, duplicate key hi. We argued impossible. But to be extra safe, we could avoid inserting right in pit handling and instead handle all in one pass? Let's see if we can design simpler and robust remove to avoid duplicate risk.
Alternative remove algorithm:
- Find first interval with hi > lo? Hmm.
Simpler: Use a temporary vector of intervals to keep? But requirement use map internally; can still use map. Could implement remove by iterating and building new map? But O(n) maybe okay but not ideal. Better keep current.
Could make remove robust by not inserting right tail in pit handling before while; instead handle pit and then while with a flag? Let's think.
Maybe simpler remove:
1. If lo>=hi return.
2. auto it = intervals_.lower_bound(lo);
   // Trim left part of interval that starts before lo.
   if (it != intervals_.begin()) {
      auto pit = std::prev(it);
      if (pit->second > lo) {
         int rightHi = pit->second;
         intervals_.erase(pit);
         if (pit->first < lo) intervals_[pit->first] = lo; // left part
         if (hi < rightHi) intervals_[hi] = rightHi; // right part
      }
   }
   // Now erase/trim intervals starting at or after lo.
   it = intervals_.lower_bound(lo);
   while (it != intervals_.end() && it->first < hi) {
      if (it->second <= hi) it = intervals_.erase(it);
      else { int rightHi = it->second; intervals_.erase(it); intervals_[hi] = rightHi; break; }
   }
This is what we have. The duplicate risk is theoretical impossible due to invariant. Fine.
But wait: In pit handling, if pit->second > lo and hi < pit->second, we insert right [hi,pit->second). Then while loop lower_bound(lo) might return an interval with first < hi that is actually the left part? no first<lo. It might return an interval with first == lo. Good. It won't return right [hi,...) because first==hi not <hi. Good.
Could while loop else branch insert [hi,it->second) when right [hi,pit->second) already exists? That would require it->first<hi and it->second>hi. Such it would overlap pit? Let's prove: pit [a,b) with b>lo and hi<b. Any interval it with first>=lo (after pit) and first<hi<b. Since it starts after pit (first>=lo>a) and before b, it overlaps pit [a,b). Impossible. If it starts before lo, lower_bound(lo) skips. So no. Good.
Need maybe in add, similar duplicate risk? add inserts newLo after erasing overlapping/touching intervals. Could there be existing interval at newLo? We erase all with first <= newHi, including any at newLo. If newLo came from pit, pit erased. If newLo=lo, any interval at lo erased in while (it->first=lo<=newHi). Good. No duplicate.
Need maybe in add, after erasing pit, `it` may point to an interval with first < newLo? no.
Potential issue: In add, while condition `it->first <= newHi` merges touching intervals. But what about an interval with first == newHi and second == newHi? impossible. Good.
Need maybe use `std::map<int,int>::iterator` etc. Fine.
Let's consider if `contains` should return true for x in [lo,hi). upper_bound(x) returns first interval with key > x. If none, begin? Actually if all keys <= x, upper_bound returns end; --it gives last interval with key <= x. If x < it->second true. If there is an interval with key == x, upper_bound(x) returns next (since key > x), --it gives that interval, x<second true. Good. If x is before first interval, upper_bound(x) returns begin (first key > x), it==begin false. Good.
Need maybe `intervals()` returns by value. Yes.
Need final code block only. Ensure no comments? Comments okay but maybe no need. Could include no comments. Use concise.
Need maybe include `<cstdint>`? no.
Let's produce final with code block only. No extra text. Ensure exactly one code block. Use ```cpp. Done.
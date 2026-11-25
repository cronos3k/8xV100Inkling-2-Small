We need answer code only. Need craft function. Need ensure correctness.

Problem: schedule(tasks: dict[str, list[str]]) -> list[list[str]]. Each key task, value list deps. Return stages parallel build: stage0 tasks no deps, later stage tasks whose deps all in earlier stages, every task earliest possible stage, each stage sorted alphabetically. Raise ValueError if dependency not key or cycle (self included). Empty dict returns [].

Need output one Python code block nothing else. Need implement robustly.

Algorithm: validate deps exist. Compute indegree (number deps). Kahn by levels. But earliest stage with sorted stages: We can compute level via longest path from sources? Since all deps must be earlier stages, earliest stage index = 0 if no deps else 1 + max(level[dep]). This is equivalent to longest path in DAG. Need detect cycle. Approach: validate all deps first. Then compute levels via memoized DFS with states, detect cycles. Or Kahn level assignment.

Kahn: indeg = len(deps). Build dependents adjacency. Queue tasks indeg 0 sorted? For stages sorted alphabetically, we can process level by level: current = sorted([t for t in tasks if indeg[t]==0]); while current: stage=current; append; next=[]; for t in stage: for dependent in dependents[t]: indeg[dependent]-=1; if becomes 0 add to next; current=sorted(next). This yields stages sorted alphabetically and earliest. Need detect cycle: if processed count != len(tasks), raise ValueError. Self dependency: indeg self=1, never zero, processed count less -> ValueError. Good.

Need be careful duplicate dependencies in list? If tasks value list contains duplicate dep, indeg len counts duplicates but dependents adjacency would decrement twice per completion, okay if we append dependent once per dep occurrence. If build dependents by iterating deps list and appending task for each dep, duplicates consistent. But if duplicate deps, indeg len includes duplicates and decrements twice, fine. However earliest stage unaffected. Could dedupe? If dedupe deps for indeg and adjacency, also fine. Simpler use deps list as given; validate each dep in tasks. dependents: for task, deps in tasks.items(): for dep in deps: dependents[dep].append(task). indeg[task]=len(deps). If duplicate dep, dependents[dep] has task twice, indeg decremented twice. Good.

Cycle detection via processed count. Need raise ValueError with message maybe.

Type hints: dict[str, list[str]] requires py3.9. Fine.

Need code block only. Include function only maybe imports none. Ensure empty dict returns []: current empty, stages empty, processed 0 ==0, return [].

Potential issue: Kahn with sorted(next) each stage yields alphabetical stage. Good.

Let's final with code block only.
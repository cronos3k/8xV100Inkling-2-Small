```python
def schedule(tasks: dict[str, list[str]]) -> list[list[str]]:
    for task, deps in tasks.items():
        for dep in deps:
            if dep not in tasks:
                raise ValueError(f"Unknown dependency {dep!r} for task {task!r}")

    indegree = {task: len(deps) for task, deps in tasks.items()}
    dependents = {task: [] for task in tasks}
    for task, deps in tasks.items():
        for dep in deps:
            dependents[dep].append(task)

    stages = []
    current = sorted(task for task, deg in indegree.items() if deg == 0)
    processed = 0

    while current:
        stages.append(current)
        processed += len(current)
        nxt = []
        for task in current:
            for dependent in dependents[task]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    nxt.append(dependent)
        current = sorted(nxt)

    if processed != len(tasks):
        raise ValueError("Cycle detected in task dependencies")

    return stages
```
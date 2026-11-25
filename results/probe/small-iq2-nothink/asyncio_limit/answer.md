```python
import asyncio

async def gather_limited(fns, limit):
    if not fns:
        return []

    results = [None] * len(fns)
    semaphore = asyncio.Semaphore(limit)
    started = 0
    tasks = []

    async def run_one(index, fn):
        async with semaphore:
            results[index] = await fn()

    try:
        for i, fn in enumerate(fns):
            task = asyncio.create_task(run_one(i, fn))
            tasks.append(task)
            started += 1
        await asyncio.gather(*tasks)
        return results
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
```
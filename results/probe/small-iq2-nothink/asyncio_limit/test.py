import sys
sys.path.insert(0, '.')

import asyncio
from sol import gather_limited
async def main():
    running = 0; peak = 0; started = 0
    def mk(i, fail=False):
        async def f():
            nonlocal running, peak, started
            started += 1; running += 1; peak = max(peak, running)
            try:
                await asyncio.sleep(0.01 * (1 + (i * 7) % 3))
                if fail:
                    raise ValueError("boom")
                return i * i
            finally:
                running -= 1
        return f
    r = await gather_limited([mk(i) for i in range(12)], 3)
    assert r == [i * i for i in range(12)], r
    assert peak == 3, "peak concurrency %d" % peak
    assert await gather_limited([], 2) == []
    started = 0
    try:
        await gather_limited([mk(i, fail=(i == 1)) for i in range(20)], 2)
        raise SystemExit("no exception was raised")
    except ValueError:
        pass
    s = started
    await asyncio.sleep(0.2)
    assert started == s and s < 20, "tasks started after the failure: %d then %d" % (s, started)
    assert running == 0, "%d task(s) left running" % running
asyncio.run(asyncio.wait_for(main(), 20))

print('ALL-OK')

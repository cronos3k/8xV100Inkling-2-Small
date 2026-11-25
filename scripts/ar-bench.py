#!/usr/bin/env python3
"""ar-bench.py STORE_FILE WORLD [GPU,GPU,...]

Measure the all-reduce the engine uses at tensor-parallel WORLD (NCCL through torch.distributed), for the
message sizes of one Inkling-2-Small decode step and one prefill chunk, plus raw card-to-card copy speed for
an NVLink pair and a PCIe pair. Run with NCCL_DEBUG=INFO to see the rings NCCL builds.
"""
import os, sys, time
import torch
import torch.distributed as dist
import torch.multiprocessing as mp

SIZES = [("decode output 1x4608", 4608), ("decode activation 8x2304", 8 * 2304),
         ("prefill output 512x4608", 512 * 4608), ("prefill activation 512x8x2304", 512 * 8 * 2304)]


def worker(rank, world, gpus, store):
    torch.cuda.set_device(gpus[rank])
    dist.init_process_group("nccl", init_method="file://" + store, world_size=world, rank=rank)
    dev = torch.device("cuda", gpus[rank])
    for name, n in SIZES:
        x = torch.ones(n, dtype=torch.float16, device=dev)
        reps = 400 if n < 100000 else 40
        for _ in range(20):
            dist.all_reduce(x.clone())
        torch.cuda.synchronize()
        dist.barrier()
        t0 = time.perf_counter()
        for _ in range(reps):
            y = x.clone()
            dist.all_reduce(y)
        torch.cuda.synchronize()
        dt = (time.perf_counter() - t0) / reps
        if rank == 0:
            print("RESULT tp%d  %-32s %9d bytes  %8.1f us per all-reduce  (sum check %s)" % (
                world, name, n * 2, dt * 1e6, "ok" if float(y[0]) == world else "WRONG"), flush=True)
    dist.destroy_process_group()


def copies():
    n = 256 * 2**20
    for a, b, kind in ((0, 1, "NVLink x2"), (0, 3, "NVLink x1"), (0, 5, "PCIe across sockets")):
        src = torch.empty(n, dtype=torch.uint8, device="cuda:%d" % a).random_()
        dst = torch.empty(n, dtype=torch.uint8, device="cuda:%d" % b)
        dst.copy_(src); torch.cuda.synchronize(a); torch.cuda.synchronize(b)
        t0 = time.perf_counter()
        for _ in range(10):
            dst.copy_(src)
        torch.cuda.synchronize(a); torch.cuda.synchronize(b)
        print("RESULT copy card %d to card %d (%s): %.1f GB/s" % (a, b, kind, 10 * n / (time.perf_counter() - t0) / 1e9), flush=True)
        del src, dst


if __name__ == "__main__":
    store, world = sys.argv[1], int(sys.argv[2])
    gpus = [int(g) for g in sys.argv[3].split(",")] if len(sys.argv) > 3 else list(range(world))
    if world == 0:
        copies()
        sys.exit(0)
    if os.path.exists(store):
        os.replace(store, store + ".old")
    mp.set_start_method("spawn")
    ps = [mp.Process(target=worker, args=(r, world, gpus, store)) for r in range(world)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()

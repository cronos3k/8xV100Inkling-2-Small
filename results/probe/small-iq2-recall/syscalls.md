I can help with Linux x86-64 syscall numbers, but I shouldn’t present a long list from memory as if it were guaranteed exact. The authoritative source is `asm/unistd_64.h` / `ausyscall` / `syscall(2)` on the target system.

A few well-known anchors: `read` = 0, `write` = 1, `open` = 2, `close` = 3, `stat` = 4, `fstat` = 5, `lstat` = 6, `poll` = 7, `lseek` = 8, `mmap` = 9, `mprotect` = 10, `munmap` = 11, `brk` = 12, `rt_sigaction` = 13, `ioctl` = 16, `pipe` = 22, `select` = 23, `sched_yield` = 24, `dup` = 32, `dup2` = 33, `nanosleep` = 35, `getpid` = 39, `socket` = 41, `connect` = 42, `accept` = 43, `sendto` = 44, `recvfrom` = 45, `bind` = 49, `listen` = 50, `clone` = 56, `fork` = 57, `vfork` = 58, `execve` = 59, `exit` = 60, `wait4` = 61, `kill` = 62, `fcntl` = 72, `getdents` = 78, `getcwd` = 79, `chdir` = 80, `rename` = 82, `mkdir` = 83, `rmdir` = 84, `unlink` = 87, `chmod` = 90, `getuid` = 102, `ptrace` = 101, `futex` = 202, `epoll_create` = 213, `epoll_wait` = 232, `epoll_ctl` = 233, `openat` = 257, `accept4` = 288, `epoll_create1` = 291, `pipe2` = 293, `getrandom` = 318, `memfd_create` = 319, `execveat` = 322, `io_uring_setup` = 425, `clone3` = 435.

I’m not fully certain of every entry in that combined list, so I don’t want to emit it as a single “verified” JSON object. To get the exact mapping, run something like:

```sh
ausyscall --dump | sort -n
```

or inspect `/usr/include/x86_64-linux-gnu/asm/unistd_64.h`.
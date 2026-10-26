#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/syscall.h>
int main(void) {
#ifdef SYS_kexec_file_load
    errno = 0;
    long rc = syscall(SYS_kexec_file_load, -1, -1, 0UL, (const char *)0, 0UL);
    printf("kexec_file_load with invalid fds: return=%ld errno=%d (%s)\n", rc, errno, strerror(errno));
#endif
#ifdef SYS_kexec_load
    errno = 0;
    /* Unknown flag bits force rejection before any load or unload operation. */
    long rc2 = syscall(SYS_kexec_load, 0UL, 0UL, (const void *)0, ~0UL);
    printf("kexec_load with invalid flags: return=%ld errno=%d (%s)\n", rc2, errno, strerror(errno));
#endif
    return 0;
}

/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Minimal user-space stand-ins for the kernel APIs used by bcm4360_data_fw.c. */
#ifndef KSHIM_H
#define KSHIM_H
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int32_t s32;
typedef size_t gfp_t;

#define GFP_KERNEL 0
#define SZ_1M 0x00100000
#define BIT(n) (1UL << (n))
#define BUILD_BUG_ON(c) _Static_assert(!(c), "BUILD_BUG_ON")
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define MODULE_FIRMWARE(x)
#ifndef EBADMSG
#define EBADMSG 74
#endif

struct device { const char *name; };
struct firmware { size_t size; const u8 *data; };
struct mutex { int dummy; };
#define DEFINE_MUTEX(m) struct mutex m
static inline void mutex_lock(struct mutex *m) { (void)m; }
static inline void mutex_unlock(struct mutex *m) { (void)m; }

static inline void *kzalloc(size_t n, gfp_t f) { (void)f; return calloc(1, n); }
static inline void kfree(const void *p) { free((void *)p); }

static inline u16 get_unaligned_le16(const void *p)
{ const u8 *b = p; return b[0] | (b[1] << 8); }
static inline u32 get_unaligned_le32(const void *p)
{ const u8 *b = p; return b[0] | (b[1] << 8) | (b[2] << 16) | ((u32)b[3] << 24); }

static inline u32 crc32_le(u32 crc, const u8 *p, size_t len)
{
	size_t i; int k;
	for (i = 0; i < len; i++) {
		crc ^= p[i];
		for (k = 0; k < 8; k++)
			crc = (crc >> 1) ^ (0xedb88320u & -(crc & 1));
	}
	return crc;
}

#define dev_err(dev, fmt, ...) fprintf(stderr, "dev_err: " fmt, ##__VA_ARGS__)

/* Provided by the test program. */
int firmware_request_nowarn(const struct firmware **fw, const char *name,
			    struct device *dev);
void release_firmware(const struct firmware *fw);
#endif

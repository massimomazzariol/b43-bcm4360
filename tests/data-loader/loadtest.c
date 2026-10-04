// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * Host test for the b43 BCM4360 data loader (bcm4360_data_fw.c).
 *
 * usage: loadtest <fwdir> <chip_id> <phy_rev> <radio_ver> <radio_rev>
 *                 <cores> <board_file> <board_tag>
 *
 * Loads the chip/radio and board packages from <fwdir> through the
 * unmodified loader source and prints the resulting data sets in a
 * canonical text form, or "error <errno>".
 */
#include "kshim.h"

#include "bcm4360.h"

static const char *fwdir;

int firmware_request_nowarn(const struct firmware **fw, const char *name,
			    struct device *dev)
{
	char path[4096];
	struct firmware *f;
	FILE *fp;
	long n;

	(void)dev;
	snprintf(path, sizeof(path), "%s/%s", fwdir, name);
	fp = fopen(path, "rb");
	if (!fp)
		return -ENOENT;
	fseek(fp, 0, SEEK_END);
	n = ftell(fp);
	fseek(fp, 0, SEEK_SET);
	f = calloc(1, sizeof(*f));
	f->data = malloc(n ? n : 1);
	f->size = fread((void *)f->data, 1, n, fp);
	fclose(fp);
	*fw = f;
	return 0;
}

void release_firmware(const struct firmware *fw)
{
	if (!fw)
		return;
	free((void *)fw->data);
	free((void *)fw);
}

static void dump_tbl(const char *what, const struct b43_phy_ac_tbl *t)
{
	unsigned int i;

	printf("%s id=%u offset=0x%04x width=%u count=%u:", what, t->id,
	       t->offset, t->width, t->count);
	for (i = 0; i < t->count; i++) {
		if (t->width == 32)
			printf(" %08x", ((const u32 *)t->data)[i]);
		else if (t->width == 16)
			printf(" %04x", ((const u16 *)t->data)[i]);
		else
			printf(" %02x", ((const u8 *)t->data)[i]);
	}
	printf("\n");
}

static void dump_u8(const char *what, const u8 *v, unsigned int n)
{
	unsigned int i;

	printf("%s:", what);
	for (i = 0; i < n; i++)
		printf(" %02x", v[i]);
	printf("\n");
}

int main(int argc, char **argv)
{
	struct b43_bcm4360_board board = { 0 };
	const struct b43_bcm4360_data *d;
	const struct b43_bcm4360_board_data *bd;
	struct device dev = { "test" };
	unsigned int i, w;
	int err;

	if (argc != 9) {
		fprintf(stderr, "usage: see source\n");
		return 2;
	}
	fwdir = argv[1];
	board.name = "test";
	board.chip_id = strtoul(argv[2], NULL, 0);
	board.phy_rev = strtoul(argv[3], NULL, 0);
	board.radio_ver = strtoul(argv[4], NULL, 0);
	board.radio_rev = strtoul(argv[5], NULL, 0);
	board.cores = strtoul(argv[6], NULL, 0);
	board.data_file = argv[7];
	board.data_tag = argv[8];

	err = b43_bcm4360_data_get(&board, &dev, &d, &bd);
	if (err) {
		printf("error %d\n", err);
		return 1;
	}

	for (i = 0; i < d->n_init_tables; i++)
		dump_tbl("init", &d->init_tables[i]);
	for (i = 0; i < d->n_chan_tables; i++)
		dump_tbl("chan", &d->chan_tables[i]);
	for (i = 0; i < d->n_rfseq7; i++)
		dump_tbl("rfseq7", &d->rfseq7[i]);
	for (i = 0; i < d->n_prefregs; i++)
		printf("prefreg %04x=%04x\n", d->prefregs[i].reg,
		       d->prefregs[i].value);
	for (i = 0; i < d->n_chan_2g; i++) {
		printf("chan_2g[%u]:", i);
		for (w = 0; w < B43_BCM2069_REV4_CHAN_WORDS; w++)
			printf(" %04x", d->chan_2g[i][w]);
		printf("\n");
	}
	for (i = 0; i < d->n_farrow_2g; i++)
		printf("farrow[%u] %04x %04x\n", i, d->farrow_2g[i].deltaphase_lo,
		       d->farrow_2g[i].deltaphase_hi);
	dump_u8("lna1_gain", d->rx_gain_tables->lna1_gain, 6);
	dump_u8("lna1_gainbits", d->rx_gain_tables->lna1_gainbits, 6);
	dump_u8("lna1_gainlimit", d->rx_gain_tables->lna1_gainlimit, 6);
	dump_u8("lna2_gain", d->rx_gain_tables->lna2_gain, 7);
	dump_u8("lna2_gainbits", d->rx_gain_tables->lna2_gainbits, 7);
	dump_u8("lna2_gainlimit", d->rx_gain_tables->lna2_gainlimit, 7);
	dump_u8("mix_gain", d->rx_gain_tables->mix_gain, 10);
	dump_u8("mix_gainbits", d->rx_gain_tables->mix_gainbits, 10);
	if (d->rx_evm) {
		dump_u8("rx_evm_lo", d->rx_evm->lo, 3);
		dump_u8("rx_evm_hi", d->rx_evm->hi, 3);
	} else {
		printf("rx_evm none\n");
	}
	for (i = 0; i < bd->n_fem_cores; i++) {
		char what[32];

		snprintf(what, sizeof(what), "fem_lut[%u]", i);
		dump_u8(what, bd->fem_lut[i], 32);
	}
	printf("elna_gain_db %u trloss_db %u\n", bd->rx_gain->elna_gain_db,
	       bd->rx_gain->trloss_db);
	printf("gain_code_a:");
	for (i = 0; i < 5; i++)
		printf(" %04x", bd->rx_gain->gain_code_a[i]);
	printf("\ngain_code_b:");
	for (i = 0; i < 5; i++)
		printf(" %04x", bd->rx_gain->gain_code_b[i]);
	printf("\nrfseq_init_gain %04x\n", bd->rx_gain->rfseq_init_gain);

	b43_bcm4360_data_release();
	return 0;
}

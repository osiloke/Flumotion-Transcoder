/*
 * Compile with:
 *
 * gcc -o mmf-crc `pkg-config --libs --cflags glib` mmf-crc.c
 *
 * (C) Fluendo SA.
 */
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>

#include <glib.h>

typedef struct
{
  guint8 tag[4];
  guint32 size;
} MMFChunk;

static guint16 crctable[256];

#define CRCPOLY1 0x1021U

static void
make_crc_table (void)
{
  guint16 i, j, r;

  for (i=0; i < 256; i++) {
    r = i << 8;
    for (j=0; j < 8; j++) {
      if (r & 0x8000U) 
        r = (r<<1) ^ CRCPOLY1;
      else
        r <<= 1;
    }
    crctable[i] = r & 0xFFFFU;
  }
}

static guint16 
calc_crc(int n, guint8* c)
{
  guint16 r;

  r = 0xFFFFU;
  while (--n >= 0) {
     r = (r << CHAR_BIT) ^ crctable[(guint8)(r >> (16 - CHAR_BIT)) ^ *c++];
  }
  return ~r & 0xFFFFU;
}

/*
 * A chunk has a 32 bit tag and a 32 bit big endian size.
 */
static int
read_chunk_header (guint8 *memp, guint8 *endp, MMFChunk *chunk)
{
  /* we need at least 8 bytes */
  if (memp + 8 >= endp)
    return -1;

  chunk->tag[0] = *memp++;
  chunk->tag[1] = *memp++;
  chunk->tag[2] = *memp++;
  chunk->tag[3] = *memp++;

  chunk->size  = ((guint32)*memp++) << 24;
  chunk->size |= ((guint32)*memp++) << 16;
  chunk->size |= ((guint32)*memp++) << 8;
  chunk->size |= ((guint32)*memp++);

  return 0;
}

static void
print_chunk (gchar *prefix, MMFChunk *chunk)
{
  g_print ("%sTAG: %-4.4s, size: %d\n", prefix, chunk->tag, chunk->size);
}

/*
 * We patch the input file in-place with an updated CRC.
 * 
 * If there is no CRC in the file, the MMMD header is patched to include 2
 * additional bytes for the CRC, which we add at the end of the file.
 *
 * If there was room for the CRC in the file, we check if it is correct and fix
 * it in case there is a difference.
 */
int main (int argc, char *argv[])
{
  int file, toread;
  gint mmmd_size, total;
  struct stat buf;
  guint8 *mem, *p, c;
  guint8 *memp, *endp;
  guint16 crc, file_crc;
  MMFChunk chunk;
  int crc_offset;

  if (argc < 2) {
    printf ("usage: %s <infile>\n", argv[0]);
    return -1;
  }

  make_crc_table();

  file = open (argv[1], O_RDWR);
  fstat(file, &buf);

  printf ("input file size: %d\n", buf.st_size);

  /* read file in memory */
  mem = p = malloc (buf.st_size);
  toread = buf.st_size;
  while (toread) {
    int got;
    
    got = read (file, mem, toread);

    toread -= got;
    p += got;
  }

  memp = mem;
  endp = mem + buf.st_size;

  if (read_chunk_header (memp, endp, &chunk) < 0)
    goto invalid;

  print_chunk (" ", &chunk);

  /* Check for MMMD */
  if (strncmp ("MMMD", chunk.tag, 4))
    goto invalid;

  memp += 8;
  mmmd_size = chunk.size;

  /* read tags inside the MMMD chunk */
  total = 0;
  while (TRUE) {
    if (read_chunk_header (memp, endp, &chunk) < 0)
      break;
    print_chunk ("  ", &chunk);

    memp += chunk.size + 8;
    total += chunk.size + 8;
  }
  g_print ("MMMD size: %d\n", mmmd_size);
  g_print ("total content size: %d\n", total);

  /* This is where we need to write the CRC, after all the data. */
  crc_offset = total + 8;

  /* this is invalid */
  if (total >= mmmd_size + 8)
    goto invalid;

  /* there is room for a CRC, check it */
  if (mmmd_size - total == 2) {
    /* Calculate CRC over all previous data */
    crc = calc_crc (crc_offset, mem);
    g_print ("file needs crc %04x\n", crc);

    file_crc = (*memp++ << 8);
    file_crc |= *memp++;

    g_print ("file has crc %04x...", file_crc);
    if (file_crc == crc) {
      g_print ("ok\n");
      /* reset CRC offset so we don't rewrite the CRC */
      crc_offset = 0;
    }
    else {
      g_print ("wrong, fixing...\n");
    }
  }
  else {
    /* patch mmmd box to the size of its content + 2 for the CRC */
    mmmd_size = total + 2;
    mem[4] = (mmmd_size >> 24) & 0xff;
    mem[5] = (mmmd_size >> 16) & 0xff;
    mem[6] = (mmmd_size >> 8) & 0xff;
    mem[7] = (mmmd_size) & 0xff;

    g_print ("file has no crc, fixing header to size %d\n", mmmd_size);
    lseek (file, 4, SEEK_SET);
    write (file, &mem[4], 4);

    /* Calculate CRC over all previous data again */
    crc = calc_crc (crc_offset, mem);
    g_print ("file needs crc %04x\n", crc);
  }

  if (crc_offset != 0) {
    g_print ("writing CRC %04x\n", crc);
    /* write CRC */
    lseek (file, crc_offset, SEEK_SET);
    c = (crc >> 8) & 0xff;
    write (file, &c, 1);
    c = crc & 0xff;
    write (file, &c, 1);
  }
  close (file);

  return 0;

invalid:
  {
    g_printerr ("invalid file\n");
    return -1;
  }
}


/*
vram_pick_selftest - the adapter-matching code of the gl2 video-memory readout (renderergl2/tr_hzm_vram_pick.h,
compiled here unchanged) against recorded adapter lists of machines we do not own. build.bat compiles and runs it;
exit code 0 = every case picked the adapter the game would be drawing on.

The descriptors are the DXGI_ADAPTER_DESC1 fields those machines report (name, PCI vendor / device, dedicated and
shared MB) and the GL_VENDOR / GL_RENDERER strings their OpenGL drivers return. HZM_MENU_ENG picks the engine tree.
*/
#include <stdio.h>
#include "tr_hzm_vram_pick.h"

#define SW                                                                                                             \
    {                                                                                                                  \
        "Microsoft Basic Render Driver", 0x1414, 0x8c, 0, 16300, 0x9001, 0, 1                                          \
    }

typedef struct {
    const char  *what;
    hzmAdapter_t list[5];
    int          n;
    int          haveLuid;
    unsigned int luidLow;
    const char  *glVendor, *glRenderer;
    int          wantIndex;
    const char  *wantHow;
} vcase_t;

static const vcase_t cases[] = {
    {"NVIDIA desktop, LUID from the driver",
     {{"NVIDIA GeForce RTX 4080", 0x10DE, 0x2704, 16048, 16300, 0xD2A1, 0, 0}, SW}, 2, 1, 0xD2A1,
     "NVIDIA Corporation", "NVIDIA GeForce RTX 4080/PCIe/SSE2", 0, "luid"},
    {"NVIDIA desktop, driver without the LUID extension",
     {{"NVIDIA GeForce GTX 1060 6GB", 0x10DE, 0x1C03, 6052, 8150, 0x1111, 0, 0}, SW}, 2, 0, 0,
     "NVIDIA Corporation", "GeForce GTX 1060 6GB/PCIe/SSE2", 0, "name"},
    {"AMD desktop",
     {{"AMD Radeon RX 6700 XT", 0x1002, 0x73DF, 12227, 16300, 0x2222, 0, 0}, SW}, 2, 0, 0,
     "ATI Technologies Inc.", "AMD Radeon RX 6700 XT", 0, "name"},
    {"AMD desktop, older driver naming",
     {{"Radeon RX 580 Series", 0x1002, 0x67DF, 8151, 8150, 0x2223, 0, 0}, SW}, 2, 0, 0,
     "ATI Technologies Inc.", "Radeon RX 580 Series", 0, "name"},
    {"Intel UHD laptop: shared memory only",
     {{"Intel(R) UHD Graphics 620", 0x8086, 0x5917, 128, 8093, 0x3333, 0, 0}, SW}, 2, 0, 0,
     "Intel", "Intel(R) UHD Graphics 620", 0, "name"},
    {"hybrid laptop, game on the NVIDIA card",
     {{"Intel(R) Iris(R) Xe Graphics", 0x8086, 0x9A49, 128, 7990, 0x4441, 0, 0},
      {"NVIDIA GeForce RTX 3060 Laptop GPU", 0x10DE, 0x2520, 5996, 7990, 0x4442, 0, 0}, SW}, 3, 0, 0,
     "NVIDIA Corporation", "NVIDIA GeForce RTX 3060 Laptop GPU/PCIe/SSE2", 1, "name"},
    {"hybrid laptop, game on the INTEGRATED chip (power saving)",
     {{"Intel(R) Iris(R) Xe Graphics", 0x8086, 0x9A49, 128, 7990, 0x4441, 0, 0},
      {"NVIDIA GeForce RTX 3060 Laptop GPU", 0x10DE, 0x2520, 5996, 7990, 0x4442, 0, 0}, SW}, 3, 0, 0,
     "Intel", "Intel(R) Iris(R) Xe Graphics", 0, "name"},
    {"hybrid laptop, LUID says integrated although the card is bigger",
     {{"Intel(R) Iris(R) Xe Graphics", 0x8086, 0x9A49, 128, 7990, 0x4441, 0, 0},
      {"NVIDIA GeForce RTX 3060 Laptop GPU", 0x10DE, 0x2520, 5996, 7990, 0x4442, 0, 0}, SW}, 3, 1, 0x4441,
     "Intel", "Intel(R) Iris(R) Xe Graphics", 0, "luid"},
    {"AMD APU + AMD card (same vendor id), game on the card",
     {{"AMD Radeon(TM) Graphics", 0x1002, 0x1638, 512, 7600, 0x5551, 0, 0},
      {"AMD Radeon RX 6600M", 0x1002, 0x73FF, 8151, 7600, 0x5552, 0, 0}, SW}, 3, 0, 0,
     "ATI Technologies Inc.", "AMD Radeon RX 6600M", 1, "name"},
    {"AMD APU + AMD card, game on the APU",
     {{"AMD Radeon(TM) Graphics", 0x1002, 0x1638, 512, 7600, 0x5551, 0, 0},
      {"AMD Radeon RX 6600M", 0x1002, 0x73FF, 8151, 7600, 0x5552, 0, 0}, SW}, 3, 0, 0,
     "ATI Technologies Inc.", "AMD Radeon(TM) Graphics", 0, "name"},
    {"GL renderer name tells nothing, one card of that vendor",
     {{"Intel(R) HD Graphics 4600", 0x8086, 0x0412, 112, 2048, 0x6661, 0, 0},
      {"NVIDIA GeForce GTX 960M", 0x10DE, 0x139B, 4042, 8100, 0x6662, 0, 0}, SW}, 3, 0, 0,
     "NVIDIA Corporation", "OpenGL Engine", 1, "vendor"},
    {"unknown vendor string, single hardware adapter",
     {{"Some Future GPU 9000", 0x1234, 0x1, 24000, 16000, 0x7771, 0, 0}, SW}, 2, 0, 0,
     "Future Corp", "FutureGL", 0, "only"},
    {"only Microsoft's software adapter (remote session, no driver)",
     {SW}, 1, 0, 0, "Microsoft Corporation", "GDI Generic", -1, "none"},
    {"one card listed three times by virtual-display drivers (the dev PC), no LUID from the driver",
     {{"NVIDIA GeForce RTX 5070 Ti", 0x10DE, 0x2C05, 15995, 16185, 0x18c2e, 0, 0},
      {"NVIDIA GeForce RTX 5070 Ti", 0x10DE, 0x2C05, 15995, 16185, 0x29bd0, 0, 0},
      {"NVIDIA GeForce RTX 5070 Ti", 0x10DE, 0x2C05, 15995, 16185, 0x25b83, 0, 0}, SW}, 4, 0, 0,
     "NVIDIA Corporation", "NVIDIA GeForce RTX 5070 Ti/PCIe/SSE2", 0, "same-card"},
    {"the same PC with the LUID: the one the game draws on, exactly",
     {{"NVIDIA GeForce RTX 5070 Ti", 0x10DE, 0x2C05, 15995, 16185, 0x18c2e, 0, 0},
      {"NVIDIA GeForce RTX 5070 Ti", 0x10DE, 0x2C05, 15995, 16185, 0x29bd0, 0, 0},
      {"NVIDIA GeForce RTX 5070 Ti", 0x10DE, 0x2C05, 15995, 16185, 0x25b83, 0, 0}, SW}, 4, 1, 0x25b83,
     "NVIDIA Corporation", "NVIDIA GeForce RTX 5070 Ti/PCIe/SSE2", 2, "luid"},
    {"two cards nothing tells apart: a guess, and flagged as one",
     {{"Display Adapter", 0x1234, 0x1, 4000, 8000, 0x8881, 0, 0}, {"Display Adapter", 0x1234, 0x2, 8000, 8000, 0x8882, 0, 0}, SW},
     3, 0, 0, "Unknown", "Unknown", 1, "largest"},
};

int main(void)
{
    int i, bad = 0, n = (int)(sizeof(cases) / sizeof(cases[0]));

    for (i = 0; i < n; i++) {
        const vcase_t *c = &cases[i];
        hzmPick_t      p = HZM_VramPickAdapter(c->list, c->n, c->haveLuid, c->luidLow, 0, c->glVendor, c->glRenderer);
        int            ok = (p.index == c->wantIndex);

        /* the APU-on-APU case: the APU's name has no model word, so the name cannot decide between two Radeons; the
           code must then NOT claim certainty unless it is right. Accept index 0 by any method, or a flagged guess. */
        if (!strcmp(c->wantHow, "vendor-or-largest")) {
            ok = (p.index == 0) || p.guess;
        } else if (ok && strcmp(p.how, c->wantHow)) {
            ok = 0;
        }
        printf("%s  %-62s -> %d (%s%s%s) %s\n", ok ? "PASS" : "FAIL", c->what, p.index, p.how, p.guess ? ", guess" : "",
               p.dup ? ", dup" : "",
               p.index >= 0 ? c->list[p.index].name : "-");
        bad += !ok;
    }
    printf("%d of %d cases passed\n", n - bad, n);
    return bad ? 1 : 0;
}

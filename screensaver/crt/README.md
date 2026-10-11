# CRT shaders

ReShade effects for Wine Saver's "Monitor effect" option, run by gamescope
(`--reshade-effect`). They're unmodified copies; at run time
`redmond2k-screensaver.py` writes a version with the source resolution set
to the chosen full-screen size into
`~/.local/share/gamescope/reshade/Shaders/redmond2k/`.

| File | Effect | Author | License | Source |
| --- | --- | --- | --- | --- |
| `CRTLottes.fx` | Shadow mask | Timothy Lottes | Public domain | [RSRetroArch](https://github.com/Matsilagi/RSRetroArch) `73dc21f` |
| `CRTGeom.fx` | Scanlines, curved glass | cgwg, Themaister, DOLLS | GPLv2+ | [RSRetroArch](https://github.com/Matsilagi/RSRetroArch) `73dc21f` |
| `zfast_crt.fx` | Soft scanlines | Greg Hogan (SoltanGris42) | GPLv2+ | [RSRetroArch](https://github.com/Matsilagi/RSRetroArch) `73dc21f` |
| `ReShade.fxh` | Shared header | crosire | CC0-1.0 | [reshade-shaders](https://github.com/crosire/reshade-shaders) (slim) `fd00221` |

The `.fx` files are matsilagi's ReShade ports of the libretro shaders.

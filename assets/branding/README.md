# Cactu identity assets

The original cactus/play mark is drawn in `cactu-video-converter.svg`. Edit that
vector, then run `python scripts/generate_branding_icons.py` with PySide6 available.
The script renders transparent PNG canvases around the dark rounded tile at
16/24/32/48/64/128/256/512 px and a seven-size Windows ICO. The unqualified PNG
is the 256 px Linux AppImage icon. Keep all exports together when replacing the
mark. `check.svg` is a separate small checkbox tick used by the shared Qt theme.

No externally sourced artwork, legal entity, trademark claim or copyright holder
is asserted by these assets. Use the same original mark for the header, window,
launcher, installer and About dialog; do not create per-screen variations.
See [branding rules](../../docs/BRANDING.md) and `scripts/check_branding.py`.

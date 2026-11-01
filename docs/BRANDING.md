# Cactu Video Converter branding

## Identity and ownership

The official name is **Cactu Video Converter**. The distribution, primary CLI
and Linux desktop/icon ID are `cactu-video-converter`; the native executable is
`CactuVideoConverter` (`.exe` on Windows). The tagline is **Smart media conversion**.
Beta display version is **0.1.0-beta.1**; package/numeric forms derive from it. Product constants live in `src/video_converter/product.py`;
version lives in `src/video_converter/__init__.py`. Packaging derives metadata
from them through `scripts/branding_metadata.py`.

The interface is a dark charcoal desktop utility with restrained cactus-green
accents. Surfaces and secondary text stay neutral. There are no invented company,
domain, publisher, copyright or trademark claims. FFmpeg, Qt, x264 and other
third parties keep their names, licenses and notices. Kosmi remains an independent
compatibility preset, rather than the entire product identity.

## Color and widget rules

`src/video_converter/ui/theme.py` is the single UI palette/QSS source.

| Role | Token | Value |
| --- | --- | --- |
| Application | BACKGROUND | `#11171c` |
| Panel / elevation | SURFACE / SURFACE_ELEVATED | `#1a2228` / `#242f37` |
| Border | BORDER | `#475760` |
| Primary / secondary / muted text | TEXT_PRIMARY / TEXT_SECONDARY / TEXT_MUTED | `#edf2f4` / `#b3bfc7` / `#8d9ba4` |
| Text on brand | TEXT_ON_ACCENT | `#0d1c12` |
| Brand / hover / pressed | ACCENT / ACCENT_HOVER / ACCENT_PRESSED | `#5faf6f` / `#6dbc7c` / `#4b9159` |
| Brand wash / border / focus | ACCENT_SUBTLE / ACCENT_BORDER / ACCENT_FOCUS | green at 12% / 35% / 75% |
| Dropdown selection | SELECTION_SURFACE | `#263b30` |
| Success | SUCCESS | `#58c7a0` |
| Warning | WARNING | `#edba59` |
| Error | ERROR | `#ec7378` |
| Information | INFO | `#89b7d2` |
| Disabled text / surface | DISABLED_TEXT / DISABLED_SURFACE | `#7d8a93` / `#1c252b` |
| Progress track | PROGRESS_TRACK | `#303c44` |

Import tokens for custom painting, as QueueDelegate does. Do not introduce
arbitrary purple accents or repeat color literals in new widgets. Use the
`primary` object name for primary actions and `danger` for destructive actions.
Primary buttons have dark text on green, explicit hover/pressed states and a
visible keyboard focus border. Disabled controls are gray. Reset Settings,
Cancel Current, Stop Queue, Remove and Clear Completed retain destructive styling.
A dialog's ordinary Cancel button can remain secondary when it just closes it.

Checked boxes have a tick; selected radios remain circular. Sliders retain a
neutral unfilled track. Inputs, links, dropdowns, selection borders and file-drop
targets use the brand tokens. Queue progress and the shared conversion/preview/
loudness bar use the same green fill; percentages sit outside the main fill so
text remains readable at 0–100%. No progress parser or denominator changed.

Warnings remain amber and errors red. Success uses a distinct emerald, but
status text/icons are mandatory: `▶ Running`, `✓ Completed`, `✕ Failed`, etc.
A selected completed row retains its check/text; selection is a border/wash,
not a substitute for status. Paused state retains its explicit text/icon.

Tests enforce at least 4.5:1 contrast for normal text and primary button text,
including the pressed color. Disabled controls are intentionally muted.

## Original logo and assets

The original SVG combines a rounded cactus silhouette with a dark play cutout
on a charcoal rounded tile. It uses only simple geometry; no external artwork
was downloaded. It is the current project icon, not a borrowed logo or temporary
third-party placeholder. See [asset instructions](../assets/branding/README.md).

Canonical source: `assets/branding/cactu-video-converter.svg`. PNG exports cover
16, 24, 32, 48, 64, 128, 256 and 512 pixels; the base PNG is 256 pixels. The ICO
contains seven resolutions through 256. `check.svg` is the theme's checkbox mark.
Regenerate exports with `python scripts/generate_branding_icons.py` after editing
the SVG. Keep its green aligned with ACCENT when changing the palette.

`ui/branding.py` locates assets in source checkouts, installed wheel data under
`share/cactu-video-converter/branding`, or frozen `assets/branding` under
`_MEIPASS`. Third-party notices follow the same source/wheel/frozen lookup. Qt uses the SVG at arbitrary DPI; native launchers use the exports.
The Settings grid avoids a long single row of actions; About retains application,
FFmpeg and FFprobe versions, attribution and access to third-party notices.

## Preferences migration

Startup sets both the Qt organization and application identity to
`Cactu Video Converter` before creating windows. This organization string is a
technical preference namespace, not a legal publisher. The desktop file name is
`cactu-video-converter`; no reverse-domain namespace is invented.

`services/settings_migration.py` checks the former organization/application pair
`Video Converter` once. If the new store is empty, it imports validated geometry,
two splitter sizes, recognized encoder backend and the last input/subtitle/bulk
output directory hints. It does not require those old directories to still exist.
It does not copy jobs, commands, measurements, external subtitle files or arbitrary
keys. Legacy settings remain untouched. Nonempty new settings always win.
`legacy_settings_migrated` and `settings_schema_version=1` prevent repeat imports.
Reset Settings preserves these markers so discarded old preferences stay discarded.

Normal Qt platform paths apply: Linux uses the new organization/application config
path, Windows the equivalent user registry identity. Startup logs identify the new
product; the log directory follows Qt's new application identity. Old log files
remain where they were, without being copied or deleted.

## Platform packaging and upgrades

| Platform | Deliverable / integration |
| --- | --- |
| Windows executable | `CactuVideoConverter.exe` |
| Windows installer | `CactuVideoConverter-Setup-<version>.exe` |
| Linux AppImage | `CactuVideoConverter-<version>-x86_64.AppImage` |
| Linux desktop/icon | `cactu-video-converter.desktop` / `cactu-video-converter` |
| Python wheel | `cactu_video_converter-<version>-py3-none-any.whl` |

Windows ProductName, FileDescription, InternalName, OriginalFilename and version
resources derive from product metadata. No CompanyName/publisher is added.
The Inno setup uses the new visible name, shortcuts, icon and uninstall icon.
It explicitly preserves `AppId=Video Converter`: the old installer had no explicit
AppId, whose default was AppName. `UsePreviousAppDir=yes` retains an existing
installation's directory when recognized. New installs use the Cactu directory.
Only the known old executable and two old shortcuts are removed during upgrade;
there is no broad removal of user files. The Python distribution rename can coexist
with an old distribution; uninstall the old development distribution before
installing the new one to avoid overlapping internal package files.

See Inno's [AppId](https://jrsoftware.org/ishelp/topic_setup_appid.htm) and
[UsePreviousAppDir](https://jrsoftware.org/ishelp/topic_setup_usepreviousappdir.htm)
references. Native upgrade/uninstall verification is still required on Windows.
Linux AppRun, desktop metadata, root AppImage icon and hicolor exports use the
new names. The build script derives artifact versions, rather than repeating 0.1.0.
The CI workflow runs branding smoke checks on Linux and Windows; it currently
has no release artifact upload job to rename.

## Deliberately preserved technical identifiers

- `video_converter`: Python imports, module launch, logger namespace and spec file.
- `video-converter`: compatibility CLI alias, log basename, temporary prefixes
  and internal queue MIME type. These are not visible product branding.
- `Video Converter`: legacy settings/installer identity and exact old shortcut
  names needed for safe migration; historical documentation only elsewhere.
- User output rules, including `Movie-Kosmi.mp4`, remain unchanged.

No planner, command builder, encoder adapter, audio filter, subtitle pipeline,
loudness cache, runner, queue scheduler, output verifier or media naming rule was
changed for this rebrand. The runtime's reinstall message uses the new product name.
Notifications are not implemented; future notifications must use PRODUCT_NAME.

## Visual review

Current screenshots below are actual Qt renders of synthetic UI jobs, not proof
that those fictitious two-hour episodes were converted. Conversion evidence is
in the automated media suite. The original supplied purple mockup and original
implementation plan are explicitly historical references.

- [Main queue](assets/batch-queue-ui.png), [audio/subtitle settings](assets/batch-queue-settings.png)
- [Empty queue](assets/cactu-empty.png), [running job](assets/cactu-running.png)
- [Loudness settings](assets/loudness-ui.png), [analysis progress](assets/cactu-analysis.png)
- [Quick Preview](assets/cactu-preview.png), [control states](assets/cactu-controls.png)
- [Settings](assets/cactu-settings.png), [About](assets/cactu-about.png)
- [Hardware diagnostics](assets/cactu-diagnostics.png), [job details](assets/cactu-job-details.png)
- [Error dialog](assets/cactu-error.png), [inline completion summary](assets/cactu-completed.png)

Review covers 100%, 125%, 150% and 200% Qt scale factors, including the small icon
sizes, selected/disabled controls and narrow Settings dialog. Native file dialogs
follow the desktop's theme; they are not custom painted by the application.
Native titlebar/taskbar/different font rendering remains a platform smoke gate.
See [implementation report](IMPLEMENTATION_REPORT.md) for exact tests and limits.

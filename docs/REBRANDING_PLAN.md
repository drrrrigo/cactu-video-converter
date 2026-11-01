# Cactu Video Converter rebranding plan

## Audit before implementation

The old product is Video Converter, version 0.1.0, with purple/lilac brand
colors. The main theme contains purple focus/buttons/progress/selection;
QueueDelegate repeats purple and border literals. The Linux SVG/PNG is a purple
play mark. MainWindow/header/About, QApplication identities and startup logs
use the old name. QSettings keys include geometry, queue_splitter,
last_input_dir, last_subtitle_dir, bulk_output_dir and preferred_encoder_backend.
The old organization and application are both `Video Converter`.

Packaging uses VideoConverter executable/dist/AppDir names, an Inno installer
without explicit AppId, a generated Linux desktop entry and a hard-coded release
version. The Python distribution and CLI are video-converter; imports use
video_converter. CI currently runs source checks and has no release artifacts.
README and build docs use the old CLI; historical plans/mockups/screenshots also
record the earlier identity. No notification implementation exists to rename.
No approved bundled FFmpeg manifest/native release exists. PyInstaller,
appimagetool and ISCC are unavailable locally; desktop-file-validate is present.

## Identity and color decisions

Display name: **Cactu Video Converter**. Slug/distribution/primary CLI:
`cactu-video-converter`. Executable: `CactuVideoConverter`. Keep version 0.1.0.
Add a single product metadata module and derive build names/version metadata
where possible. Keep the Python package, technical logger namespaces, temporary
file prefixes, internal queue MIME and hardware-test environment variable for
compatibility. Keep the old CLI as a documented compatibility alias.

Replace the theme with centralized neutral charcoal surfaces, near-white text,
cactus #5FAF6F / hover #6DBC7C / pressed #4B9159, subtle green selection/focus
and neutral progress tracks. Use dark text on filled green buttons for contrast.
Success, warning, error, information and disabled colors remain separate tokens.
Style hover/pressed/focus/disabled controls explicitly, including slider handles,
checkbox/radio marks, dropdown selections, queue rows and drag highlights. Queue
custom painting must consume theme tokens. Preserve icon/text status semantics.

## Icon and assets

Create an original geometric cactus with a play-shaped negative space, without
external artwork or raster generation. Canonical SVG and generated PNG/ICO
assets live in assets/branding. Use Qt SVG rendering to export standard small
sizes and a multi-resolution Windows ICO. Load the same source icon in the app,
header, PyInstaller, installer and Linux launcher. Document replacing the SVG
and regeneration without widget changes. Include installed-package asset lookup
and PyInstaller data lookup. Inspect 16/24/32/48/128/256 px and HiDPI renders.

## Settings migration

Use new organization/application identity Cactu Video Converter (a technical
namespace, not a legal company claim). On startup, before opening MainWindow,
copy only known compatible keys from legacy QSettings if the new store is empty.
Do not copy queue/jobs, concrete subtitles or unknown transient values. Validate
basic value shapes, preserve the legacy store, and mark migration/schema version
even when no copy is needed. Never overwrite nonempty/new settings on later runs.

## Packaging and upgrades

Update distribution name, executable, installer shortcuts/display/version fields,
AppRun, desktop file/icon and artifact naming. Use centralized metadata to
generate Inno definitions and Windows version resources; no CompanyName or
publisher/copyright owner will be invented. Preserve the old Inno default AppId
explicitly as `Video Converter`: Inno defaults it to AppName, so changing it
would break upgrade recognition. Preserve existing install-directory behavior;
remove only known old executable/shortcut names on upgrade. Native upgrade
execution remains unverified until Windows tooling is available.

Linux uses the project slug as the desktop ID (no invented domain). Keep the
FFmpeg staging paths and release validation unchanged. Add metadata/asset smoke
checks for both platform configurations that do not need native installer tools;
attempt the native Linux build and report the unchanged release-gate failure.
Do not claim that structural checks produce working Windows installers/AppImages.

## Documentation and verification

Update active documentation/product descriptions/commands and regenerate current
screenshots. Preserve the supplied mockup and explicitly historical planning
artifacts as old-identity references; label/link them appropriately. Preserve all
third-party names/attributions. Add BRANDING.md and code-review/report sections.

Test product constants, theme/contrast, title/icon and About metadata, one-time
migration (including nonempty new settings), icon dimensions and both packaging
configurations without native tool dependencies. Render populated/empty queue,
running and loudness progress, preview, audio/subtitles, hardware/diagnostic,
settings and error/success dialog states at common sizes and HiDPI factors.
Run the complete existing media suite, including real RX 7700 XT tests with host
access, to verify that conversion behavior remains unchanged. No planner,
command-builder, FFmpeg/audio/subtitle/queue scheduling logic will be modified.

## Risks and limits

Muted green must retain text/control contrast; disabled selectors must not look
active. Brand and success both use green families, so selection borders and
status text/icons remain mandatory. SVG detail must survive small icons.
Settings migration must precede reads and never replace new preferences. Native
Windows installer metadata/upgrades and Linux AppImage runtime remain release
verification gates; all such limitations will be explicit in the report.

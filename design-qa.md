# Design QA — image rendering hotfix

- Source visual truth: user-provided conversation appshot, `RimWorld-Autopilot Appshot 2026-09-22T14-54-12.988Z.jpg`.
- Implementation screenshot: `artifacts/ui-after-render-fix.png`.
- Focused hero evidence: `artifacts/ui-after-render-fix-hero.png`.
- Viewport: native Windows desktop window, source 1440 × 931 px; implementation 1456 × 939 px including the Windows frame.
- Density normalization: both captures were inspected at their native 1:1 pixel density. This is a native Tk desktop application, so CSS size and browser device scale factor do not apply.
- State: Russian Overview screen, RimWorld unavailable, Laya stopped, version 0.0.2.

## Full-view comparison evidence

The revised application preserves the source layout and information hierarchy. The generated mascot, navigation icons, flags, and colony panorama now render as the intended artwork. The hero artwork fills the available banner width instead of occupying a partial fixed-size region. No controls overflow or disappear at the tested 1440 × 900 application geometry.

## Focused-region comparison evidence

The focused hero capture shows a continuous edge-to-edge crop, smooth detail at native display density, and visible rounded corners on all four sides. Text remains readable over the image and is not rasterized into the artwork.

## Findings

- No remaining P0, P1, or P2 mismatch was found for the requested rendering changes.
- Typography: Segoe UI hierarchy, weights, line lengths, and antialiasing remain consistent with the existing interface.
- Spacing and layout: the hero fills its responsive content width; card padding, border, shadow, and 18 px corner radius are coherent.
- Colors and tokens: the dark navy palette, cyan accent, violet action color, and semantic status colors are preserved.
- Image quality: artwork is decoded with Pillow and resized using Lanczos filtering; the hero uses a cover crop and a supersampled alpha mask for smooth rounded corners.
- Copy: Russian labels and the requested hero copy are unchanged.
- Motion: the mascot/orbit loop is real-time based and schedules frames every 16 ms (approximately 60 FPS), replacing the previous 70 ms tick loop.

## Comparison history

1. Earlier implementation: fixed-step Tk subsampling produced visibly pixelated assets; the hero used a fixed image size and did not cover the full banner; motion updated every 70 ms.
2. Fixes: introduced high-quality raster rendering, responsive debounced hero resizing, cover cropping, supersampled rounded masking, and real-time 16 ms animation scheduling.
3. Post-fix evidence: `artifacts/ui-after-render-fix.png` and `artifacts/ui-after-render-fix-hero.png`; 61 unit tests, Tk smoke checks, packaged executable build, installation, and native-window capture all passed.

## Implementation checklist

- [x] Replace integer Tk subsampling with Lanczos resizing.
- [x] Render the hero at the live container width.
- [x] Apply a smooth 18 px rounded alpha mask.
- [x] Use cover cropping without stretching.
- [x] Make animation time-based at approximately 60 FPS.
- [x] Verify the packaged and installed executable.

## Follow-up polish

No blocking or moderate visual issues remain in the requested area.

final result: passed

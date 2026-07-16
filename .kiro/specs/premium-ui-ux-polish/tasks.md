# Implementation Plan: Premium UI/UX Polish

## Overview

This plan turns the design system primitives into code incrementally: pure Qt-free token/motion modules first, then the theme QSS refactor, then the reusable state/micro-interaction layer, then adoption across widgets, shell, and pages, and finally the optional native backdrop. Each step builds on the previous one and ends wired into the running app. This is a slimmed-down implementation-only plan focused on core coding tasks; it does not include the optional property/guardrail test sub-tasks. All code is Python 3.14 + PySide6, tested manually headless under `QT_QPA_PLATFORM=offscreen` with `PYTHONPATH=src`.

## Tasks

- [x] 1. Create Qt-free design token foundation (`tokens.py`)
  - [x] 1.1 Implement spacing, radius, and typography token scales
    - Create `src/cortex_unified/ui/premium/tokens.py` (pure Python, no Qt import)
    - Add `Spacing` (8pt base: XXS..XXL), `Radius` (SM/MD/LG/PILL), and `TYPE_ROLES` mapping name → (px_size, weight, letter_spacing)
    - _Requirements: 3.3, 3.4, 3.5_

  - [x] 1.2 Implement elevation scale and per-level style resolver
    - Add `Elevation(IntEnum)` with BACKGROUND/SURFACE/RAISED/OVERLAY levels
    - Add frozen `ElevationStyle` dataclass and `elevation_style(palette, level)` returning surface/border/shadow_blur/shadow_alpha/surface_alpha with monotonic depth cues
    - _Requirements: 12.1, 12.2_

  - [x] 1.3 Implement WCAG contrast utility
    - Add `contrast_ratio(fg_hex, bg_hex)` using WCAG 2.1 relative luminance
    - _Requirements: 10.3, 10.4_

- [x] 2. Create motion system (`motion.py`)
  - [x] 2.1 Implement durations, easing constants, and animation helpers
    - Create `src/cortex_unified/ui/premium/motion.py` (depends only on `PySide6.QtCore`)
    - Add `Duration` (INSTANT=90, FAST=160, NORMAL=220, SLOW=320), `EASING_STANDARD`/`EASING_EMPHASIS`
    - Add `fade_in(widget, duration, on_done)` that uses a `QGraphicsOpacityEffect` removed on `finished`, and `animate_property(target, prop, start, end, duration, easing)`
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 3. Refactor theme to build QSS from tokens (`theme.py`)
  - [x] 3.1 Extend `Palette` with elevation, glass, and gradient token fields
    - Add `surface_raised`, `overlay`, `glass_alpha`, `glass_border`, `accent_grad_stops`, and `glass(level)` helper; provide valid values for both `MIDNIGHT` and `DAYLIGHT`
    - _Requirements: 12.1, 12.3, 12.6, 12.7_

  - [x] 3.2 Rebuild `build_stylesheet` to source spacing/radius/color from tokens
    - Replace scattered literals with `tokens` + `Palette` values; add elevation-aware `QFrame#Card`/`#HeroCard`/`#Glass` surfaces with glass fill and top-highlight border; apply token-styled scrollbars
    - _Requirements: 3.1, 3.2, 5.3, 12.3_

  - [x] 3.3 Add complete control states and focus ring to QSS
    - Add `:hover`, `:pressed`, `:focus`, `:disabled` for buttons (Primary/Ghost/Danger), NavItem, QLineEdit/QComboBox/QSpinBox, QCheckBox, and item-view rows/indicators; add a distinct accent focus outline that differs from hover
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 3.4 Verify `apply_theme` restyles the whole app from one Palette
    - Ensure `apply_theme` remains the single entry point (Fusion + full stylesheet) and stays defensive when Qt/app is absent
    - _Requirements: 3.6_

- [x] 4. Create state panels and micro-interaction helpers (`states.py`)
  - [x] 4.1 Implement `StatePanel` with loading/empty/error/hidden modes
    - Create `src/cortex_unified/ui/premium/states.py`; implement `show_loading`/`show_empty`/`show_error`/`clear` and assertable `mode()`; loading uses indeterminate indicator unless a determinate count is provided; error shows verbatim message with retry affordance
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 2.4, 11.4_

  - [x] 4.2 Implement micro-interaction helpers
    - Add `install_hover_lift(widget, dy, duration)` and `focus_ring(widget)` built on `motion` timings, wrapped so failures fail soft
    - _Requirements: 12.5_

- [x] 5. Checkpoint - Ensure token/motion/theme/state layers pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Make widgets elevation-aware and lock icon caching (`widgets.py`)
  - [x] 6.1 Retarget widget surfaces and animations to tokens/motion
    - Update `Card`/`StatCard`/`CircularGauge`/`Badge` to derive surface/border/shadow from `elevation_style`; retarget `StatCard._pulse` and `CircularGauge.animate_to` to `motion` timings; apply accent gradient to the gauge arc and primary CTA
    - _Requirements: 12.1, 12.2, 12.6, 4.4, 4.5_

  - [x] 6.2 Formalize `icon_for_exe` caching and placeholder fallback
    - Ensure icons are cached by source path (including `None` results) and render a token placeholder glyph when the icon is null; names/icons/descriptions from local system only
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 7. Wire motion, scroll policy, and accessibility helpers into the shell (`window.py`)
  - [x] 7.1 Reimplement page fade-in on the motion system
    - Reimplement `_fade_in` on `motion.fade_in`, keeping a single `_page_anim` reference so only one appearance animation runs per transition
    - _Requirements: 4.2, 4.3, 4.6_

  - [x] 7.2 Formalize `_Page` scroll policy and add `SingleScrollFilter`
    - Card-heavy pages scroll the outer area; list/tree pages give the list a stretch factor and small `minimumHeight`; add reusable `SingleScrollFilter` event filter routing a wheel gesture to one Scroll_Container; use `ScrollBarAsNeeded`
    - _Requirements: 5.1, 5.2, 5.4, 5.5_

  - [x] 7.3 Add keyboard/focus and modal helpers
    - Add `set_tab_order(parent, widgets)` for predictable order, verify primary actions are focusable, and add `run_modal(dialog, trigger)` that returns focus to the trigger on close
    - _Requirements: 10.1, 10.2, 10.6_

- [x] 8. Add optional native backdrop (`backdrop.py`)
  - [x] 8.1 Implement best-effort Mica/Acrylic with graceful degradation
    - Create `src/cortex_unified/ui/premium/backdrop.py` with `apply_backdrop(win)` via `ctypes`/DWM; return applied mode name or `"opaque"`; never raise; call once from `PremiumMainWindow.__init__` after frameless flags are set, with opaque fallback preserving contrast
    - _Requirements: 12.4, 12.8_

- [x] 9. Adopt state panels, scroll policy, and honest progress across pages
  - [x] 9.1 Adopt `StatePanel` on data-backed pages
    - Wire loading on worker start, empty on zero results, error (verbatim `failed` message) with return-to-idle, and result reveal on completion across analysis/system/network/tools/report/more pages
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 9.2 Apply scroll policy and responsive margins to all pages
    - Apply the `_Page` scroll contract and `SingleScrollFilter` to list/tree/table pages; confirm width-to-margin mapping and multi-column card reflow within the viewport; keep aero-snap/edge resize working
    - _Requirements: 5.1, 5.2, 9.1, 9.2, 9.3, 9.4_

  - [x] 9.3 Apply non-color semantic signaling and item placeholders
    - Ensure any semantic-colored status also carries text/label (extend `Badge` policy); use icon/name placeholders for missing item detail
    - _Requirements: 10.5, 8.1, 8.3_

- [x] 10. Enforce non-blocking, cancellable, honest interaction (`workers.py` + pages)
  - [x] 10.1 Verify worker contract and immediate acknowledgment
    - Confirm scan/clean/duplicate/large-file/restore/storage/wipe run on the Worker_Runtime; ensure activation gives feedback (disable + `show_loading`) within the response budget; ensure first-view data loads via `_autoload`; ensure tree expansion computes children off-thread
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7_

  - [x] 10.2 Ensure cancellation and progress honesty
    - Ensure cancellable workers expose `cancel()` + `threading.Event`, pages show an enabled Cancel while running and return to idle; determinate bars use real work-unit counts, otherwise indeterminate; progress text set only from `progress` signals
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- This is a slimmed-down, implementation-focused plan: the optional property-based and guardrail test sub-tasks from the design's Correctness Properties section have been removed to reduce scope. The correctness properties still exist in the design document and can be re-added as test tasks later if desired.
- Each task references specific granular requirements for traceability.
- Two checkpoints (tasks 5 and 11) provide incremental validation points.
- The subjective "premium feel" (real scrolling smoothness, Mica appearance on Windows 11, micro-interaction crispness) is confirmed by manually running `run_gui.py` on the target machine.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "8.1"] },
    { "id": 1, "tasks": ["1.2", "7.1"] },
    { "id": 2, "tasks": ["1.3", "7.2"] },
    { "id": 3, "tasks": ["3.1", "6.1", "7.3"] },
    { "id": 4, "tasks": ["3.2", "6.2"] },
    { "id": 5, "tasks": ["3.3"] },
    { "id": 6, "tasks": ["3.4"] },
    { "id": 7, "tasks": ["4.1"] },
    { "id": 8, "tasks": ["4.2"] },
    { "id": 9, "tasks": ["9.1"] },
    { "id": 10, "tasks": ["9.2"] },
    { "id": 11, "tasks": ["9.3"] },
    { "id": 12, "tasks": ["10.1"] },
    { "id": 13, "tasks": ["10.2"] }
  ]
}
```

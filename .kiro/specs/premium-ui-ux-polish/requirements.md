# Requirements Document

## Introduction

Cortex Cleaner is a Python 3.14 + PySide6 (Qt 6.11) Windows desktop cleaner/optimizer with a frameless custom title bar and a sidebar navigating 41+ pages. The visual foundation already exists: a centralized design-token palette (`theme.Palette` / `MIDNIGHT` / `DAYLIGHT`), a QSS builder, reusable widgets (`Card`, `StatCard`, `CircularGauge`, `Badge`, `TrafficGraph`, `CoreBars`, `attach_glow`), a `_Page` base that wraps content in a scroll area, a subtle page fade-in, and a `run_worker` QThread helper.

This feature is a cross-cutting quality pass that makes the whole app feel "premium and professional": every scroll, click, hover, and state transition should feel smooth, consistent, and honest. It is not a single screen. The goal is to define measurable, enforceable quality attributes for interaction responsiveness, motion, visual consistency, scrolling, interactive control states, loading/empty/error states, and accessibility — without adding any network calls and without any fake progress or gimmicks.

This feature also elevates the visual language to a modern, 2027-grade premium look: layered depth via an elevation scale, refined "glass" (frosted, translucent) surfaces, token-defined accent gradients, and tactile micro-interactions — grounded in current design practice (dark glassmorphism, elevation-driven depth cues, and strict design-token systems) while staying honest about platform limits (true backdrop blur is a progressive enhancement, not a dependency).

The requirements below deliberately favor verifiable criteria (time budgets, token usage, presence of states) that can be exercised under Qt's `offscreen` platform, code-level audits, and existing headless GUI smoke tests, because full "feel" perception requires human review that the acceptance criteria support rather than replace.

## Glossary

- **Cortex_App**: The complete PySide6 desktop application (`cortex_unified.ui.premium`), including the main window, sidebar, title bar, and all pages.
- **UI_Thread**: The Qt main/GUI thread on which the event loop and all widget painting run.
- **Worker_Runtime**: The background execution mechanism (`run_worker` + `QThread`-hosted `QObject` workers in `workers.py`) that performs slow work off the UI_Thread.
- **Design_Tokens**: The centralized style values defined on `theme.Palette` (surfaces, text, accent, semantic colors) plus the shared typography and spacing constants used to build QSS and widgets.
- **Theme_System**: The `theme.py` module that builds and applies a complete stylesheet from a `Palette` (`build_stylesheet`, `apply_theme`), including the dark (`MIDNIGHT`) and light (`DAYLIGHT`) themes.
- **Page**: Any content view derived from the `_Page` base class, reachable via sidebar navigation.
- **Scroll_Container**: The `QScrollArea` (and its viewport) that a `_Page` uses to host scrollable content.
- **Interactive_Control**: Any user-operable widget — buttons, nav items, inputs, combo boxes, checkboxes, list/tree/table rows — that a user can hover, press, or focus.
- **Motion_System**: The set of animations used across the app (page fade-in, gauge sweep, stat-card pulse, hover/press transitions) and their shared duration/easing configuration.
- **Loading_State**: A visible indication that a Page or panel is fetching or computing data.
- **Empty_State**: A visible indication that a completed operation produced no results.
- **Error_State**: A visible indication that an operation failed, including a human-readable message.
- **Response_Budget**: The maximum time between a user input event and the corresponding visible acknowledgment on the UI_Thread.
- **Frame_Budget**: The target maximum time the UI_Thread may spend handling a single event or paint before it is considered a jank/hitch.
- **Focus_Indicator**: A visible style change identifying which Interactive_Control currently holds keyboard focus.
- **Contrast_Ratio**: The WCAG 2.1 relative luminance contrast ratio between a foreground and background color.
- **Elevation_Scale**: A named, ordered set of Design_Tokens describing surface depth (background, base surface, raised surface, overlay/modal) and the shadow/border treatment applied at each level.
- **Glass_Surface**: A translucent, softly-bordered surface treatment (frosted-glass look) used for elevated cards, overlays, and the title bar, achieved with token-defined surface alpha, borders, and elevation — with an optional native backdrop (Windows 11 Mica/Acrylic) as a progressive enhancement that never becomes a functional dependency.
- **Micro_Interaction**: A small, short-duration feedback animation on an Interactive_Control (hover lift, press depress, focus ring bloom, checkbox/toggle transition) governed by the Motion_System.
- **Backdrop_Enhancement**: An optional, platform-specific window-composition effect (e.g. Windows 11 system backdrop) applied behind the Cortex_App content when the OS supports it.

## Requirements

### Requirement 1: Non-blocking interaction responsiveness

**User Story:** As a user, I want the app to respond instantly to my clicks and never freeze, so that it feels premium and I trust that it is working.

#### Acceptance Criteria

1. WHEN a user activates an Interactive_Control that starts a scan, clean, duplicate search, large-file search, restore-point, storage, or wipe operation, THE Cortex_App SHALL execute that operation on the Worker_Runtime rather than on the UI_Thread.
2. WHEN a user activates an Interactive_Control, THE Cortex_App SHALL present a visible acknowledgment (state change, Loading_State, or navigation) within a Response_Budget of 100 milliseconds.
3. WHILE a Worker_Runtime operation is running, THE Cortex_App SHALL keep the UI_Thread able to process input events, window drag, resize, and navigation without blocking.
4. THE Cortex_App SHALL NOT perform filesystem walking, hashing, deletion, subprocess execution, or PowerShell invocation on the UI_Thread.
5. WHEN a Page is displayed for the first time, THE Cortex_App SHALL load that Page's data via the Worker_Runtime so that navigation completes without waiting for data.
6. IF a single UI_Thread event handler exceeds a Frame_Budget of 16 milliseconds during automated audit, THEN THE Cortex_App SHALL be flagged as non-compliant for that handler.
7. WHEN a tree node is expanded, THE Cortex_App SHALL compute the node's children on the Worker_Runtime and apply them to the tree within a Response_Budget of 100 milliseconds of the results arriving.

### Requirement 2: Cancellable and honest progress

**User Story:** As a user, I want to cancel long operations and see only real progress, so that I stay in control and am never shown fake activity.

#### Acceptance Criteria

1. WHILE a cancellable Worker_Runtime operation is running, THE Cortex_App SHALL display an enabled control that requests cancellation.
2. WHEN a user requests cancellation, THE Cortex_App SHALL signal the running worker's cancel event and return the affected Page to an interactive idle state.
3. WHERE a progress indicator reflects a determinate operation, THE Cortex_App SHALL derive the displayed progress value from actual work-unit counts reported by the Worker_Runtime.
4. WHERE an operation's remaining work is not measurable, THE Cortex_App SHALL display an indeterminate progress indicator rather than a synthetic percentage.
5. THE Cortex_App SHALL update displayed progress text only from progress signals emitted by the Worker_Runtime.

### Requirement 3: Consistent visual design tokens

**User Story:** As a user, I want every screen to share the same colors, spacing, and typography, so that the app feels like one cohesive, professional product.

#### Acceptance Criteria

1. THE Cortex_App SHALL derive all surface, text, accent, and semantic colors used in widget styling from Design_Tokens defined on `theme.Palette`.
2. WHERE a widget applies a color, THE Cortex_App SHALL reference a Design_Token rather than a literal hard-coded color value outside the Theme_System and per-widget token-derived styling.
3. THE Cortex_App SHALL apply a single shared typographic scale, defining a fixed set of named text roles (for example page title, section title, metric, body, caption) with consistent size and weight across all Pages.
4. THE Cortex_App SHALL apply spacing between and within surfaces from a single shared spacing scale using a consistent base unit.
5. THE Cortex_App SHALL apply a consistent corner-radius scale to cards, inputs, buttons, and list surfaces.
6. WHEN the Theme_System applies a theme, THE Cortex_App SHALL restyle every Page and Interactive_Control from that single `Palette` without leaving any widget on a prior theme's colors.

### Requirement 4: Consistent motion and animation

**User Story:** As a user, I want smooth, consistent motion throughout the app, so that transitions feel intentional and premium rather than abrupt or random.

#### Acceptance Criteria

1. THE Motion_System SHALL define a single shared set of named animation durations and easing curves used by all animations in the Cortex_App.
2. WHEN a Page becomes visible, THE Cortex_App SHALL animate its appearance using a Motion_System duration in the range of 150 to 300 milliseconds.
3. WHEN an animation completes, THE Cortex_App SHALL remove any temporary graphics effect it added so that the widget returns to its normal rendering path.
4. WHERE a value updates on a metric or gauge as a one-shot result, THE Cortex_App SHALL animate the change using a Motion_System easing curve.
5. WHILE a live metric refreshes on a recurring timer, THE Cortex_App SHALL update the value without a per-update flicker animation.
6. THE Cortex_App SHALL cap concurrent decorative animations so that no more than one appearance animation runs per Page transition.

### Requirement 5: Premium scroll behavior

**User Story:** As a user, I want scrolling to feel smooth and predictable, so that browsing long pages and lists feels polished.

#### Acceptance Criteria

1. WHERE a Page's content exceeds the viewport height, THE Cortex_App SHALL provide vertical scrolling through the Page's Scroll_Container.
2. WHILE a Page contains a fixed hero region and a scrollable region, THE Cortex_App SHALL scroll only the scrollable region and keep the hero region fixed.
3. THE Cortex_App SHALL render scrollbars using the Theme_System scrollbar styling with the Design_Token track and handle colors.
4. WHEN a Page fits within the viewport, THE Cortex_App SHALL NOT display a vertical scrollbar for that Page.
5. THE Cortex_App SHALL route wheel scrolling to a single Scroll_Container per gesture so that nested scrollable regions do not scroll simultaneously.

### Requirement 6: Interactive control states

**User Story:** As a user, I want every button and control to visibly react to hover, press, and keyboard focus, so that the interface feels alive and responsive.

#### Acceptance Criteria

1. WHERE an Interactive_Control is enabled, THE Cortex_App SHALL define a distinct hover style for that control.
2. WHEN a user presses an enabled button, THE Cortex_App SHALL display a distinct pressed style for the duration of the press.
3. WHERE an Interactive_Control can receive keyboard focus, THE Cortex_App SHALL display a Focus_Indicator that is visually distinct from the control's normal and hover styles.
4. WHERE an Interactive_Control is disabled, THE Cortex_App SHALL display a distinct disabled style and SHALL NOT display hover or pressed styling for that control.
5. THE Cortex_App SHALL apply hover, pressed, focus, and disabled styling to all standard Interactive_Control types (buttons, nav items, inputs, combo boxes, checkboxes, list/tree/table rows) from the Theme_System.

### Requirement 7: Loading, empty, and error states

**User Story:** As a user, I want clear feedback while data loads, when there is nothing to show, and when something fails, so that I always understand what the app is doing.

#### Acceptance Criteria

1. WHILE a Page is fetching or computing data through the Worker_Runtime, THE Cortex_App SHALL display a Loading_State on that Page.
2. WHEN a Worker_Runtime operation completes with zero results, THE Cortex_App SHALL display an Empty_State that describes the absence of results.
3. IF a Worker_Runtime operation fails, THEN THE Cortex_App SHALL display an Error_State containing a human-readable message and SHALL return the Page to an interactive idle state.
4. WHEN a Worker_Runtime operation completes with results, THE Cortex_App SHALL replace the Loading_State with the results content.
5. IF an operation fails, THEN THE Cortex_App SHALL keep the UI_Thread responsive and SHALL NOT display a fabricated success outcome.

### Requirement 8: Live process and item detail presentation

**User Story:** As a user, I want lists of processes and files to show real names, icons, and descriptions, so that I can make informed decisions and the app feels trustworthy and refined.

#### Acceptance Criteria

1. WHERE a list row represents an executable or application, THE Cortex_App SHALL display that item's real name and, WHERE available, its native icon.
2. WHERE a native icon is retrieved for an item, THE Cortex_App SHALL cache the icon by source path so that repeated live refreshes do not re-fetch the same icon.
3. IF an item's icon or description is unavailable, THEN THE Cortex_App SHALL display the item using its name and a Design_Token placeholder without raising an error.
4. THE Cortex_App SHALL compute item names, icons, and descriptions using only local system information and SHALL NOT issue network requests to obtain them.

### Requirement 9: Responsive-to-window-size layout

**User Story:** As a user, I want the layout to adapt as I resize the window, so that content stays readable and well-proportioned at any size.

#### Acceptance Criteria

1. WHEN the main window width changes, THE Cortex_App SHALL adjust content margins according to a defined width-to-margin mapping.
2. WHILE the window is at or below a defined narrow-width threshold, THE Cortex_App SHALL keep all primary content and navigation reachable without horizontal scrolling of the overall layout.
3. WHEN the window is resized, THE Cortex_App SHALL reflow multi-column card layouts so that cards remain fully visible within the viewport width.
4. WHERE the frameless window is dragged to a screen edge, THE Cortex_App SHALL support native aero-snap and edge resizing.

### Requirement 10: Accessibility — keyboard, contrast, and focus

**User Story:** As a keyboard and low-vision user, I want to navigate by keyboard, see clear focus, and read text with sufficient contrast, so that the app is usable and genuinely professional.

#### Acceptance Criteria

1. THE Cortex_App SHALL allow every primary action and navigation target to be reached and activated using the keyboard.
2. WHEN a user moves focus with the keyboard, THE Cortex_App SHALL move the Focus_Indicator in a predictable order that follows the visual layout.
3. THE Theme_System SHALL define body-text-to-background token pairs whose Contrast_Ratio meets or exceeds 4.5:1 for the dark and light themes.
4. THE Theme_System SHALL define large-text and essential-UI token pairs whose Contrast_Ratio meets or exceeds 3:1 for the dark and light themes.
5. WHERE information is conveyed by a semantic color (success, warning, danger), THE Cortex_App SHALL also convey that information through text or an accompanying label.
6. WHEN a modal or blocking prompt is shown, THE Cortex_App SHALL move keyboard focus into that prompt and return focus to the triggering control when the prompt closes.

### Requirement 11: Offline and testability guarantees

**User Story:** As a maintainer, I want the polish work to stay fully offline and verifiable headlessly, so that the app remains trustworthy and the quality attributes stay enforced over time.

#### Acceptance Criteria

1. THE Cortex_App SHALL operate without network access for all functionality except the clearly-labeled Software Updater.
2. WHEN UI code executes any polish behavior added by this feature, THE Cortex_App SHALL NOT open network connections.
3. THE Cortex_App SHALL construct and render every Page under Qt's `offscreen` platform without a physical display.
4. THE Cortex_App SHALL expose the Motion_System durations, Design_Tokens, and state indicators in a form that automated headless tests can assert against.

### Requirement 12: Modern premium visual language (depth, glass, and micro-interactions)

**User Story:** As a user, I want a modern 2027-grade visual language with layered depth, refined glass surfaces, and tactile micro-interactions, so that the app looks and feels genuinely premium rather than flat and dated.

#### Acceptance Criteria

1. THE Theme_System SHALL define an Elevation_Scale of at least four ordered levels (window background, base surface, raised surface, overlay/modal) as Design_Tokens, and every surface SHALL derive its background, border, and shadow from its assigned Elevation_Scale level.
2. WHERE a surface is at a higher Elevation_Scale level than the surface beneath it, THE Cortex_App SHALL render it with a visually distinct treatment (lighter surface, stronger border, or larger shadow) so that depth order is perceivable.
3. THE Cortex_App SHALL render elevated cards, overlays, and the title bar as Glass_Surface treatments whose translucency, border, and elevation are derived from Design_Tokens.
4. WHERE the operating system supports a Backdrop_Enhancement, THE Cortex_App SHALL apply it behind the window content; and IF the Backdrop_Enhancement is unavailable or fails, THEN THE Cortex_App SHALL fall back to an opaque token-defined background without error and without loss of functionality.
5. WHEN a user hovers, presses, or focuses an Interactive_Control, THE Cortex_App SHALL play a Micro_Interaction governed by the Motion_System durations and easing (hover feedback within 120 milliseconds).
6. THE Cortex_App SHALL apply the accent as a token-defined gradient (for example the primary call-to-action and the gauge arc) rather than a single flat fill, using Design_Token gradient stops.
7. THE Theme_System SHALL provide the complete modern visual language (Elevation_Scale, Glass_Surface tokens, gradients, micro-interaction timings) for both the dark (`MIDNIGHT`) and light (`DAYLIGHT`) themes.
8. WHERE decorative depth or translucency is applied, THE Cortex_App SHALL preserve the Contrast_Ratio requirements of Requirement 10 for all text rendered on those surfaces.

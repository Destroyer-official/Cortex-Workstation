# NexusExplorer Widget — User-Facing Feature Audit
Source: `src/NexusExplorer/native/nexus_explorer.py` (~8364 lines, widget `ExplorerWidget` + helper classes).
Code refs: `_register_palette_actions()` (~6271), `_bind_shortcuts()` (~6196), `_context_menu()` (~7963), `_smart_folder_context_menu()` (~7305), toolbar setup Tier 1–3 (~5580–5839), `ShortcutsDialog._SHORTCUTS` (~5043).

## Palette actions
`CommandPalette` (`Ctrl+Shift+P` toggle, fuzzy filter, Enter/double-click executes, Esc hides). All registered via `p.register(name, hint, slot)` in `_register_palette_actions` (34 actions):
- `Navigate Back` | hint `Alt+←` | trigger: palette search "Navigate Back" + Enter | effect: `go_back()` — history back.
- `Navigate Forward` | hint `Alt+→` | palette | effect: `go_forward()`.
- `Go Up` | hint `Backspace` | palette | effect: `go_up()` — parent dir.
- `Go Home` | hint `` (none) | palette | effect: `navigate(~)` — home dir.
- `Toggle View` | hint `` | palette | effect: `_toggle_view()` — Details ↔ Large icons.
- `Toggle Flat Branch View` | hint `Ctrl+Shift+F` | palette | effect: `toggle_flat_branch_view()` — recursive Total-Commander flat listing ON/OFF (note: same seq also bound to Find Duplicates).
- `Toggle Dual Pane` | hint `Ctrl+D` | palette | effect: `_toggle_dual_pane()` — show/hide right pane.
- `Quick Look` | hint `Space` | palette | effect: `_quick_look()` — floating `QuickLookPopup`.
- `Bulk Rename` | hint `Ctrl+B` | palette | effect: `_bulk_rename()` — opens `BulkRenameDialog` (needs ≥2 selection).
- `New Folder` | hint `F7 / Ctrl+Shift+N` | palette | effect: `_new_folder()` — inline/InputDialog create.
- `New Nested Folders` | hint `Ctrl+Alt+N` | palette | effect: `_new_nested_folder()` — `NestedFolderDialog`.
- `New File` | hint `Ctrl+N` | palette | effect: `_new_file()` — new file w/ optional template ext.
- `New File in Nested Path` | hint `Ctrl+Alt+F` | palette | effect: `_new_nested_file()` — `NestedFileDialog`.
- `Batch Scaffold Project / Tree` | hint `Ctrl+Shift+B` | palette | effect: `_batch_scaffold()` — `BatchScaffoldDialog`.
- `Delete` | hint `F8/Delete` | palette | effect: `_delete()` — recycle-bin delete selection.
- `Rename` | hint `F2` | palette | effect: `_rename()` — inline rename.
- `Copy Here` | hint `F5` | palette | effect: `_clip("copy")+_paste()` — copy staged clipboard in place (duplicate).
- `Move Here` | hint `F6` | palette | effect: `_clip("cut")+_paste()` — NOTE: conflicts with `F6` sort-cycle binding.
- `Copy` | hint `Ctrl+C` | palette | effect: `_clip("copy")` — stage to shelf/clipboard.
- `Cut` | hint `Ctrl+X` | palette | effect: `_clip("cut")`.
- `Paste` | hint `Ctrl+V` | palette | effect: `_paste()` — paste into current dir (or `_paste(target)`).
- `Undo` | hint `Ctrl+Z` | palette | effect: `_undo()` via `UndoManager`.
- `Redo` | hint `Ctrl+Y` | palette | effect: `_redo()`.
- `Select All` | hint `Ctrl+A` | palette | effect: `_select_all()`.
- `Toggle Sidebar` | hint `Ctrl+H` | palette | effect: `_toggle_sidebar()`.
- `Toggle Debug Overlay` | hint `F12` | palette | effect: `_toggle_debug()` — `DebugOverlay`.
- `Refresh` | hint `Shift+F5` | palette | effect: `_reload_current()`.
- `New Tab` | hint `Ctrl+T` | palette | effect: `add_tab(~)` — new Home tab.
- `Close Tab` | hint `Ctrl+W` | palette | effect: `_close_current_tab()`.
- `Toggle Terminal` | hint `` Ctrl+` `` | palette | effect: `_toggle_terminal()` — embedded `TerminalWidget`.
- `Find Duplicates` | hint `Ctrl+Shift+F` | palette | effect: `_open_duplicate_finder()` — `DuplicateFinderDialog`.
- `Search Files` | hint `Ctrl+Shift+S` | palette | effect: `_search()` — `SearchDialog` (Enter in filter box also triggers).
- `Add Bookmark` | hint `` | palette | effect: `_add_bookmark()` — pin current path to Ctrl+1..0 slots.
- `Go to Path` | hint `Ctrl+G` | palette | effect: `_go_to_path()` — `GoToPathDialog`.

## Shortcuts
All `QShortcut(QKeySequence(seq))` in `_bind_shortcuts` (51 bindings; suppressed when a `QLineEdit/QTextEdit/QPlainTextEdit` has focus unless `allow_in_text`). Trigger → effect:
- `Alt+Left` → `go_back()` (history back). `Alt+Right` → `go_forward()`.
- `Backspace` → `go_up()`.
- `F5` → copy+paste in place (Copy Here). `Shift+F5` → `_reload_current()` (refresh).
- `F7`, `Ctrl+Shift+N` → `_new_folder()`. `Ctrl+Alt+N` → nested folders dialog. `Ctrl+N` → new file. `Ctrl+Alt+F` → nested file dialog. `Ctrl+Shift+B` → batch scaffold dialog.
- `F8`, `Delete` → `_delete()` (recycle bin). `Shift+Delete` → `_delete(permanent=True)`.
- `F2` → `_rename()`.
- `Ctrl+C` / `Ctrl+X` → stage copy/cut. `Ctrl+V` → paste. `Ctrl+A` → select all.
- `Ctrl+Z` → undo. `Ctrl+Y`, `Ctrl+Shift+Z` → redo.
- `Ctrl+T` → new Home tab. `Ctrl+W` → close current tab.
- `Ctrl+F` → focus inline filter box (`proxy.setFilterFixedString` live filter).
- `Ctrl+D` → dual pane toggle. `Ctrl+H` → sidebar toggle. `` Ctrl+` `` → terminal toggle. `F12` → debug overlay toggle.
- `Ctrl+L` → `_start_edit_path()` (breadcrumbs → editable `AddrBar`; Enter commits, `editingFinished` cancels).
- `Space` → `_quick_look()` (Quick Look popup).
- `Ctrl+B` → bulk rename dialog.
- `Ctrl+Shift+P` → palette toggle.
- `Ctrl+Shift+F` → registered TWICE: `_open_duplicate_finder` then `toggle_flat_branch_view` (second connection wins in practice / both fire; palette hint shows it for both).
- `Ctrl+1`…`Ctrl+0` (10) → `_go_bookmark(0..9)`.
- `Shift+/` (`?`), `F1`, `Ctrl+?` → `_show_shortcuts()` (Shortcuts dialog).
- `Ctrl+G` → Go-to-Path dialog.
- `F6` → `_sort_cycle_column()` (Name→Modified→Type→Size). `Shift+F6` → `_sort_toggle_order()` (Asc↔Desc).
- Discrepancies vs `ShortcutsDialog` table text: dialog labels `Alt+↑` (code binds only `Backspace` for Up), `Ctrl+Shift+R` for Bulk Rename (code: `Ctrl+B`), `Ctrl+F / F3` (code: only `Ctrl+F`), `F5 / Shift+F5` refresh (code: `F5`=Copy Here, `Shift+F5`=refresh), `F6` Move Here in palette vs `F6` sort-cycle in bindings.

## Context menu
Right-click (`customContextMenuRequested → _context_menu` on table, icon_list, right_table, right_icon_list; click first re-selects/clears under cursor). Four variants:
Archive-mode open (when `_archive_mode`): trigger right-click inside archive listing → `Open` (activate entries) | `Extract Here` (to archive's dir) | `Extract to…` (chooser) | separator | `Exit Archive` | `Select All`.
With selection (file/folder rows selected):
- `Open` → activate all selected (folder=navigate, archive=open in-place, file=`os.startfile`). `Open in New Tab` → folder (or file's parent) in new tab.
- `Cut` (`Ctrl+X`), `Copy` (`Ctrl+C`) → stage. `Paste`/`Move Here` (label follows clipboard mode; disabled if shelf/clipboard empty). `Paste into '<folder>'` (only when exactly 1 dir selected; disabled if empty).
- `Copy Path` → newline-joined paths to system clipboard. `Copy Filename` → basenames to clipboard.
- `Rename…` (only single selection) → inline rename. `Delete` → recycle. `Delete permanently` (accent) → permanent.
- `Bulk rename… (Ctrl+B)` + `New folder with selection` + `Move to folder…` (only when ≥2 selected).
- `Compress` submenu → `ZIP (.zip)` / `7z (.7z)` / `TAR.GZ (.tar.gz)` via `_compress_to`.
- Archive-only (if any selected path `is_archive`) → `Open Archive` | `Extract Here` | `Extract to…`.
- `Color tag` submenu → one action per `ColorTagManager.TAG_COLORS` + `Remove tag` → `_set_color_tag`.
- `Select All` | `Invert Selection`. Single-file only: `Properties` → `PropertiesDialog`; `Calculate Checksums…` → `FileChecksumDialog`; `Open with…` → system handler chooser.
On empty background (no selection):
- `New folder` (direct) + `New` submenu → `Folder (Ctrl+Shift+N)` | `Nested Folders… (Ctrl+Alt+N)` | sep | `File… (Ctrl+N)` | `File in Nested Path… (Ctrl+Alt+F)` | sep | `Batch Scaffold Project / Tree… (Ctrl+Shift+B)` | sep | `Templates` submenu (one per `FILE_TEMPLATES` ext → `_new_file(ext)`).
- `Paste`/`Move Here` (disabled if empty). `Refresh` | `Save as smart folder` | sep | `Select All` | sep | `Find Duplicates (Ctrl+Shift+F)` | `Sort By` submenu → per `_SORT_COLUMNS` (Name/Modified/Type/Size) each with `↑ Ascending` / `↓ Descending` actions.
Smart-folder sidebar (`_smart_folder_context_menu` on `smart_list`): on item → `Open` (load saved path) | `Remove` (delete saved entry); on empty → `Add current folder` (save current dir as smart folder).

## Toolbar
Tier 1 — Tab row (`#TabBarContainer`): `QTabBar` (closable tabs, `add_tab`/`_close_current_tab`) + `+` NewTabBtn (`New tab (Ctrl+T)` → Home tab).
Tier 2 — Nav + Address + Search (`#NavAddressContainer`): `Back (Alt+←)` | `Forward (Alt+→)` | `Up (Backspace)` | `Refresh (Shift+F5)` (all `nav_btn` 30×28); full-width `CrumbBar` (click segment=navigate, click empty/double-click=edit path; collapses >6 segs to `drive + … + last3`) + hidden editable `AddrBar` (`Ctrl+L` to edit, Enter commits); `SearchInput` filter box (`Search current folder…`, live `setFilterFixedString`, Enter opens full `SearchDialog`).
Tier 3 — Command bar (`#CommandBarContainer`): `+ New` split-button (click=`_new_folder`; menu: `New Folder`, `New Nested Folders…`, `New File…`, `New File in Nested Path…`, `Batch Scaffold…`) | sep | `Cut` | `Copy` | `Paste` | `Rename (F2)` | `Delete (Del)` | sep | `Sort` dropdown (Name/Date modified/Type/Size × Asc/Desc) | `View` dropdown (`Details view`→table, `Large icons view`→icons, `Toggle Dual Pane`) | sep | `Dual pane (Ctrl+D)` (checkable) | `Quick Look (Space)` | `Transfers` (opens `TransferMonitorDialog`) | `···` More menu (`Find Duplicates`, `Bulk Rename…`, `Save as Smart Folder`, `Open Terminal`, `Keyboard Shortcuts`) | stretch | `Toggle Navigation Pane (Ctrl+H)` (checkable, default on) | `Details` preview toggle (checkable, default on → `_toggle_preview`).

## Dialogs
- `QuickLookPopup` (`Space`, `btn_quicklook`): frameless 480×400 popup; icon/name/meta(kind+size+mtime+path); raster preview (`png/jpg/jpeg/gif/bmp/webp/ico` ≤50 MB via `QImageReader` 440×220) else 128px type icon; auto-flips to stay on-screen.
- `BulkRenameDialog` (`Ctrl+B`, ≥2 files): 5 modes via combo+stacked pages — `Find & Replace` (regex find+replace), `Sequential Numbering` (prefix+start+padding), `Date Prefix` (mtime/ctime + separator), `Case Transform` (UPPER/lower/Title/Sentence), `Add/Remove Suffix & Prefix`; live 2-col preview (`Original/Renamed`); `Apply Rename` records undo, skips existing targets with warning summary.
- `DuplicateFinderDialog` (`Ctrl+Shift+F`, More menu): dir input + Browse, progress bar + status, results table (checkbox+path+size+hash), `Scan` (size-prefilter + MD5 worker thread), `Select Duplicates` (auto-check keep-one-per-group), `Delete Selected`, reclaimable-space label.
- `PropertiesDialog` (ctx menu single selection, `Checksums…` button): grid Name/Size/Type/Path/Modified/Hidden/Read-only; file-only `Checksums…` opens checksum dialog; Close.
- `FileChecksumDialog` (ctx menu + Properties): threaded MD5/SHA-1/SHA-256/SHA-512 with progress; click-to-copy hash fields + compare-box with match indicator.
- `GoToPathDialog` (`Ctrl+G`): path input prefilled with current dir; resolves `%ENV%`, `~`, `shell:` folders (RecycleBin/Downloads/Desktop/Documents/Pictures/Music/Video via registry); file path → navigates to parent; red border on invalid; Go/Cancel.
- `SearchDialog` (`Ctrl+Shift+S`, filter Enter): pattern input + scope combo (`Current folder` flat / `Current folder (recursive)` / `All drives`), Cancel button, sortable results table (Name/Path/Size/Modified, double-click or Open navigates/opens), status count.
- `ShortcutsDialog` (`F1`/`Shift+?`/`Ctrl+?`, More menu): non-modal 6-category table (Navigation / View & Panels / File Creation & Scaffolding / File Operations / Search & Power Tools / Tabs & History), Close.
- Creation trio: `NestedFolderDialog` (`Ctrl+Alt+N`: path input + 4 quick presets + live target preview + Create Folders); `NestedFileDialog` (`Ctrl+Alt+F`: relative path + template combo auto-detected by ext + content editor + preview + Create File); `BatchScaffoldDialog` (`Ctrl+Shift+B`: preset combo from `PROJECT_SCAFFOLD_PRESETS` + indented-tree/path-list spec editor + Target root label + Scaffold).
- Plus: `CommandPalette` dialog (fuzzy, frameless top-pinned) and `DebugOverlay` (`F12`: FPS + last-22 event log) and `TransferMonitorDialog` (via Transfers button; pause/resume/cancel) and `ExtractionProgressWidget` (embedded progress bar panel).

## Views
- `Details/table view` (`View→Details view`, palette Toggle View): `QTableView` + `SortProxy` (sortable headers, stretch Name col, 150/90/90 others, alternating rows, multi-extended select, drag-drop both ways, double-click activates, selection drives preview+status).
- `Large icons view` (`View→Large icons view`): `QListWidget` IconMode 96px icons, word-wrap, Adjust resize, same context menu/selection wiring.
- `Empty state` (auto when 0 rows): centered folder glyph + "This folder is empty" + "Drop files here or create a new folder" (drop target).
- `Dual pane` (`Ctrl+D`): right `QStackedWidget` (right table + right icons) with own model/proxy/tabs; same menus/shortcuts operate on focused pane (`sender`-aware `_selected_rows`).
- `Flat Branch View` (palette / `Ctrl+Shift+F` clash): `engine.list_flat_branch` recursive file dump with "Loading…" status; toggle off reloads normal dir.
- `Archive browsing` (double-click/`Open Archive` on zip/rar/7z): table replaced by archive entries; dedicated ctx menu; breadcrumb shows archive path; `Exit Archive` restores FS.
- `Preview / Details pane` (`Details` toggle): `PreviewPane` — name/meta/icon + `staging shelf` (staged cut/copy list with paste/add-selected) + `TransferStatusDock`; follows last-selected row, clears on empty selection.
- `Sidebar` sections: `QUICK ACCESS` (Home/Desktop/Downloads/Documents/Pictures/Videos/Music → navigate); `FOLDERS` (`FolderTreeWidget` drive tree → navigate, hidden if import fails); `SMART FOLDERS` (saved paths → open on click, right-click Open/Remove/Add-current).
- `Tabs + Breadcrumbs + Terminal`: multi-tab (`add_tab`, per-tab path/history), `CrumbBar` segments, collapsible `TerminalWidget` bottom splitter (70/30 split on show).
- `Status bar` (`#Status`, 28px; click `status_items` cycles 3 modes): mode 0 `"{total} items ({folders} folders, {files} files)"`; mode 1 appends `" | Selected: {n} selected ({size})"` when selection exists; mode 2 shows `"{drive}\ Free: {free} Total: {total}"` via `shutil.disk_usage` (cached `_status_disk_text`); right labels: `status_sel` (selection summary, drop-hint override), `status_transfer` (active job `Transfer {pct}% — {text}` / `Transfer active (id…)` / `Transfer cancelled`), `status_undo` (pending undo/redo description); transient overrides (`Sort by:`, `Bookmarked:`, `Renamed to`, `Staged…`, `Nothing to undo/redo`) auto-restore after ~1.2 s.

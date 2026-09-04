"""The single source of truth for every tool page in the premium shell.

Why this module exists
----------------------
Navigation used to be three parallel structures inside ``window.py``: a flat
``_NAV`` list (order + labels + icons), a ``_NAV_GROUPS`` tuple (sidebar
hierarchy), and a ``_PAGE_FACTORIES`` dict (module + class to construct). Adding
one tool meant editing all three in the correct places, and a runtime
``RuntimeError`` existed purely to catch the inevitable desync.

That is fragile by construction. Here a page is declared **once** as a
:class:`PageSpec`; ordering, grouping, labels, icons, and lazy construction are
all *derived* from that declaration, so the structures cannot disagree.

Adding a tool
-------------
Append one :class:`PageSpec` to :data:`PAGES` and give it an existing
``group``. Nothing else needs to change: the sidebar, search, the page stack,
and lazy construction all pick it up automatically::

    PageSpec(
        id="mytool",
        title="My Tool",
        icon="\\u2692",
        group="system",
        factory="cortex_unified.ui.premium.pages.mytool:MyToolPage",
    )

Ordering is the declaration order within each group, and groups render in the
order given by :data:`GROUPS`.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from PySide6.QtWidgets import QWidget


@dataclass(frozen=True, slots=True)
class NavGroup:
    """A collapsible sidebar section."""

    id: str
    title: str


@dataclass(frozen=True, slots=True)
class PageSpec:
    """Everything the shell needs to know about one tool page.

    ``factory`` is a ``"module.path:ClassName"`` string rather than an imported
    class so that declaring a page costs nothing at import time - the module is
    only imported when the user actually opens that page.

    ``icon`` is the *name* of a shipped SVG in ``resources/icons`` (without the
    extension), not a Unicode glyph. Glyphs depended on system font fallback,
    which Qt 6 no longer guarantees, so they rendered at inconsistent weights
    and sizes - and five were duplicated across different tools.
    """

    id: str
    title: str
    icon: str
    group: str
    factory: str

    def load(self) -> type[QWidget]:
        """Import and return the page class this spec points at."""
        module_path, _, attr = self.factory.partition(":")
        if not module_path or not attr:
            raise ValueError(
                f"page {self.id!r} has a malformed factory {self.factory!r}; "
                'expected "module.path:ClassName"'
            )
        from importlib import import_module

        return getattr(import_module(module_path), attr)


#: Sidebar sections, in display order.
GROUPS: tuple[NavGroup, ...] = (
    NavGroup("overview", "Command Center"),
    NavGroup("cleanup", "Cleanup & Storage"),
    NavGroup("files", "Files & Explorer"),
    NavGroup("system", "System Performance"),
    NavGroup("activity", "Privacy & Activity"),
    NavGroup("network", "Network & Defense"),
    NavGroup("apps", "Apps & Security"),
    NavGroup("security", "Security Tools"),
    NavGroup("recovery", "Recovery & Reports"),
    NavGroup("maintenance", "Maintenance & Repair"),
)

_SHELL = "cortex_unified.ui.premium.window"
_ANALYSIS = "cortex_unified.ui.premium.analysis_pages"
_MORE = "cortex_unified.ui.premium.more_pages"
_NETWORK = "cortex_unified.ui.premium.network_pages"
_REPORT = "cortex_unified.ui.premium.report_pages"
_SYSTEM = "cortex_unified.ui.premium.system_pages"
_TOOLS = "cortex_unified.ui.premium.tools_pages"
_NEXUS = "cortex_unified.ui.premium.nexus_page"
_LICENSE = "cortex_unified.ui.premium.license_page"
_HUB = "cortex_unified.ui.premium.cleanup_hub_page"
_WSL = "cortex_unified.ui.premium.wsl_page"
_LOG = "cortex_unified.ui.premium.log_sweeper_page"
_MODEL = "cortex_unified.ui.premium.model_cache_page"
_NEAR = "cortex_unified.ui.premium.near_duplicates_page"
_PERCEPTUAL = "cortex_unified.ui.premium.perceptual_duplicates_page"
_REGISTRY_AI = "cortex_unified.ui.premium.registry_ai_page"
_COMPACT_OS = "cortex_unified.ui.premium.compact_os_page"
_FUZZY = "cortex_unified.ui.premium.fuzzy_hash_page"
_AUDIO = "cortex_unified.ui.premium.audio_duplicates_page"
_VIDEO = "cortex_unified.ui.premium.video_duplicates_page"
_S3FIFO = "cortex_unified.ui.premium.s3_fifo_page"
_CDC = "cortex_unified.ui.premium.cdc_page"
_CLOUD = "cortex_unified.ui.premium.cloud_storage_page"
_ADVANCED_UNINSTALLER = "cortex_unified.ui.premium.advanced_uninstaller_page"
_PRIVACY_BLOCKER = "cortex_unified.ui.premium.privacy_blocker_page"
_PORTABLE = "cortex_unified.ui.premium.portable_manager_page"
_SECURE_SHREDDER = "cortex_unified.ui.premium.secure_shredder_page"
_WIN_UPDATE_REPAIR = "cortex_unified.ui.premium.win_update_repair_page"
_STARTUP_OPT = "cortex_unified.ui.premium.startup_optimizer_page"
_DRIVER_MANAGER = "cortex_unified.ui.premium.driver_manager_page"
_DISK_ADVANCED = "cortex_unified.ui.premium.disk_analyzer_page"

_POWER = "cortex_unified.ui.premium.power_tools_pages"
_EXPANDED = "cortex_unified.ui.premium.expanded_tools_pages"
_APEX = "cortex_unified.ui.premium.apex_tools_pages"
_SUITE = "cortex_unified.ui.premium.power_suite_pages"
_ENTERPRISE = "cortex_unified.ui.premium.enterprise_suite_pages"
_NEXTGEN = "cortex_unified.ui.premium.nextgen_suite_pages"
_WINAPP2 = "cortex_unified.ui.premium.winapp2_page"
_SRUM_BAM = "cortex_unified.ui.premium.srum_bam_page"
_DIRECTSTORAGE = "cortex_unified.ui.premium.directstorage_page"
_STANDBY_MEM = "cortex_unified.ui.premium.memory_standby_page"
_MFT_SLACK = "cortex_unified.ui.premium.mft_slack_page"
_SEARCH_OPT = "cortex_unified.ui.premium.search_optimizer_page"
_GAME_MODE = "cortex_unified.ui.premium.game_mode_page"
_DELIVERY = "cortex_unified.ui.premium.delivery_optimization_page"
_WAN_AUDIT = "cortex_unified.ui.premium.wan_audit_page"
_OLD_FILES = "cortex_unified.ui.premium.old_files_page"
_RESIDUAL = "cortex_unified.ui.premium.residual_cleaner_page"
_BAD_FILES = "cortex_unified.ui.premium.bad_files_studio_page"
_PROC_STUDIO = "cortex_unified.ui.premium.process_studio_page"

#: Every page, declared once. Order within a group is display order.
PAGES: tuple[PageSpec, ...] = (
    # -- Command Center ----------------------------------------------------
    PageSpec(
        "dashboard", "System Overview Dashboard", "dashboard", "overview", f"{_SHELL}:DashboardPage"
    ),
    PageSpec(
        "health", "PC Health Check", "health", "overview", f"{_ANALYSIS}:HealthCheckPage"
    ),
    # -- Cleanup & Storage -------------------------------------------------
    PageSpec(
        "cleanuphub", "One-Click Cleanup Hub", "cleanuphub", "cleanup", f"{_HUB}:CleanupHubPage"
    ),
    PageSpec(
        "duplicates", "Duplicate Files Finder", "duplicates", "cleanup", f"{_SHELL}:DuplicatesPage"
    ),
    PageSpec(
        "photos",
        "Similar & Duplicate Photos",
        "photos",
        "cleanup",
        f"{_SHELL}:DuplicatePhotosPage",
    ),
    PageSpec(
        "dupfolders",
        "Duplicate Folders Finder",
        "dupfolders",
        "cleanup",
        f"{_MORE}:DuplicateFoldersPage",
    ),
    PageSpec("large", "Large Files Finder", "large", "cleanup", f"{_SHELL}:LargeFilesPage"),
    PageSpec("empty", "Empty Files & Folders", "empty", "cleanup", f"{_SHELL}:EmptyPage"),
    PageSpec(
        "analyzer",
        "Visual Disk Space Map",
        "analyzer",
        "cleanup",
        f"{_ANALYSIS}:DiskAnalyzerPage",
    ),
    PageSpec(
        "brokenlinks",
        "Broken Shortcuts & Links",
        "brokenlinks",
        "cleanup",
        f"{_MORE}:BrokenLinksPage",
    ),
    PageSpec(
        "logsweep", "System & App Log Sweeper", "logsweep", "cleanup", f"{_LOG}:LogSweeperPage"
    ),
    PageSpec(
        "packages",
        "Developer Package Caches",
        "packages",
        "cleanup",
        f"{_MORE}:PackageCachePage",
    ),
    PageSpec(
        "projcaches",
        "Project Build Caches",
        "projcaches",
        "cleanup",
        f"{_MORE}:ProjectCachesPage",
    ),
    PageSpec(
        "modelcache", "AI Model Cache Cleaner", "modelcache", "cleanup", f"{_MODEL}:ModelCachePage"
    ),
    PageSpec(
        "neardup",
        "Similar Text Documents",
        "neardup",
        "cleanup",
        f"{_NEAR}:NearDuplicatesPage",
    ),
    PageSpec(
        "perceptual",
        "Similar Photo Matching",
        "perceptual",
        "cleanup",
        f"{_PERCEPTUAL}:PerceptualDuplicatesPage",
    ),
    PageSpec(
        "registryai",
        "Intelligent Registry Cleaner",
        "registry_ai",
        "cleanup",
        f"{_REGISTRY_AI}:RegistryAICleanerPage",
    ),
    PageSpec(
        "fuzzyhash",
        "Fuzzy Duplicate Finder",
        "fuzzyhash",
        "cleanup",
        f"{_FUZZY}:FuzzyHashPage",
    ),
    PageSpec(
        "audio", "Duplicate Music & Audio", "audio", "cleanup", f"{_AUDIO}:AudioDuplicatesPage"
    ),
    PageSpec(
        "video", "Duplicate Video Files", "video", "cleanup", f"{_VIDEO}:VideoDuplicatesPage"
    ),
    PageSpec("cdc", "Block-Level Deduplicator", "cdc", "cleanup", f"{_CDC}:CdcPage"),
    PageSpec(
        "cloud",
        "Cloud Storage Cache Cleaner",
        "cloud_storage",
        "cleanup",
        f"{_CLOUD}:CloudStoragePage",
    ),
    PageSpec(
        "portable",
        "Portable Applications Manager",
        "portable_manager",
        "cleanup",
        f"{_PORTABLE}:PortableManagerPage",
    ),
    PageSpec(
        "crashdumps",
        "Crash Dumps & Error Reports",
        "folder-dump",
        "cleanup",
        f"{_POWER}:CrashDumpCleanerPage",
    ),
    PageSpec(
        "eventlogs",
        "Windows Event Log Cleaner",
        "log",
        "cleanup",
        f"{_POWER}:EventLogCleanerPage",
    ),
    PageSpec(
        "devcleaner",
        "Software Development Artifacts",
        "folder-code",
        "cleanup",
        f"{_EXPANDED}:DevCleanerPage",
    ),
    PageSpec(
        "browserdeep",
        "Deep Web Browser Cleaner",
        "folder-shared",
        "cleanup",
        f"{_EXPANDED}:BrowserDeepCleanerPage",
    ),
    PageSpec(
        "imgopt",
        "Image Compressor & Optimizer",
        "folder-images",
        "cleanup",
        f"{_APEX}:ImageOptimizerPage",
    ),
    PageSpec(
        "fonts",
        "Font Cache & Registry Optimizer",
        "font",
        "cleanup",
        f"{_SUITE}:FontCacheManagerPage",
    ),
    PageSpec(
        "tempcleaner",
        "Deep System Temp Cleaner",
        "folder-trash",
        "cleanup",
        f"{_SUITE}:TempFolderCleanerPage",
    ),
    # -- Files & Explorer --------------------------------------------------
    PageSpec(
        "nexus", "Nexus File Explorer", "folder", "files", f"{_NEXUS}:NexusExplorerPage"
    ),
    PageSpec(
        "hasher", "File Hash & Checksum Verifier", "verified", "files", f"{_POWER}:HashVerifierPage"
    ),
    PageSpec(
        "renamer", "Batch File Renamer", "label", "files", f"{_POWER}:BatchRenamerPage"
    ),
    PageSpec(
        "foldersync",
        "Folder Compare & Sync",
        "diff",
        "files",
        f"{_POWER}:FolderSyncPage",
    ),
    PageSpec(
        "splitter",
        "Large File Splitter & Joiner",
        "binary",
        "files",
        f"{_POWER}:FileSplitterPage",
    ),
    PageSpec(
        "unlocker", "Locked File Unlocker", "lock", "files", f"{_POWER}:FileUnlockerPage"
    ),
    PageSpec(
        "adsmanager",
        "NTFS Alternate Data Streams (ADS)",
        "document",
        "files",
        f"{_POWER}:AdsManagerPage",
    ),
    PageSpec(
        "linksmanager",
        "Symbolic Links & Junctions",
        "folder-link",
        "files",
        f"{_EXPANDED}:LinksManagerPage",
    ),
    PageSpec(
        "fastcopier",
        "High-Speed File Copier",
        "rocket",
        "files",
        f"{_EXPANDED}:FastCopierPage",
    ),
    PageSpec(
        "timestamptouch",
        "File Date & Timestamp Editor",
        "folder-constant",
        "files",
        f"{_EXPANDED}:TimestampTouchPage",
    ),
    PageSpec(
        "archivemanager",
        "Archive Studio (Zip/7z/Tar)",
        "zip",
        "files",
        f"{_EXPANDED}:ArchiveManagerPage",
    ),
    PageSpec(
        "sniffer",
        "File Type & Header Inspector",
        "folder-syntax",
        "files",
        f"{_APEX}:FileSignatureSnifferPage",
    ),
    PageSpec(
        "binarydiff",
        "Binary & Hex File Compare",
        "folder-delta",
        "files",
        f"{_APEX}:BinaryDifferPage",
    ),
    PageSpec(
        "usnjournal",
        "NTFS Change Journal (USN) Viewer",
        "folder-log",
        "files",
        f"{_APEX}:UsnJournalPage",
    ),
    PageSpec(
        "par2", "PAR2 Archive Parity & Repair", "certificate", "files", f"{_APEX}:Par2RecoveryPage"
    ),
    PageSpec(
        "slackspace",
        "NTFS Cluster Slack Analyzer",
        "disc",
        "files",
        f"{_SUITE}:SlackSpaceAnalyzerPage",
    ),
    # -- System Performance ------------------------------------------------
    PageSpec(
        "updater",
        "Software Updater",
        "updater",
        "system",
        f"{_MORE}:SoftwareUpdaterPage",
    ),
    PageSpec(
        "drives", "Drive Optimizer (TRIM & Defrag)", "drives", "system", f"{_MORE}:DriveOptimizerPage"
    ),
    PageSpec(
        "vdisks", "Virtual Hard Disks (VHD/VHDX)", "vdisks", "system", f"{_MORE}:VirtualDisksPage"
    ),
    PageSpec("wsl", "Linux Subsystem (WSL) Cleaner", "wsl", "system", f"{_WSL}:WslPage"),
    PageSpec(
        "compactos", "CompactOS System Compression", "compactos", "system", f"{_COMPACT_OS}:CompactOsPage"
    ),
    PageSpec("s3fifo", "Cache Algorithm Benchmark (S3-FIFO)", "s3fifo", "system", f"{_S3FIFO}:S3FifoPage"),
    PageSpec(
        "diskhealth",
        "Disk S.M.A.R.T. Health Monitor",
        "diskhealth",
        "system",
        f"{_ANALYSIS}:DiskHealthPage",
    ),
    PageSpec(
        "bootperf",
        "Windows Boot Diagnostics",
        "bootperf",
        "system",
        f"{_ANALYSIS}:BootPerformancePage",
    ),
    PageSpec(
        "repair",
        "System File Integrity (SFC & DISM)",
        "repair",
        "system",
        f"{_ANALYSIS}:SystemRepairPage",
    ),
    PageSpec(
        "compstore",
        "WinSxS Component Store Cleaner",
        "compstore",
        "system",
        f"{_ANALYSIS}:ComponentStorePage",
    ),
    PageSpec(
        "schedule",
        "Windows Scheduled Tasks",
        "schedule",
        "system",
        f"{_ANALYSIS}:ScheduledTasksPage",
    ),
    PageSpec(
        "performance",
        "Power Plan & Performance",
        "performance",
        "system",
        f"{_TOOLS}:PerformancePage",
    ),
    PageSpec(
        "systemcache",
        "Icon & Thumbnail Cache Rebuilder",
        "tune",
        "system",
        f"{_POWER}:SystemCacheRebuilderPage",
    ),
    PageSpec(
        "netoptimizer",
        "TCP/IP & Network Optimizer",
        "routing",
        "system",
        f"{_POWER}:NetworkOptimizerPage",
    ),
    PageSpec(
        "startupopt",
        "Startup Programs Optimizer",
        "startup_optimizer",
        "system",
        f"{_STARTUP_OPT}:StartupOptimizerPage",
    ),
    PageSpec(
        "prefetch",
        "Prefetch & SysMain Cache",
        "pipeline",
        "system",
        f"{_EXPANDED}:PrefetchAnalyzerPage",
    ),
    PageSpec(
        "searchoptimizer",
        "Windows Search Index Optimizer",
        "search",
        "system",
        f"{_EXPANDED}:SearchIndexOptimizerPage",
    ),
    PageSpec(
        "diskbenchmark",
        "Storage Speed Benchmark",
        "folder-benchmark",
        "system",
        f"{_EXPANDED}:DiskBenchmarkPage",
    ),
    PageSpec(
        "memoryoptimizer",
        "Memory & Working Set Optimizer",
        "folder-cluster",
        "system",
        f"{_EXPANDED}:MemoryOptimizerPage",
    ),
    PageSpec(
        "powerplan",
        "Power Plan & CPU Tuning",
        "flash",
        "system",
        f"{_APEX}:PowerPlanOptimizerPage",
    ),
    PageSpec(
        "envvars",
        "Environment Variables Manager",
        "terminal",
        "system",
        f"{_SUITE}:EnvVariableManagerPage",
    ),
    PageSpec(
        "services",
        "Windows Services Optimizer",
        "folder-server",
        "system",
        f"{_SUITE}:WindowsServiceManagerPage",
    ),
    PageSpec(
        "pagefile",
        "Virtual Memory (Pagefile) Tuning",
        "folder-resource",
        "system",
        f"{_SUITE}:PagefileOptimizerPage",
    ),
    # -- Privacy & Activity ------------------------------------------------
    PageSpec("privacy", "Privacy & Tracking Shield", "privacy", "activity", f"{_SYSTEM}:PrivacyPage"),
    PageSpec("startup", "Startup Applications", "startup", "activity", f"{_SYSTEM}:StartupPage"),
    PageSpec(
        "processes", "Active Running Processes", "processes", "activity", f"{_SYSTEM}:ProcessesPage"
    ),
    PageSpec(
        "shellbags",
        "Folder View History (Shellbags)",
        "folder-secure",
        "activity",
        f"{_APEX}:ShellbagsCleanerPage",
    ),
    PageSpec(
        "diagdata",
        "Diagnostic Data & Telemetry",
        "folder-core",
        "activity",
        f"{_SUITE}:DiagnosticDataManagerPage",
    ),
    PageSpec(
        "startupimpact",
        "Startup Boot Delay Impact",
        "console",
        "activity",
        f"{_SUITE}:StartupImpactPage",
    ),
    PageSpec(
        "eventmon",
        "Hardware Fault & BSOD Monitor",
        "folder-database",
        "activity",
        f"{_SUITE}:EventLogMonitorPage",
    ),
    # -- Network & Defense -------------------------------------------------
    PageSpec(
        "network", "Active Connections Monitor", "network", "network", f"{_SYSTEM}:NetworkPage"
    ),
    PageSpec(
        "traffic",
        "Network Throughput Monitor",
        "traffic",
        "network",
        f"{_NETWORK}:TrafficMonitorPage",
    ),
    PageSpec(
        "netmap", "Local Network Map", "netmap", "network", f"{_NETWORK}:NetworkMapPage"
    ),
    PageSpec(
        "landevices",
        "Connected LAN Devices",
        "landevices",
        "network",
        f"{_NETWORK}:LanDevicesPage",
    ),
    PageSpec(
        "nettools",
        "Network Diagnostic Toolkit",
        "nettools",
        "network",
        f"{_NETWORK}:NetworkToolsPage",
    ),
    PageSpec(
        "loadtest", "Network Load & Ping Tester", "loadtest", "network", f"{_NETWORK}:LoadTesterPage"
    ),
    PageSpec("firewall", "Windows Firewall Rules", "firewall", "network", f"{_NETWORK}:FirewallPage"),
    PageSpec(
        "dnsbenchmark",
        "DNS Speed Benchmark",
        "folder-connection",
        "network",
        f"{_EXPANDED}:DnsBenchmarkPage",
    ),
    PageSpec(
        "hostsfile",
        "Hosts File & Domain Shield",
        "hosts",
        "network",
        f"{_APEX}:HostsFileManagerPage",
    ),
    # -- Apps & Security ---------------------------------------------------
    PageSpec(
        "extensions",
        "Browser Extensions Manager",
        "extensions",
        "apps",
        f"{_TOOLS}:BrowserExtensionsPage",
    ),
    PageSpec(
        "drivers",
        "Device Driver Inventory",
        "drivers",
        "apps",
        f"{_TOOLS}:DriverInventoryPage",
    ),
    PageSpec(
        "drivermanager",
        "Device Driver Manager",
        "driver_manager",
        "apps",
        f"{_DRIVER_MANAGER}:DriverManagerPage",
    ),
    PageSpec(
        "driverstore",
        "Outdated Driver Store Cleaner",
        "folder-tools",
        "apps",
        f"{_APEX}:DriverStoreCleanerPage",
    ),
    PageSpec(
        "uninstaller",
        "Applications Uninstaller",
        "uninstaller",
        "apps",
        f"{_SYSTEM}:UninstallerPage",
    ),
    PageSpec(
        "advanced_uninstaller",
        "Deep Software Uninstaller",
        "advanced_uninstaller",
        "apps",
        f"{_ADVANCED_UNINSTALLER}:AdvancedUninstallerPage",
    ),
    PageSpec(
        "leftovers",
        "Uninstalled Software Leftovers",
        "leftovers",
        "apps",
        f"{_SYSTEM}:LeftoverScannerPage",
    ),
    PageSpec("telemetry", "Windows Telemetry Settings", "telemetry", "apps", f"{_SYSTEM}:TelemetryPage"),
    PageSpec("registry", "Registry Issues & Backups", "registry", "apps", f"{_SYSTEM}:RegistryPage"),
    PageSpec("security", "Windows Defender Security", "security", "apps", f"{_ANALYSIS}:SecurityPage"),
    PageSpec(
        "storagesense",
        "Windows Storage Sense",
        "storagesense",
        "apps",
        f"{_ANALYSIS}:StorageSensePage",
    ),
    PageSpec(
        "secrets", "API Keys & Secrets Scanner", "secrets", "apps", f"{_MORE}:SecretsScannerPage"
    ),
    PageSpec(
        "notifications",
        "Windows Notification Cleaner",
        "folder-messages",
        "apps",
        f"{_APEX}:NotificationCleanerPage",
    ),
    PageSpec(
        "contextmenu",
        "Right-Click Context Menu Manager",
        "menu",
        "apps",
        f"{_SUITE}:ContextMenuManagerPage",
    ),
    # -- Security Tools ---------------------------------------------------
    PageSpec(
        "privacyblock",
        "Windows Privacy Blocker",
        "privacy_blocker",
        "security",
        f"{_PRIVACY_BLOCKER}:PrivacyBlockerPage",
    ),
    PageSpec(
        "shred",
        "Secure File Shredder",
        "secure_shredder",
        "security",
        f"{_SECURE_SHREDDER}:SecureShredderPage",
    ),
    # -- Recovery & Reports ------------------------------------------------
    PageSpec(
        "backups", "System Restore & Backups", "backups", "recovery", f"{_REPORT}:BackupsPage"
    ),
    PageSpec(
        "report", "Comprehensive Health Report", "report", "recovery", f"{_REPORT}:HealthReportPage"
    ),
    PageSpec(
        "sysinfo", "Hardware & OS Specifications", "sysinfo", "recovery", f"{_MORE}:SystemInfoPage"
    ),
    PageSpec(
        "license", "License & Tiers", "check", "recovery", f"{_LICENSE}:LicensePage"
    ),
    PageSpec("settings", "Settings & Preferences", "settings", "recovery", f"{_SHELL}:SettingsPage"),
    # -- Maintenance & Repair -----------------------------------------------
    PageSpec(
        "winupdate",
        "Windows Update Cleaner",
        "winupdate",
        "maintenance",
        f"{_ANALYSIS}:WindowsUpdatePage",
    ),
    PageSpec(
        "winrepair",
        "Windows Update Reset & Repair",
        "win_update_repair",
        "maintenance",
        f"{_WIN_UPDATE_REPAIR}:WinUpdateRepairPage",
    ),
    PageSpec(
        "diskanalyzer",
        "Deep Disk Space Scanner",
        "disk_analyzer",
        "maintenance",
        f"{_DISK_ADVANCED}:DiskAnalyzerPage",
    ),
    # -- Enterprise Storage, Security & Forensics Suite ---------------------
    PageSpec(
        "vssmanager",
        "Volume Shadow Copies (VSS)",
        "vss",
        "maintenance",
        f"{_ENTERPRISE}:VssManagerPage",
    ),
    PageSpec(
        "devdrive",
        "Dev Drive & Copy-on-Write",
        "devdrive",
        "system",
        f"{_ENTERPRISE}:DevDriveOptimizerPage",
    ),
    PageSpec(
        "bitlocker",
        "BitLocker Drive Encryption",
        "bitlocker",
        "security",
        f"{_ENTERPRISE}:BitLockerAuditorPage",
    ),
    PageSpec(
        "junctions",
        "NTFS Junction Points Explorer",
        "junctions",
        "files",
        f"{_ENTERPRISE}:JunctionAuditorPage",
    ),
    PageSpec(
        "bitrot",
        "Data Integrity & Bitrot Scrubber",
        "bitrot",
        "security",
        f"{_ENTERPRISE}:BitRotScrubberPage",
    ),
    PageSpec(
        "memcompress",
        "RAM Compression Monitor",
        "memcompress",
        "system",
        f"{_ENTERPRISE}:MemoryCompressionPage",
    ),
    PageSpec(
        "sandbox",
        "Windows Sandbox Cleaner",
        "sandbox",
        "cleanup",
        f"{_ENTERPRISE}:SandboxCleanerPage",
    ),
    PageSpec(
        "smbshares",
        "Network File Shares (SMB)",
        "smbshares",
        "network",
        f"{_ENTERPRISE}:SmbShareAuditorPage",
    ),
    PageSpec(
        "processtokens",
        "Process Security Tokens & Privileges",
        "tokens",
        "security",
        f"{_ENTERPRISE}:ProcessTokenPage",
    ),
    PageSpec(
        "growthtracker",
        "Folder Storage Growth Tracker",
        "growth",
        "files",
        f"{_ENTERPRISE}:StorageGrowthTrackerPage",
    ),
    # -- Next-Generation Enterprise Suite ---------------------------------
    PageSpec(
        "shadercache",
        "DirectX & GPU Shader Caches",
        "shadercache",
        "cleanup",
        f"{_NEXTGEN}:ShaderCachePage",
    ),
    PageSpec(
        "aitelemetry",
        "AI Features & Recall Sanitizer",
        "aitelemetry",
        "activity",
        f"{_NEXTGEN}:AiTelemetryCleanerPage",
    ),
    PageSpec(
        "ssdtrim",
        "SSD & NVMe TRIM Optimizer",
        "ssdtrim",
        "system",
        f"{_NEXTGEN}:SsdTrimOptimizerPage",
    ),
    PageSpec(
        "rmunlocker",
        "Process Restart Manager Unlocker",
        "rmunlocker",
        "files",
        f"{_NEXTGEN}:RestartManagerUnlockerPage",
    ),
    PageSpec(
        "vsshealth",
        "Volume Shadow Copy (VSS) Health",
        "vsshealth",
        "maintenance",
        f"{_NEXTGEN}:VssHealthAnalyzerPage",
    ),
    PageSpec(
        "devpackage",
        "Language Package Caches (npm/pip/cargo)",
        "devpackage",
        "cleanup",
        f"{_NEXTGEN}:DevPackageCachePage",
    ),
    PageSpec(
        "checksummatrix",
        "Multi-Hash Integrity Matrix",
        "checksummatrix",
        "files",
        f"{_NEXTGEN}:ChecksumMatrixPage",
    ),
    PageSpec(
        "winapp2",
        "Extended Third-Party App Caches",
        "winapp2",
        "cleanup",
        f"{_WINAPP2}:Winapp2CleanerPage",
    ),
    PageSpec(
        "srumbam",
        "Application Execution Forensics (BAM & SRUM)",
        "srumbam",
        "activity",
        f"{_SRUM_BAM}:SrumBamCleanerPage",
    ),
    PageSpec(
        "directstorage",
        "DirectStorage & BypassIO Gaming Acceleration",
        "directstorage",
        "system",
        f"{_DIRECTSTORAGE}:DirectStorageOptimizerPage",
    ),
    PageSpec(
        "standbymem",
        "Kernel Memory Standby List Purger",
        "standbymem",
        "system",
        f"{_STANDBY_MEM}:MemoryStandbyPurgerPage",
    ),
    PageSpec(
        "mftslack",
        "MFT File Record Slack Scrubber",
        "mftslack",
        "files",
        f"{_MFT_SLACK}:MftSlackScrubberPage",
    ),
    PageSpec(
        "searchopt",
        "Windows Search Catalog Compactor",
        "searchopt",
        "system",
        f"{_SEARCH_OPT}:SearchIndexOptimizerPage",
    ),
    PageSpec(
        "gamemode",
        "Gaming Session & FPS Booster",
        "controller",
        "system",
        f"{_GAME_MODE}:GameModePage",
    ),
    PageSpec(
        "delivery",
        "Delivery Optimization (WUDO) Cache",
        "download",
        "cleanup",
        f"{_DELIVERY}:DeliveryOptimizationPage",
    ),
    PageSpec(
        "wanaudit",
        "WAN & UPnP Gateway Auditor",
        "http",
        "network",
        f"{_WAN_AUDIT}:WanAuditPage",
    ),
    PageSpec(
        "oldfiles",
        "Old & Inactive Files Finder",
        "folder-temp",
        "cleanup",
        f"{_OLD_FILES}:OldFilesPage",
    ),
    PageSpec(
        "residuals",
        "Uninstalled App Residual Hunter",
        "crashdumps",
        "apps",
        f"{_RESIDUAL}:ResidualCleanerPage",
    ),
    PageSpec(
        "badfiles",
        "Bad Extensions & EXIF Studio",
        "warning",
        "files",
        f"{_BAD_FILES}:BadFilesStudioPage",
    ),
    PageSpec(
        "procstudio",
        "Advanced Process & Threat Studio",
        "processing",
        "system",
        f"{_PROC_STUDIO}:ProcessStudioPage",
    ),
)


def _validate() -> None:
    """Reject a malformed registry at import time rather than on first click."""
    seen: set[str] = set()
    group_ids = {group.id for group in GROUPS}
    for spec in PAGES:
        if spec.id in seen:
            raise RuntimeError(f"duplicate page id: {spec.id!r}")
        seen.add(spec.id)
        if spec.group not in group_ids:
            raise RuntimeError(
                f"page {spec.id!r} references unknown group {spec.group!r}; "
                f"known groups: {sorted(group_ids)}"
            )
        if ":" not in spec.factory:
            raise RuntimeError(
                f"page {spec.id!r} factory must be 'module:Class', "
                f"got {spec.factory!r}"
            )
    empty = [g.id for g in GROUPS if not any(p.group == g.id for p in PAGES)]
    if empty:
        raise RuntimeError(f"navigation groups with no pages: {empty}")


_validate()

#: page id -> spec, in declaration order.
BY_ID: Mapping[str, PageSpec] = {spec.id: spec for spec in PAGES}

#: The default landing page.
DEFAULT_PAGE_ID = PAGES[0].id


def ordered_ids() -> tuple[str, ...]:
    """Every page id, grouped by sidebar section then declaration order."""
    return tuple(spec.id for spec in ordered_specs())


def ordered_specs() -> tuple[PageSpec, ...]:
    """Every spec in sidebar order (group order, then declaration order)."""
    return tuple(spec for group in GROUPS for spec in PAGES if spec.group == group.id)


def grouped() -> Iterator[tuple[NavGroup, Sequence[PageSpec]]]:
    """Yield ``(group, pages)`` for each section in display order."""
    for group in GROUPS:
        yield group, tuple(spec for spec in PAGES if spec.group == group.id)


def group_of(page_id: str) -> str:
    """Return the group id owning *page_id*."""
    return BY_ID[page_id].group


__all__ = [
    "BY_ID",
    "DEFAULT_PAGE_ID",
    "GROUPS",
    "PAGES",
    "NavGroup",
    "PageSpec",
    "group_of",
    "grouped",
    "ordered_ids",
    "ordered_specs",
]

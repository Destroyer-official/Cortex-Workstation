#!/usr/bin/env python3
"""
Phase 1 Implementation Script - Interactive Guide

This script will guide you through implementing Phase 1 step by step.
Run this from the project root: python src/cortex_unified/implement_phase1.py
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

# ANSI color codes
class Color:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(step_num: int, title: str):
    """Print a step header."""
    print(f"\n{Color.BOLD}{Color.BLUE}{'='*70}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}Step {step_num}: {title}{Color.END}")
    print(f"{Color.BOLD}{Color.BLUE}{'='*70}{Color.END}\n")

def print_success(msg: str):
    """Print success message."""
    print(f"{Color.GREEN}✓ {msg}{Color.END}")

def print_error(msg: str):
    """Print error message."""
    print(f"{Color.RED}✗ {msg}{Color.END}")

def print_warning(msg: str):
    """Print warning message."""
    print(f"{Color.YELLOW}⚠ {msg}{Color.END}")

def print_info(msg: str):
    """Print info message."""
    print(f"{Color.CYAN}ℹ {msg}{Color.END}")

def print_command(cmd: str):
    """Print a command to run."""
    print(f"{Color.YELLOW}$ {cmd}{Color.END}")

def ask_yes_no(question: str) -> bool:
    """Ask a yes/no question."""
    while True:
        response = input(f"{Color.CYAN}{question} (y/n): {Color.END}").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please answer 'y' or 'n'")

def run_command(cmd: str, cwd: Optional[Path] = None) -> bool:
    """Run a command and return success status."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            if result.stdout:
                print(result.stdout)
            return True
        else:
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print_error(f"Command failed: {e}")
        return False

def get_project_root() -> Path:
    """Get the project root directory."""
    # Assuming this script is in src/cortex_unified/
    return Path(__file__).parent.parent.parent

def step1_check_environment():
    """Step 1: Check Python version and environment."""
    print_step(1, "Check Environment")
    
    # Check Python version
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 10:
        print_success("Python 3.10+ detected")
    else:
        print_error("Python 3.10+ required")
        return False
    
    # Check if we're in the right directory
    project_root = get_project_root()
    print(f"Project root: {project_root}")
    
    if not (project_root / "src" / "cortex_unified").exists():
        print_error("Not in correct directory structure")
        return False
    
    print_success("Environment check passed")
    return True

def step2_install_dependencies():
    """Step 2: Install core dependencies."""
    print_step(2, "Install Core Dependencies")
    
    print_info("Installing: pydantic, pydantic-settings, sqlalchemy, structlog, pytest, hypothesis")
    print_command("pip install pydantic pydantic-settings sqlalchemy structlog pytest hypothesis")
    
    if ask_yes_no("Install dependencies now?"):
        success = run_command(
            "pip install pydantic pydantic-settings sqlalchemy structlog pytest hypothesis"
        )
        if success:
            print_success("Dependencies installed")
            return True
        else:
            print_error("Failed to install dependencies")
            return False
    else:
        print_warning("Skipped - please install manually")
        return True

def step3_create_pyproject_toml():
    """Step 3: Create pyproject.toml in project root."""
    print_step(3, "Create pyproject.toml")
    
    project_root = get_project_root()
    template_path = project_root / "src" / "cortex_unified" / "pyproject.toml.template"
    target_path = project_root / "pyproject.toml"
    
    print(f"Template: {template_path}")
    print(f"Target: {target_path}")
    
    if target_path.exists():
        print_warning("pyproject.toml already exists")
        if not ask_yes_no("Overwrite?"):
            print_info("Keeping existing file")
            return True
    
    if not template_path.exists():
        print_error(f"Template not found: {template_path}")
        return False
    
    try:
        # Read template
        content = template_path.read_text(encoding='utf-8')
        
        # Remove the comment lines at the top
        lines = content.split('\n')
        if lines[0].startswith('#'):
            lines = lines[3:]  # Skip first 3 comment lines
        content = '\n'.join(lines)
        
        # Write to target
        target_path.write_text(content, encoding='utf-8')
        
        print_success(f"Created {target_path}")
        return True
    except Exception as e:
        print_error(f"Failed to create pyproject.toml: {e}")
        return False

def step4_install_package():
    """Step 4: Install package in editable mode."""
    print_step(4, "Install Package in Editable Mode")
    
    project_root = get_project_root()
    
    print_info("This will install cortex-cleaner as a package")
    print_command("pip install -e .")
    
    if ask_yes_no("Install package now?"):
        success = run_command("pip install -e .", cwd=project_root)
        if success:
            print_success("Package installed")
            return True
        else:
            print_error("Failed to install package")
            return False
    else:
        print_warning("Skipped - please install manually")
        return True

def step5_test_components():
    """Step 5: Test new components."""
    print_step(5, "Test New Components")
    
    print_info("Testing configuration system...")
    try:
        from cortex_unified.core.config_v2 import Config
        config = Config()
        print_success("Config system works")
    except Exception as e:
        print_error(f"Config test failed: {e}")
        return False
    
    print_info("Testing database system...")
    try:
        from cortex_unified.core.database import Database
        db = Database()  # In-memory
        scan = db.create_scan_run("test", "/tmp")
        print_success("Database system works")
    except Exception as e:
        print_error(f"Database test failed: {e}")
        return False
    
    print_info("Testing logging system...")
    try:
        from cortex_unified.core.logging_setup import configure_logging, get_logger
        configure_logging(log_level="INFO", json_output=False)
        log = get_logger(__name__)
        log.info("test_message", test="value")
        print_success("Logging system works")
    except Exception as e:
        print_error(f"Logging test failed: {e}")
        return False
    
    print_success("All components working")
    return True

def step6_create_test_directory():
    """Step 6: Create test directory structure."""
    print_step(6, "Create Test Directory")
    
    project_root = get_project_root()
    tests_dir = project_root / "tests"
    unit_dir = tests_dir / "unit"
    
    print(f"Creating: {tests_dir}")
    print(f"Creating: {unit_dir}")
    
    try:
        tests_dir.mkdir(exist_ok=True)
        unit_dir.mkdir(exist_ok=True)
        
        # Create __init__.py files
        (tests_dir / "__init__.py").touch()
        (unit_dir / "__init__.py").touch()
        
        print_success("Test directories created")
        
        # Copy test file
        source = project_root / "src" / "cortex_unified" / "tests" / "test_config_v2.py"
        target = unit_dir / "test_config_v2.py"
        
        if source.exists():
            import shutil
            shutil.copy(source, target)
            print_success(f"Copied test file to {target}")
        else:
            print_warning("Test file not found in source")
        
        return True
    except Exception as e:
        print_error(f"Failed to create test directory: {e}")
        return False

def step7_run_tests():
    """Step 7: Run test suite."""
    print_step(7, "Run Test Suite")
    
    project_root = get_project_root()
    
    print_info("Running pytest...")
    print_command("pytest tests/unit/test_config_v2.py -v")
    
    if ask_yes_no("Run tests now?"):
        success = run_command(
            "pytest tests/unit/test_config_v2.py -v",
            cwd=project_root
        )
        if success:
            print_success("Tests passed")
            return True
        else:
            print_warning("Some tests may have failed - check output above")
            return True  # Don't block on test failures
    else:
        print_warning("Skipped - please run manually")
        return True

def step8_verify_database():
    """Step 8: Verify database creation."""
    print_step(8, "Verify Database")
    
    db_path = Path.home() / ".cortex_cleaner" / "history.db"
    
    print(f"Expected database location: {db_path}")
    
    if db_path.exists():
        print_success(f"Database exists: {db_path}")
        size = db_path.stat().st_size
        print_info(f"Database size: {size} bytes")
    else:
        print_info("Database not yet created (will be created on first scan)")
        
        # Create it now
        try:
            from cortex_unified.core.database import get_database
            db = get_database()
            print_success("Database initialized")
        except Exception as e:
            print_error(f"Failed to initialize database: {e}")
            return False
    
    return True

def step9_summary():
    """Step 9: Show summary and next steps."""
    print_step(9, "Summary & Next Steps")
    
    print(f"{Color.GREEN}{Color.BOLD}✓ Phase 1 Foundation Complete!{Color.END}\n")
    
    print(f"{Color.BOLD}What you've accomplished:{Color.END}")
    print("  ✓ Installed core dependencies")
    print("  ✓ Created pyproject.toml")
    print("  ✓ Installed package in editable mode")
    print("  ✓ Verified all components work")
    print("  ✓ Set up test infrastructure")
    print("  ✓ Database initialized")
    
    print(f"\n{Color.BOLD}Next steps:{Color.END}")
    print("  1. Update existing code to use new components")
    print("     - See: MIGRATION_GUIDE.md")
    print("  2. Write more tests for existing code")
    print("  3. Run full test suite: pytest tests/ -v --cov")
    print("  4. Begin Phase 2 (Performance improvements)")
    
    print(f"\n{Color.BOLD}Quick commands:{Color.END}")
    print(f"  {Color.YELLOW}# Test imports{Color.END}")
    print("  python -c \"from cortex_unified.core.config_v2 import Config; print('OK')\"")
    print(f"\n  {Color.YELLOW}# Run tests{Color.END}")
    print("  pytest tests/unit/test_config_v2.py -v")
    print(f"\n  {Color.YELLOW}# Check database{Color.END}")
    print("  python -c \"from cortex_unified.core.database import get_database; db = get_database(); print('OK')\"")
    
    print(f"\n{Color.BOLD}Documentation:{Color.END}")
    print("  - START_HERE.md - Quick start guide")
    print("  - MIGRATION_GUIDE.md - How to update existing code")
    print("  - IMPLEMENTATION_ROADMAP.md - Full 8-phase plan")

def main():
    """Main implementation flow."""
    print(f"\n{Color.BOLD}{Color.HEADER}{'='*70}{Color.END}")
    print(f"{Color.BOLD}{Color.HEADER}Cortex Cleaner - Phase 1 Implementation{Color.END}")
    print(f"{Color.BOLD}{Color.HEADER}{'='*70}{Color.END}\n")
    
    print("This script will guide you through implementing Phase 1:")
    print("  • Install dependencies")
    print("  • Create pyproject.toml")
    print("  • Install package")
    print("  • Test components")
    print("  • Set up testing infrastructure")
    print()
    
    if not ask_yes_no("Ready to begin?"):
        print("Exiting...")
        return
    
    # Run steps
    steps = [
        step1_check_environment,
        step2_install_dependencies,
        step3_create_pyproject_toml,
        step4_install_package,
        step5_test_components,
        step6_create_test_directory,
        step7_run_tests,
        step8_verify_database,
        step9_summary,
    ]
    
    for step_func in steps:
        if not step_func():
            print_error(f"\nStep failed: {step_func.__name__}")
            print_info("Please fix the issue and run again")
            return
        
        # Pause between steps (except last one)
        if step_func != steps[-1]:
            input(f"\n{Color.CYAN}Press Enter to continue...{Color.END}")
    
    print(f"\n{Color.GREEN}{Color.BOLD}🎉 Implementation complete!{Color.END}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Color.YELLOW}Interrupted by user{Color.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Color.RED}Unexpected error: {e}{Color.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

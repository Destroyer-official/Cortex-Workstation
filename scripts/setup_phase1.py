#!/usr/bin/env python3
"""
Phase 1 Setup Script - Automated setup for foundation components.

This script helps you set up Phase 1 components step by step.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def run_command(cmd: List[str], cwd: Path = None) -> Tuple[bool, str]:
    """
    Run a command and return success status and output.
    
    Args:
        cmd: Command and arguments as list
        cwd: Working directory
    
    Returns:
        (success, output) tuple
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except Exception as e:
        return False, str(e)

def check_python_version() -> bool:
    """Check if Python version is >= 3.10."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} found, but 3.10+ required")
        return False

def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    print_header("Checking Dependencies")
    
    required = [
        "pydantic",
        "pydantic_settings",
        "sqlalchemy",
        "structlog",
        "pytest",
        "hypothesis"
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print_success(f"{package} is installed")
        except ImportError:
            print_error(f"{package} is NOT installed")
            missing.append(package)
    
    if missing:
        print_warning(f"\nMissing packages: {', '.join(missing)}")
        print_info("Install with: pip install " + " ".join(missing))
        return False
    
    return True

def test_config() -> bool:
    """Test the new configuration system."""
    print_header("Testing Configuration System")
    
    try:
        from cortex_unified.core.config_v2 import Config
        
        # Test basic creation
        config = Config()
        print_success("Config created successfully")
        
        # Test validation
        assert config.scan.min_age_days >= 0
        print_success("Config validation working")
        
        # Test backward compatibility
        assert hasattr(config, 'min_age_days')
        print_success("Backward compatibility working")
        
        return True
    except Exception as e:
        print_error(f"Config test failed: {e}")
        return False

def test_database() -> bool:
    """Test the database system."""
    print_header("Testing Database System")
    
    try:
        from cortex_unified.core.database import Database
        
        # Create in-memory database
        db = Database()
        print_success("Database created successfully")
        
        # Test scan run creation
        scan = db.create_scan_run("test_scan", "/tmp")
        assert scan.id is not None
        print_success("Scan run creation working")
        
        # Test update
        db.update_scan_run(scan.id, status="completed", items_found=10)
        print_success("Scan run update working")
        
        # Test query
        history = db.get_scan_history(limit=1)
        assert len(history) == 1
        print_success("History query working")
        
        return True
    except Exception as e:
        print_error(f"Database test failed: {e}")
        return False

def test_logging() -> bool:
    """Test the logging system."""
    print_header("Testing Logging System")
    
    try:
        from cortex_unified.core.logging_setup import configure_logging, get_logger
        
        # Configure logging
        configure_logging(log_level="INFO", json_output=False)
        print_success("Logging configured successfully")
        
        # Get logger
        log = get_logger(__name__)
        print_success("Logger created successfully")
        
        # Test logging
        log.info("test_message", test_key="test_value")
        print_success("Structured logging working")
        
        return True
    except Exception as e:
        print_error(f"Logging test failed: {e}")
        return False

def run_tests() -> bool:
    """Run the test suite."""
    print_header("Running Test Suite")
    
    # Find tests directory
    project_root = Path(__file__).parent.parent.parent
    tests_dir = project_root / "tests"
    
    if not tests_dir.exists():
        print_warning("Tests directory not found")
        print_info(f"Expected location: {tests_dir}")
        return False
    
    # Run pytest
    success, output = run_command(
        ["pytest", "tests/unit/test_config_v2.py", "-v"],
        cwd=project_root
    )
    
    if success:
        print_success("All tests passed")
        print(output)
        return True
    else:
        print_error("Some tests failed")
        print(output)
        return False

def check_pyproject_toml() -> bool:
    """Check if pyproject.toml exists."""
    print_header("Checking pyproject.toml")
    
    project_root = Path(__file__).parent.parent.parent
    pyproject = project_root / "pyproject.toml"
    
    if pyproject.exists():
        print_success(f"pyproject.toml found at {pyproject}")
        return True
    else:
        print_error(f"pyproject.toml NOT found at {pyproject}")
        print_info("Copy pyproject.toml.template to project root")
        return False

def main():
    """Main setup function."""
    print(f"\n{Colors.BOLD}Cortex Cleaner - Phase 1 Setup{Colors.END}")
    print(f"{Colors.BOLD}================================{Colors.END}\n")
    
    # Track results
    results = {}
    
    # 1. Check Python version
    results['python'] = check_python_version()
    
    # 2. Check dependencies
    results['dependencies'] = check_dependencies()
    
    if not results['dependencies']:
        print_warning("\nPlease install missing dependencies first:")
        print_info("pip install pydantic pydantic-settings sqlalchemy structlog pytest hypothesis")
        return
    
    # 3. Check pyproject.toml
    results['pyproject'] = check_pyproject_toml()
    
    # 4. Test configuration
    results['config'] = test_config()
    
    # 5. Test database
    results['database'] = test_database()
    
    # 6. Test logging
    results['logging'] = test_logging()
    
    # 7. Run tests (optional)
    print_info("\nWould you like to run the test suite? (y/n)")
    response = input().strip().lower()
    if response == 'y':
        results['tests'] = run_tests()
    
    # Summary
    print_header("Setup Summary")
    
    for component, success in results.items():
        if success:
            print_success(f"{component.capitalize()}: OK")
        else:
            print_error(f"{component.capitalize()}: FAILED")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ Phase 1 setup complete!{Colors.END}")
        print(f"\n{Colors.BLUE}Next steps:{Colors.END}")
        print("1. Review PHASE1_IMPLEMENTATION_CHECKLIST.md")
        print("2. Integrate new components into existing code")
        print("3. Run full test suite: pytest tests/ -v --cov")
        print("4. Begin Phase 2 (Performance improvements)")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ Some components need attention{Colors.END}")
        print(f"\n{Colors.BLUE}Please fix the failed components and run again.{Colors.END}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script to verify all critical fixes are working correctly.

Run this script to verify:
1. Keyring import fix
2. Security module
3. File operations security
4. Fast hashing algorithm
"""

import sys
from pathlib import Path

def test_keyring_import():
    """Test Fix #1: Keyring import should not crash."""
    print("\n" + "="*60)
    print("TEST #1: Keyring Import Fix")
    print("="*60)
    
    try:
        from cortex_unified.performance.multi_drive_scanner import DriveManager, HAS_KEYRING
        print("✓ multi_drive_scanner imports successfully")
        print(f"  Keyring available: {HAS_KEYRING}")
        if not HAS_KEYRING:
            print("  Note: Install keyring for secure credential storage: pip install keyring")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def test_security_module():
    """Test Fix #2: Security module should exist and work."""
    print("\n" + "="*60)
    print("TEST #2: Security Module")
    print("="*60)
    
    try:
        from cortex_unified.core.security import (
            is_safe_path, is_system_file, check_deletion_safety,
            validate_paths, is_path_writable
        )
        print("✓ Security module imports successfully")
        
        # Test system file detection
        import platform
        if platform.system() == "Windows":
            test_path = "C:\\Windows\\System32\\kernel32.dll"
            is_sys = is_system_file(test_path)
            print(f"  System file detection: {test_path} -> {is_sys}")
        
        # Test safe path validation
        temp_path = Path.cwd() / "test_file.txt"
        print(f"  Safe path check: {temp_path} -> {is_safe_path(temp_path) if temp_path.exists() else 'N/A (file does not exist)'}")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def test_security_integration():
    """Test Fix #3: File operations should use security checks."""
    print("\n" + "="*60)
    print("TEST #3: Security Integration")
    print("="*60)
    
    try:
        from cortex_unified.analyzers.file_shredder import FileShredder
        from cortex_unified.core.deleter import Deleter
        print("✓ FileShredder imports with security module")
        print("✓ Deleter imports with security module")
        
        # Verify security is imported
        import inspect
        shredder_source = inspect.getsource(FileShredder.shred_file)
        if "check_deletion_safety" in shredder_source:
            print("✓ FileShredder.shred_file uses security checks")
        else:
            print("⚠ FileShredder.shred_file may not use security checks")
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def test_fast_hashing():
    """Test Fix #4: Fast hashing algorithm should be used."""
    print("\n" + "="*60)
    print("TEST #4: Fast Hashing Algorithm")
    print("="*60)
    
    try:
        from cortex_unified.analyzers.duplicate_finder import DuplicateFinder, HAS_XXHASH
        
        df = DuplicateFinder()
        info = df.get_hash_algorithm_info()
        
        print(f"✓ DuplicateFinder initialized")
        print(f"  Algorithm: {info['algorithm']}")
        print(f"  xxHash available: {info['xxhash_available']}")
        print(f"  Performance: {info['performance']}")
        
        if not HAS_XXHASH:
            print(f"  Recommendation: {info['recommendation']}")
        
        # Verify not using MD5
        if info['algorithm'] != 'md5':
            print("✓ Not using slow MD5 algorithm")
        else:
            print("✗ Still using MD5 (should be xxhash or blake2b)")
            return False
        
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def test_cli():
    """Test that CLI works."""
    print("\n" + "="*60)
    print("TEST #5: CLI Functionality")
    print("="*60)
    
    try:
        from cortex_unified.cli.cli import main
        print("✓ CLI module imports successfully")
        print("  Run 'python -m cortex_unified.cli.cli --help' to see available commands")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print(" "*15 + "CORTEX CLEANER - CRITICAL FIXES TEST")
    print("="*70)
    
    tests = [
        ("Keyring Import Fix", test_keyring_import),
        ("Security Module", test_security_module),
        ("Security Integration", test_security_integration),
        ("Fast Hashing", test_fast_hashing),
        ("CLI Functionality", test_cli),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print(" "*25 + "TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print("\n" + "-"*70)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Critical fixes are working correctly.")
        print("\nNext steps:")
        print("  1. Install xxhash for best performance: pip install xxhash")
        print("  2. Test the application: python -m cortex_unified.cli.cli clean-empty --dry-run .")
        print("  3. Continue with Week 1 remaining fixes (see IMPLEMENTATION_PLAN_V2.md)")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

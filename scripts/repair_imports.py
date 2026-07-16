import os
from pathlib import Path

def replace_in_file(filepath, replacements):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        modified = content
        for old, new in replacements:
            modified = modified.replace(old, new)
            
        if modified != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(modified)
            print(f"Updated {filepath}")
    except Exception as e:
        print(f"Failed to process {filepath}: {e}")

def main():
    target_dir = Path(r"d:\desktop\desktop\Main_projects\Cortex_Cleaner")
    
    # Global package renames
    global_replacements = [
        ("cortex_engine", "cortex_unified"),
        ("deep_cleaner", "cortex_unified"),
        ("cortex_cleaner", "cortex_unified")
    ]
    
    # Process tests folder
    tests_dir = target_dir / "tests"
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.endswith('.py'):
                replace_in_file(os.path.join(root, file), global_replacements)
                
    # UI specific fixes for main_window.py
    main_window_path = target_dir / "src" / "cortex_unified" / "ui" / "main_window.py"
    if main_window_path.exists():
        ui_replacements = [
            ("from tabs.", "from cortex_unified.ui.tabs."),
            ("from navigation.", "from cortex_unified.ui.navigation."),
            ("from safety.", "from cortex_unified.ui.safety.")
        ]
        replace_in_file(main_window_path, ui_replacements)

    # Launcher fix
    launcher_path = target_dir / "src" / "cortex_unified" / "ui" / "launcher.py"
    if launcher_path.exists():
        launcher_replacements = [
            ("from main_window import main", "from cortex_unified.ui.main_window import main"),
            ("sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))", "sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))")
        ]
        replace_in_file(launcher_path, launcher_replacements)

if __name__ == "__main__":
    main()

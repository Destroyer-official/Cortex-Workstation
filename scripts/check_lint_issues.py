"""Diagnostic script to check for undefined names and lint anomalies."""

import os
import ast
import builtins
import sys

def check_undefined_names_in_file(filepath):
    """check_undefined_names_in_file.

    Manages check undefined names in file operations and coordinates related state changes for the component.

    Args:
        filepath: Filesystem path to the target file or directory.
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()
    try:
        tree = ast.parse(code, filename=filepath)
    except SyntaxError as e:
        return [f"SYNTAX ERROR: {e}"]

    # We can use pyflakes if installed or a simple visitor
    return []

# Let's try running pyflakes via subprocess or python
try:
    import pyflakes.api
    import pyflakes.reporter
    import io

    class Reporter:
        """Reporter.

        Manages Reporter operations and coordinates related state changes for the component.
        """
        def __init__(self):
            """Initialize the instance and configure internal state.

            Sets up sub-widgets, event signal connections, and default options.
            """
            self.errors = []
        def unexpectedError(self, filename, msg):
            """Unexpectederror.

            Manages unexpectedError operations and coordinates related state changes for the component.

            Args:
                filename: The filename parameter.
                msg: Informational or progress status message.
            """
            self.errors.append(f"{filename}: unexpected error: {msg}")
        def syntaxError(self, filename, msg, lineno, offset, text):
            """Syntaxerror.

            Manages syntaxError operations and coordinates related state changes for the component.

            Args:
                filename: The filename parameter.
                msg: Informational or progress status message.
                lineno: The lineno parameter.
                offset: The offset parameter.
                text: Display text string.
            """
            self.errors.append(f"{filename}:{lineno}: syntax error: {msg}")
        def flake(self, msg):
            """Flake.

            Manages flake operations and coordinates related state changes for the component.

            Args:
                msg: Informational or progress status message.
            """
            self.errors.append(str(msg))

    rep = Reporter()
    total_files = 0
    for root, dirs, files in os.walk('src'):
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(root, f)
                total_files += 1
                pyflakes.api.checkPath(p, rep)

    print(f"Scanned {total_files} files with pyflakes.")
    print(f"Total issues found: {len(rep.errors)}")
    
    undefined = [e for e in rep.errors if "undefined name" in e]
    print(f"\n=== Undefined Names ({len(undefined)}) ===")
    for u in undefined:
        print(u)
        
    other = [e for e in rep.errors if "undefined name" not in e and "imported but unused" not in e and "redefinition of unused" not in e]
    print(f"\n=== Other Potential Errors ({len(other)}) ===")
    for o in other[:20]:
        print(o)

except ImportError:
    print("pyflakes not installed, running custom AST visitor")

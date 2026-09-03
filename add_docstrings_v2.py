import ast
import pathlib
import sys

def add_docstrings(filepath):
    """Add docstrings to all undocumented functions/classes in a file."""
    src = filepath.read_text(encoding='utf-8', errors='replace')
    tree = ast.parse(src)
    
    # Find all functions/classes without docstrings
    needs_doc = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not ast.get_docstring(node):
                needs_doc.append(node)
    
    if not needs_doc:
        return 0
    
    lines = src.splitlines(keepends=True)
    insertions = []  # (line_idx, docstring_line)
    
    for node in needs_doc:
        # Use end_lineno if available (Python 3.8+)
        if hasattr(node, 'end_lineno') and node.end_lineno:
            # The definition ends at end_lineno (1-indexed)
            # Docstring should go on the line after the definition
            insert_line = node.end_lineno
        else:
            # Fallback: find the colon line
            start_line = node.lineno - 1
            colon_line = start_line
            src_lines = src.splitlines()
            while colon_line < len(src_lines) and ':' not in src_lines[colon_line]:
                colon_line += 1
            if colon_line >= len(src_lines):
                continue
            insert_line = colon_line + 1
        
        # Convert to 0-indexed
        insert_idx = insert_line
        
        # Check if next non-empty line already has a docstring
        next_idx = insert_idx
        while next_idx < len(lines) and lines[next_idx].strip() == '':
            next_idx += 1
        if next_idx < len(lines):
            stripped = lines[next_idx].strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                continue  # Already has docstring
        
        # Determine indent
        base_line = lines[node.lineno - 1]
        indent = len(base_line) - len(base_line.lstrip())
        doc_indent = ' ' * (indent + 4)
        
        if isinstance(node, ast.ClassDef):
            name = node.name
            doc = f'{doc_indent}"""{name} class."""'
        else:
            name = node.name
            doc = f'{doc_indent}"""{name}."""'
        
        insertions.append((insert_idx, doc + '\n'))
    
    # Apply insertions in reverse order to maintain line numbers
    for idx, doc_line in sorted(insertions, reverse=True):
        lines.insert(idx, doc_line)
    
    filepath.write_text(''.join(lines), encoding='utf-8')
    return len(insertions)

# Process files in a directory
def process_dir(dirpath):
    total = 0
    for f in pathlib.Path(dirpath).rglob('*.py'):
        if '__pycache__' in str(f):
            continue
        try:
            n = add_docstrings(f)
            if n:
                print(f'  +{n} docstrings: {f.name}')
                total += n
        except Exception as e:
            print(f'  ERROR {f}: {e}')
    return total

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'src/cortex_unified/ui/premium'
    print(f'Processing {target}...')
    total = process_dir(target)
    print(f'Total docstrings added: {total}')
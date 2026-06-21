import re
import glob

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    def repl(m):
        indent = m.group(1)
        return (f'{indent}except Exception as _exc:\\n{indent}    '
                f'import logging; logging.getLogger(__name__).debug("! caught exception: %s", _exc)')

    new_content, count = re.subn(r'^([ \t]+)except Exception:', repl, content, flags=re.MULTILINE)
    
    def repl_bare(m):
        indent = m.group(1)
        return (f'{indent}except Exception as _exc:\\n{indent}    '
                f'import logging; logging.getLogger(__name__).debug("! caught bare except: %s", _exc)')
    
    new_content, count2 = re.subn(r'^([ \t]+)except:', repl_bare, new_content, flags=re.MULTILINE)

    if count > 0 or count2 > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed {count + count2} occurrences in {filepath}')

for py_file in glob.glob('app/**/*.py', recursive=True):
    fix_file(py_file)

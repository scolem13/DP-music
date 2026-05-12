#!/usr/bin/env python3
"""Pre-render hook: ensure blank lines before list items in all .qmd files.

Pandoc requires a blank line between a paragraph and the first list item.
Without it the list is rendered as a continuation of the paragraph.
This script inserts the missing blank line wherever a prose line is
immediately followed by a bullet or ordered-list line, skipping YAML
front matter and fenced code blocks.
"""
import re, pathlib, sys

LIST_START = re.compile(r'^[ \t]*(?:[-*+]|\d+[.)]) ')

SKIP_PREV = re.compile(
    r'^(?:'
    r'\s*$'          # blank
    r'|#'            # heading
    r'|[-*+] '       # existing list item
    r'|\d+[.)]\s'    # ordered list item
    r'|```|~~~'      # code fence
    r'|\|'           # table
    r'|>'            # blockquote
    r'|:'            # definition / div
    r'|---'          # thematic break / YAML
    r'|\.\.\.'       # YAML end
    r')'
)

def fix(path):
    text = path.read_text()
    lines = text.split('\n')
    out = []
    in_yaml = True
    in_code = False
    changed = 0

    for i, line in enumerate(lines):
        # YAML front matter: skip until closing ---
        if in_yaml:
            out.append(line)
            if i > 0 and line.strip() == '---':
                in_yaml = False
            continue

        # Track fenced code blocks
        s = line.strip()
        if s.startswith('```') or s.startswith('~~~'):
            in_code = not in_code

        if not in_code and LIST_START.match(line) and out:
            prev = out[-1]
            if prev.strip() and not SKIP_PREV.match(prev):
                out.append('')
                changed += 1

        out.append(line)

    if changed:
        path.write_text('\n'.join(out))
        print(f'  {path.name}: +{changed} blank lines inserted')
    return changed

root = pathlib.Path(__file__).parent
total = 0
for qmd in sorted(root.rglob('*.qmd')):
    # Skip _site output and node_modules-style dirs
    if any(p in {'.git', '_site', '_book', '_freeze', 'node_modules'}
           for p in qmd.parts):
        continue
    total += fix(qmd)

if total:
    print(f'fix-blank-lines.py: {total} insertions total')

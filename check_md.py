#!/usr/bin/env python3
import re

with open('README.md') as f:
    content = f.read()

errors = []

# Check code block balance
if content.count('```') % 2 != 0:
    errors.append('Unmatched code block fences')

# Check for broken wiki-style links
if '[[' in content:
    errors.append('Broken link [[ found')

# Check heading level skips
headings = []
for line in content.split('\n'):
    m = re.match(r'^(#+)\s', line)
    if m:
        headings.append(len(m.group(1)))

for i in range(len(headings)-1):
    if headings[i+1] - headings[i] > 1:
        errors.append(f'Heading level skip: H{headings[i]} → H{headings[i+1]}')

if errors:
    print('❌ Markdown issues:')
    for e in errors:
        print(f'  - {e}')
    exit(1)
else:
    print('✅ Markdown structure valid')
    print(f'   Lines: {len(content.splitlines())}')
    print(f'   Code blocks: {content.count("```") // 2}')
    print(f'   Headings: {len(headings)}')

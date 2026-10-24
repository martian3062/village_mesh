"""Maintain generated report sections and export notices from the single README."""
import argparse
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def section_bounds(text, section):
    if not re.fullmatch(r'[a-z0-9-]+', section):
        raise ValueError('Invalid README section id')
    begin, end = f'<!-- BEGIN:{section} -->', f'<!-- END:{section} -->'
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError('Expected one complete README section: ' + section)
    start = text.index(begin) + len(begin)
    stop = text.index(end)
    if stop <= start:
        raise ValueError('README section markers are out of order: ' + section)
    return start, stop


def update_report(section, markdown, source_dir, root=ROOT):
    """Replace only one existing report, keeping other guides and notices intact."""
    path = root / 'README.md'
    text = path.read_text(encoding='utf-8')
    start, stop = section_bounds(text, section)
    lines = markdown.splitlines()
    if lines and lines[0].startswith('# '):
        lines = lines[1:]
    in_fence = False
    rendered = []
    headings = {}
    for line in lines:
        if line.startswith('```'):
            in_fence = not in_fence
        if not in_fence:
            heading = re.match(r'^#{2,5}\s+(.+)', line)
            if heading:
                title = re.sub(r'[`*_]', '', heading[1]).lower()
                slug = ''.join(c for c in title if c in '-_ ' or unicodedata.category(c)[0] in 'LN').replace(' ', '-')
                count = headings.get(slug, 0)
                headings[slug] = count + 1
                rendered.append(f'<a id="{section}-{slug}' + (f'-{count}' if count else '') + '"></a>')
            line = re.sub(r'^(#{2,5}) ', r'#\1 ', line)
            def link(match):
                target = match[1]
                if target.startswith('#') or urlsplit(target).scheme:
                    return match[0]
                relative, separator, fragment = target.partition('#')
                resolved = (root / source_dir / relative).resolve().relative_to(root.resolve()).as_posix()
                return '](' + resolved + (separator + fragment if separator else '') + ')'
            line = re.sub(r'\]\(([^)]+)\)', link, line)
        rendered.append(line)
    replacement = '\n\n' + '\n'.join(rendered).strip() + '\n\n'
    path.write_text(text[:start] + replacement + text[stop:], encoding='utf-8', newline='\n')


def export_package_readme(destination, root=ROOT):
    """Keep section links local and resolve repository files from a portable package."""
    text = (root / 'README.md').read_text(encoding='utf-8')
    def link(match):
        label, target = match[1], match[2]
        if target.startswith('#') or urlsplit(target).scheme:
            return match[0]
        if target.startswith('README.md#'):
            target = target.removeprefix('README.md')
        else:
            host = 'raw.githubusercontent.com' if label.startswith('!') else 'github.com'
            branch = 'main/' if label.startswith('!') else 'blob/main/'
            target = f'https://{host}/martian3062/village_mesh/{branch}' + target
        return label + '(' + target + ')'
    text = re.sub(r'(!?\[[^\]]*\])\(([^)]+)\)', link, text)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding='utf-8', newline='\n')


def export_notices(destination, root=ROOT):
    text = (root / 'README.md').read_text(encoding='utf-8')
    start, stop = section_bounds(text, 'third-party-notices')
    notices = text[start:stop].strip()
    notices = re.sub(r'^<a id="[^"]+"></a>\n?', '', notices, flags=re.MULTILINE).strip()
    if not notices:
        raise ValueError('Third-party notices are empty')
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('VILLAGE MESH - THIRD-PARTY NOTICES\n\n' + notices + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export-notices'])
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    export_notices(args.destination)

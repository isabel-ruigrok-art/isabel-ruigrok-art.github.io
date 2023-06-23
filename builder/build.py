#!/bin/env python3
import itertools
import logging
import re
from pathlib import Path
from typing import TypeAlias
from xml.etree import ElementTree as ET

import jinja2
import markdown

# Markdown-generated root element directly contains all <p>, <h1>, <h2>, etc.
MarkdownBody: TypeAlias = ET.Element

markdown_parser = markdown.Markdown(extensions=['meta', 'extra'])
jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(Path(__file__).parent / 'templates')
)


def extract_title(body: ET.Element, include_markup: bool = False) -> str | None:
    """ returns the text of the highest-level header that is a direct child of body. """
    for tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        if (h := body.find(tag)) is not None:
            break
    else:
        return None
    if include_markup:
        raise NotImplementedError()
    return h.text


def build_page(markdown_file: Path, output_dir: Path = Path('generated/projects')) -> Path:
    page_template = jinja_environment.get_template('project_page.html')
    page_file = output_dir / (slug(markdown_file.stem) + '.html')

    markdown_text = markdown_file.read_text()
    html_text = markdown_parser.reset().convert(markdown_text)
    html: MarkdownBody = ET.fromstring('<html>' + html_text + '</html>')
    title = extract_title(html)

    page = page_template.render(title=title, body=html_text)

    logging.info('%s -> %s', markdown_file, page_file)
    page_file.parent.mkdir(exist_ok=True, parents=True)
    page_file.write_text(page)
    return page_file


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('targets', type=Path, nargs='*')
    parser.add_argument('-v', '--verbose', action='count', dest='verbosity', default=0)
    parser.add_argument('-q', '--quiet', action='count', dest='quietness', default=0)
    args = parser.parse_args()
    logging.getLogger().setLevel(30 - 10 * (args.verbosity-args.quietness))
    targets: list[Path] = args.targets
    markdown_files = itertools.chain.from_iterable(file.rglob('*.md') if file.is_dir() else (file,) for file in targets)
    for markdown_file in markdown_files:
        build_page(markdown_file)


if __name__ == '__main__':
    main()

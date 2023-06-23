#!/bin/env python3
import itertools
import logging
import re
from pathlib import Path

import jinja2
import markdown

markdown_parser = markdown.Markdown(extensions=['meta', 'extra'])
jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(Path(__file__).parent / 'templates')
)


def slug(title: str) -> str:
    """ 'A (Normal) Title.' -> 'a-normal-title' """
    return re.sub(r'\W+', '-', title).strip('-').lower()


def build_page(markdown_file: Path, output_dir: Path = Path('generated/projects')) -> Path:
    page_template = jinja_environment.get_template('project_page.html')
    page_file = output_dir / (slug(markdown_file.stem) + '.html')

    markdown_text = markdown_file.read_text()
    html_text = markdown_parser.reset().convert(markdown_text)

    title = markdown_file.stem  # TODO
    body = html_text
    page = page_template.render(title=title, body=body)

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

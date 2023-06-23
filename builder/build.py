#!/bin/env python3
from __future__ import annotations

import dataclasses
import functools
import itertools
import logging
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import jinja2
import markdown

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


def sluggify(title: str) -> str:
    """ 'A (Normal) Title.' -> 'a-normal-title' """
    return re.sub(r'\W+', '-', title).strip('-').lower()


@dataclasses.dataclass
class Document:
    slug: str
    root: ET.Element
    """ Markdown-generated root element directly contains all <p>, <h1>, <h2>, etc. """
    metadata: dict[str] = dataclasses.field(default_factory=dict)

    @classmethod
    def load_file(cls, path: Path):
        if path.suffix not in ('.md', '.html', '.htm'):
            raise ValueError(f'Document.load_file() expects a markdown file, got {path}')
        return cls.from_string(path.read_text(), slug=sluggify(path.stem))

    @classmethod
    def from_string(cls, text: str, slug: str | None = None, *,
                    markdown_parser: markdown.Markdown = markdown_parser,
                    xml_parser: ET.XMLParser = None) -> Document:
        inner_html = markdown_parser.reset().convert(text)
        metadata = getattr(markdown_parser, 'Meta', None) or {}
        root = ET.fromstring(''.join(('<html>', inner_html, '</html>')), parser=xml_parser)

        instance = cls(slug, root, metadata=metadata)
        if instance.slug is None:
            instance.slug = sluggify(instance.title)
        return instance

    @functools.cached_property
    def title(self) -> str:
        return extract_title(self.root)

    def inner_html(self):
        return ET.tostring(self.root, encoding='unicode').replace('<html>', '').replace('</html>', '')


def build_page(markdown_file: Path, output_dir: Path = Path('generated/projects')) -> Path:
    page_template = jinja_environment.get_template('project_page.html')
    page_file = output_dir / (sluggify(markdown_file.stem) + '.html')

    document = Document.load_file(markdown_file)
    page = page_template.render(title=document.title, body=document.inner_html())

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

#!/bin/env python3
from __future__ import annotations

import dataclasses
import functools
import itertools
import logging
import re
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import jinja2
import markdown

import config

CONFIG = config.Config()

markdown_parser = markdown.Markdown(extensions=['meta', 'extra'])
jinja_environment = jinja2.Environment()


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


def identify_headline_image(body: ET.Element) -> tuple[ET.Element, ET.Element] | None:
    """ find the first image preceding any text elements and return the containing element and image element, or None if no such image exists. """
    for el in body:
        if el.text:
            return None
        if (img := el.find('img')) is not None:
            return el, img
    return None


def pop_headline_image(body: ET.Element) -> ET.Element:
    """ remove and return headline image from body """
    match identify_headline_image(body):
        case None:
            raise NotImplementedError('')
        case (p, img):
            body.remove(p)
            img: ET.Element
            if 'headline' not in img.get('class', '').split():
                img.set('class', img.get('class', '') + ' headline')
            return img


def sluggify(title: str) -> str:
    """ 'A (Normal) Title.' -> 'a-normal-title' """
    return re.sub(r'\W+', '-', title).strip('-').lower()


@dataclasses.dataclass
class Document:
    slug: str
    root: ET.Element
    """ Markdown-generated root element directly contains all <p>, <h1>, <h2>, etc. """
    headline_image: ET.Element = None
    """ image used in preview and at the top of page """
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
        img = pop_headline_image(root)

        instance = cls(slug, root, metadata=metadata, headline_image=img)
        if instance.slug is None:
            instance.slug = sluggify(instance.title)
        return instance

    @functools.cached_property
    def title(self) -> str:
        return extract_title(self.root)

    def inner_html(self):
        return ET.tostring(self.root, encoding='unicode').replace('<html>', '').replace('</html>', '')


def build_page(markdown_file: Path) -> Path:
    page_template = jinja_environment.get_template('project_page.html')
    page_file = CONFIG.output_dir / CONFIG.projects_dir.relative_to(CONFIG.input_dir) / (sluggify(markdown_file.stem) + '.html')

    document = Document.load_file(markdown_file)
    page = page_template.render(title=document.title, description=document.inner_html(), headline=ET.tostring(document.headline_image, encoding='unicode'))

    logging.info('%s -> %s', markdown_file, page_file)
    page_file.parent.mkdir(exist_ok=True, parents=True)
    page_file.write_text(page)
    return page_file


def gallery_item(document: Document) -> dict:
    # TODO: automatically determine this from image dimensions
    is_wide = 'wide' in document.headline_image.get('class').split()
    return dict(
        link=str('/' / CONFIG.projects_dir.relative_to(CONFIG.input_dir) / (document.slug + '.html')),
        title=document.title,
        image_src=document.headline_image.get('src'),
        wide=is_wide
    )


def build_projects_index(documents: Iterable[Document], output_path: Path = Path('projects/index.html')) -> Path:
    output_path = output_path if output_path.is_absolute() else CONFIG.output_dir / output_path
    template = jinja_environment.get_template('projects.html')
    page = template.render(items=(gallery_item(doc) for doc in documents))
    logging.info('-> %s', output_path)
    output_path.write_text(page)
    return output_path


def build_homepage(documents: Iterable[Document], output_path: Path = Path('index.html')) -> Path:
    output_path = output_path if output_path.is_absolute() else CONFIG.output_dir / output_path
    template = jinja_environment.get_template('index.html')
    newest_docs = itertools.islice(documents, 6)  # TODO: use date metadata
    page = template.render(items=(gallery_item(doc) for doc in newest_docs))
    logging.info('-> %s', output_path)
    output_path.write_text(page)
    return output_path


def main():
    global CONFIG
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('targets', type=Path, nargs='*')
    parser.add_argument('--gallery', action=argparse.BooleanOptionalAction, dest='should_update_gallery', default=True)
    parser.add_argument('-v', '--verbose', action='count', dest='verbosity', default=0)
    parser.add_argument('-q', '--quiet', action='count', dest='quietness', default=0)
    parser.add_argument('-c', '--config', type=Path, default=None)
    args = parser.parse_args()
    config_path: Path = args.config
    log_level: int = 30 - 10 * (args.verbosity - args.quietness)
    targets: list[Path] = args.targets

    logging.getLogger().setLevel(log_level)

    if config_path and not config_path.exists():
        logging.warning(f'config file not found: {config_path}')
    else:
        if not config_path and (Path.cwd() / 'config.ini').exists():
            config_path = Path.cwd() / 'config.ini'
        if config_path:
            CONFIG = config.Config.parse(config_path)
    jinja_environment.loader = jinja2.FileSystemLoader(CONFIG.templates_dir)

    markdown_files = list(
        itertools.chain.from_iterable(file.rglob('*.md') if file.is_dir() else (file,) for file in targets))
    for markdown_file in markdown_files:
        build_page(markdown_file)
    if args.should_update_gallery:
        build_projects_index(Document.load_file(file) for file in markdown_files)
        build_homepage(Document.load_file(file) for file in markdown_files)


if __name__ == '__main__':
    main()

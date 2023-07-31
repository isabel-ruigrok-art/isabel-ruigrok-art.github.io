from __future__ import annotations

import copy
import dataclasses
import functools
from pathlib import Path
from typing import Callable, Iterable
from xml.etree import ElementTree as ET

import markdown

from util import sluggify

markdown_parser = markdown.Markdown(extensions=['meta', 'extra'])


def get_highest_level_heading_tag(body: ET.Element) -> str | None:
    """ return the highest level heading tag occurring in `body`, or None if there are no headings.  """
    for tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        if (el := body.find(tag)) is not None:
            return el.tag
    return None


def section_by_heading(body: ET.Element, heading: str = None) -> None:
    """ split body into sections based on top-level headings. """
    if heading is None:
        heading = get_highest_level_heading_tag(body)
    sections = []
    section = []
    for el in body:
        if el.tag == heading:
            sections.append(section)
            section = [el]
        else:
            section.append(el)
    sections.append(section)

    def make_section_element(children: Iterable[ET.Element]) -> ET.Element:
        el = ET.SubElement(body, 'section')
        el.extend(children)
        return el

    body[:] = [*sections[0], *(make_section_element(children) for children in sections[1:])]


def extract_title(body: ET.Element, include_markup: bool = False) -> str | None:
    """ returns the text of the first highest-level header"""
    for tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        if (h := body.find(f'.//{tag}')) is not None:
            break
    else:
        return None
    if include_markup:
        raise NotImplementedError()
    return h.text


def identify_primary_image(body: ET.Element) -> ET.Element | None:
    """ find the primary image in document body.

    If there is an image with .headline class, this is the primary image.
    Otherwise, the first image element is returned, or None if there are no images.
    """
    return next((img for img in body.iter('img') if 'headline' in img.get('class', '').split()), None) or next(body.iter('img'), None)


def process_headline_image(body: ET.Element) -> None:
    """ give headline images the class `headline` and move them to a div.

    An image is considered a headline image if:
        - it is the first image in the document, and
        - it is the only child of a top-level <p> element, and
        - it is not preceded by any text content.
    """
    for i, el in enumerate(body):
        if el.text:
            return
        if el.tag == 'p' and len(el) == 1 and el[0].tag == 'img':
            el.tag = 'div'
            classes = el.get('class', '').split()
            if 'headline' not in classes:
                classes.append('headline')
                el.set('class', ' '.join(classes))


@dataclasses.dataclass
class Document:
    slug: str
    root: ET.Element
    """ Markdown-generated root element directly contains all <p>, <h1>, <h2>, etc. """
    primary_image: ET.Element = None
    """ image used in preview and at the top of page """
    metadata: dict[str] = dataclasses.field(default_factory=dict)

    @classmethod
    def load_file(cls, path: Path):
        if path.suffix not in ('.md', '.html', '.htm'):
            raise ValueError(f'Document.load_file() expects a markdown file, got {path}')
        return cls.from_string(path.read_text(), slug=sluggify(path.stem))

    @classmethod
    def from_string(cls, text: str, slug: str | None = None) -> Document:
        inner_html = markdown_parser.reset().convert(text)
        metadata = getattr(markdown_parser, 'Meta', None) or {}
        root = ET.fromstring(''.join(('<html>', inner_html, '</html>')), parser=xml_parser)
        root = ET.fromstring(''.join(('<html>', inner_html, '</html>')))
        # deep copy to avoid problems with double-rewriting urls.
        img = copy.deepcopy(identify_primary_image(root))

        instance = cls(slug, root, metadata=metadata, primary_image=img)
        if instance.slug is None:
            instance.slug = sluggify(instance.title)
        return instance

    @functools.cached_property
    def title(self) -> str:
        return extract_title(self.root)

    def inner_html(self):
        return ET.tostring(self.root, encoding='unicode').replace('<html>', '').replace('</html>', '')

    def rewrite_urls(self, fn: Callable[[str], str]) -> None:
        self.primary_image.set('src', fn(self.primary_image.get('src')))
        for el in self.root.iter('img'):
            if el is self.primary_image:
                continue
            el.set('src', fn(el.get('src')))
        for el in self.root.iter('a'):
            el.set('href', fn(el.get('href')))

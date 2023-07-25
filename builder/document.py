from __future__ import annotations

import copy
import dataclasses
import functools
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree as ET

import markdown

from util import sluggify

markdown_parser = markdown.Markdown(extensions=['meta', 'extra'])


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


def identify_thumbnail_image(body: ET.Element) -> tuple[ET.Element, ET.Element] | None:
    for el in body:
        if (img := el.find('img')) is not None:
            return el, img
    return None


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
        img = (identify_headline_image(root) or identify_thumbnail_image(root) or (None, None))[1]
        img = copy.deepcopy(img)

        instance = cls(slug, root, metadata=metadata, headline_image=img)
        if instance.slug is None:
            instance.slug = sluggify(instance.title)
        return instance

    @functools.cached_property
    def title(self) -> str:
        return extract_title(self.root)

    def inner_html(self):
        return ET.tostring(self.root, encoding='unicode').replace('<html>', '').replace('</html>', '')

    def rewrite_urls(self, fn: Callable[[str], str]) -> None:
        for el in self.root.iter('img'):
            el.set('src', fn(el.get('src')))
        for el in self.root.iter('a'):
            el.set('href', fn(el.get('href')))
        self.headline_image.set('src', fn(self.headline_image.get('src')))

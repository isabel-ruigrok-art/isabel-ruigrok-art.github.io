from __future__ import annotations

import dataclasses
import functools
import logging
import re
from pathlib import Path
from typing import Callable, ClassVar
from xml.etree import ElementTree as ET

import markdown

markdown_parser = markdown.Markdown(extensions=['meta', 'extra'])


def make_headline_image(src: str, alt: str, wide: bool = False) -> ET.Element:
    """ make an `img.headline` element with the given src and alt text, and optionally the 'wide' class. """
    img = ET.Element('img')
    img.set('src', str(src))
    img.set('alt', alt)
    if wide:
        img.set('class', 'wide headline')
    else:
        img.set('class', 'headline')
    return img


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


def is_wide(path: Path) -> bool:
    """ Return true if the image width is greater than the height. """
    # todo: implement
    return False


@dataclasses.dataclass
class Resource:
    DIRECTORY: ClassVar[Path]
    """ relative path to output directory (should be set by subclasses, e.g. pieces/ or projects/) """
    path: Path
    """ Piece directory """
    slug: str = None
    """ Piece slug, defaults to directory name """
    description_path: Path = None
    """ Path to description file, defaults to index.md """

    def __post_init__(self):
        if not self.slug:
            self.slug = sluggify(self.path.stem)

    @classmethod
    def from_path(cls, path: Path):
        if path.suffix in ('.md', '.html'):
            return cls(path.parent, description_path=path)
        else:
            return cls(path)

    @functools.cached_property
    def assets(self) -> list[Path]:
        return [p for p in self.path.iterdir() if p.suffix not in ('.md', '.html', '')]

    @functools.cached_property
    def description(self) -> Document:
        if self.description_path:
            pass
        elif (p := self.path / 'index.md').exists():
            self.description_path = p
        elif (p := self.path / f'{self.slug}.md').exists():
            self.description_path = p
        elif p := next(self.path.glob('.md'), None):
            self.description_path = p
        else:
            logging.debug('generating default description for %s/%s', self.DIRECTORY, self.slug)
            return self._generate_description()
        return Document.load_file(self.description_path)

    def _generate_description(self) -> Document:
        """ generate a simple description document for when no index.md is present. """
        if not self.assets:
            headline_img = None
        else:
            path = next((p for p in self.assets if sluggify(p.stem) == self.slug), self.assets[0])
            headline_img = make_headline_image(str(path.relative_to(self.path)), alt=str(path.stem), wide=is_wide(path))

        return Document(
            self.slug,
            ET.fromstring(f'<html><h1>{self.slug}</h1></html>'),
            headline_image=headline_img
        )


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

    def rewrite_urls(self, fn: Callable[[str], str]) -> None:
        for el in self.root.iter('img'):
            el.set('src', fn(el.get('src')))
        for el in self.root.iter('a'):
            el.set('href', fn(el.get('href')))
        self.headline_image.set('src', fn(self.headline_image.get('src')))


@dataclasses.dataclass
class Piece(Resource):
    DIRECTORY: ClassVar[Path] = Path('pieces')


@dataclasses.dataclass
class Project(Resource):
    DIRECTORY: ClassVar[Path] = Path('projects')

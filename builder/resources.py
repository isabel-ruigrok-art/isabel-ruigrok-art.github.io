from __future__ import annotations

import copy
import dataclasses
import functools
import logging
import urllib.parse
from pathlib import Path
from typing import ClassVar

from document import Document
from util import sluggify, is_wide


def is_relative_url(url: str):
    url = urllib.parse.urlsplit(url, scheme='file')
    return url.scheme == 'file' and not url.path.startswith('/')


@dataclasses.dataclass
class Resource:
    DIRECTORY: ClassVar[Path]
    """ relative path to output directory (should be set by subclasses, e.g. pieces/ or projects/) """
    path: Path
    """ Piece directory """
    slug: str = None
    """ Piece slug, defaults to directory name """
    _description_path: Path = None
    description_path: dataclasses.InitVar[Path] = None
    """ Path to description file, defaults to slug.md or index.md """

    def __post_init__(self, description_path: Path = None):
        if not self.slug:
            self.slug = sluggify(self.path.stem)
        if description_path is not None:
            self._description_path = description_path

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
    def description_path(self) -> Path | None:
        if (p := self.path / 'index.md').exists():
            return p
        if (p := self.path / f'{self.slug}.md').exists():
            return p
        if p := next(self.path.glob('*.md'), None):
            return p
        return None

    @functools.cached_property
    def description(self) -> Document:
        if not self.description_path:
            logging.debug('generating default description for %s/%s', self.DIRECTORY, self.slug)
            return self._generate_description()
        return Document.load_file(self.description_path)

    @functools.cached_property
    def description_with_absolute_urls(self) -> Document:
        doc = copy.deepcopy(self.description)

        def fn(url: str):
            if not is_relative_url(url):
                return url
            return str((Path('/') / self.DIRECTORY / self.slug / url).resolve())

        doc.rewrite_urls(fn)
        return doc

    def _generate_description(self) -> Document:
        """ generate a simple description document for when no index.md is present. """
        if not self.assets:
            headline_img = ''
        else:
            path = next((p for p in self.assets if sluggify(p.stem) == self.slug), self.assets[0])
            alt = path.stem
            relative_path = path.relative_to(self.path)
            classes = '.wide .headline' if is_wide(path) else '.headline'
            headline_img = f'![{alt}]({relative_path}){{{classes}}}'
        md = f'{headline_img}\n# {self.slug}'
        return Document.from_string(md, slug=self.slug)


@dataclasses.dataclass
class Piece(Resource):
    DIRECTORY: ClassVar[Path] = Path('pieces')


@dataclasses.dataclass
class Project(Resource):
    DIRECTORY: ClassVar[Path] = Path('projects')

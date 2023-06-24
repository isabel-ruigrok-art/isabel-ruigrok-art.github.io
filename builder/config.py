from __future__ import annotations

import configparser
import dataclasses
import re
import shlex
from pathlib import Path
from typing import Collection


@dataclasses.dataclass()
class Config:
    root_dir: Path = Path.cwd()
    build_dir: Path = Path('build')
    output_dir: Path = Path('generated')
    input_dir: Path = Path('source')
    templates_dir: Path = input_dir / 'templates'
    static_paths: Collection[Path] = (input_dir / 'style', input_dir / 'script', input_dir / 'images')
    projects_dir: Path = input_dir / 'projects'

    def __post_init__(self):
        if not self.root_dir:
            return
        for field in 'build_dir', 'output_dir', 'input_dir', 'templates_dir', 'projects_dir':
            dir_path: Path = getattr(self, field)
            if not dir_path.is_absolute():
                setattr(self, field, self.root_dir / dir_path)
        self.static_paths = [path if path.is_absolute() else self.root_dir / path for path in self.static_paths]

    @classmethod
    def parse(cls, config_path: Path) -> Config:
        parser = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
            converters={
                'path': Path,
                'list': str.split,
                'pathlist': lambda val: [Path(p) for p in shlex.split(val)]
            },
            defaults={
                'root': str(config_path.parent)
            }
        )
        parser.optionxform = lambda optionstr, p=re.compile('\W+'): p.sub('_', optionstr).strip('_')
        parser.SECTCRE = re.compile(r"\[ *(?P<header>[^]]+?) *\]")
        parser.read(config_path)

        return cls(
            root_dir=parser['paths'].getpath('root', config_path.parent),
            build_dir=parser['paths'].getpath('build', cls.build_dir),
            output_dir=parser['paths'].getpath('output', cls.output_dir),
            templates_dir=parser['paths'].getpath('templates', cls.templates_dir),
            input_dir=parser['paths'].getpath('input', cls.input_dir),
            projects_dir=parser['paths'].getpath('projects', cls.projects_dir),
            static_paths=parser['paths'].getpathlist('static', cls.static_paths)
        )

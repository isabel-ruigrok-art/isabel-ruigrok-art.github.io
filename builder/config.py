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
    pieces_dir: Path = input_dir / 'pieces'

    def __post_init__(self):
        if not self.root_dir:
            return
        for field in 'build_dir', 'output_dir', 'input_dir', 'templates_dir', 'projects_dir', 'pieces_dir':
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
            pieces_dir=parser['paths'].getpath('pieces', cls.pieces_dir),
            static_paths=parser['paths'].getpathlist('static', cls.static_paths)
        )


def _get_config() -> Config:
    import argparse
    import sys
    import warnings
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('-c', '--config', type=Path)
    args, unparsed = parser.parse_known_args()
    sys.argv = [sys.argv[0], *unparsed]  # ⚠️
    config_path: Path | None = args.config
    default_config_path: Path = Path.cwd() / 'config.ini'

    if config_path and not config_path.exists():
        raise FileNotFoundError(f'config file not found: {config_path}')
    if config_path:
        return Config.parse(config_path)
    if default_config_path.exists():
        return Config.parse(default_config_path)
    warnings.warn('no config file; using default config.')
    return Config()


CONFIG = _get_config()

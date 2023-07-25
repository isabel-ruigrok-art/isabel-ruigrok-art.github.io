#!/bin/env python3
from __future__ import annotations

import itertools
import logging
import os
import shutil
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

import jinja2

from document import Document, Piece, Project, Resource
from config import CONFIG

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(CONFIG.templates_dir)
)


def build_resource(resource: Resource) -> Path:
    page_template = jinja_environment.get_template(f'resource_page.html')
    page_dir = CONFIG.output_dir / resource.DIRECTORY / resource.slug
    page_file = page_dir / 'index.html'
    description = resource.description
    page = page_template.render(
        title=description.title,
        description=description.inner_html(),
        headline=ET.tostring(description.headline_image, encoding='unicode') if
        description.headline_image is not None and 'headline' in description.headline_image.get('class', '').split() else ''
    )

    logging.info('%s -> %s', resource.slug, page_file)
    page_dir.mkdir(exist_ok=True, parents=True)
    page_file.write_text(page)
    for asset in resource.assets:
        # TODO: avoid unnecessary copying
        logging.info('%s -> %s', asset, page_dir / asset.name)
        shutil.copy(asset, page_dir / asset.name)
    return page_file


def gallery_item(resource: Resource) -> dict:
    description = resource.description
    # TODO: automatically determine this from image dimensions
    is_wide = 'wide' in description.headline_image.get('class', '').split()
    return dict(
        link=str(Path('/') / resource.DIRECTORY / resource.slug),
        title=description.title,
        image_src=description.headline_image.get('src'),
        wide=is_wide
    )


def build_resources_index(resources: Iterable[Resource], kind: type[Resource] | str) -> Path:
    kind = Path(getattr(kind, 'DIRECTORY', kind))
    output_path = CONFIG.output_dir / kind / 'index.html'
    template = jinja_environment.get_template(f'resource_index.html')
    page = template.render(items=(gallery_item(r) for r in resources if r.DIRECTORY == kind))
    logging.info('-> %s', output_path)
    output_path.write_text(page)
    return output_path


def build_homepage(projects: Iterable[Project], output_path: Path = Path('index.html')) -> Path:
    output_path = output_path if output_path.is_absolute() else CONFIG.output_dir / output_path
    template = jinja_environment.get_template('index.html')
    newest_projects = itertools.islice(projects, 6)  # TODO: use date metadata
    page = template.render(items=(gallery_item(project) for project in newest_projects))
    logging.info('-> %s', output_path)
    output_path.write_text(page)
    return output_path


def sync_static_path(src: Path) -> Path:
    dst = CONFIG.output_dir / src.relative_to(CONFIG.input_dir)
    if src.is_file():
        if not dst.exists():
            try:
                os.link(src, dst)
                logging.info('%s => %s', src, dst)
            except OSError:
                shutil.copy2(src, dst)
                logging.info('%s -> %s', src, dst)
        elif dst.samefile(src):
            pass
        else:
            shutil.copy2(src, dst)
            logging.info('%s -> %s', src, dst)
    elif src.is_dir():
        if not dst.exists():
            try:
                os.symlink(src, dst, target_is_directory=True)
                logging.info('%s => %s', src, dst)
            except OSError:
                shutil.copytree(src, dst)
                logging.info('%s -> %s', src, dst)
        elif dst.is_symlink():
            pass
        else:
            # TODO: only sync changes.
            shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
            logging.info('%s -> %s', src, dst)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('targets', type=Path, nargs='*',
                        help='project .md files to build / include in gallery.\n'
                             'if not given, includes all .md files in the projects directory.')
    parser.add_argument('--project-pages', action=argparse.BooleanOptionalAction, dest='should_build_project_pages', default=True, help='build project pages')
    parser.add_argument('--piece-pages', action=argparse.BooleanOptionalAction, dest='should_build_piece_pages', default=True, help='build piece pages')
    parser.add_argument('--gallery', action=argparse.BooleanOptionalAction, dest='should_update_gallery', default=True, help='update project index and homepage')
    parser.add_argument('--sync-static', action=argparse.BooleanOptionalAction, dest='should_sync_static', default=False, help='copy/link static files to output')
    parser.add_argument('-v', '--verbose', action='count', dest='verbosity', default=0)
    parser.add_argument('-q', '--quiet', action='count', dest='quietness', default=0)
    args = parser.parse_args()
    log_level: int = 30 - 10 * (args.verbosity - args.quietness)
    targets: list[Path] = args.targets

    logging.getLogger().setLevel(log_level)

    if targets:
        projects = [Project.from_path(file) for file in targets if CONFIG.projects_dir in file.parents]
        pieces = [Piece.from_path(file) for file in targets if CONFIG.pieces_dir in file.parents]
        other = [file for file in targets if CONFIG.projects_dir not in file.parents and CONFIG.pieces_dir not in file.parents]
        if other:
            logging.warning('ignoring files outside of projects and pieces directories: %s', other)
    else:
        projects = [Project.from_path(file) for file in CONFIG.projects_dir.iterdir()]
        pieces = [Piece.from_path(file) for file in CONFIG.pieces_dir.iterdir()]

    if args.should_build_project_pages:
        for project in projects:
            build_resource(project)
    if args.should_build_piece_pages:
        for piece in pieces:
            build_resource(piece)
    if args.should_update_gallery:
        for resource in itertools.chain(projects, pieces):
            # todo: make this less hacky
            def fn(url):
                if ':' in url:  # should really use urlparse, but this is good enough for now
                    return url
                if url.startswith('/'):
                    return url
                # FIXME: this assumes input and output directories have the same structure
                absolute = (resource.path / url).resolve()
                try:
                    return absolute.relative_to(CONFIG.input_dir / resource.DIRECTORY).as_posix()
                except ValueError:
                    return '/' + absolute.relative_to(CONFIG.input_dir).as_posix()
            resource.description.rewrite_urls(fn)
        build_resources_index(projects, kind=Project)
        build_resources_index(pieces, kind=Piece)
        build_homepage(projects)
    if args.should_sync_static:
        for static_path in CONFIG.static_paths:
            sync_static_path(static_path)


if __name__ == '__main__':
    main()

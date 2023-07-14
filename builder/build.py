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

from document import Document, Piece
from config import CONFIG

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(CONFIG.templates_dir)
)


def build_page(document: Document) -> Path:
    page_template = jinja_environment.get_template('project_page.html')
    page_file = CONFIG.output_dir / CONFIG.projects_dir.relative_to(CONFIG.input_dir) / (document.slug + '.html')

    page = page_template.render(title=document.title, description=document.inner_html(), headline=ET.tostring(document.headline_image, encoding='unicode'))

    logging.info('%s -> %s', document.slug, page_file)
    page_file.parent.mkdir(exist_ok=True, parents=True)
    page_file.write_text(page)
    return page_file


def build_piece(piece: Piece) -> Path:
    page_template = jinja_environment.get_template('project_page.html')
    page_dir = CONFIG.output_dir / CONFIG.pieces_dir.relative_to(CONFIG.input_dir) / piece.slug
    page_file = page_dir / 'index.html'
    description = piece.description

    page = page_template.render(title=description.title, description=description.inner_html(), headline=ET.tostring(description.headline_image, encoding='unicode'))

    logging.info('%s -> %s', piece.slug, page_file)
    page_dir.mkdir(exist_ok=True, parents=True)
    page_file.write_text(page)
    for asset in piece.assets:
        # TODO: avoid unnecessary copying
        logging.info('%s -> %s', asset, page_dir / asset.name)
        shutil.copy(asset, page_dir / asset.name)
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
        markdown_files = itertools.chain.from_iterable(file.rglob('*.md') if file.is_dir() else (file,) for file in targets)
        projects = [Document.load_file(file) for file in markdown_files if file.is_relative_to(CONFIG.projects_dir)]
        pieces = [Piece(file) for file in markdown_files if file.is_relative_to(CONFIG.pieces_dir)]
        other = [file for file in markdown_files if not file.is_relative_to(CONFIG.pieces_dir) and not file.is_relative_to(CONFIG.projects_dir)]
        if other:
            logging.warning('ignoring files outside of projects and pieces directories: %s', other)
    else:
        projects = [Document.load_file(file) for file in CONFIG.projects_dir.glob('*.md')]
        pieces = [Piece(file) for file in CONFIG.pieces_dir.iterdir()]

    if args.should_build_project_pages:
        for document in projects:
            build_page(document)
    if args.should_build_piece_pages:
        for piece in pieces:
            build_piece(piece)
    if args.should_update_gallery:
        build_projects_index(projects)
        build_homepage(projects)
    if args.should_sync_static:
        for static_path in CONFIG.static_paths:
            sync_static_path(static_path)


if __name__ == '__main__':
    main()

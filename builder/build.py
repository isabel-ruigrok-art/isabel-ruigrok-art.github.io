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

import config
from builder.document import Document

CONFIG = config.Config()

jinja_environment = jinja2.Environment()


def build_page(document: Document) -> Path:
    page_template = jinja_environment.get_template('project_page.html')
    page_file = CONFIG.output_dir / CONFIG.projects_dir.relative_to(CONFIG.input_dir) / (document.slug + '.html')

    page = page_template.render(title=document.title, description=document.inner_html(), headline=ET.tostring(document.headline_image, encoding='unicode'))

    logging.info('%s -> %s', document.slug, page_file)
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
    global CONFIG
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('targets', type=Path, nargs='*',
                        help='project .md files to build / include in gallery.\n'
                             'if not given, includes all .md files in the projects directory.')
    parser.add_argument('--project-pages', action=argparse.BooleanOptionalAction, dest='should_build_project_pages', default=True, help='build project pages')
    parser.add_argument('--gallery', action=argparse.BooleanOptionalAction, dest='should_update_gallery', default=True, help='update project index and homepage')
    parser.add_argument('--sync-static', action=argparse.BooleanOptionalAction, dest='should_sync_static', default=False, help='copy/link static files to output')
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

    if targets:
        markdown_files = itertools.chain.from_iterable(file.rglob('*.md') if file.is_dir() else (file,) for file in targets)
    else:
        markdown_files = CONFIG.projects_dir.glob('*.md')
    documents = [Document.load_file(file) for file in markdown_files]
    if args.should_build_project_pages:
        for document in documents:
            build_page(document)
    if args.should_update_gallery:
        build_projects_index(documents)
        build_homepage(documents)
    if args.should_sync_static:
        for static_path in CONFIG.static_paths:
            sync_static_path(static_path)


if __name__ == '__main__':
    main()

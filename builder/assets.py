import dataclasses
import logging
import mimetypes
import shutil
from pathlib import Path

import PIL.Image

from config import CONFIG

mimetypes.add_type('image/webp', '.webp')


def is_up_to_date(source: Path, target: Path) -> bool:
    return target.exists() and target.stat().st_mtime >= source.stat().st_mtime


def convert_image(source: Path, target: Path, source_mimetype: str, target_mimetype: str):
    with PIL.Image.open(source) as img:
        if img.mode == 'RGBA' and target_mimetype == 'image/jpeg':
            background = PIL.Image.new('RGBA', img.size, CONFIG.background_color)
            background.paste(img, mask=img)
            img = background.convert('RGB')
        img.save(target)


def convert_video(source: Path, target: Path, source_mimetype: str, target_mimetype: str):
    raise NotImplementedError()


def copy_or_convert(source: Path, target: Path, source_mimetype: str, target_mimetype: str):
    """ Copy source to target, converting if necessary. """
    if source_mimetype == target_mimetype:
        logging.info('%s -> %s', source, target)
        shutil.copyfile(source, target)
        return
    source_kind = source_mimetype.split('/')[0]
    target_kind = target_mimetype.split('/')[0]
    if source_kind != target_kind:
        raise NotImplementedError(f'cannot convert {source_kind} {source}  to  {target_kind} {target}')
    if source_kind == 'image':
        logging.info('%s -> %s', source, target)
        convert_image(source, target, source_mimetype, target_mimetype)
        return target
    elif source_kind == 'video':
        logging.info('%s -> %s', source, target)
        convert_image(source, target, source_mimetype, target_mimetype)
        return target
    raise NotImplementedError(f'cannot convert {source_mimetype} {source}  to  {target_mimetype} {target}')


@dataclasses.dataclass(eq=True)
class Asset:
    """ Represents a single media object, which may come in multiple formats. """
    source: Path

    def __init__(self, path: Path):
        self.source = Path(path).with_suffix('')

    def _find_best_source(self, target_mimetype: str = 'image/*') -> tuple[Path, str]:
        """ Find the best source file for a given mimetype.

            :returns: (source, mimetype)
        """
        candidates = (self.source.with_suffix(ext) for ext in mimetypes.guess_all_extensions(target_mimetype))
        if p := next((p for p in candidates if p.exists()), None):
            return p, target_mimetype
        if target_mimetype.startswith('image/'):
            candidates = (self.source.with_suffix(ext) for ext in ('.png', '.jpg', '.jpeg', '.webp'))  # look for lossless formats first
            if p := next((p for p in candidates if p.exists()), None):
                return p, mimetypes.guess_type(p)[0]
        elif target_mimetype.startswith('video/'):
            pass
        raise FileNotFoundError(f'no source file found for {self.source} matching mimetype {target_mimetype}')

    def to(self, target: Path, mimetype=None) -> Path:
        """ copy source to target if source is newer than target, converting if necessary """
        if mimetype is None:
            mimetype = mimetypes.guess_type(target)[0]
        source, source_mimetype = self._find_best_source(mimetype)
        if not is_up_to_date(source, target):
            copy_or_convert(source, target, source_mimetype, mimetype)
        return target

    def to_dir(self, directory: Path, mimetype: str = 'image/*') -> Path:
        """ copy source to directory if source is newer than target, converting if necessary """
        source, source_mimetype = self._find_best_source(mimetype)
        target = directory / (source.stem + (mimetypes.guess_extension(mimetype) or source.suffix))
        if not is_up_to_date(source, target):
            copy_or_convert(source, target, source_mimetype, mimetype)
        return target

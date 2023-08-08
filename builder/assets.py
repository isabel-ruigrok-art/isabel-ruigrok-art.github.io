import dataclasses
import logging
from pathlib import Path
import functools
import mimetypes


def is_up_to_date(source: Path, target: Path) -> bool:
    return target.exists() and target.stat().st_mtime > source.stat().st_mtime


@dataclasses.dataclass
class Asset:
    """ Represents a single media object, which may come in multiple formats. """
    source: Path

    @functools.cached_property
    def mimetype(self):
        return mimetypes.guess_type(self.source)[0]

    def to(self, target: Path, mimetype=None) -> Path:
        """ copy source to target if source is newer than target, converting if necessary """
        if is_up_to_date(self.source, target):
            return target
        if mimetype is None:
            mimetype = mimetypes.guess_type(target)[0]
        if mimetype == self.mimetype:
            logging.info('%s -> %s', self.source, target)
            target.write_bytes(self.source.read_bytes())
        else:
            raise NotImplementedError(f"Cannot convert {self.mimetype} to {mimetype}.")
        return target

    def to_dir(self, directory: Path, mimetype=None) -> Path:
        """ copy source to directory if source is newer than target, converting if necessary """
        if mimetype is None or mimetype == self.mimetype:
            target = directory / self.source.name
        else:
            target = directory / (self.source.stem + mimetypes.guess_extension(mimetype))
        self.to(target, mimetype)
        return target

from __future__ import annotations

import re
from pathlib import Path


def sluggify(title: str) -> str:
    """ 'A (Normal) Title.' -> 'a-normal-title' """
    return re.sub(r'\W+', '-', title).strip('-').lower()


def is_wide(path: Path) -> bool:
    """ Return true if the image width is greater than the height. """
    # todo: implement
    return False

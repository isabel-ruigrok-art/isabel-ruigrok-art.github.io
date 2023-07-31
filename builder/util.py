from __future__ import annotations

import re
import datetime
from pathlib import Path

P_ISO_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')


def sluggify(title: str) -> str:
    """ 'A (Normal) Title.' -> 'a-normal-title' """
    return re.sub(r'\W+', '-', title).strip('-').lower()


def get_slug_and_optional_date(name: str) -> tuple[str, datetime.date | None]:
    """ '2000-01-01 A (Normal) Title.' -> ('a-normal-title', date(2000,1,1)) """
    if m := P_ISO_DATE.match(name):
        date = datetime.date.fromisoformat(m[0])
        slug = sluggify(name[m.end():].lstrip('-_ '))
        return slug, date
    else:
        return sluggify(name), None


def is_wide(path: Path) -> bool:
    """ Return true if the image width is greater than the height. """
    # todo: implement
    return False

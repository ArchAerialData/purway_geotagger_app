from __future__ import annotations

import re
from datetime import datetime
from dateutil import parser as dtparser

# Acceptable timestamp formats (extend only if necessary):
# - 2023-08-30_20:51:00
# - 2023-08-30 20:51:00
# - 2023/08/30 20:51:00
# - 20230830_205100
# - 20230830 205100
# - Any ISO-like string parseable by dateutil as a last resort.

FILENAME_TS_REGEXES = [
    re.compile(r"(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})[ _](?P<h>\d{2})[-:](?P<mi>\d{2})[-:](?P<s>\d{2})"),
    re.compile(r"(?P<y>\d{4})(?P<m>\d{2})(?P<d>\d{2})[ _]?(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})"),
]

PURWAY_TS_REGEX = re.compile(
    r"^(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})[ _]"
    r"(?P<h>\d{2}):(?P<mi>\d{2}):(?P<s>\d{2})(?::(?P<ms>\d{1,3}))?$"
)

def parse_csv_timestamp(value: str) -> datetime:
    """Parse a CSV timestamp string into a datetime.

    This must not guess timezone. Treat values as local time unless user adds a timezone
    feature later. If strings contain timezone offsets, preserve them.
    """
    v = value.strip()
    # Normalize common separators
    v2 = v.replace("/", "-")
    m = PURWAY_TS_REGEX.match(v2)
    if m:
        gd = m.groupdict()
        ms = gd.get("ms")
        micro = int(ms) * 1000 if ms else 0
        return datetime(
            int(gd["y"]), int(gd["m"]), int(gd["d"]),
            int(gd["h"]), int(gd["mi"]), int(gd["s"]),
            microsecond=micro,
        )
    v2 = v2.replace("_", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y%m%d %H%M%S"):
        try:
            return datetime.strptime(v2, fmt)
        except ValueError:
            pass
    # Last resort
    return dtparser.parse(v2)

def parse_photo_timestamp_from_name(stem: str) -> datetime | None:
    """Extract timestamp from photo filename stem (no extension)."""
    for rx in FILENAME_TS_REGEXES:
        m = rx.search(stem)
        if not m:
            continue
        gd = m.groupdict()
        try:
            return datetime(
                int(gd["y"]), int(gd["m"]), int(gd["d"]),
                int(gd["h"]), int(gd["mi"]), int(gd["s"])
            )
        except ValueError:
            continue
    return None

def format_exif_datetime(dt: datetime) -> str:
    """Format datetime to EXIF DateTimeOriginal format: YYYY:MM:DD HH:MM:SS."""
    return dt.strftime("%Y:%m:%d %H:%M:%S")

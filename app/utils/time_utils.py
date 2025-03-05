import datetime
from typing import Union

def current_timestamp() -> str:
    """
    Get current timestamp in ISO format.
    """
    return datetime.datetime.now().isoformat()

def to_utc_z(dt: Union[datetime.datetime, str]) -> str:
    """
    Convert a datetime object or ISO 8601 string to UTC ISO 8601 format with a trailing "Z".
    Example: "2025-03-03T13:00:00Z"
    """
    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt)
    
    # If the datetime is naive, assume it is already in UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    # Convert to UTC and format with trailing "Z"
    return dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def from_utc_z(utc_str: str) -> datetime.datetime:
    """
    Convert a UTC ISO 8601 string with a trailing "Z" to a datetime object.
    Example: "2025-03-03T13:00:00Z" -> datetime(2025, 3, 3, 13, 0, 0, tzinfo=UTC)
    """
    if utc_str.endswith("Z"):
        utc_str = utc_str[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(utc_str)

def seconds_to_minutes(seconds: int) -> int:
    """
    Convert seconds to minutes, rounding up to the nearest minute.
    """
    return (seconds + 59) // 60  # Round up

def minutes_to_seconds(minutes: int) -> int:
    """
    Convert minutes to seconds.
    """
    return minutes * 60

def meters_to_kilometers(meters: float) -> float:
    """
    Convert meters to kilometers, rounding to 1 decimal place.
    """
    return round(meters / 1000, 1)

def kilometers_to_meters(kilometers: float) -> int:
    """
    Convert kilometers to meters.
    """
    return int(kilometers * 1000)

def format_duration(seconds: int) -> str:
    """
    Format a duration in seconds to a human-readable string.
    Example: 3665 -> "1 hour 1 minute"
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 and not parts:  # Only show seconds if there are no hours or minutes
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    return " ".join(parts) or "0 seconds"

def format_time(dt: Union[datetime.datetime, str]) -> str:
    """
    Format a datetime object or ISO 8601 string to a human-readable time string.
    Example: "2025-03-03T13:00:00Z" -> "1:00 PM"
    """
    if isinstance(dt, str):
        dt = from_utc_z(dt)
    
    return dt.strftime("%-I:%M %p")  # %-I removes leading zeros

def format_date(dt: Union[datetime.datetime, str]) -> str:
    """
    Format a datetime object or ISO 8601 string to a human-readable date string.
    Example: "2025-03-03T13:00:00Z" -> "Monday, March 3, 2025"
    """
    if isinstance(dt, str):
        dt = from_utc_z(dt)
    
    return dt.strftime("%A, %B %-d, %Y")  # %-d removes leading zeros

def parse_time(time_str: str) -> datetime.time:
    """
    Parse a time string in HH:MM format to a time object.
    """
    return datetime.datetime.strptime(time_str, "%H:%M").time()

def combine_date_time(date: datetime.date, time_str: str) -> datetime.datetime:
    """
    Combine a date object with a time string in HH:MM format.
    """
    time_obj = parse_time(time_str)
    return datetime.datetime.combine(date, time_obj)

"""The full event history of a run (pure logic, no pygame): every message the game said, with the day and the place it
happened, grouped under headers like "Day 8 - Riverton" for the history screen."""

HISTORY_LIMIT = 500   # the oldest entries are dropped beyond this many


def add_entry(history, day, location, text):
    """Append one message (newest last) and keep at most HISTORY_LIMIT entries."""
    history.append({"day": int(day), "location": str(location), "text": str(text)})
    del history[:-HISTORY_LIMIT]


def header(day, location):
    return f"Day {day} - {location}"


def history_rows(history):
    """Display rows, NEWEST first like the RECENT EVENTS bar: ("header", text) once per run of messages from the same
    day and place, each followed by its ("line", text) rows (newest first within the group)."""
    rows = []
    group = None
    for entry in reversed(history):
        key = (entry["day"], entry["location"])
        if key != group:
            group = key
            rows.append(("header", header(*key)))
        rows.append(("line", entry["text"]))
    return rows


def clamp_scroll(offset, row_count, visible):
    """A scroll offset (first visible row) kept within the rows."""
    return max(0, min(int(offset), max(0, row_count - max(1, visible))))

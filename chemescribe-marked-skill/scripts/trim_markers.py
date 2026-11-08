#!/usr/bin/env python3
"""Remove the sections a speaker marked off with STOP RECORD / START RECORD.

Usage:
    python3 trim_markers.py <rawTranscriptFile> > <trimmedFile>

The trimmed transcript goes to stdout. A JSON log goes to stderr with one
entry per marker event and per removed section, plus word counts, so the
caller can report exactly what was removed and where.

Marker phrases (case-insensitive, punctuation ignored):
    stop record, stop recording, stop the record, stop the recording
    start record, start recording, start the record, start the recording

State machine:
    The recording starts in the KEEP state.
    A stop marker switches to the DROP state. A stop marker seen while
    already in DROP is a duplicate: it is counted and changes nothing,
    so any number of repeated stops behave as one.
    A start marker switches back to KEEP. A start marker seen while
    already in KEEP is a stray: it is counted and changes nothing, so
    any number of repeated starts behave as one.
    The marker words themselves are never kept.
    If the text ends in DROP, the trailing section stays removed and the
    log carries "unclosed_stop": true.

Markers are matched on the whole word stream, so a marker split across
two transcript lines (or two transcription chunks) is still found, and a
marker in the middle of a line splits that line: the words before it
follow the old state and the words after it follow the new state.

A line may carry a timestamp prefix such as [00:25-00:50]. Prefixes pass
through with the line's kept words. A line whose words are all removed
is dropped together with its prefix. Spacing inside a kept line is
normalised to single spaces; the tidy stage runs after this one.
"""
import json
import re
import sys

TS_PREFIX = re.compile(r"^\[([^\]]+)\]\s*")
WORD_CLEAN = re.compile(r"[^a-z0-9]")

START_WORDS = {"start"}
STOP_WORDS = {"stop"}
TAIL_WORDS = {"record", "recording"}


def clean(word):
    return WORD_CLEAN.sub("", word.lower())


def marker_at(tokens, i):
    """Return (kind, length) if a marker phrase starts at token i."""
    first = clean(tokens[i][0])
    if first not in START_WORDS and first not in STOP_WORDS:
        return None
    kind = "start" if first in START_WORDS else "stop"
    j = i + 1
    if j < len(tokens) and clean(tokens[j][0]) == "the":
        j += 1
    if j < len(tokens) and clean(tokens[j][0]) in TAIL_WORDS:
        return kind, j - i + 1
    return None


def main(argv):
    if len(argv) != 2:
        print("usage: python3 trim_markers.py <rawTranscriptFile>", file=sys.stderr)
        return 1
    text = open(argv[1], encoding="utf-8").read()

    # Build the word stream. Each token is (word, line index, timestamp
    # label of its line or None).
    line_ts = []
    tokens = []
    for line in text.splitlines():
        m = TS_PREFIX.match(line)
        ts = m.group(1) if m else None
        line_ts.append(ts)
        body = line[m.end():] if m else line
        for word in body.split():
            tokens.append((word, len(line_ts) - 1, ts))

    keep = True
    kept_by_line = {}
    events = []
    sections = []
    section = None
    words_kept = 0
    words_removed = 0
    markers_consumed = 0
    duplicate_stop = 0
    duplicate_start = 0

    i = 0
    while i < len(tokens):
        hit = marker_at(tokens, i)
        if hit:
            kind, length = hit
            ts = tokens[i][2]
            markers_consumed += length
            if kind == "stop" and keep:
                keep = False
                section = {"from": ts, "to": None, "words": 0}
                sections.append(section)
                events.append({"marker": "stop", "at": ts, "action": "drop_start"})
            elif kind == "stop":
                duplicate_stop += 1
                events.append({"marker": "stop", "at": ts, "action": "duplicate"})
            elif kind == "start" and not keep:
                keep = True
                section["to"] = ts
                section = None
                events.append({"marker": "start", "at": ts, "action": "keep_resume"})
            else:
                duplicate_start += 1
                events.append({"marker": "start", "at": ts, "action": "duplicate"})
            i += length
            continue
        word, line_idx, _ts = tokens[i]
        if keep:
            kept_by_line.setdefault(line_idx, []).append(word)
            words_kept += 1
        else:
            words_removed += 1
            if section is not None:
                section["words"] += 1
        i += 1

    unclosed_stop = not keep
    out_lines = []
    for line_idx in sorted(kept_by_line):
        words = kept_by_line[line_idx]
        if not words:
            continue
        ts = line_ts[line_idx]
        prefix = "[" + ts + "] " if ts else ""
        out_lines.append(prefix + " ".join(words))
    sys.stdout.write("\n".join(out_lines) + ("\n" if out_lines else ""))

    log = {
        "events": events,
        "sections_removed": sections,
        "section_count": len(sections),
        "duplicate_stop": duplicate_stop,
        "duplicate_start": duplicate_start,
        "unclosed_stop": unclosed_stop,
        "markers_consumed": markers_consumed,
        "words_kept": words_kept,
        "words_removed": words_removed,
    }
    print(json.dumps(log), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

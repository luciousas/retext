# vim: ts=4:sw=4:expandtab

"""Markdown heading extraction for the document outline sidebar."""

import re


HEADING_RE = re.compile(r'^(#{1,6})[ \t]+(.+?)[ \t]*$')
FENCE_RE = re.compile(r'^[ \t]*(`{3,}|~{3,})')
TRAILING_HASHES_RE = re.compile(r'[ \t]+#+[ \t]*$')


def get_markdown_headings(text):
    """Return ``(level, title, zero_based_line)`` tuples for Markdown headings.

    Fenced code is deliberately ignored, so an example heading in a code block
    never becomes a navigation target.
    """
    headings = []
    fence = None
    for line_number, line in enumerate(text.splitlines()):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            continue
        if fence is not None:
            continue
        heading_match = HEADING_RE.match(line)
        if heading_match:
            title = TRAILING_HASHES_RE.sub('', heading_match.group(2)).strip()
            if title:
                headings.append((len(heading_match.group(1)), title, line_number))
    return headings

import unittest

from ReText.outline import get_markdown_headings


class MarkdownOutlineTests(unittest.TestCase):
    def test_extracts_atx_headings_with_hierarchy_and_source_lines(self):
        text = '# Title #\nintro\n### Detail\n\n## Next\n'
        self.assertEqual(get_markdown_headings(text), [
            (1, 'Title', 0),
            (3, 'Detail', 2),
            (2, 'Next', 4),
        ])

    def test_ignores_heading_examples_inside_fenced_code(self):
        text = '## Real\n```markdown\n# Not a heading\n```\n### Also real\n'
        self.assertEqual(get_markdown_headings(text), [
            (2, 'Real', 0),
            (3, 'Also real', 4),
        ])

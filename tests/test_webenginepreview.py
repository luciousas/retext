import unittest

from ReText.webenginepreview import ReTextWebEnginePage, ReTextWebEnginePreview


class PositionMapCallbackTests(unittest.TestCase):
    def setUp(self):
        self.page = type('Page', (), {
            '_positionMapEpoch': 0,
            '_positionMapRequest': 0,
        })()
        self.callbacks = []
        self.page.runJavaScript = lambda script, callback: self.callbacks.append((script, callback))

    def get_position_map(self, callback):
        ReTextWebEnginePage.getPositionMap(self.page, callback)
        return self.callbacks[-1]

    def test_replaced_document_ignores_old_callback(self):
        received = []
        _, oldCallback = self.get_position_map(received.append)
        ReTextWebEnginePage.invalidatePositionMaps(self.page)

        oldCallback({'4': 120})

        self.assertEqual(received, [])

    def test_newest_position_map_wins_and_invalid_results_are_ignored(self):
        received = []
        _, oldCallback = self.get_position_map(received.append)
        script, newCallback = self.get_position_map(received.append)

        oldCallback({'2': 40})
        newCallback(None)
        newCallback({'2': {}, '3': True, '5': 120})

        self.assertEqual(received, [{5: 120.0}])
        self.assertIn('!document.body', script)
        self.assertIn('elementTop', script)

    def test_mode_switch_position_map_uses_the_rendered_heading_block(self):
        # mdx_posmap keys are the empty line after each Markdown block.
        positionMap = {1: 0, 9: 120, 16: 340}

        self.assertEqual(
            ReTextWebEnginePreview.sourceLineForPreviewPosition(positionMap, 150),
            8,
        )
        self.assertEqual(
            ReTextWebEnginePreview.previewPositionForSourceLine(positionMap, 12),
            340,
        )

    def test_loading_preview_does_not_report_a_transient_top_position(self):
        preview = type('Preview', (), {
            '_positionReady': False,
            'positionMap': {1: 0, 9: 120},
            'page': lambda self: type('Page', (), {
                'scrollPosition': lambda self: type('Point', (), {'y': lambda self: 0})(),
            })(),
        })()

        self.assertIsNone(ReTextWebEnginePreview.sourceLineAtCurrentScroll(preview))

    def test_restored_heading_wins_over_fractional_dom_boundary(self):
        preview = type('Preview', (), {
            '_positionReady': True,
            '_restoredAnchor': (66, 1657),
            'positionMap': {65: 1657.4, 67: 1670.0},
            'page': lambda self: type('Page', (), {
                'scrollPosition': lambda self: type('Point', (), {'y': lambda self: 1657})(),
            })(),
        })()

        self.assertEqual(ReTextWebEnginePreview.sourceLineAtCurrentScroll(preview), 66)

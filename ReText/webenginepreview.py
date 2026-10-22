# vim: ts=4:sw=4:expandtab

# This file is part of ReText
# Copyright: 2017-2025 Dmitry Shachnev
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from bisect import bisect_left, bisect_right
from numbers import Real

from PyQt6.QtCore import QEvent, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QFontInfo,
    QGuiApplication,
    QPalette,
    QTextDocument,
)
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineSettings,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QLabel

from ReText import debugLog, globalCache, globalSettings
from ReText.editor import getColor


class ReTextWebEngineUrlRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        if (info.resourceType() == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeXhr
                and info.requestUrl().isLocalFile()):
            # For security reasons, disable XMLHttpRequests to local files
            info.block(True)


def str_rgba(color: QColor):
    """ Todo: More elegant use of QColor with alpha in stylesheet """
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"

class UrlPopup(QLabel):
    def __init__(self, window):
        super().__init__(window)
        self.window = window

        self.setStyleSheet('''
            border: 1px solid {:s};
            border-radius: 3px;
            background: {:s};
            '''.format(str_rgba(getColor('urlPopupBorder')),
                       str_rgba(getColor('urlPopupArea'))))
        self.fontHeight = self.fontMetrics().height()
        self.setVisible(False)

    def pop(self, url: str):
        """ Show link target on mouse hover

        QWebEnginePage emits signal 'linkHovered' which provides
        url: str -- target of link hovered (or empty on mouse-release)
        """
        if url:
            self.setText(url)
            windowBottom = self.window.rect().bottom()
            textWidth = self.fontMetrics().horizontalAdvance(url)
            self.setGeometry(-2, windowBottom-self.fontHeight-6,
                    textWidth+10, self.fontHeight+10)
            self.setVisible(True)
        else:
            self.setVisible(False)


class ReTextWebEnginePage(QWebEnginePage):
    def __init__(self, parent, tab):
        QWebEnginePage.__init__(self, parent)
        self.tab = tab
        # JavaScript callbacks outlive the DOM that issued them.  Keep an
        # explicit document generation and request sequence so a callback from
        # a replaced page can never update synchronized scrolling state.
        self._positionMapEpoch = 0
        self._positionMapRequest = 0
        self.interceptor = ReTextWebEngineUrlRequestInterceptor(self)
        self.setUrlRequestInterceptor(self.interceptor)
        self.urlPopup = UrlPopup(self.tab.p)
        self.linkHovered.connect(self.urlPopup.pop)
        self.loadStarted.connect(self.invalidatePositionMaps)

    def invalidatePositionMaps(self):
        self._positionMapEpoch += 1

    def setScrollPosition(self, pos):
        self.runJavaScript(f"window.scrollTo({pos.x()}, {pos.y()});")

    def getPositionMap(self, callback):
        epoch = self._positionMapEpoch
        self._positionMapRequest += 1
        request = self._positionMapRequest

        def resultCallback(result):
            if epoch != self._positionMapEpoch or request != self._positionMapRequest:
                return
            if not isinstance(result, dict):
                return
            positionMap = {}
            for line, position in result.items():
                try:
                    line = int(line)
                except (TypeError, ValueError):
                    continue
                if isinstance(position, Real) and not isinstance(position, bool):
                    positionMap[line] = float(position)
            # An empty map is meaningful to the caller while a document is
            # still settling: it may make one bounded retry.  Do not silently
            # turn that state into a permanent "top of document" position.
            callback(positionMap)

        script = """
        if (!document.body) {
            ({});
        } else {
        var elements = document.querySelectorAll('[data-posmap]');
        var result = {};
        var bodyTop = document.body.getBoundingClientRect().top;
        for (var i = 0; i < elements.length; ++i) {
            var element = elements[i];
            var value = element.getAttribute('data-posmap');
            // A chapter anchor denotes the beginning of a rendered block.
            // Using its bottom delays outline changes and returns to the
            // preceding paragraph when a heading is selected.
            var elementTop = element.getBoundingClientRect().top - bodyTop;
            result[value] = elementTop;
        }
        result;
        }
        """
        self.runJavaScript(script, resultCallback)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceId):
        print(f"level={level!r} message={message!r} lineNumber={lineNumber!r} sourceId={sourceId!r}")

    def acceptNavigationRequest(self, url, type, isMainFrame):
        if not isMainFrame:
            return True
        if url.scheme() == "data":
            return True
        if url.isLocalFile():
            localFile = url.toLocalFile()
            if localFile == self.tab.fileName:
                self.tab.startPendingConversion()
                return False
            if self.tab.openSourceFile(localFile):
                return False
        if globalSettings.handleWebLinks:
            return True
        QDesktopServices.openUrl(url)
        return False


class ReTextWebEnginePreview(QWebEngineView):

    # Emitted only after the current document has a position map and its
    # requested anchor has been applied.  Consumers must not use the transient
    # zero scroll position emitted during a WebEngine load as navigation state.
    positionRestored = pyqtSignal()

    def __init__(self, tab):

        QWebEngineView.__init__(self, parent=tab)
        webPage = ReTextWebEnginePage(self, tab)

        handCursor = QCursor(Qt.CursorShape.PointingHandCursor)
        arrowCursor = QCursor(Qt.CursorShape.ArrowCursor)
        webPage.linkHovered.connect(lambda value: self.setCursor(handCursor if value else arrowCursor))

        self.setPage(webPage)
        # The preview and editor deliberately do not subscribe to one another's
        # scroll events.  In a Wayland WebEngine view those asynchronous events
        # can arrive after a reload and form a feedback loop.  We only map a
        # position once while switching between source and reading modes.
        self.positionMap = {}
        self._renderEpoch = 0
        self._pendingSourceLine = None
        self._positionReady = False
        self._positionMapAttempts = 0
        self._restoredAnchor = None
        self._navigationEpoch = 0
        self.loadFinished.connect(self._documentLoaded)

        settings = self.settings()
        settings.setDefaultTextEncoding('utf-8')
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        if hasattr(QWebEngineSettings.WebAttribute, 'ForceDarkMode'):  # Qt >= 6.7
            # QGuiApplication.instance().styleHints().colorScheme() does not seem to
            # work properly on KDE Plasma, so let's re-use the same approach as our
            # editor uses.
            palette = QApplication.palette()
            windowColor = palette.color(QPalette.ColorRole.Window)
            if windowColor.lightness() <= 150:
                settings.setAttribute(QWebEngineSettings.WebAttribute.ForceDarkMode, True)

    def setFont(self, font):
        settings = self.settings()
        settings.setFontFamily(QWebEngineSettings.FontFamily.StandardFont,
                               font.family())
        pixelSize = QFontInfo(font).pixelSize()
        settings.setFontSize(QWebEngineSettings.FontSize.DefaultFontSize, pixelSize)
        settings.setFontSize(QWebEngineSettings.FontSize.DefaultFixedFontSize, pixelSize)

    def setHtml(self, html, baseUrl):
        # A hack to prevent WebEngine from stealing the focus
        self.setEnabled(False)
        self._renderEpoch += 1
        self.positionMap = {}
        self._positionReady = False
        self._positionMapAttempts = 0
        self._restoredAnchor = None
        self._navigationEpoch += 1
        self.page().invalidatePositionMaps()
        debugLog('preview-render', epoch=self._renderEpoch)
        super().setHtml(html, baseUrl)
        self.setEnabled(True)

    def invalidateNavigationState(self):
        """Make every position event from the previous visible preview stale.

        Conversion is intentionally delayed.  Without this boundary, the old
        hidden page can emit a final scroll event during that delay and replace
        the anchor captured for the source-to-reading transition.
        """
        self._positionReady = False
        self.positionMap = {}
        self._pendingSourceLine = None
        self._restoredAnchor = None
        self._navigationEpoch += 1
        self.page().invalidatePositionMaps()
        debugLog('preview-navigation-invalidated', epoch=self._renderEpoch)

    @staticmethod
    def sourceLineForPreviewPosition(positionMap, previewY):
        """Return the zero-based source line for a preview position."""
        if not positionMap:
            return None
        ordered = sorted((position, line) for line, position in positionMap.items())
        positions = [position for position, _line in ordered]
        # mdx_posmap stores the empty line *after* a rendered Markdown block.
        # Convert it once here so every caller uses zero-based source lines.
        return max(0, ordered[max(0, bisect_right(positions, previewY) - 1)][1] - 1)

    @staticmethod
    def previewPositionForSourceLine(positionMap, sourceLine):
        """Return the rendered block position corresponding to a source line."""
        if not positionMap:
            return None
        lines = sorted(positionMap)
        # The map is keyed by the line after each block.  For a heading at
        # source line N, the first map entry at or after N + 1 is its block,
        # while the old predecessor lookup incorrectly selected the previous
        # paragraph.
        index = bisect_left(lines, sourceLine + 1)
        line = lines[min(index, len(lines) - 1)]
        return positionMap[line]

    def sourceLineAtCurrentScroll(self):
        if not self._positionReady:
            return None
        scrollY = self.page().scrollPosition().y()
        if self._restoredAnchor is not None:
            sourceLine, restoredY = self._restoredAnchor
            # QWebEngine takes integral scroll positions while DOM geometry is
            # fractional.  At a restored heading it can report one pixel
            # before the marker, which belongs to the previous paragraph in a
            # position map.  Treat the requested anchor as authoritative until
            # the user actually scrolls away from that position.
            if abs(scrollY - restoredY) <= 3:
                return sourceLine
            self._restoredAnchor = None
        return self.sourceLineForPreviewPosition(self.positionMap, scrollY)

    def restoreSourceLine(self, sourceLine):
        """Restore one source anchor after the current document has loaded."""
        self._pendingSourceLine = (self._renderEpoch, int(sourceLine))
        debugLog('preview-restore-request', epoch=self._renderEpoch,
                 anchor=sourceLine, mapSize=len(self.positionMap))
        if self.positionMap:
            self._applyPendingRestore()

    def _documentLoaded(self, ok):
        if not ok:
            return
        epoch = self._renderEpoch
        debugLog('preview-loaded', epoch=epoch, ok=ok)
        # Let the initial layout settle once.  This is a one-shot read, not a
        # continuous resize/scroll observer.
        QTimer.singleShot(100, lambda: self._refreshPositionMap(epoch))

    def _refreshPositionMap(self, epoch):
        if epoch != self._renderEpoch:
            return
        self._positionMapAttempts += 1
        self.page().getPositionMap(
            lambda positionMap: self._storePositionMap(epoch, positionMap))

    def _storePositionMap(self, epoch, positionMap):
        if epoch != self._renderEpoch:
            return
        if not positionMap:
            debugLog('preview-map-empty', epoch=epoch,
                     attempts=self._positionMapAttempts)
            # This is a single layout retry.  It is deliberately not a timer
            # loop or scroll listener: after a real document load, either the
            # Markdown markers exist or the old stable anchor is retained.
            if self._positionMapAttempts < 2:
                QTimer.singleShot(250, lambda: self._refreshPositionMap(epoch))
            return
        self.positionMap = positionMap
        debugLog('preview-map-ready', epoch=epoch, size=len(positionMap),
                 pending=self._pendingSourceLine)
        self._applyPendingRestore()

    def _applyPendingRestore(self):
        if self._pendingSourceLine is None:
            return
        epoch, sourceLine = self._pendingSourceLine
        if epoch != self._renderEpoch or not self.positionMap:
            return
        self._pendingSourceLine = None
        position = self.previewPositionForSourceLine(self.positionMap, sourceLine)
        if isinstance(position, Real) and not isinstance(position, bool):
            # Ignore WebEngine's load-time y=0 notification until the stable
            # document map and the requested anchor are both in place.
            debugLog('preview-restore-applied', epoch=epoch, anchor=sourceLine,
                     position=int(position))
            navigationEpoch = self._navigationEpoch

            def scrollApplied(actualPosition):
                if (epoch != self._renderEpoch or
                        navigationEpoch != self._navigationEpoch):
                    return
                restoredY = (int(actualPosition)
                             if isinstance(actualPosition, Real)
                             and not isinstance(actualPosition, bool)
                             else int(position))
                self._positionReady = True
                self._restoredAnchor = (sourceLine, restoredY)
                debugLog('preview-restore-visible', epoch=epoch,
                         anchor=sourceLine, position=restoredY)
                self.positionRestored.emit()

            self.page().runJavaScript(
                f"window.scrollTo(0, {int(position)}); window.scrollY;",
                scrollApplied,
            )

    def event(self, event):
        # Work-around https://bugreports.qt.io/browse/QTBUG-43602
        if event.type() == QEvent.Type.ChildAdded:
            event.child().installEventFilter(self)
        elif event.type() == QEvent.Type.ChildRemoved:
            event.child().removeEventFilter(self)
        return super().event(event)

    def eventFilter(self, object, event):
        if event.type() == QEvent.Type.Wheel:
            if QGuiApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
                self.wheelEvent(event)
                return True
        return False

    def findText(self, text, flags):
        options = QWebEnginePage.FindFlag(0)
        if flags & QTextDocument.FindFlag.FindBackward:
            options |= QWebEnginePage.FindFlag.FindBackward
        if flags & QTextDocument.FindFlag.FindCaseSensitively:
            options |= QWebEnginePage.FindFlag.FindCaseSensitively
        super().findText(text, options)
        return True

    def disconnectExternalSignals(self):
        self._pendingSourceLine = None

    def wheelEvent(self, event):
        if QGuiApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
            newZoomFactor = globalCache.webEngineZoomFactor * (1.001 ** event.angleDelta().y())
            # Valid values are within the range from 0.25 to 5.0.
            globalCache.webEngineZoomFactor = max(min(newZoomFactor, 5.0), 0.25)
            self.setZoomFactor(globalCache.webEngineZoomFactor)
        return super().wheelEvent(event)

    def showEvent(self, event):
        self.setZoomFactor(globalCache.webEngineZoomFactor)
        return super().showEvent(event)

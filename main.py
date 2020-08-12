from PyQt5.QtGui import QKeyEvent, QPalette, QDesktopServices
from PyQt5.QtNetwork import QNetworkReply, QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QLineEdit, QTreeWidget, QApplication, QFrame, QTreeWidgetItem
from PyQt5.QtCore import QObject, QEvent, QTimer, Qt, QPoint, QMetaObject, QXmlStreamReader, QUrl


class GSuggestCompletion(QObject):

    def __init__(self, parent: QLineEdit = None):
        super().__init__(parent=parent)

        self.editor = parent
        self.timer = QTimer()
        self.networkManager = QNetworkAccessManager(self)

        self.popup = QTreeWidget()
        self.popup.setWindowFlag(Qt.Popup)
        self.popup.setFocusPolicy(Qt.NoFocus)
        self.popup.setFocusProxy(self.editor)
        self.popup.setMouseTracking(True)

        self.popup.setColumnCount(1)
        self.popup.setUniformRowHeights(True)
        self.popup.setRootIsDecorated(False)
        self.popup.setEditTriggers(QTreeWidget.NoEditTriggers)
        self.popup.setSelectionBehavior(QTreeWidget.SelectRows)
        self.popup.setFrameStyle(QFrame.Box | QFrame.Panel)
        self.popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.popup.header().hide()

        self.popup.installEventFilter(self)

        self.popup.itemClicked.connect(self.doneCompletion)

        self.timer.setSingleShot(True)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.autoSuggest)
        self.editor.textEdited.connect(self.timer.start)

        self.networkManager.finished.connect(self.handleNetworkData)

    def eventFilter(self, obj: QObject, ev: QEvent):
        if obj != self.popup:
            return False

        if ev.type() == QEvent.MouseButtonPress:
            self.popup.hide()
            self.editor.setFocus()
            return True

        if ev.type() == QEvent.KeyPress:
            consumed = False
            ev: QKeyEvent
            key = ev.key()

            if (Qt.Key_Enter == key) or (Qt.Key_Return == key):
                self.doneCompletion()
                consumed = True
            elif Qt.Key_Return == key:
                self.editor.setFocus()
                self.popup.hide()
                consumed = True
            elif (key == Qt.Key_Undo) or (key == Qt.Key_Down) or (key == Qt.Key_Home) or (key == Qt.Key_End) or (
                    key == Qt.Key_PageUp) or (key == Qt.Key_PageDown):
                pass
            else:
                self.editor.setFocus()
                self.editor.event(ev)
                self.popup.hide()
            return consumed
        return False

    def showCompletion(self, choices: list):
        if not choices:
            return

        pal: QPalette = self.editor.palette()
        color = pal.color(QPalette.Disabled, QPalette.WindowText)

        self.popup.setUpdatesEnabled(False)
        self.popup.clear()

        for choice in choices:
            item = QTreeWidgetItem(self.popup)
            item.setText(0, choice)
            item.setForeground(0, color)

        self.popup.setCurrentItem(self.popup.topLevelItem(0))
        self.popup.resizeColumnToContents(0)
        self.popup.setUpdatesEnabled(True)

        self.popup.move(self.editor.mapToGlobal(QPoint(0, self.editor.height())))
        self.popup.setFocus()
        self.popup.show()

    def doneCompletion(self):
        self.timer.stop()
        self.popup.hide()
        self.editor.setFocus()
        item: QTreeWidgetItem = self.popup.currentItem()
        if item:
            self.editor.setText(item.text(0))
            QMetaObject.invokeMethod(self.editor, "returnPressed")

    def preventSuggest(self):
        self.timer.stop()

    def autoSuggest(self):
        url = f"http://google.com/complete/search?output=toolbar&q={self.editor.text()}"
        self.networkManager.get(QNetworkRequest(QUrl(url)))

    def handleNetworkData(self, networkReply: QNetworkReply):
        if networkReply.error() == QNetworkReply.NoError:
            choices = []
            response = networkReply.readAll()
            xml = QXmlStreamReader(response)
            while not xml.atEnd():
                xml.readNext()
                if xml.tokenType() == QXmlStreamReader.StartElement:
                    if xml.name() == 'suggestion':
                        string = xml.attributes().value('data')
                        choices.append(string)
            self.showCompletion(choices)
        networkReply.deleteLater()


class SearchBox(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = GSuggestCompletion(self)
        self.returnPressed.connect(self.doSearch)

        self.setWindowTitle("Search with Google")

        self.adjustSize()
        self.resize(400, self.height())
        self.setFocus()

    def doSearch(self):
        self.completer.preventSuggest()
        QDesktopServices.openUrl(QUrl(f"http://www.google.com/search?q={self.text()}"))


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    w = SearchBox()
    w.show()
    exit(app.exec())

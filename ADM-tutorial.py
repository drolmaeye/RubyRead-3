import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg


class MainWindow(qtw.QMainWindow):

    def __init__(self):
        super().__init__()
        # main UI code
        self.textedit = qtw.QTextEdit()
        self.setCentralWidget(self.textedit)

        # Menubar

        menubar = self.menuBar()
        flie_menu = menubar.addMenu('File')
        flie_menu.addAction('Save')
        flie_menu.addAction('Open')



        # End main UI code
        self.show()


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())

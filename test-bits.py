import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg

class MainWindow(qtw.QWidget):

    def __int__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # your code will go here



        # your code ends here
        self.show()


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    w = MainWindow()
    # w.show()
    sys.exit(app.exec_())


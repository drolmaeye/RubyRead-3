__author__ = 'jssmith'

'''
A GUI for measuring ruby pressure with Ocean Optics or Ocean Insight spectrometers

build command line for executable --unknown--
'''

# import necessary modules
import sys
from PyQt5 import QtWidgets
import seabreeze.spectrometers as sb


class Window(QtWidgets.QWidget):
    def __int__(self):
        super().__init__()
        self.setWindowTitle('RubyRead3')
        # self.show()


class CoreData:
    def __int__(self):
        self.devices = sb.list_devices()
        self.spec = sb.Spectrometer(self.devices[0])
        self.spec.integration_time_micros(100000)

        self.xs = self.spec.wavelengths()
        self.ys = self.spec.intensities()

        self.op()

    def op(self):
        print(self.xs)


app = QtWidgets.QApplication(sys.argv)
core = CoreData()
gui = Window()
gui.show()
core.op()
sys.exit(app.exec_())





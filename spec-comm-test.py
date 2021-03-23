__author__ = 'j.smith'

'''
Snippets to test if spectrometer is working in python 3
'''
import seabreeze.spectrometers as sb
from PyQt5 import QtWidgets as qtw
import sys

app=qtw.QApplication(sys.argv)

devices = sb.list_devices()
# ###if len(devices) == 0:
# ###
# ###    title = ('No spectrometers available')
# ###    text = ('No spectrometer available.\n'
# ###                'Please connect a spectrometer.\n'
# ###                'If spectrometer is already connected, '
# ###                'please make sure it is not already in use.\n'
# ###                'Troubleshoot: try replugging the USB cable to spectrometer')
# ###    msg = qtw.QMessageBox.warning(title, text)
# ###    sys.exit()
# ###elif len(devices) > 1:
# ###    choice = qtw.QDialogButtonBox()
# ###    choice.isModal(True)
# ###    choice.setWindowTitle('Multiple spectrometers found')
# ###    choice_layout = qtw.QVBoxLayout()
# ###    choice.setLayout(choice_layout)
# ###    choice_label = qtw.QLabel('Please select which spectrometer to use')
# ###    choice_layout.addWidget(choice_label)
# ###    for each in range(len(devices)):
# ###        button = qtw.QPushButton(str(devices[each]))
# ###        choice_layout.addWidget(button)
# ###    choice.show()


index = 0

print(index)
spec = sb.Spectrometer(devices[index])
spec.integration_time_micros(100000)

xs = spec.wavelengths()
ys = spec.intensities()

print(xs, ys)

print(spec.max_intensity)
print(spec.pixels)
print(ys.shape, len(ys))
qtw.QMessageBox.information(None, 'waiting', 'waiting')

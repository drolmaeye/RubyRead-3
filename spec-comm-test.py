__author__ = 'j.smith'

'''
Snippets to test if spectrometer is working in python 3
'''
import seabreeze.spectrometers as sb

devices = sb.list_devices()
print(devices)

spec = sb.Spectrometer(devices[0])
spec.integration_time_micros(100000)

xs = spec.wavelengths()
ys = spec.intensities()

print(xs, ys)

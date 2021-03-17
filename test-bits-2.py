from SPrEader import SpeFile
import numpy as np
from lmfit.models import LinearModel, PseudoVoigtModel
import time
from scipy.optimize import curve_fit
from math import pi, sqrt
import pyqtgraph as pg


def double_pseudo(x, a1, c1, eta1, w1, a2, c2, eta2, w2, m, bg):
    return a1 * (eta1 * (2 / pi) * (w1 / (4 * (x - c1) ** 2 + w1 ** 2)) +
                 (1 - eta1) * (sqrt(4 * np.log(2)) / (sqrt(pi) * w1)) * np.exp(
                -(4 * np.log(2) / w1 ** 2) * (x - c1) ** 2)) + \
           a2 * (eta2 * (2 / pi) * (w2 / (4 * (x - c2) ** 2 + w2 ** 2)) +
                 (1 - eta2) * (sqrt(4 * np.log(2)) / (sqrt(pi) * w2)) * np.exp(
                -(4 * np.log(2) / w2 ** 2) * (x - c2) ** 2)) + \
           m * x + bg


spectra = SpeFile('Bi-cell4-ruby7.SPE')
num_spectra = spectra.header.NumFrames
pressures = np.ones(num_spectra)

xs = spectra.xaxis

curve_roi_start = time.perf_counter()
for each in range(num_spectra):
# for each in range(10):
    ys = spectra.data[each]
    ys.resize(1340,)
    full_max_index = np.argmax(ys)
    roi_min = full_max_index - 150
    roi_max = full_max_index + 150
    # handle edge situations (for example, during background-only spectra)
    if roi_min < 0:
        roi_min = 0
    if roi_max > 1339:
        roi_max = -1
    xs_roi = xs[roi_min:roi_max]
    ys_roi = ys[roi_min:roi_max]
    roi_max_index = np.argmax(ys_roi)
    # start with approximate linear background (using full spectrum)
    slope = (ys[-1] - ys[0]) / (xs[-1] - xs[0])
    intercept = ys[0] - slope * xs[0]
    # obtain initial guesses for fitting parameters using ROI array
    r1_pos = xs_roi[roi_max_index]
    r2_pos = r1_pos - 1.4
    r1_height = ys_roi[roi_max_index] - (slope * r1_pos + intercept)
    r2_height = r1_height / 2.0

    # define fitting parameters p0 (area approximated by height)
    p0 = [r2_height, r2_pos, 0.5, 1.0, r1_height, r1_pos, 0.5, 1.0, slope, intercept]
    try:
        popt, pcov = curve_fit(double_pseudo, xs_roi, ys_roi, p0=p0)
    except RuntimeError:
        print('Poor fit')
    pressure = 1870 * ((1 / 10.69) * (((popt[5] / 694.260) ** 10.69) - 1))
    pressures[each] = pressure
curve_roi_duration = time.perf_counter() - curve_roi_start
print('curve and roi:', curve_roi_duration)

pwidget = pg.plot()
pwidget.plot(pressures)
pg.QtGui.QApplication.exec_()






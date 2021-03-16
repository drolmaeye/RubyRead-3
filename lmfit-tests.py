from lmfit.models import LinearModel, PseudoVoigtModel
import numpy as np
from scipy.optimize import curve_fit
from math import pi, sqrt
import time
import pyqtgraph as pg


def double_pseudo(x, a1, c1, eta1, w1, a2, c2, eta2, w2, m, bg):
    return a1 * (eta1 * (2 / pi) * (w1 / (4 * (x - c1) ** 2 + w1 ** 2)) +
                 (1 - eta1) * (sqrt(4 * np.log(2)) / (sqrt(pi) * w1)) * np.exp(
                -(4 * np.log(2) / w1 ** 2) * (x - c1) ** 2)) + \
           a2 * (eta2 * (2 / pi) * (w2 / (4 * (x - c2) ** 2 + w2 ** 2)) +
                 (1 - eta2) * (sqrt(4 * np.log(2)) / (sqrt(pi) * w2)) * np.exp(
                -(4 * np.log(2) / w2 ** 2) * (x - c2) ** 2)) + \
           m * x + bg


# generate x, y data
name = 'full_spectrum.txt'
xs, ys = np.genfromtxt(name,
                       delimiter=',',
                       skip_header=1,
                       filling_values=1,
                       usecols=(0, 1),
                       unpack=True)

# set up roi spectra, get initial guesses
# start by defining ROI arrays and get max_index for ROI
full_max_index = np.argmax(ys)
roi_min = full_max_index - 150
roi_max = full_max_index + 150
# handle edge situations (for example, during background-only spectra)
if roi_min < 0:
    roi_min = 0
if roi_max > 2047:
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
curve_roi_start = time.perf_counter()
try:
    popt, pcov = curve_fit(double_pseudo, xs_roi, ys_roi, p0=p0)
except RuntimeError:
    print('Poor fit')
curve_roi_duration = time.perf_counter() - curve_roi_start
print('curve and roi:', curve_roi_duration)

# define fitting parameters p0 (area approximated by height)
p0 = [r2_height, r2_pos, 0.5, 1.0, r1_height, r1_pos, 0.5, 1.0, slope, intercept]
curve_full_start = time.perf_counter()
try:
    poptf, pcovf = curve_fit(double_pseudo, xs, ys, p0=p0)
except RuntimeError:
    print('Poor fit')
curve_full_duration = time.perf_counter() - curve_full_start
print('curve and full:', curve_full_duration)

r1 = PseudoVoigtModel(prefix='r1_')
r2 = PseudoVoigtModel(prefix='r2_')
bg = LinearModel()

params = r1.make_params()
params.update(r2.make_params())
params.update(bg.make_params())
ruby_model = r1 + r2 + bg



params['r1_amplitude'].value = r1_height
params['r1_center'].value = r1_pos
params['r1_sigma'].value = 1.0
params['r1_fraction'].value = 0.5
params['r2_amplitude'].value = r2_height
params['r2_center'].value = r2_pos
params['r2_sigma'].value = 1.0
params['r2_fraction'].value = 0.5
params['slope'].value = slope
params['intercept'].value = intercept

lmfit_roi_start = time.perf_counter()
out = ruby_model.fit(ys_roi, params=params, x=xs_roi)
lmfit_roi_duration = time.perf_counter() - lmfit_roi_start
print('lmfit and roi:', lmfit_roi_duration)
# print(out.fit_report())

lmfit_full_start = time.perf_counter()
outf = ruby_model.fit(ys, params=params, x=xs)
lmfit_full_duration = time.perf_counter() - lmfit_full_start
print('lmfit and full:', lmfit_full_duration)

params['r1_amplitude'].value = 1262.0
params['r1_center'].value = 700.2
params['r1_sigma'].value = 0.46
params['r1_fraction'].value = 0.58
params['r2_amplitude'].value = 539
params['r2_center'].value = 698.8
params['r2_sigma'].value = 0.42
params['r2_fraction'].value = 0.14
params['slope'].value = -3.75
params['intercept'].value = 3432.0

lmfit_cheat_start = time.perf_counter()
outcheat = ruby_model.fit(ys_roi, params=params, x=xs_roi)
lmfit_cheat_duration = time.perf_counter() - lmfit_cheat_start
print('lmfit and cheat:', lmfit_cheat_duration)









# ###plotwidget = pg.plot()
# ###plotwidget.plot(xs, ys)
# ###plotwidget.plot(xs_roi, out.best_fit, pen='y')
# #### plotwidget.plot(xs_roi, double_pseudo(xs_roi, *popt), pen='r')
# ###
# ###pg.QtGui.QApplication.exec_()

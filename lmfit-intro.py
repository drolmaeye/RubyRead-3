from lmfit.models import LinearModel, PseudoVoigtModel
import numpy as np
from SPrEader import SpeFile
import pyqtgraph as pg

spectra = SpeFile('Bi-cell4-ruby7.SPE')

x = spectra.xaxis
y = spectra.data[0]
y.resize(1340,)

full_max_index = np.argmax(y)
roi_min = full_max_index - 150
roi_max = full_max_index + 150
# #### handle edge situations (for example, during background-only spectra)
if roi_min < 0:
    roi_min = 0
if roi_max > 1339:
    roi_max = -1
x_roi = x[roi_min:roi_max]
y_roi = y[roi_min:roi_max]
roi_max_index = np.argmax(y_roi)
# start with approximate linear background (using full spectrum)
slope = float((y[-1] - y[0]) / (x[-1] - x[0]))
intercept = float(y[0] - slope * x[0])
# obtain initial guesses for fitting parameters using ROI array
r1_pos = x_roi[roi_max_index]
r2_pos = r1_pos - 1.4
r1_height = float(y_roi[roi_max_index] - (slope * r1_pos + intercept))
r2_height = r1_height / 2.0
# check r1_height is within range before fitting
# ###if r1_height < core.threshold:
# ###    warning = 'Too weak'
# ###elif y_roi[roi_max_index] > 16000:
# ###    warning = 'Saturated'
# ###else:
# ###    # define fitting parameters p0 (area approximated by height)
# ###    p0 = [r2_height, r2_pos, 0.5, 1.0, r1_height, r1_pos, 0.5, 1.0, slope, intercept]
# ###    try:
# ###        popt, pcov = curve_fit(double_pseudo, x_roi, y_roi, p0=p0)
# ###        warning = ''
# ###        fit_dict['popt'] = popt
# ###    except RuntimeError:
# ###        warning = 'Poor fit'
# ###fit_dict['warning'] = warning
# ###self.fit_thread_callback_signal.emit(fit_dict)

r1 = PseudoVoigtModel(prefix='r1_')
r2 = PseudoVoigtModel(prefix='r2_')
bg = LinearModel()

params = bg.guess(y, x=x)
print(params)
params.update(r1.make_params())
print(params)
params.update(r2.make_params())
print(params)
params['r1_amplitude'].value = r1_height
params['r1_center'].value = r1_pos
params['r1_sigma'].value = 0.1
# params['r1_fraction'].value = 0.5
params['r2_amplitude'].value = r2_height
params['r2_center'].value = r2_pos
params['r2_sigma'].value = 0.1
# params['r2_fraction'].value = 0.5





ruby_fit = r1 + r2 + bg

# print(ruby_fit, ruby_fit.param_names)
# ###params = ruby_fit.make_params(
# ###    r1_center=r1_pos,
# ###    r1_amplitude=r1_height,
# ###    r1_sigma=0.1,
# ###    r1_fraction=0.5,
# ###    r2_center=r2_pos,
# ###    r2_amplitude=500.0,
# ###    r2_sigma=0.1,
# ###    r2_fraction=0.5,
# ###    slope=0.001,
# ###    intercept=700)

# #for each in ruby_fit.param_names:
# #    print(params.get(each))
# #
# #print(type(params.values()))

eval_y = ruby_fit.eval(params, x=x)

# print(y_roi, y_roi.shape, type(y_roi))


out = ruby_fit.fit(y, params=params, x=x)
print(out.fit_report())

fit_y = ruby_fit.eval(params, x=x)

y.resize(1340,)
eval_y.resize(1340,)
fit_y.resize(1340,)

print(type(y_roi))
y_roi.resize(300,)
print(y_roi.shape)
pwidget = pg.plot()
pwidget.plot(x, y)
pwidget.plot(x, out.init_fit)
pwidget.plot(x, out.best_fit)

if __name__ == '__main__':
    import sys
    if sys.flags.interactive != 1 or not hasattr(QtCore, 'PYQT_VERSION'):
        pg.QtGui.QApplication.exec_()

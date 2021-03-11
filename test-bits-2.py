import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
import pyqtgraph as pg
from pyqtgraph.GraphicsScene import exportDialog
import seabreeze.spectrometers as sb
import numpy as np
from scipy.optimize import curve_fit
from math import pi, sqrt, exp
from epics import PV
import time
import os

name = 'C:/Users/jssmith/anaconda3/Jgrams/RubyRead-3/full_spectrum.txt'
xs, ys = np.genfromtxt(name,
                       delimiter=',',
                       skip_header=1,
                       filling_values=1,
                       usecols=(0, 1),
                       unpack=True)

print(type(xs))
print(xs.shape)
print(xs)
print(ys)


p0 = [531.0848398470498, 698.8231000000001, 0.5, 1.0, 1062.1696796940996, 700.2231, 0.5, 1.0, -0.1326276183752504, 863.6992423902353]


def double_pseudo(x, a1, c1, eta1, w1, a2, c2, eta2, w2, m, bg):
    return a1 * (eta1 * (2 / pi) * (w1 / (4 * (x - c1) ** 2 + w1 ** 2)) +
                 (1 - eta1) * (sqrt(4 * np.log(2)) / (sqrt(pi) * w1)) * np.exp(
                -(4 * np.log(2) / w1 ** 2) * (x - c1) ** 2)) + \
           a2 * (eta2 * (2 / pi) * (w2 / (4 * (x - c2) ** 2 + w2 ** 2)) +
                 (1 - eta2) * (sqrt(4 * np.log(2)) / (sqrt(pi) * w2)) * np.exp(
                -(4 * np.log(2) / w2 ** 2) * (x - c2) ** 2)) + \
           m * x + bg

test = double_pseudo(xs, p0[0], p0[1], p0[2], p0[3], p0[4], p0[5], p0[6], p0[7], p0[8], p0[9])


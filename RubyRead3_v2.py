__author__ = 'jssmith'

'''
A GUI for measuring ruby pressure with Ocean Optics or Ocean Insight spectrometers

build command line for executable thus far built with hidden imports (not single file):
hiddenimports=['six', 'scipy.spatial.transform._rotation_groups'],
as copied from the .spec file
'''

# import necessary modules
import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
import pyqtgraph as pg
from pyqtgraph.GraphicsScene import exportDialog
import seabreeze.spectrometers as sb
import numpy as np
from scipy.optimize import curve_fit
from math import pi, sqrt
from epics import PV
import time
import os


class MainWindow(qtw.QMainWindow):

    spectra_requested_signal = qtc.pyqtSignal(bool)
    fit_requested_signal = qtc.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1080, 720)
        self.setWindowTitle('RubyRead Python3 Development Version')
        self.setWindowIcon(qtg.QIcon('ruby4.png'))

        # test a blank object to use for click-to-edit
        self.had_focus = None

        # create the main window widget and make it central
        self.mw = qtw.QWidget()
        self.setCentralWidget(self.mw)
        # now make and set layout for the mw (main window)
        self.mw_layout = qtw.QVBoxLayout()
        self.mw.setLayout(self.mw_layout)

        '''
        Menu Bar
        '''

        # actions
        self.load_data_action = qtw.QAction('Load', self)
        self.load_data_action.setShortcut('Ctrl+L')
        self.load_data_action.triggered.connect(self.load_data)

        self.save_data_action = qtw.QAction('Save', self)
        self.save_data_action.setShortcut('Ctrl+S')
        self.save_data_action.triggered.connect(self.save_data)

        self.close_rubyread_action = qtw.QAction('Exit', self)
        self.close_rubyread_action.setShortcut('Ctrl+Q')
        self.close_rubyread_action.triggered.connect(self.closeEvent)

        self.options_window_action = qtw.QAction('Options', self)
        self.options_window_action.setShortcut('Ctrl+O')
        self.options_window_action.triggered.connect(lambda: self.ow.show())

        self.about_window_action = qtw.QAction('About', self)
        self.about_window_action.setShortcut('Ctrl+A')
        self.about_window_action.triggered.connect(lambda: self.aw.show())

        # make menu, add headings, put actions under headings
        self.main_menu = self.menuBar()
        self.file_menu = self.main_menu.addMenu('File')
        self.file_menu.addAction(self.load_data_action)
        self.file_menu.addAction(self.save_data_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.close_rubyread_action)
        self.options_menu = self.main_menu.addMenu('Options')
        self.options_menu.addAction(self.options_window_action)
        self.about_menu = self.main_menu.addMenu('About')
        self.about_menu.addAction(self.about_window_action)

        '''
        Custom Toolbar
        '''

        # make custom toolbar for top of main window
        self.tb = qtw.QWidget()
        self.tb_layout = qtw.QHBoxLayout()
        self.tb_layout.setAlignment(qtc.Qt.AlignLeft)
        self.tb.setLayout(self.tb_layout)

        # make custom toolbar widgets
        self.take_spec_label = qtw.QLabel('Collect')
        self.take_one_spec_btn = qtw.QPushButton('1')
        self.take_one_spec_btn.setShortcut(qtc.Qt.Key_F1)
        self.take_one_spec_btn.setToolTip('Collect one spectrum (F1)')
        self.take_n_spec_btn = qtw.QPushButton('n')
        self.take_n_spec_btn.setShortcut(qtc.Qt.Key_F2)
        self.take_n_spec_btn.setToolTip('Continuously collect spectra (F2)')
        self.take_n_spec_btn.setCheckable(True)

        self.remaining_time_display = qtw.QLabel('Idle')
        self.remaining_time_display.setFrameShape(qtw.QFrame.Panel)
        self.remaining_time_display.setFrameShadow(qtw.QFrame.Sunken)
        self.remaining_time_display.setMinimumWidth(80)
        self.remaining_time_display.setAlignment(qtc.Qt.AlignCenter)
        self.remaining_time_display.setToolTip('Remaining collection time (s)')

        self.fit_spec_label = qtw.QLabel('Fit')
        self.fit_one_spec_btn = qtw.QPushButton('1')
        self.fit_one_spec_btn.setShortcut(qtc.Qt.Key_F3)
        self.fit_one_spec_btn.setToolTip('Fit one spectrum (F3)')
        self.fit_n_spec_btn = qtw.QPushButton('n')
        self.fit_n_spec_btn.setShortcut(qtc.Qt.Key_F4)
        self.fit_n_spec_btn.setToolTip('Continuously fit spectra (F4)')
        self.fit_n_spec_btn.setCheckable(True)

        self.fit_warning_display = qtw.QLabel('')
        self.fit_warning_display.setFrameShape(qtw.QFrame.Panel)
        self.fit_warning_display.setFrameShadow(qtw.QFrame.Sunken)
        self.fit_warning_display.setMinimumWidth(80)
        self.fit_warning_display.setAlignment(qtc.Qt.AlignCenter)
        self.fit_warning_display.setToolTip('Fit warning')

        self.threshold_label = qtw.QLabel('Fit threshold')
        self.threshold_min_input = qtw.QSpinBox()
        self.threshold_min_input.setRange(0, 16000)
        self.threshold_min_input.setValue(1000)
        self.threshold_min_input.setSingleStep(100)
        self.threshold_min_input.setMinimumWidth(70)

        self.zoom_full_btn = qtw.QPushButton('Zoom Full')
        self.zoom_fit_btn = qtw.QPushButton('Zoom Fit')
        self.test_9000_lbl = qtw.QLabel('test')

        # connect custom toolbar signals
        self.take_one_spec_btn.clicked.connect(self.take_one_spectrum)
        self.take_n_spec_btn.clicked.connect(self.take_n_spectra)
        self.fit_one_spec_btn.clicked.connect(self.fit_one_spectrum)
        self.fit_n_spec_btn.clicked.connect(self.fit_n_spectra)
        self.threshold_min_input.valueChanged.connect(self.set_threshold)
        self.zoom_full_btn.clicked.connect(self.zoom_full)
        self.zoom_fit_btn.clicked.connect(self.zoom_fit)

        # add custom toolbar widgets to toolbar layout
        self.tb_layout.addWidget(self.take_spec_label)
        self.tb_layout.addWidget(self.take_one_spec_btn)
        self.tb_layout.addWidget(self.take_n_spec_btn)
        self.tb_layout.addWidget(self.remaining_time_display)
        self.tb_layout.addSpacing(20)

        self.tb_layout.addWidget(self.fit_spec_label)
        self.tb_layout.addWidget(self.fit_one_spec_btn)
        self.tb_layout.addWidget(self.fit_n_spec_btn)
        self.tb_layout.addWidget(self.fit_warning_display)
        self.tb_layout.addSpacing(20)

        self.tb_layout.addWidget(self.threshold_label)
        self.tb_layout.addWidget(self.threshold_min_input)
        self.tb_layout.addSpacing(20)

        self.tb_layout.addWidget(self.zoom_full_btn)
        self.tb_layout.addWidget(self.zoom_fit_btn)
        # self.tb_layout.addWidget(self.test_9000_lbl)

        # add custom toolbar to main window
        self.mw_layout.addWidget(self.tb)

        '''
        Plot Window
        '''

        # make the plot window for the left side of bottom layout
        # custom viewbox, vb, allows for custom button event handling
        self.pw = pg.PlotWidget(viewBox=vb, name='Plot1')

        # ###EXPERIMENT WITH STYLE###
        # self.pw.setTitle('Spectrum', size='12pt')
        # label_style = {'color': '#808080', 'font-size': '11px'}
        label_style = {'color': '#808080', 'font': ' bold 16px'}
        self.pw.plotItem.getAxis('left').enableAutoSIPrefix(False)
        self.pw.setLabel('left', 'Intensity', units='counts', **label_style)
        self.pw.setLabel('bottom', 'Wavelength', units='nm', **label_style)

        # create plot items (need to be added when necessary)
        self.raw_data = pg.PlotDataItem(name='raw')
        self.fit_data = pg.PlotDataItem(name='fit')
        self.r1_data = pg.PlotDataItem(name='r1')
        self.r2_data = pg.PlotDataItem(name='r2')
        self.bg_data = pg.PlotDataItem(name='bg')

        # stylize plot items
        self.fit_data.setPen(color='r', width=2)
        self.r1_data.setPen(color='g')
        self.r2_data.setPen(color='g')
        self.bg_data.setPen(color='c')

        line_dict = {'angle': 90, 'fill': 'k'}
        self.vline_press = pg.InfiniteLine(pos=694.260, angle=90.0, movable=False,
                                           pen='g', label='Fit', labelOpts=line_dict)
        self.vline_ref = pg.InfiniteLine(pos=694.260, angle=90.0, movable=False,
                                         pen='m', label='Reference', labelOpts=line_dict)
        self.vline_target = pg.InfiniteLine(pos=694.260, angle=90.0, movable=True,
                                            pen='y', label='Target', labelOpts=line_dict)

        # raw data is always visible, add rest when or as needed
        self.pw.addItem(self.raw_data)

        # create signal for target pressure line
        self.vline_target.sigPositionChanged.connect(self.target_line_moved)

        # ###LAYOUT MANAGEMENT###
        # make layout for plot window and control window and add to main window
        self.bottom_layout = qtw.QHBoxLayout()
        self.mw_layout.addLayout(self.bottom_layout)

        # add plot widget to bottom layout
        self.bottom_layout.addWidget(self.pw)

        '''
        Control Window
        '''

        # make the control window for the right side and add it to main window layout
        self.cw = qtw.QWidget()
        self.cw.setMaximumWidth(300)
        self.bottom_layout.addWidget(self.cw)

        # make the layout for the control widget
        self.cw_layout = qtw.QVBoxLayout()
        self.cw_layout.setAlignment(qtc.Qt.AlignTop)
        self.cw.setLayout(self.cw_layout)

        '''
        Spectrum control window
        '''

        # make top right widget for spectrometer control
        self.spec_control = qtw.QGroupBox()
        self.spec_control.setTitle('Spectrum Control')
        self.cw_layout.addWidget(self.spec_control)
        self.cw_layout.addSpacing(10)

        # make and set layout to Spectrum Control QGroupBox
        self.spec_control_layout = qtw.QVBoxLayout()
        self.spec_control_layout.setAlignment(qtc.Qt.AlignTop)
        self.spec_control.setLayout(self.spec_control_layout)

        # ###make individual widgets to spec control grid layout

        # create count time label
        self.count_time_label = qtw.QLabel('Integration time (ms)')
        # create, configure count time input
        self.count_time_input = qtw.QLineEdit('100')
        self.count_time_input.setStyleSheet('font: bold 18px')
        self.count_time_input.setValidator(qtg.QIntValidator())
        self.count_time_input.setMaxLength(4)
        # crate count time shortcut buttons
        self.count_less_button = qtw.QPushButton('')
        self.count_less_button.setIcon(qtw.QApplication.style().standardIcon(qtw.QStyle.SP_ArrowLeft))
        self.count_less_button.setMinimumWidth(70)
        self.count_more_button = qtw.QPushButton('')
        self.count_more_button.setIcon(qtw.QApplication.style().standardIcon(qtw.QStyle.SP_ArrowRight))
        self.count_more_button.setMinimumWidth(70)
        # create checkbox widget, create and configure spinbox widget
        self.average_spec_cbox = qtw.QCheckBox('Average n spectra')
        self.average_spec_sbox = qtw.QSpinBox()
        self.average_spec_sbox.setMaximumWidth(50)
        self.average_spec_sbox.setValue(1)
        self.average_spec_sbox.setMinimum(1)
        self.average_spec_sbox.setMaximum(10)

        # connect signals
        self.count_time_input.editingFinished.connect(self.update_count_time)
        self.count_less_button.clicked.connect(lambda: self.count_time_shortcut('down'))
        self.count_more_button.clicked.connect(lambda: self.count_time_shortcut('up'))
        self.average_spec_cbox.stateChanged.connect(self.toggle_average)
        self.average_spec_sbox.valueChanged.connect(self.set_num_average)

        # add widgets to layout
        self.spec_control_layout.addWidget(self.count_time_label)

        self.count_time_layout = qtw.QHBoxLayout()
        self.count_time_layout.addWidget(self.count_less_button)
        self.count_time_layout.addWidget(self.count_time_input)
        self.count_time_layout.addWidget(self.count_more_button)
        self.spec_control_layout.addLayout(self.count_time_layout)

        self.spec_control_layout.addSpacing(10)

        self.average_spec_layout = qtw.QHBoxLayout()
        self.average_spec_layout.setAlignment(qtc.Qt.AlignLeft)
        self.average_spec_layout.addWidget(self.average_spec_cbox)
        self.average_spec_layout.addWidget(self.average_spec_sbox)
        self.spec_control_layout.addLayout(self.average_spec_layout)

        '''
        Plot control window
        '''

        # make middle-right widget for plot control
        self.plot_control = qtw.QGroupBox()
        self.plot_control.setTitle('Plot Control')
        self.cw_layout.addWidget(self.plot_control)
        self.cw_layout.addSpacing(10)

        # make and set primary layout for Plot Control QGroupBox
        self.plot_control_layout = qtw.QVBoxLayout()
        self.plot_control_layout.setAlignment(qtc.Qt.AlignTop)
        self.plot_control.setLayout(self.plot_control_layout)

        # ### make and add individual widgets to plot control

        # custom checked styles for checkbuttons
        showcurve_style = 'QPushButton::checked {border:4px solid red}'
        showr1r2_style = 'QPushButton::checked {border:4px solid green}'
        showbg_style = 'QPushButton::checked {border:4px solid cyan}'
        showfit_style = 'QPushButton::checked {border:4px solid green}'
        showref_style = 'QPushButton::checked {border:4px solid magenta}'
        showtarget_style = 'QPushButton::checked {border:4px solid yellow}'

        # create and style all show checkbuttons
        self.show_fits_label = qtw.QLabel('Show fitted data')
        self.show_curve_cbtn = qtw.QPushButton('Curve')
        self.show_curve_cbtn.setCheckable(True)
        self.show_curve_cbtn.setStyleSheet(showcurve_style)
        self.show_r1r2_cbtn = qtw.QPushButton('R1, R2')
        self.show_r1r2_cbtn.setCheckable(True)
        self.show_r1r2_cbtn.setStyleSheet(showr1r2_style)
        self.show_bg_cbtn = qtw.QPushButton('Background')
        self.show_bg_cbtn.setCheckable(True)
        self.show_bg_cbtn.setStyleSheet(showbg_style)
        self.show_fit_p_cbtn = qtw.QPushButton('P(fit)')
        self.show_fit_p_cbtn.setCheckable(True)
        self.show_fit_p_cbtn.setStyleSheet(showfit_style)
        self.show_ref_p_cbtn = qtw.QPushButton('P(ref)')
        self.show_ref_p_cbtn.setCheckable(True)
        self.show_ref_p_cbtn.setStyleSheet(showref_style)
        self.show_target_p_cbtn = qtw.QPushButton('P(target)')
        self.show_target_p_cbtn.setCheckable(True)
        self.show_target_p_cbtn.setStyleSheet(showtarget_style)

        # create labels, headings, displays, and inputs for marker locations
        self.show_refs_label = qtw.QLabel('Show pressure markers')
        self.markers_lambda_heading = qtw.QLabel(u'\u03BB' + ' (nm)')
        self.markers_pressure_heading = qtw.QLabel('P (GPa)')
        self.markers_delta_p_heading = qtw.QLabel(u'\u0394' + 'P (GPa)')
        self.show_ref_p_lambda = qtw.QLabel('694.260')
        self.show_ref_p_pressure = qtw.QLabel('0.00')
        self.show_ref_p_delta = qtw.QLabel('0.00')
        self.show_target_p_lambda = qtw.QLineEdit('694.260')
        self.show_target_p_lambda.setValidator(qtg.QDoubleValidator(669.000, 767.000, 3))
        self.show_target_p_pressure = qtw.QLineEdit('0.00')
        self.show_target_p_pressure.setValidator(qtg.QDoubleValidator(-57.00, 335.00, 2))
        self.show_target_p_delta = qtw.QLineEdit('0.00')
        self.show_target_p_delta.setValidator(qtg.QDoubleValidator(-57.00, 335.00, 2))
        # create buttons to define reference
        self.set_ref_p_label = qtw.QLabel('Set P(ref) position')
        self.set_ref_from_zero_btn = qtw.QPushButton('from Zero')
        self.set_ref_from_fit_btn = qtw.QPushButton('from Fit')
        self.set_ref_from_target_btn = qtw.QPushButton('from Target')
        # create buttons for y-scale control
        self.set_y_scaling_label = qtw.QLabel('Intensity scaling')
        self.auto_y_btn = qtw.QPushButton('Auto')
        self.grow_y_btn = qtw.QPushButton('Grow')
        self.fix_y_btn = qtw.QPushButton('Fix')
        self.auto_y_btn.setCheckable(True)
        self.grow_y_btn.setCheckable(True)
        self.fix_y_btn.setCheckable(True)
        self.auto_y_btn.setChecked(True)
        self.scale_y_btn_grp = qtw.QButtonGroup()
        self.scale_y_btn_grp.addButton(self.auto_y_btn, 0)
        self.scale_y_btn_grp.addButton(self.grow_y_btn, 1)
        self.scale_y_btn_grp.addButton(self.fix_y_btn, 2)

        # connect plot control signals
        self.show_curve_cbtn.clicked.connect(self.show_curve_cbtn_clicked)
        self.show_r1r2_cbtn.clicked.connect(self.show_r1r2_cbtn_clicked)
        self.show_bg_cbtn.clicked.connect(self.show_bg_cbtn_clicked)
        self.show_fit_p_cbtn.clicked.connect(self.show_fit_p_cbtn_clicked)
        self.show_ref_p_cbtn.clicked.connect(self.show_ref_p_cbtn_clicked)
        self.show_target_p_cbtn.clicked.connect(self.show_target_p_cbtn_clicked)
        self.show_target_p_lambda.editingFinished.connect(self.show_target_p_lambda_changed)
        self.show_target_p_pressure.editingFinished.connect(self.show_target_p_pressure_changed)
        self.show_target_p_delta.editingFinished.connect(self.show_target_p_delta_changed)
        self.set_ref_from_zero_btn.clicked.connect(self.set_ref_from_zero)
        self.set_ref_from_fit_btn.clicked.connect(self.set_ref_from_fit)
        self.set_ref_from_target_btn.clicked.connect(self.set_ref_from_target)
        self.auto_y_btn.clicked.connect(lambda: vb.enableAutoRange(axis=vb.YAxis))
        self.grow_y_btn.clicked.connect(lambda: vb.disableAutoRange())
        self.fix_y_btn.clicked.connect(lambda: vb.disableAutoRange())

        # add widgets to layout
        self.plot_control_layout.addWidget(self.show_fits_label)

        self.reference_curves_layout = qtw.QHBoxLayout()
        self.reference_curves_layout.addWidget(self.show_curve_cbtn)
        self.reference_curves_layout.addWidget(self.show_r1r2_cbtn)
        self.reference_curves_layout.addWidget(self.show_bg_cbtn)
        self.plot_control_layout.addLayout(self.reference_curves_layout)

        self.plot_control_layout.addSpacing(10)

        self.plot_control_layout.addWidget(self.show_refs_label)

        self.reference_lines_layout = qtw.QGridLayout()
        self.reference_lines_layout.addWidget(self.show_fit_p_cbtn, 1, 0)
        self.reference_lines_layout.addWidget(self.markers_lambda_heading, 1, 1)
        self.reference_lines_layout.addWidget(self.markers_pressure_heading, 1, 2)
        self.reference_lines_layout.addWidget(self.markers_delta_p_heading, 1, 3)
        self.reference_lines_layout.addWidget(self.show_ref_p_cbtn, 2, 0)
        self.reference_lines_layout.addWidget(self.show_ref_p_lambda, 2, 1)
        self.reference_lines_layout.addWidget(self.show_ref_p_pressure, 2, 2)
        self.reference_lines_layout.addWidget(self.show_ref_p_delta, 2, 3)
        self.reference_lines_layout.addWidget(self.show_target_p_cbtn, 3, 0)
        self.reference_lines_layout.addWidget(self.show_target_p_lambda, 3, 1)
        self.reference_lines_layout.addWidget(self.show_target_p_pressure, 3, 2)
        self.reference_lines_layout.addWidget(self.show_target_p_delta, 3, 3)
        self.plot_control_layout.addLayout(self.reference_lines_layout)

        self.plot_control_layout.addSpacing(10)

        self.plot_control_layout.addWidget(self.set_ref_p_label)

        self.set_reference_layout = qtw.QHBoxLayout()
        self.set_reference_layout.addWidget(self.set_ref_from_zero_btn)
        self.set_reference_layout.addWidget(self.set_ref_from_fit_btn)
        self.set_reference_layout.addWidget(self.set_ref_from_target_btn)
        self.plot_control_layout.addLayout(self.set_reference_layout)

        self.plot_control_layout.addSpacing(10)

        self.plot_control_layout.addWidget(self.set_y_scaling_label)

        self.zoom_buttons_layout = qtw.QHBoxLayout()
        self.zoom_buttons_layout.addWidget(self.auto_y_btn)
        self.zoom_buttons_layout.addWidget(self.grow_y_btn)
        self.zoom_buttons_layout.addWidget(self.fix_y_btn)
        self.plot_control_layout.addLayout(self.zoom_buttons_layout)

        '''
        Pressure Control window
        '''

        # make bottom right widget for Pressure control
        self.press_control = qtw.QGroupBox()
        self.press_control.setTitle('Pressure Control')
        self.cw_layout.addWidget(self.press_control)

        # make and add primary layout to Pressure Control QGroupBox
        self.press_control_layout = qtw.QGridLayout()
        self.press_control_layout.setAlignment(qtc.Qt.AlignTop)
        self.press_control.setLayout(self.press_control_layout)

        # ###make and add individual widgets to press control layout

        # create pressure control widgets
        self.press_calibration_label = qtw.QLabel('Calibration')
        self.press_calibration_display = qtw.QLabel('IPPS-Ruby2020 (2020)')
        self.lambda_naught_295_label = qtw.QLabel(u'\u03BB' + '<sub>0</sub>' + '(295)' + ' (nm)')
        self.lambda_naught_295_display = qtw.QLabel('694.260')
        self.lambda_naught_t_label = qtw.QLabel(u'\u03BB' + '<sub>0</sub>' + '(T)' + ' (nm)')
        self.lambda_naught_t_display = qtw.QLabel('694.260')
        self.lambda_r1_label = qtw.QLabel(u'\u03BB' + '<sub>R1</sub>' + ' (nm)')
        self.lambda_r1_display = qtw.QLabel('694.260')
        self.temperature_label = qtw.QLabel('T(K)')
        self.temperature_label.setStyleSheet('QLabel {font: bold 18px}')
        self.temperature_input = qtw.QSpinBox()
        self.temperature_input.setStyleSheet('QSpinBox {font: bold 24px}')
        self.temperature_input.setRange(1, 600)
        self.temperature_input.setValue(295)
        self.temperature_track_cbox = qtw.QCheckBox('Track')
        self.temperature_track_cbox.setEnabled(False)
        self.pressure_fit_label = qtw.QLabel('P(GPa)')
        self.pressure_fit_label.setStyleSheet('QLabel {font: bold 18px}')
        self.pressure_fit_display = qtw.QLabel('0.00')
        self.pressure_fit_display.setMinimumWidth(100)
        self.pressure_fit_display.setStyleSheet('QLabel {font: bold 36px}')

        # connect pressure control signals
        self.temperature_input.valueChanged.connect(self.calculate_lambda_0_t)

        # add pressure control widgets to pressure control layout
        self.press_control_layout.addWidget(self.press_calibration_label, 0, 0)
        self.press_control_layout.addWidget(self.press_calibration_display, 0, 1, 1, 2)
        self.press_control_layout.addWidget(self.lambda_naught_295_label, 1, 0)
        self.press_control_layout.addWidget(self.lambda_naught_295_display, 1, 1)
        self.press_control_layout.addWidget(self.lambda_naught_t_label, 2, 0)
        self.press_control_layout.addWidget(self.lambda_naught_t_display, 2, 1)
        self.press_control_layout.addWidget(self.lambda_r1_label, 3, 0)
        self.press_control_layout.addWidget(self.lambda_r1_display, 3, 1)
        self.press_control_layout.addWidget(self.temperature_label, 4, 0)
        self.press_control_layout.addWidget(self.temperature_input, 4, 1)
        self.press_control_layout.addWidget(self.temperature_track_cbox, 4, 2)
        self.press_control_layout.addWidget(self.pressure_fit_label, 5, 0)
        self.press_control_layout.addWidget(self.pressure_fit_display, 5, 1)

        '''
        Options window
        '''

        self.ow = qtw.QTabWidget()
        self.ow.setWindowTitle('Options')

        # ###PRESSURE CALIBRATION###
        # make pressure calibration tab
        self.p_calibration_tab = qtw.QWidget()
        self.p_calibration_tab_layout = qtw.QVBoxLayout()
        self.p_calibration_tab_layout.setAlignment(qtc.Qt.AlignTop)
        self.p_calibration_tab.setLayout(self.p_calibration_tab_layout)

        # make Group Box for lambda naught
        self.set_lambda_naught_gb = qtw.QGroupBox()
        self.set_lambda_naught_gb.setTitle('Reference wavelength')
        self.p_calibration_tab_layout.addWidget(self.set_lambda_naught_gb)
        self.set_lambda_naught_gb_layout = qtw.QVBoxLayout()
        self.set_lambda_naught_gb.setLayout(self.set_lambda_naught_gb_layout)

        # make widgets for lambda naught
        self.manual_lambda_naught_label = qtw.QLabel('Enter user-defined ' + u'\u03BB' + '<sub>0</sub>' + '(295)')
        self.manual_lambda_naught_input = qtw.QLineEdit('694.260')
        self.manual_lambda_naught_input.setValidator(qtg.QDoubleValidator(692.000, 696.000, 3))
        self.auto_lambda_naught_btn = qtw.QPushButton('Get ' + u'\u03BB' + '(295) from fit')

        # connect signals
        self.manual_lambda_naught_input.returnPressed.connect(lambda: self.set_lambda_naught('manual'))
        self.auto_lambda_naught_btn.clicked.connect(lambda: self.set_lambda_naught('auto'))

        # add lambda naught widgets to set lambda naught gb layout
        self.manual_lambda_naught_layout = qtw.QHBoxLayout()
        self.manual_lambda_naught_layout.addWidget(self.manual_lambda_naught_label)
        self.manual_lambda_naught_layout.addWidget(self.manual_lambda_naught_input)
        self.set_lambda_naught_gb_layout.addLayout(self.manual_lambda_naught_layout)

        self.set_lambda_naught_gb_layout.addWidget(self.auto_lambda_naught_btn)

        # make Group Box for Calibration selection
        self.set_p_calibration_gb = qtw.QGroupBox()
        self.set_p_calibration_gb.setTitle('Pressure Calibration')
        self.p_calibration_tab_layout.addWidget(self.set_p_calibration_gb)
        self.set_p_calibration_gb_layout = qtw.QVBoxLayout()
        self.set_p_calibration_gb.setLayout(self.set_p_calibration_gb_layout)

        # make widgets for calibration selection
        self.choose_calibration_drop = qtw.QComboBox()
        self.choose_calibration_drop.addItems(['IPPS-Ruby2020, Shen et al., HPR 40, 299-314 (2020)',
                                               'Mao et al., JGR 91, 4673 (1986)',
                                               'Dewaele et al., PRB 69, 092106 (2004)'])
        self.p_calibration_alpha_label = qtw.QLabel('<i>A</i> =')
        self.p_calibration_alpha_label.setAlignment(qtc.Qt.AlignRight)
        self.p_calibration_alpha_display = qtw.QLabel('1870')
        self.p_calibration_beta_label = qtw.QLabel('<i>B</i> =')
        self.p_calibration_beta_label.setAlignment(qtc.Qt.AlignRight)
        self.p_calibration_beta_display = qtw.QLabel('10.69')
        # ###self.calculation_label = QtGui.QLabel('P = ' + u'\u03B1' + '/' + u'\u03B2' + '[(' + u'\u03BB' + '/' + u'\u03BB' + '<sub>0</sub>)<sup>' + u'\u03B2' + '</sup> - 1]')
        self.calculation_label = qtw.QLabel('<i>P</i> = <i>A/B</i> [(' + u'\u03BB' + '/' + u'\u03BB' + '<sub>0</sub>)<sup><i>B</i></sup> - 1]')
        self.calculation_label.setStyleSheet('font-size: 16pt; font-weight: bold')
        self.calculation_label.setAlignment(qtc.Qt.AlignCenter)

        # connect signal
        self.choose_calibration_drop.currentIndexChanged.connect(self.set_new_p_calibration)

        # add widgets to layout
        self.set_p_calibration_gb_layout.addWidget(self.choose_calibration_drop)

        self.p_cal_constants_layout = qtw.QHBoxLayout()
        self.p_cal_constants_layout.addWidget(self.p_calibration_alpha_label)
        self.p_cal_constants_layout.addWidget(self.p_calibration_alpha_display)
        self.p_cal_constants_layout.addWidget(self.p_calibration_beta_label)
        self.p_cal_constants_layout.addWidget(self.p_calibration_beta_display)
        self.set_p_calibration_gb_layout.addLayout(self.p_cal_constants_layout)

        self.set_p_calibration_gb_layout.addWidget(self.calculation_label)

        self.ow.addTab(self.p_calibration_tab, 'P Calibration')

        # ###WAVELENGTH CALIBRATION###
        # make wavelength calibration tab
        self.w_calibraiton_tab = qtw.QWidget()
        self.w_calibration_tab_layout = qtw.QVBoxLayout()
        self.w_calibration_tab_layout.setAlignment(qtc.Qt.AlignTop)
        self.w_calibraiton_tab.setLayout(self.w_calibration_tab_layout)

        # make calibration line entry widgets
        self.use_label = qtw.QLabel('Use')
        self.pixel_input_label = qtw.QLabel('Pixel (guess)')
        self.pixel_fit_label = qtw.QLabel('Pixel (fit)')
        self.wave_fit_label = qtw.QLabel('Fit (nm)')
        self.wave_expected_label = qtw.QLabel('Ref (nm)')
        self.wave_error_label = qtw.QLabel('Error')
        self.cal1 = CalibrationEntry()
        self.cal2 = CalibrationEntry()
        self.cal3 = CalibrationEntry()
        self.cal4 = CalibrationEntry()
        self.cal5 = CalibrationEntry()
        self.cal6 = CalibrationEntry()
        self.cal7 = CalibrationEntry()
        self.cal8 = CalibrationEntry()
        self.cal9 = CalibrationEntry()
        self.cal_btn = qtw.QPushButton('Calibrate')

        # connect signals for wavelength calibration
        self.cal_btn.clicked.connect(self.calibrate_spectrometer)


        # add wavelength calibration widgets to layout
        self.w_calibration_heading_layout = qtw.QHBoxLayout()
        self.w_calibration_heading_layout.addWidget(self.use_label)
        self.w_calibration_heading_layout.addWidget(self.pixel_input_label)
        self.w_calibration_heading_layout.addWidget(self.pixel_fit_label)
        self.w_calibration_heading_layout.addWidget(self.wave_fit_label)
        self.w_calibration_heading_layout.addWidget(self.wave_expected_label)
        self.w_calibration_heading_layout.addWidget(self.wave_error_label)
        self.w_calibration_tab_layout.addLayout(self.w_calibration_heading_layout)
        self.w_calibration_tab_layout.addWidget(self.cal1)
        self.w_calibration_tab_layout.addWidget(self.cal2)
        self.w_calibration_tab_layout.addWidget(self.cal3)
        self.w_calibration_tab_layout.addWidget(self.cal4)
        self.w_calibration_tab_layout.addWidget(self.cal5)
        self.w_calibration_tab_layout.addWidget(self.cal6)
        self.w_calibration_tab_layout.addWidget(self.cal7)
        self.w_calibration_tab_layout.addWidget(self.cal8)
        self.w_calibration_tab_layout.addWidget(self.cal9)
        self.w_calibration_tab_layout.addWidget(self.cal_btn)

        self.ow.addTab(self.w_calibraiton_tab, 'W Calibration')



        # ###DURATION TAB###
        # Main widget and layout
        self.focus_time_tab = qtw.QWidget()
        self.focus_time_tab_layout = qtw.QVBoxLayout()
        self.focus_time_tab_layout.setAlignment(qtc.Qt.AlignTop)
        self.focus_time_tab.setLayout(self.focus_time_tab_layout)

        # make duration tab widgets
        self.duration_time_label = qtw.QLabel('Set focusing duration (in minutes)')
        # self.duration_time_label.setStyleSheet('font-size: 12pt')
        self.duration_time_sbox = qtw.QSpinBox()
        self.duration_time_sbox.setRange(1, 10)
        self.duration_time_sbox.setValue(5)
        # self.duration_time_sbox.setStyleSheet('font-size: 12pt')
        self.duration_time_sbox.setMaximumWidth(70)

        # connect signals
        self.duration_time_sbox.valueChanged.connect(lambda value: self.set_duration(value))

        # place widgets
        self.focus_time_tab_layout.addWidget(self.duration_time_label)
        self.focus_time_tab_layout.addWidget(self.duration_time_sbox)

        # add tab to tab widget
        self.ow.addTab(self.focus_time_tab, 'Focusing')

        # ###FITTING TAB###
        # Main widget and layout
        self.fitting_tab = qtw.QWidget()
        self.fitting_tab_layout = qtw.QVBoxLayout()
        self.fitting_tab_layout.setAlignment(qtc.Qt.AlignTop)
        self.fitting_tab.setLayout(self.fitting_tab_layout)

        ### roi selection ###
        # make widgets for roi selection
        self.fit_roi_min_label = qtw.QLabel('ROI minimum')
        self.fit_roi_min_sbox = qtw.QSpinBox()
        self.fit_roi_min_sbox.setRange(10, 500)
        self.fit_roi_min_sbox.setValue(150)
        self.fit_roi_min_sbox.setSingleStep(10)
        self.fit_roi_max_label = qtw.QLabel('ROI maximum')
        self.fit_roi_max_sbox = qtw.QSpinBox()
        self.fit_roi_max_sbox.setRange(10, 500)
        self.fit_roi_max_sbox.setValue(150)
        self.fit_roi_max_sbox.setSingleStep(10)

        # connect signals for roi selection
        self.fit_roi_min_sbox.valueChanged.connect(lambda value: self.set_roi_range('min', value))
        self.fit_roi_max_sbox.valueChanged.connect(lambda value: self.set_roi_range('max', value))

        # add roi selection widgets to fitting tab
        self.roi_selection_gb = qtw.QGroupBox('ROI extrema for fitting (delta pixels)')
        self.fitting_tab_layout.addWidget(self.roi_selection_gb)
        self.roi_selection_gb_layout = qtw.QHBoxLayout()
        self.roi_selection_gb.setLayout(self.roi_selection_gb_layout)
        self.roi_selection_gb_layout.addWidget(self.fit_roi_min_label)
        self.roi_selection_gb_layout.addWidget(self.fit_roi_min_sbox)
        self.roi_selection_gb_layout.addWidget(self.fit_roi_max_label)
        self.roi_selection_gb_layout.addWidget(self.fit_roi_max_sbox)
        self.fitting_tab_layout.addSpacing(10)

        ### user-defined r1 ###
        # make user-defined r1 widgets
        self.manual_r1_label = qtw.QLabel('R1 guess')
        self.manual_r1_input = MouseLineEdit('694.260')
        self.manual_r1_input.setValidator(qtg.QDoubleValidator(680.000, 760.000, 3))
        self.manual_r1_cbox = qtw.QCheckBox('Use R1 guess')

        # connect user-defined r1 signals

        # add user-defined r1 widgets to fitting tab
        self.user_defined_r1_gb = qtw.QGroupBox('User-defined R1 (wavelength)')
        self.fitting_tab_layout.addWidget(self.user_defined_r1_gb)
        self.user_defined_r1_gb_layout = qtw.QHBoxLayout()
        self.user_defined_r1_gb.setLayout(self.user_defined_r1_gb_layout)
        self.user_defined_r1_gb_layout.addWidget(self.manual_r1_label)
        self.user_defined_r1_gb_layout.addWidget(self.manual_r1_input)
        self.user_defined_r1_gb_layout.addWidget(self.manual_r1_cbox)
        self.fitting_tab_layout.addSpacing(10)

        ### background subtraction ###
        # make background subtraction widgets
        self.fetch_bg_btn = qtw.QPushButton('Grab current spectrum')
        self.subtract_bg_cbox = qtw.QCheckBox('Subtract background')

        # connect background subtraction signals

        # add background subtraction widgets to fitting tab
        self.background_subtraction_gb = qtw.QGroupBox('Background subtraction')
        self.fitting_tab_layout.addWidget(self.background_subtraction_gb)
        self.background_subtraction_gb_layout = qtw.QHBoxLayout()
        self.background_subtraction_gb.setLayout(self.background_subtraction_gb_layout)
        self.background_subtraction_gb_layout.addWidget(self.fetch_bg_btn)
        self.background_subtraction_gb_layout.addWidget(self.subtract_bg_cbox)
        self.fitting_tab_layout.addSpacing(10)

        ### fitting model ###
        # make fitting model widgets
        self.fit_moffat_btn = qtw.QPushButton('Moffat')
        self.fit_pseudovoigt_btn = qtw.QPushButton('Pseudo-Voigt')
        self.fit_moffat_btn.setCheckable(True)
        self.fit_pseudovoigt_btn.setCheckable(True)
        self.fit_moffat_btn.setChecked(True)
        self.fit_model_btn_group = qtw.QButtonGroup()
        self.fit_model_btn_group.addButton(self.fit_moffat_btn, 0)
        self.fit_model_btn_group.addButton(self.fit_pseudovoigt_btn, 1)

        # connect fitting model signals

        # add fitting model widgets to fitting tab
        self.fitting_model_gb = qtw.QGroupBox('Select fitting model')
        self.fitting_tab_layout.addWidget(self.fitting_model_gb)
        self.fitting_model_gb_layout = qtw.QHBoxLayout()
        self.fitting_model_gb.setLayout(self.fitting_model_gb_layout)
        self.fitting_model_gb_layout.addWidget(self.fit_moffat_btn)
        self.fitting_model_gb_layout.addWidget(self.fit_pseudovoigt_btn)

        self.ow.addTab(self.fitting_tab, 'Fitting')

        # ###EPICS tab###
        # make EPICS tab
        self.epics_tab = qtw.QWidget()
        self.epics_tab_layout = qtw.QVBoxLayout()
        self.epics_tab_layout.setAlignment(qtc.Qt.AlignTop)
        self.epics_tab.setLayout(self.epics_tab_layout)

        # make widgets
        self.epics_label = qtw.QLabel('Select EPICS PV for temperature tracking')
        self.epics_drop = qtw.QComboBox()
        self.epics_drop.addItems(['None (disconnected)',
                                  'Lake Shore 336 TC1 Input 1',
                                  'Lake Shore 336 TC1 Input 2',
                                  'Lake Shore 336 TC1 Input 3',
                                  'Lake Shore 336 TC1 Input 4',
                                  'Lake Shore 336 TC2 Input 1',
                                  'Lake Shore 336 TC2 Input 2',
                                  'Lake Shore 336 TC2 Input 3',
                                  'Lake Shore 336 TC2 Input 4',
                                  'Custom PV Entry'])
        self.epics_status_label = qtw.QLabel('Current EPICS connection status:')
        self.epics_status_display = qtw.QLabel('Disconnected')
        self.epics_custom_label = qtw.QLabel('Custom PV Entry')
        self.epics_custom_entry = qtw.QLineEdit()

        # connect signals
        self.epics_drop.currentIndexChanged.connect(self.initialize_epics)
        self.epics_custom_entry.returnPressed.connect(self.custom_epics)

        # add widgets to layout
        self.epics_tab_layout.addWidget(self.epics_label)
        self.epics_tab_layout.addWidget(self.epics_drop)

        self.epics_tab_connection_layout = qtw.QHBoxLayout()
        self.epics_tab_connection_layout.addWidget(self.epics_status_label)
        self.epics_tab_connection_layout.addWidget(self.epics_status_display)
        self.epics_tab_layout.addLayout(self.epics_tab_connection_layout)

        self.epics_tab_layout.addSpacing(20)

        self.epics_tab_layout.addWidget(self.epics_custom_label)
        self.epics_tab_layout.addWidget(self.epics_custom_entry)

        self.ow.addTab(self.epics_tab, 'EPICS')

        '''
        About window
        '''

        self.aw = qtw.QWidget()
        self.aw.setWindowTitle('About')
        self.aw_layout = qtw.QVBoxLayout()
        self.aw.setLayout(self.aw_layout)

        self.owner_label = qtw.QLabel(
            'RubyRead developed by HPCAT\n'
            'Python 3.7 (64-bit), PyQt 5.9, PyQtGraph 0.11\n'
            'Beta version developed March 2021')
        self.aw_layout.addWidget(self.owner_label)

        # from Clemens' Dioptas
        # file = open(os.path.join("stylesheet.qss"))
        # stylesheet = file.read()
        # self.setStyleSheet(stylesheet)
        # file.close()

        '''
        Thread stuff
        '''

        # initialize collection thread
        self.collect = CollectSpecs()
        self.collect_thread = qtc.QThread()
        self.collect.moveToThread(self.collect_thread)
        self.collect_thread.start()
        self.collect.spectra_returned_signal.connect(self.data_set)
        self.spectra_requested_signal.connect(self.collect.collect_specs)

        # initialize fit thread
        self.fit = FitSpecs()
        self.fit_thread = qtc.QThread()
        self.fit.moveToThread(self.fit_thread)
        self.fit_thread.start()
        self.fit.fit_returned_signal.connect(self.fit_set)
        self.fit_requested_signal.connect(self.fit.fit_specs)

        self.temperature_pv = []

        # last bit o' code
        self.show()

    '''
    Class methods
    '''

    def load_data(self):
        if self.collect.go:
            qtw.QMessageBox.warning(self, 'Unable to load data', 'You must stop continuous data collection before attempting to load data')
            return
        name, _ = qtw.QFileDialog.getOpenFileName(self, 'Open file', filter='*.csv, *.txt')
        xs, ys = np.genfromtxt(name,
                               delimiter=',',
                               skip_header=1,
                               filling_values=1,
                               usecols=(0, 1),
                               unpack=True)
        core.xs = xs
        print(len(xs))
        core.ys = ys
        update()

    def save_data(self):
        scene = self.raw_data.scene()
        self.dialog_window = exportDialog.ExportDialog(scene)
        self.dialog_window.show(self.raw_data)

    def closeEvent(self, *args, **kwargs):
        self.fit_thread.quit()
        self.fit_thread.wait()
        if self.collect.go:
            self.collect.go = False
        self.collect_thread.quit()
        self.collect_thread.wait()
        app.closeAllWindows()
        sys.exit()

    # class methods for custom tool bar
    def take_one_spectrum(self):
        if not self.collect.go:
            intensities = core.spec.intensities()
            if self.average_spec_cbox.isChecked():
                num = self.average_spec_sbox.value()
                for each in range(num - 1):
                    intensities += core.spec.intensities()
                intensities = intensities / num
            core.ys = intensities
            update()

    def take_n_spectra(self):
        if not self.collect.go:
            self.spectra_requested_signal.emit(True)
        else:
            self.collect.stop()

    def fit_one_spectrum(self):
        if not self.fit_n_spec_btn.isChecked():
            self.fit_requested_signal.emit(True)

    def fit_n_spectra(self):
        if self.fit_n_spec_btn.isChecked():
            if not self.show_curve_cbtn.isChecked():
                self.show_curve_cbtn.click()
            if not self.show_fit_p_cbtn.isChecked():
                self.show_fit_p_cbtn.click()
        else:
            if self.show_curve_cbtn.isChecked():
                self.show_curve_cbtn.click()
            if self.show_fit_p_cbtn.isChecked():
                self.show_fit_p_cbtn.click()

    def set_threshold(self):
        core.threshold = self.threshold_min_input.value()

    def zoom_full(self):
        vb.autoRange()

    def zoom_fit(self):
        vb.zoom_roi()

    # class methods for spectrum control
    def update_count_time(self):
        count_time = int(self.count_time_input.text()) * 1000
        core.spec.integration_time_micros(count_time)

    def count_time_shortcut(self, direction):
        # quickly increase count time over common range
        old_time = int(self.count_time_input.text())
        preset_times = ['20', '50', '100', '200', '500', '1000']
        if direction == 'down':
            for each in reversed(preset_times):
                if int(each) < old_time:
                    self.count_time_input.setText(each)
                    core.spec.integration_time_micros(int(each)*1000)
                    break
        if direction == 'up':
            for each in preset_times:
                if int(each) > old_time:
                    self.count_time_input.setText(each)
                    core.spec.integration_time_micros(int(each)*1000)
                    break

    def toggle_average(self):
        core.average = self.average_spec_cbox.isChecked()

    def set_num_average(self):
        core.num_average = self.average_spec_sbox.value()

    # class methods for plot control
    def show_curve_cbtn_clicked(self):
        if self.show_curve_cbtn.isChecked():
            self.pw.addItem(self.fit_data)
        else:
            self.pw.removeItem(self.fit_data)

    def show_r1r2_cbtn_clicked(self):
        if self.show_r1r2_cbtn.isChecked():
            self.pw.addItem(self.r1_data)
            self.pw.addItem(self.r2_data)
        else:
            self.pw.removeItem(self.r1_data)
            self.pw.removeItem(self.r2_data)

    def show_bg_cbtn_clicked(self):
        if self.show_bg_cbtn.isChecked():
            self.pw.addItem(self.bg_data)
        else:
            self.pw.removeItem(self.bg_data)

    def show_fit_p_cbtn_clicked(self):
        if self.show_fit_p_cbtn.isChecked():
            self.pw.addItem(self.vline_press)
        else:
            self.pw.removeItem(self.vline_press)

    def show_ref_p_cbtn_clicked(self):
        if self.show_ref_p_cbtn.isChecked():
            self.pw.addItem(self.vline_ref)
        else:
            self.pw.removeItem(self.vline_ref)

    def show_target_p_cbtn_clicked(self):
        if self.show_target_p_cbtn.isChecked():
            self.pw.addItem(self.vline_target)
        else:
            self.pw.removeItem(self.vline_target)

    def show_target_p_lambda_changed(self):
        target_lambda = float(self.show_target_p_lambda.text())
        self.show_target_p_lambda.setText('%.3f' % target_lambda)
        self.vline_target.setX(target_lambda)
        self.calculate_target_pressure(target_lambda)

    def show_target_p_pressure_changed(self):
        target_pressure = float(self.show_target_p_pressure.text())
        self.show_target_p_pressure.setText('%.2f' % target_pressure)
        target_lambda = core.lambda_0_t_user * ((target_pressure * core.beta / core.alpha + 1) ** (1 / core.beta))
        self.vline_target.setX(target_lambda)
        self.show_target_p_lambda.setText('%.3f' % target_lambda)
        self.calculate_deltas()

    def show_target_p_delta_changed(self):
        delta_p = float(self.show_target_p_delta.text())
        self.show_target_p_delta.setText('%.2f' % delta_p)
        fit_p = float(self.pressure_fit_display.text())
        target_p = fit_p + delta_p
        self.show_target_p_pressure.setText('%.2f' % target_p)
        self.show_target_p_pressure_changed()

    def set_ref_from_zero(self):
        self.show_ref_p_lambda.setText(self.lambda_naught_t_display.text())
        self.show_ref_p_pressure.setText('0.00')
        self.vline_ref.setX(float(self.lambda_naught_t_display.text()))
        self.calculate_deltas()

    def set_ref_from_fit(self):
        self.show_ref_p_lambda.setText(self.lambda_r1_display.text())
        self.show_ref_p_pressure.setText(self.pressure_fit_display.text())
        self.vline_ref.setX(float(self.lambda_r1_display.text()))
        self.calculate_deltas()

    def set_ref_from_target(self):
        self.show_ref_p_lambda.setText(self.show_target_p_lambda.text())
        self.show_ref_p_pressure.setText(self.show_target_p_pressure.text())
        self.vline_ref.setX(float(self.show_target_p_lambda.text()))
        self.calculate_deltas()

    def target_line_moved(self):
        target_lambda = self.vline_target.getXPos()
        self.show_target_p_lambda.setText('%.3f' % target_lambda)
        self.calculate_target_pressure(target_lambda)
        self.calculate_deltas()

    def calculate_target_p_lambda(self):
        target_pressure = float(self.show_target_p_pressure.text())
        target_lambda = core.lambda_0_t_user * ((target_pressure * core.beta / core.alpha + 1) ** (1 / core.beta))
        self.show_target_p_lambda.setText('%.3f' % target_lambda)
        self.show_target_p_lambda_changed()

    def calculate_target_pressure(self, lambda_r1):
        target_pressure = core.alpha * ((1 / core.beta) * (((lambda_r1 / core.lambda_0_t_user) ** core.beta) - 1))
        self.show_target_p_pressure.setText('%.2f' % target_pressure)
        self.calculate_deltas()

    def calculate_deltas(self):
        fit_p = float(self.pressure_fit_display.text())
        ref_p = float(self.show_ref_p_pressure.text())
        target_p = float(self.show_target_p_pressure.text())
        self.show_ref_p_delta.setText('%.2f' % (ref_p - fit_p))
        self.show_target_p_delta.setText('%.2f' % (target_p - fit_p))

    # class methods for pressure control
    def calculate_lambda_0_t(self):
        t = self.temperature_input.value()
        cold_style = 'QSpinBox {background-color: #add8e6; font: bold 24px}'
        hot_style = 'QSpinBox {background-color: #ffb347; font: bold 24px}'
        rt_style = 'QSpinBox {background-color: #ffffff; font: bold 24px}'
        if t < 295:
            self.temperature_input.setStyleSheet(cold_style)
        elif t > 295:
            self.temperature_input.setStyleSheet(hot_style)
        else:
            self.temperature_input.setStyleSheet(rt_style)
        offset = core.lambda_0_user - core.lambda_0_ref
        lambda_0_t = 10000000 / (14423.0 + 0.0446*t - 0.000481*t*t + 0.000000371*t*t*t)
        core.lambda_0_t_user = lambda_0_t + offset
        self.lambda_naught_t_display.setText('%.3f' % core.lambda_0_t_user)
        calculate_pressure(core.lambda_r1)
        self.calculate_target_p_lambda()

    # class methods for tabs
    def set_lambda_naught(self, source):
        if source == 'manual':
            new_lambda = float(self.manual_lambda_naught_input.text())
        elif source == 'auto':
            new_lambda = core.lambda_r1
        core.lambda_0_user = new_lambda
        self.lambda_naught_295_display.setText('%.3f' % new_lambda)
        self.calculate_lambda_0_t()
        # save data in file for software restart
        new_gui_lambda_string = 'gui.lambda_naught_295_display.setText(\'' + '%.3f' % new_lambda + '\')'
        new_core_lambda_string = 'core.lambda_0_user = ' + '%.3f' % new_lambda
        textfile = open('rubyread.txt', 'w')
        textfile.write(new_gui_lambda_string + '\n' + new_core_lambda_string + '\n')
        textfile.close()

    def set_new_p_calibration(self):
        index = self.choose_calibration_drop.currentIndex()
        if index == 0:
            calibration = 'IPPS-Ruby2020 (2020)'
            a = 1870
            b = 10.69
        elif index == 1:
            calibration = 'Mao et al. (1986)'
            a = 1904
            b = 7.665
        else:
            calibration = 'Dewaele et al. (2004)'
            a = 1904
            b = 9.5
        self.press_calibration_display.setText(calibration)
        core.alpha = a
        core.beta = b
        self.p_calibration_alpha_display.setText(str(a))
        self.p_calibration_beta_display.setText(str(b))
        calculate_pressure(core.lambda_r1)
        self.calculate_target_pressure(float(self.show_target_p_lambda.text()))
        self.calculate_deltas()

    # class methods for duration tab
    def set_duration(self, value):
        core.duration = value*60

    # class methods for w calibration tab
    def calibrate_spectrometer(self):
        ###START HERE###
        cal_pixels = []
        cal_wavelengths = []
        all_peaks = [self.cal1,
                     self.cal2,
                     self.cal3,
                     self.cal4,
                     self.cal5,
                     self.cal6,
                     self.cal7,
                     self.cal8,
                     self.cal9]
        for each in all_peaks:
            if each.cbox.isChecked():
                cal_pixels.append(float(each.pixel_fit.text()))
                cal_wavelengths.append(float(each.wave_guess.text()))
        print(cal_pixels, cal_wavelengths)
        pixel_array = np.array(cal_pixels)
        wavelength_array = np.array(cal_wavelengths)
        a = np.polyfit(pixel_array, wavelength_array, 3)
        print(a)
        f = lambda x: a[0]*x**3 + a[1]*x**2 + a[2]*x + a[3]
        new_xs = f(np.arange(0, 2048))
        print(new_xs[0], new_xs[-1], new_xs.size)
        pwid = pg.plot()
        pwid.plot(core.xs)
        pwid.plot(new_xs, pen='r')
        core.xs = new_xs


    # class methods for fitting roi tab
    def set_roi_range(self, end, value):
        if end == 'min':
            core.roi_min = value
        if end == 'max':
            core.roi_max = value

    # class methods for EPICS tab
    def initialize_epics(self):
        pv_list = ['None (disconnected)',
                   '16LakeShore1:LS336:TC1:IN1',
                   '16LakeShore1:LS336:TC1:IN2',
                   '16LakeShore1:LS336:TC1:IN3',
                   '16LakeShore1:LS336:TC1:IN4',
                   '16LakeShore2:LS336:TC2:IN1',
                   '16LakeShore2:LS336:TC2:IN2',
                   '16LakeShore2:LS336:TC2:IN3',
                   '16LakeShore2:LS336:TC2:IN4']
        if self.epics_drop.currentIndex() == 0:
            self.temperature_pv.disconnect()
            self.temperature_track_cbox.setChecked(False)
            self.temperature_track_cbox.setEnabled(False)
            self.epics_status_display.setText('Disconnected')
            return
        if not type(self.temperature_pv) == list:
            self.temperature_pv.disconnect()
        if not self.epics_drop.currentIndex() == 9:
            temperature_pv = pv_list[self.epics_drop.currentIndex()]
        else:
            trial_pv = str(self.epics_custom_entry.text())
            if trial_pv == '':
                self.epics_custom_entry.setText('Enter your PV here')
            temperature_pv = str(self.epics_custom_entry.text())
        self.temperature_pv = PV(temperature_pv, callback=self.track_temperature_pv,
                                 auto_monitor=True, connection_callback=self.epics_disconnect,
                                 connection_timeout=1.0)
        if not self.temperature_pv.wait_for_connection(timeout=1.0):
            self.epics_status_display.setText('Failed to connect')
            self.temperature_pv.disconnect()
            self.temperature_track_cbox.setChecked(False)
            self.temperature_track_cbox.setEnabled(False)
            self.epics_drop.setCurrentIndex(0)
        else:
            self.epics_status_display.setText('Connected')
            self.temperature_track_cbox.setEnabled(True)

    def custom_epics(self):
        self.epics_drop.setCurrentIndex(9)
        self.initialize_epics()

    def track_temperature_pv(self, value, **kwargs):
        if self.temperature_track_cbox.isChecked():
            if 0 < value < 601:
                self.temperature_input.setValue(value)

    def epics_disconnect(self, conn, **kwargs):
        if not conn:
            self.epics_drop.setCurrentIndex(0)

    # ###THREAD CALLBACK METHODS### #
    def data_set(self, data_dict):
        if int(data_dict['remaining_time']) == 0:
            self.remaining_time_display.setStyleSheet('')
            self.remaining_time_display.setText('Idle')
            self.take_n_spec_btn.setChecked(False)
        else:
            core.ys = data_dict['raw_y']
            self.remaining_time_display.setStyleSheet('background-color: green; color: yellow')
            remaining_time = str(int(data_dict['remaining_time']))
            self.remaining_time_display.setText(remaining_time)
            update()

    def fit_set(self, fit_dict):
        warning = fit_dict['warning']
        if not warning == '':
            self.fit_warning_display.setStyleSheet('background-color: red; color: yellow')
            fitted_list = [self.show_curve_cbtn, self.show_r1r2_cbtn, self.show_bg_cbtn]
            for each in fitted_list:
                if each.isChecked():
                    each.click()
        else:
            popt = fit_dict['popt']
            self.lambda_r1_display.setText('%.3f' % popt[5])
            self.fit_data.setData(core.xs_roi, double_pseudo(core.xs_roi, *popt))
            self.r1_data.setData(core.xs_roi, pseudo(core.xs_roi, popt[4], popt[5], popt[6], popt[7], popt[8], popt[9]))
            self.r2_data.setData(core.xs_roi, pseudo(core.xs_roi, popt[0], popt[1], popt[2], popt[3], popt[8], popt[9]))
            self.bg_data.setData(core.xs_roi, (popt[8] * core.xs_roi + popt[9]))
            # calculate pressure
            core.lambda_r1 = popt[5]
            calculate_pressure(core.lambda_r1)
            self.vline_press.setPos(popt[5])
            if not self.show_curve_cbtn.isChecked():
                self.show_curve_cbtn.click()
            if not self.show_fit_p_cbtn.isChecked():
                self.show_fit_p_cbtn.click()
            self.fit_warning_display.setStyleSheet('')
        self.fit_warning_display.setText(warning)


class CoreData:
    def __init__(self):
        # get spectrometer going
        # list of approved spectrometers
        spec_list = ['HR+C0308',
                     'HR+C0996',
                     'HR+D1333',
                     'HR+C2429',
                     'HR+C0614',
                     'HR+C2911',
                     'HR+C1514',
                     'HR+D2121',
                     'HR+C1923',
                     'HR+D0677',
                     'FLMS18881',
                     'FLMT06374']
        # look for and select among available spectrometers
        index = -1
        retries = 0
        while index == -1:
            devices = sb.list_devices()
            num_devices = len(devices)
            if num_devices == 1:
                index = 0
            elif num_devices == 0:
                # Important to make the number of retry checks here
                if retries > 2:
                    qtw.QMessageBox.warning(None,
                                            'Too many retries',
                                            'Too many retries, program will quit')
                    sys.exit()
                msgbox = qtw.QMessageBox()
                msgbox.setWindowTitle('No Spectrometers Available')
                msgbox.setText('Please connect a spectrometer.\n'
                               'If spectrometer is already connected, please make sure it is not already in use.\n'
                               'Troubleshoot: try reconnecting USB cable to spectrometer.')
                msgbox.addButton(qtw.QMessageBox.Retry)
                msgbox.addButton(qtw.QMessageBox.Abort)
                msgbox.addButton(qtw.QMessageBox.Ignore)
                choice = msgbox.exec_()
                if choice == qtw.QMessageBox.Retry:
                    retries += 1
                elif choice == qtw.QMessageBox.Ignore:
                    qtw.QMessageBox.information(None,
                                                'No spectrometer',
                                                'No spectrometer found, entering data viewing mode (future).\n'
                                                'Exiting program (temporary until data-only implemented).')
                    sys.exit()
                elif choice == qtw.QMessageBox.Abort:
                    sys.exit()
            elif num_devices == 2:
                msgbox = qtw.QMessageBox()
                msgbox.setWindowTitle('Multiple Spectrometers')
                msgbox.setText('Two spectrometers found.\n'
                               'Please select between the spectrometers below:')
                msgbox.addButton(str(devices[0]), qtw.QMessageBox.YesRole)
                msgbox.addButton(str(devices[1]), qtw.QMessageBox.NoRole)
                choice = msgbox.exec_()
                index = choice
            else:
                # refuse 3+ spectrometers
                msgbox = qtw.QMessageBox.warning(None,
                                                 'Too many spectrometers',
                                                 'Please limit number of spectrometers and run program again.')
                sys.exit()
        # initialize spectrometer and check serial number is valid
        self.spec = sb.Spectrometer(devices[index])
        if self.spec.serial_number not in spec_list:
            msg = qtw.QMessageBox.warning(None,
                                          'Spectrometer not recognized',
                                          'The serial number of your spectrometer is not recognized.\n'
                                          'Contact HPCAT staff to add your spectrometer to the list of approved devices.')
            sys.exit()
        # set default integration time of 100 ms
        self.spec.integration_time_micros(100000)

        # establish initial spectrum
        self.xs = self.spec.wavelengths()
        self.ys = self.spec.intensities()

        # define initial fit boundaries
        self.roi_min = 150
        self.roi_max = 150

        # TODO: send below parameters to fitting as needed
        # define plot and fit limits from hardware specifications
        self.max_intensity = self.spec.max_intensity
        self.num_pixels = self.spec.pixels

        # set initial roi arrays
        default_zoom = np.abs(self.xs-694.260).argmin()
        self.xs_roi = self.xs[default_zoom - self.roi_min:default_zoom + self.roi_max]
        self.ys_roi = self.ys[default_zoom - self.roi_min:default_zoom + self.roi_max]

        # variables to pass through thread
        self.average = False
        self.num_average = 1
        self.threshold = 1000
        self.warning = ''

        # initial focusing time
        self.duration = 300

        # pressure calculation parameters
        # lambda zero (ref) is 694.260 based on Ragan et al JAP 72, 5539 (1992) at 295K
        self.alpha = 1870
        self.beta = 10.69
        self.lambda_0_ref = 694.260
        self.lambda_0_user = 694.260
        self.lambda_0_t_user = 694.260
        self.lambda_r1 = 694.260
        self.temperature = 295
        self.pressure = 0.00


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)

    # reimplement right-click to zoom roi
    def mouseClickEvent(self, ev):
        if ev.button() == qtc.Qt.RightButton:
            self.zoom_roi()
        if ev.button() == qtc.Qt.LeftButton:
            if gui.had_focus:
                pos = ev.pos()
                data = self.mapToView(pos)
                wavelength = data.x()
                index = np.abs(core.xs - wavelength).argmin()
                if gui.had_focus.parentWidget() == gui.user_defined_r1_gb:
                    gui.had_focus.setText('%.3f' % wavelength)
                else:
                    # widget is part of wavelength calibration
                    gui.had_focus.setText(str(index))
                gui.had_focus = None




    def mouseDoubleClickEvent(self, ev):
        if ev.button() == qtc.Qt.LeftButton:
            self.autoRange()

    def mouseDragEvent(self, ev):
        if ev.button() == qtc.Qt.RightButton:
            ev.ignore()
        else:
            pg.ViewBox.mouseDragEvent(self, ev)

    def zoom_roi(self):
        self.setXRange(core.xs_roi[0], core.xs_roi[-1])
        self.setYRange(core.ys_roi.min(), core.ys_roi.max())


class MouseLineEdit(qtw.QLineEdit):

    def focusOutEvent(self, event):
        gui.had_focus = self
        super(MouseLineEdit, self).focusOutEvent(event)


class CalibrationEntry(qtw.QWidget):

    def __init__(self):
        super().__init__()

        self.cbox = qtw.QCheckBox()
        # self.cbox.setFixedWidth(5)
        self.pixel_input = MouseLineEdit()
        self.pixel_input.setFixedWidth(60)
        self.pixel_fit = qtw.QLineEdit()
        self.pixel_fit.setFixedWidth(60)
        self.wave_fit = qtw.QLineEdit()
        self.wave_fit.setFixedWidth(60)
        self.wave_guess = qtw.QLineEdit()
        self.wave_guess.setFixedWidth(60)
        self.wave_error = qtw.QLineEdit()
        self.wave_error.setFixedWidth(60)

        # connect signals
        self.pixel_input.textChanged.connect(lambda text: self.fit_and_fill(text))

        self.cal_entry_line_layout = qtw.QHBoxLayout()
        self.setLayout(self.cal_entry_line_layout)

        self.cal_entry_line_layout.addWidget(self.cbox)
        self.cal_entry_line_layout.addWidget(self.pixel_input)
        self.cal_entry_line_layout.addWidget(self.pixel_fit)
        self.cal_entry_line_layout.addWidget(self.wave_fit)
        self.cal_entry_line_layout.addWidget(self.wave_guess)
        self.cal_entry_line_layout.addWidget(self.wave_error)

    def fit_and_fill(self, text):
        # gather info around user-selected point and create local arrays
        calibration_lines = np.array([671.704, 692.947, 703.241, 724.517, 750.387, 763.511])
        user_guess = int(text)
        fit_width = 20
        guess_max_index = np.argmax(core.ys[user_guess - fit_width:user_guess + fit_width])
        global_max_index = user_guess - fit_width + guess_max_index
        roi_min = global_max_index - fit_width
        roi_max = global_max_index + fit_width
        local_ys = core.ys[roi_min:roi_max]
        local_xs = core.xs[roi_min:roi_max]
        local_pixels = np.arange(roi_min, roi_max)
        print(user_guess, guess_max_index, global_max_index)
        # generate the initial parameters for peak fitting vs. pixel
        height = np.amax(local_ys) - np.amin(local_ys)
        position_pixels = global_max_index
        slope_pixels = (local_ys[-1] - local_ys[0]) / (local_pixels[-1] - local_pixels[0])
        intercept_pixels = local_ys[0] - slope_pixels*local_pixels[0]
        p0 = [height, position_pixels, 0.5, 1.0, slope_pixels, intercept_pixels]
        print(height, position_pixels, slope_pixels, intercept_pixels)
        # generate the initial parameters for peak fitting vs. wavelength
        position = core.xs[global_max_index]
        slope = (local_ys[-1] - local_ys[0]) / (local_xs[-1] - local_xs[0])
        intercept = local_ys[0] - slope*local_xs[0]
        w0 = [height, position, 0.5, 1.0, slope, intercept]
        print(height, position, slope, intercept)
        # fit peaks against pixels
        popt, _ = curve_fit(pseudo, local_pixels, local_ys, p0)
        print(popt)
        self.pixel_fit.setText('%.3f' % popt[1])
        # fit curve against wavelength
        wopt, _ = curve_fit(pseudo, local_xs, local_ys, w0)
        print(wopt)
        self.wave_fit.setText('%.3f' % wopt[1])
        wave_cal = calibration_lines[np.abs(calibration_lines - wopt[1]).argmin()]
        self.wave_guess.setText('%.3f' % wave_cal)
        delta_wavelength = wopt[1] - wave_cal
        self.wave_error.setText('%.3f' % delta_wavelength)
        if delta_wavelength < 1.0:
            self.cbox.setChecked(True)







class CollectSpecs(qtc.QObject):

    spectra_returned_signal = qtc.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.go = False

    def collect_specs(self, emit_sig):
        self.go = emit_sig
        data_dict = {'remaining_time': '', 'raw_y': ''}
        start_time = time.perf_counter()
        while self.go:
            # get the spectrum
            intensities = core.spec.intensities()
            # average if needed
            if core.average:
                num = core.num_average
                for each in range(num - 1):
                    intensities += core.spec.intensities()
                intensities = intensities / num
            # determine remaining time to collect spectra
            remaining_time = core.duration - (time.perf_counter() - start_time)
            # update dictionary values and send the dict signal
            data_dict['remaining_time'] = remaining_time
            data_dict['raw_y'] = intensities
            self.spectra_returned_signal.emit(data_dict)
            # check if it's time to stop
            if not remaining_time > 0:
                self.stop()
        data_dict['remaining_time'] = 0
        self.spectra_returned_signal.emit(data_dict)

    def stop(self):
        self.go = False


class FitSpecs(qtc.QObject):

    fit_returned_signal = qtc.pyqtSignal(dict)

    def __init__(self):
        super().__init__()

    def fit_specs(self):
        fit_dict = {'warning': '', 'popt': ''}
        # start by defining ROI arrays and get max_index for ROI
        full_max_index = np.argmax(core.ys)
        roi_min = full_max_index - core.roi_min
        roi_max = full_max_index + core.roi_max
        # handle edge situations (for example, during background-only spectra)
        if roi_min < 0:
            roi_min = 0
        if roi_max > core.num_pixels - 1:
            roi_max = -1
        core.xs_roi = core.xs[roi_min:roi_max]
        core.ys_roi = core.ys[roi_min:roi_max]
        roi_max_index = np.argmax(core.ys_roi)
        # start with approximate linear background (using full spectrum)
        slope = (core.ys[-1] - core.ys[0]) / (core.xs[-1] - core.xs[0])
        intercept = core.ys[0] - slope * core.xs[0]
        # obtain initial guesses for fitting parameters using ROI array
        r1_pos = core.xs_roi[roi_max_index]
        r2_pos = r1_pos - 1.4
        r1_height = core.ys_roi[roi_max_index] - (slope * r1_pos + intercept)
        r2_height = r1_height / 2.0
        local_xs = core.xs_roi
        local_ys = core.ys_roi
        # check r1_height is within range before fitting
        if r1_height < core.threshold:
            warning = 'Too weak'
        elif core.ys_roi[roi_max_index] > core.max_intensity - 1:
            warning = 'Saturated'
        else:
            # define fitting parameters p0 (area approximated by height)
            p0 = [r2_height, r2_pos, 0.5, 1.0, r1_height, r1_pos, 0.5, 1.0, slope, intercept]
            try:
                popt, pcov = curve_fit(double_pseudo, local_xs, local_ys, p0=p0)
                warning = ''
                fit_dict['popt'] = popt
            except RuntimeError:
                warning = 'Poor fit'
        fit_dict['warning'] = warning
        self.fit_returned_signal.emit(fit_dict)


def update():
    # take current intesities and plot them
    # Set up y scaling options
    if gui.scale_y_btn_grp.checkedId() == 1:
        viewable = vb.viewRange()
        left_index = np.abs(core.xs-viewable[0][0]).argmin()
        right_index = np.abs(core.xs-viewable[0][1]).argmin()
        view_min = core.ys[left_index:right_index].min()
        view_max = core.ys[left_index:right_index].max()
        if view_max > viewable[1][1]:
            vb.setRange(yRange=(view_min, view_max))
        if view_min < viewable[1][0]:
            vb.setRange(yRange=(view_min, viewable[1][1]))
    # y scaling done, ready to assign new data to curve
    gui.raw_data.setData(core.xs, core.ys)
    if gui.fit_n_spec_btn.isChecked():
        gui.fit_requested_signal.emit(True)


def calculate_pressure(lambda_r1):
    core.pressure = core.alpha * ((1 / core.beta) * (((lambda_r1 / core.lambda_0_t_user) ** core.beta) - 1))
    gui.pressure_fit_display.setText('%.2f' % core.pressure)
    gui.calculate_deltas()


def double_pseudo(x, a1, c1, eta1, w1, a2, c2, eta2, w2, m, bg):
    return a1 * (eta1 * (2 / pi) * (w1 / (4 * (x - c1) ** 2 + w1 ** 2)) +
                 (1 - eta1) * (sqrt(4 * np.log(2)) / (sqrt(pi) * w1)) * np.exp(
                -(4 * np.log(2) / w1 ** 2) * (x - c1) ** 2)) + \
           a2 * (eta2 * (2 / pi) * (w2 / (4 * (x - c2) ** 2 + w2 ** 2)) +
                 (1 - eta2) * (sqrt(4 * np.log(2)) / (sqrt(pi) * w2)) * np.exp(
                -(4 * np.log(2) / w2 ** 2) * (x - c2) ** 2)) + \
           m * x + bg


def pseudo(x, a, c, eta, w, m, bg):
    return a * (eta * (2 / pi) * (w / (4 * (x - c) ** 2 + w ** 2)) +
                (1 - eta) * (sqrt(4 * np.log(2)) / (sqrt(pi) * w)) * np.exp(
                -(4 * np.log(2) / w ** 2) * (x - c) ** 2)) + m * x + bg


def double_moffat(x, a1, c1, w1, b1, a2, c2, w2, b2, m, bg):
    return a1*((((x - c1)/w1)**2 + 1)**-b1) + \
           a2*((((x - c2)/w2)**2 + 1)**-b2) + \
           m*x + bg


def moffat(x, a, c, w, b, m, bg):
    return a*((((x - c)/w)**2 + 1)**-b) + m*x + bg


def recall_lambda_naught():
    # try to restore lambda naught values from previous definition
    try:
        textfile = open('rubyread.txt', 'r')
        exec(textfile.read())
        textfile.close()
        gui.calculate_lambda_0_t()
    except IOError:
        print('Initialization file not found, unable to update zero pressure wavelength')
    except TypeError:
        print('File format not correct, unable to update zero pressure wavelength')


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    core = CoreData()
    vb = CustomViewBox()
    gui = MainWindow()
    update()
    recall_lambda_naught()
    sys.exit(app.exec_())

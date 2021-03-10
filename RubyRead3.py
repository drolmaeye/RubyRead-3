__author__ = 'jssmith'

'''
A GUI for measuring ruby pressure with Ocean Optics or Ocean Insight spectrometers

build command line for executable --unknown--
'''

# import necessary modules
import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
import pyqtgraph as pg
import seabreeze.spectrometers as sb
import numpy as np
from scipy.optimize import curve_fit
# from scipy import exp
from math import pi, sqrt
from epics import PV
import time


class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1080, 720)
        self.setWindowTitle('RubyRead Python3 Development Version')
        self.setWindowIcon(qtg.QIcon('ruby4.png'))

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
        # #self.load_data_action.triggered.connect(self.load_data)

        self.save_data_action = qtw.QAction('Save', self)
        self.save_data_action.setShortcut('Ctrl+S')
        # #self.save_data_action.triggered.connect(self.save_data)

        self.close_rubyread_action = qtw.QAction('Exit', self)
        self.close_rubyread_action.setShortcut('Ctrl+Q')
        self.close_rubyread_action.triggered.connect(self.close)
        # #self.close_rubyread_action.triggered.connect(self.closeEvent)

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

        # connect custom toolbar signals
        # #self.take_one_spec_btn.clicked.connect(self.take_one_spectrum)
        # #self.take_n_spec_btn.clicked.connect(self.take_n_spectra)
        # #self.fit_one_spec_btn.clicked.connect(self.fit_one_spectrum)
        # #self.fit_n_spec_btn.clicked.connect(self.fit_n_spectra)
        # #self.threshold_min_input.valueChanged.connect(self.set_threshold)

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

        # add custom toolbar to main window
        self.mw_layout.addWidget(self.tb)

        '''
        Plot Window
        '''

        # make the plot window for the left side of bottom layout
        # custom viewbox, vb, allows for custom button event handling
        # #self.pw = pg.PlotWidget(viewBox=vb, name='Plot1')
        self.pw = pg.PlotWidget(name='Plot1')

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
        # #self.vline_target.sigPositionChanged.connect(self.target_line_moved)

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
        # #self.count_time_input.editingFinished.connect(self.update_count_time)
        # #self.count_less_button.clicked.connect(lambda: self.count_time_shortcut('down'))
        # #self.count_more_button.clicked.connect(lambda: self.count_time_shortcut('up'))
        # #self.average_spec_cbox.stateChanged.connect(self.toggle_average)
        # #self.average_spec_sbox.valueChanged.connect(self.set_num_average)

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
        # #self.show_curve_cbtn.clicked.connect(self.show_curve_cbtn_clicked)
        # #self.show_r1r2_cbtn.clicked.connect(self.show_r1r2_cbtn_clicked)
        # #self.show_bg_cbtn.clicked.connect(self.show_bg_cbtn_clicked)
        # #self.show_fit_p_cbtn.clicked.connect(self.show_fit_p_cbtn_clicked)
        # #self.show_ref_p_cbtn.clicked.connect(self.show_ref_p_cbtn_clicked)
        # #self.show_target_p_cbtn.clicked.connect(self.show_target_p_cbtn_clicked)
        # #self.show_target_p_lambda.editingFinished.connect(self.show_target_p_lambda_changed)
        # #self.show_target_p_pressure.editingFinished.connect(self.show_target_p_pressure_changed)
        # #self.show_target_p_delta.editingFinished.connect(self.show_target_p_delta_changed)
        # #self.set_ref_from_zero_btn.clicked.connect(self.set_ref_from_zero)
        # #self.set_ref_from_fit_btn.clicked.connect(self.set_ref_from_fit)
        # #self.set_ref_from_target_btn.clicked.connect(self.set_ref_from_target)
        # #self.auto_y_btn.clicked.connect(lambda: vb.enableAutoRange(axis=vb.YAxis))
        # #self.grow_y_btn.clicked.connect(lambda: vb.disableAutoRange())
        # #self.fix_y_btn.clicked.connect(lambda: vb.disableAutoRange())

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
        self.press_calibration_display = qtw.QLabel('Dorogokupets and Oganov (2007)')
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
        # #self.temperature_input.valueChanged.connect(self.calculate_lambda_0_t)

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
        # #self.manual_lambda_naught_input.returnPressed.connect(lambda: self.set_lambda_naught('manual'))
        # #self.auto_lambda_naught_btn.clicked.connect(lambda: self.set_lambda_naught('auto'))

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
        self.choose_calibration_drop.addItems(['Dorogokupets and Oganov, PRB 75, 024115 (2007)',
                                               'Mao et al., JGR 91, 4673 (1986)',
                                               'Dewaele et al., PRB 69, 092106 (2004)'])
        self.p_calibration_alpha_label = qtw.QLabel('<i>A</i> =')
        self.p_calibration_alpha_label.setAlignment(qtc.Qt.AlignRight)
        self.p_calibration_alpha_display = qtw.QLabel('1885')
        self.p_calibration_beta_label = qtw.QLabel('<i>B</i> =')
        self.p_calibration_beta_label.setAlignment(qtc.Qt.AlignRight)
        self.p_calibration_beta_display = qtw.QLabel('11.0')
        # ###self.calculation_label = QtGui.QLabel('P = ' + u'\u03B1' + '/' + u'\u03B2' + '[(' + u'\u03BB' + '/' + u'\u03BB' + '<sub>0</sub>)<sup>' + u'\u03B2' + '</sup> - 1]')
        self.calculation_label = qtw.QLabel('<i>P</i> = <i>A/B</i> [(' + u'\u03BB' + '/' + u'\u03BB' + '<sub>0</sub>)<sup><i>B</i></sup> - 1]')
        self.calculation_label.setStyleSheet('font-size: 16pt; font-weight: bold')
        self.calculation_label.setAlignment(qtc.Qt.AlignCenter)

        # connect signal
        # #self.choose_calibration_drop.currentIndexChanged.connect(self.set_new_p_calibration)

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
        # #self.duration_time_sbox.valueChanged.connect(lambda value: self.set_duration(value))

        # place widgets
        self.focus_time_tab_layout.addWidget(self.duration_time_label)
        self.focus_time_tab_layout.addWidget(self.duration_time_sbox)

        # add tab to tab widget
        self.ow.addTab(self.focus_time_tab, 'Focusing')

        # ###Fitting tab###
        # Main widget and layout
        self.fitting_roi_tab = qtw.QWidget()
        self.fitting_roi_tab_layout = qtw.QVBoxLayout()
        self.fitting_roi_tab_layout.setAlignment(qtc.Qt.AlignTop)
        self.fitting_roi_tab.setLayout(self.fitting_roi_tab_layout)

        # make widgets
        self.fitting_roi_label = qtw.QLabel('Set roi extrema for fitting (delta pixels)')
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

        # conect signals
        # #self.fit_roi_min_sbox.valueChanged.connect(lambda value: self.set_roi_range('min', value))
        # #self.fit_roi_max_sbox.valueChanged.connect(lambda value: self.set_roi_range('max', value))

        # add widgets to layout
        self.fitting_roi_tab_layout.addWidget(self.fitting_roi_label)

        self.pixel_select_layout = qtw.QHBoxLayout()
        self.pixel_select_layout.addWidget(self.fit_roi_min_label)
        self.pixel_select_layout.addWidget(self.fit_roi_min_sbox)
        self.pixel_select_layout.addWidget(self.fit_roi_max_label)
        self.pixel_select_layout.addWidget(self.fit_roi_max_sbox)
        self.fitting_roi_tab_layout.addLayout(self.pixel_select_layout)

        self.ow.addTab(self.fitting_roi_tab, 'Fitting ROI')

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
        # #self.epics_drop.currentIndexChanged.connect(self.initialize_epics)
        # #self.epics_custom_entry.returnPressed.connect(self.custom_epics)

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

        # initialize collection thread
        # ###self.collect_thread = CollectThread(self)
        # ###self.collect_thread.collect_thread_callback_signal.connect(self.data_set)
        # #### initialize fit thread
        # ###self.fit_thread = FitThread(self)
        # ###self.fit_thread.fit_thread_callback_signal.connect(self.fit_set)
        # ###
        # #### self.show()
        # ###self.temperature_pv = []

        # last bit o' code
        self.show()


class CoreData:
    def __init__(self):
        self.devices = sb.list_devices()
        self.spec = sb.Spectrometer(self.devices[0])
        self.spec.integration_time_micros(100000)

        self.xs = self.spec.wavelengths()
        self.ys = self.spec.intensities()


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    core = CoreData()
    gui = MainWindow()
    sys.exit(app.exec_())

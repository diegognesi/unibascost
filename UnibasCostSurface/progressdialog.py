# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UnibasCostSurfaceDialog
                                 A QGIS plugin
 Tool for cost surface analysis and cost surface allocation with a lot of options.
                             -------------------
        begin                : 2013-03-15
        copyright            : (C) 2013 by Diego Gnesi Bartolani, Dimitris Roubis
        email                : diego.gnesi@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os, sys, threading

from PyQt4 import QtCore, QtGui
from qgis.core import *
from ui_progress import Ui_Progress
import wcost

class ProgressDialog(QtGui.QDialog):

    def __init__(self, iface, settings):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_Progress()
        self.ui.setupUi(self)
        self.iface = iface
        self.settings = settings
        self.cost_thread = None
        self.abort_cost = QtCore.SIGNAL("abortcost()")
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Cancel).clicked.connect(self.cancel_pressed)

    def begin_analysis(self):
        # Call wcost thread
        self.cost_thread = CostThread(self, self.settings)
        self.connect( self.cost_thread, self.cost_thread.progress_signal, self.update_message )
        self.connect( self.cost_thread, self.cost_thread.finished_signal, self.finished )
        self.connect( self.cost_thread, self.cost_thread.critical_signal, self.critical )
        self.cost_thread.start()

    def finished(self, files):
        QtGui.QMessageBox.information(self, "Unibas Cost Surface Analysis Tool", "Cost analysis completed!", buttons=QtGui.QMessageBox.Ok)
        if self.settings["load_cost"]:
            self.load_raster_layer(files[0], "cost")
        if self.settings["load_allocation"]:
            self.load_raster_layer(files[1], "cost-based allocations")
        self.close()

    def load_raster_layer(self, file_name, alt_name):
        lyr_name = os.path.basename(file_name)
        if not lyr_name:
            lyr_name = alt_name
        the_layer = QgsRasterLayer(file_name, lyr_name)
        if the_layer.isValid():
            the_layer.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)
            QgsMapLayerRegistry.instance().addMapLayer(the_layer)
        else:
            QtGui.QMessageBox.critical(self, "Impossibile caricare il layer corrispondente al file:\n{0}\nProvare a caricare il layer manualmente".format(files[i]), buttons=QtGui.QMessageBox.Ok)

    def critical(self, message):
        QtGui.QMessageBox.critical(self, "Unibas Cost Surface Analysis Tool", "Critical error:\nError: " + message, buttons=QtGui.QMessageBox.Ok)
        self.close()

    def update_message(self, message):
        if self.ui.lblProgress.text() != message:
            self.ui.lblProgress.setText(message)

    def closeEvent(self, event):
        if self.cost_thread:
            self.emit(self.abort_cost)
        return QtGui.QDialog.closeEvent(self, event)

    def cancel_pressed(self):
        self.close()

class CostThread(QtCore.QThread):

    def __init__(self, sender, settings):
        QtCore.QThread.__init__( self, QtCore.QThread.currentThread() )
        self.sender = sender
        self.settings = settings
        self.aborted = False
        self.connect( self.sender, self.sender.abort_cost, self.abort_requested )
        self.progress_signal = QtCore.SIGNAL("progress( PyQt_PyObject )")
        self.finished_signal = QtCore.SIGNAL("analysis_finished( PyQt_PyObject )")
        self.critical_signal = QtCore.SIGNAL("critical( PyQt_PyObject )")
        
    def run(self):
        try:
            c = wcost.CostAnalyzer(self.settings, self.emit_progress, self)
            files = c.analyze()
            self.emit(self.finished_signal, files)
        except Exception as e:
            if not self.aborted:
                self.emit(self.critical_signal, str(e))
            
    def emit_progress(self, message):
        if not self.aborted:
            self.emit( self.progress_signal , message )

    def abort_requested(self):
        self.aborted = True

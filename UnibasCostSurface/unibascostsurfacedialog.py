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

from PyQt4 import QtCore, QtGui

from ui_unibascostsurface import Ui_UnibasCostSurface
from helpdialog import HelpDialog

from qgis.core import *
import osgeo.gdal as gdal
from gdalconst import *
import GdalTools_utils as Utils


class UnibasCostSurfaceDialog(QtGui.QDialog):
    def __init__(self, iface):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_UnibasCostSurface()
        self.ui.setupUi(self)
        self.supported_formats = None
        self.iface = iface
        self.init_controls()
        self.ui.btnBrowseCost.clicked.connect(self.browse_cost)
        self.ui.btnBrowseAllocation.clicked.connect(self.browse_allocation)
        self.toggle_ok_button()
        self.toggle_all_touched()
        self.ui.cmbEntitiesLayer.currentIndexChanged.connect(self.toggle_ok_button)
        self.ui.cmbEntitiesLayer.currentIndexChanged.connect(self.toggle_all_touched)
        self.ui.cmbSurfaceRaster.currentIndexChanged.connect(self.toggle_ok_button)
        self.ui.cmbSurfaceRaster.currentIndexChanged.connect(self.toggle_ok_button)
        self.ui.cmbIdField.currentIndexChanged.connect(self.toggle_ok_button)
        self.ui.chkAllTouched.toggled.connect(self.toggle_ok_button)
        self.ui.chkLoadCost.toggled.connect(self.toggle_ok_button)
        self.ui.chkAllocate.toggled.connect(self.toggle_ok_button)
        self.ui.chkLoadAllocation.toggled.connect(self.toggle_ok_button)
        self.ui.lnCostFile.textChanged.connect(self.toggle_ok_button)
        self.ui.lnAllocationFile.textChanged.connect(self.toggle_ok_button)
        self.ui.buttonBox.button(QtGui.QDialogButtonBox.Help).clicked.connect(self.help_requested)

    def help_requested(self, value=None):
        dlg = HelpDialog()
        dlg.show()
        dlg.exec_()

    def load_supported_formats(self):
        if not self.supported_formats:
            num = gdal.GetDriverCount()
            formats = {} # QtCore.QStringList()
            for i in range(0, num):
                drv = gdal.GetDriver(i)
                name = drv.LongName
                ext = drv.GetMetadataItem(DMD_EXTENSION)
                if ext:
                    format_str = "{0} *.{1} (*.{1})".format(name, ext)
                else:
                    format_str = "{0} (*.*)".format(name)
                formats[format_str] = ext
            self.supported_formats = formats
            labels = sorted([x for x in formats])
            self.supported_formats_labels = "\n".join(labels)

    def browse_cost(self):
        file_name = self.get_raster_name()
        if file_name:
            self.ui.lnCostFile.setText(file_name)

    def browse_allocation(self):
        file_name = self.get_raster_name()
        if file_name:
            self.ui.lnAllocationFile.setText(file_name)

    def get_raster_name(self):
        lastUsedFilter = Utils.FileFilter.lastUsedRasterFilter()
        # rasterize supports output file creation for GDAL 1.8
        gdalVersion = Utils.GdalConfig.version()
        fileDialogFunc = Utils.FileDialog.getSaveFileName
        outputFile = fileDialogFunc(self, self.tr( "Select the raster file to save the results to" ), Utils.FileFilter.allRastersFilter(), lastUsedFilter)
        if outputFile.isEmpty():
            return
        Utils.FileFilter.setLastUsedRasterFilter(lastUsedFilter)
        return outputFile

    def init_controls(self):
        self.load_layers()
        self.ui.cmbEntitiesLayer.currentIndexChanged.connect(self.update_attributes_cmb)
        indx = self.ui.cmbEntitiesLayer.currentIndex()
        if indx > -1:
            self.update_attributes_cmb(indx)

    def load_layers(self):
        self.ui.cmbEntitiesLayer.clear()
        self.ui.cmbSurfaceRaster.clear()
        # Add layer names to combo boxes
        layers = self.iface.legendInterface().layers()
        for layer in layers:
            if layer.isValid() and (layer.type() == QgsMapLayer.RasterLayer or layer.type() == QgsMapLayer.VectorLayer):
                self.ui.cmbEntitiesLayer.addItem(layer.name(), layer.id())
                if layer.type() == QgsMapLayer.RasterLayer:
                    self.ui.cmbSurfaceRaster.addItem(layer.name(), layer.id())

    def update_attributes_cmb(self, layer_index):
        # Get layer id
        if layer_index > -1:
            qgs_id = self.ui.cmbEntitiesLayer.itemData(layer_index).toString()
            cmb = self.ui.cmbEntitiesMultipliers
            cmbId = self.ui.cmbIdField
            cmb.clear()
            cmbId.clear()
            layer = QgsMapLayerRegistry.instance().mapLayer(qgs_id)
            cmb.addItem("[Do not use multipliers]", "[]")
            if layer and layer.isValid():
                if layer.type() == QgsMapLayer.RasterLayer:
                    for band_num in range(1, layer.bandCount() + 1):
                        cmb.addItem("Band " + str(band_num), str(band_num))
                        cmbId.addItem("Band " + str(band_num), str(band_num))
                elif layer.type() == QgsMapLayer.VectorLayer:
                    # Iterate over vector attributes, but consider only numeric attributes.
                    fields = layer.dataProvider().fields()
                    numeric_types = ["numeric", "byte", "int", "integer", "short", "long", "single", "double", "float", "real"]
                    for i, field in fields.iteritems():
                        if field.typeName().toLower() in numeric_types:
                            cmb.addItem(field.name(), field.name())
                            cmbId.addItem(field.name(), field.name())

    def get_settings(self):
        dc = {
            "ent_layer": self.get_cmb_value_string(self.ui.cmbEntitiesLayer),
            "surface_raster": self.get_cmb_value_string(self.ui.cmbSurfaceRaster),
            "all_touched": self.ui.chkAllTouched.isChecked(),
            "cost_file": self.ui.lnCostFile.text(),
            "load_cost": self.ui.chkLoadCost.isChecked(),
            "perform_allocation": self.ui.chkAllocate.isChecked(),
            "id_field": self.get_cmb_value_string(self.ui.cmbIdField),
            "ent_multipliers": self.get_cmb_value_string(self.ui.cmbEntitiesMultipliers),
            "allocation_file": self.ui.lnAllocationFile.text(),
            "load_allocation": self.ui.chkLoadAllocation.isChecked(),
            "use_ram": self.ui.chkUseMemory.isChecked()
        }
        return dc

    def toggle_ok_button(self, val=None):
        s = self.get_settings()
        if not s["ent_layer"] or s["cost_file"].isEmpty() or not s["surface_raster"] or \
          (s["perform_allocation"] == True and (not s["id_field"] or s["allocation_file"].isEmpty())):
            enabled = False
        else:
            enabled = True
        btn = self.ui.buttonBox.button(QtGui.QDialogButtonBox.Ok);
        btn.setEnabled(enabled);

    def toggle_all_touched(self, val=None):
        enabled_val = False
        qgs_id = self.get_settings()["ent_layer"]
        if qgs_id:
            layer = QgsMapLayerRegistry.instance().mapLayer(qgs_id)
            if layer.type() == QgsMapLayer.VectorLayer:
                enabled_val = True
        self.ui.chkAllTouched.setEnabled(enabled_val)

    def get_complete_settings(self):
        s = self.get_settings()
        # Get the entity layer
        ent_layer = QgsMapLayerRegistry.instance().mapLayer(s["ent_layer"])
        s["ent_source"] = str(ent_layer.source().toUtf8())
        s["ent_is_vector"] = True if ent_layer.type() == QgsMapLayer.VectorLayer else False
        friction_layer = QgsMapLayerRegistry.instance().mapLayer(s["surface_raster"])
        s["friction_source"] = str(friction_layer.source().toUtf8())
        s["cost_file"] = str(s["cost_file"].toUtf8())
        s["id_field"] = str(s["id_field"].toUtf8())
        s["ent_multipliers"] = str(s["ent_multipliers"].toUtf8())
        s["allocation_file"] = str(s["allocation_file"].toUtf8())
        return s

    def get_cmb_value_string(self, combo):
        indx = combo.currentIndex()
        if indx > -1:
            text = combo.itemData(indx).toString()
        else:
            text = ""
        return text

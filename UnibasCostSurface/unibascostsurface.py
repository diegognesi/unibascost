# -*- coding: utf-8 -*-
"""
/***************************************************************************
 UnibasCostSurface
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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from unibascostsurfacedialog import UnibasCostSurfaceDialog
from progressdialog import ProgressDialog


class UnibasCostSurface:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = QFileInfo(QgsApplication.qgisUserDbFilePath()).path() + "/python/plugins/unibascostsurface"
        # initialize locale
        localePath = ""
        locale = QSettings().value("locale/userLocale").toString()[0:2]

        if QFileInfo(self.plugin_dir).exists():
            localePath = self.plugin_dir + "/i18n/unibascostsurface_" + locale + ".qm"

        if QFileInfo(localePath).exists():
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/unibascostsurface/icon.png"),
            u"UNIBAS Cost urface Analysis", self.iface.mainWindow())
        # connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered()"), self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&UNIBAS Cost urface Analysis", self.action)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(u"&UNIBAS Cost urface Analysis", self.action)
        self.iface.removeToolBarIcon(self.action)

    # run method that performs all the real work
    def run(self):
        # Create the dialog (after translation) and keep reference
        dlg = UnibasCostSurfaceDialog(self.iface)
        # show the dialog
        dlg.show()
        dlg.init_controls()
        # Run the dialog event loop
        result = dlg.exec_()
        dlg.close()
        # See if OK was pressed
        if result == 1:
            settings = dlg.get_complete_settings()
            prg = ProgressDialog(self.iface, settings)
            prg.show()
            prg.begin_analysis()
            prg.exec_()

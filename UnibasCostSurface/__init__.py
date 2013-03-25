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
 This script initializes the plugin, making it known to QGIS.
"""


def name():
    return "UNIBAS Cost urface Analysis"


def description():
    return "Tool for cost surface analysis and cost surface allocation with a lot options."


def version():
    return "Version 0.1"


def icon():
    return "icon.png"


def qgisMinimumVersion():
    return "1.8"

def author():
    return "Diego Gnesi Bartolani, Dimitris Roubis"

def email():
    return "diego.gnesi@gmail.com"

def classFactory(iface):
    # load UnibasCostSurface class from file UnibasCostSurface
    from unibascostsurface import UnibasCostSurface
    return UnibasCostSurface(iface)

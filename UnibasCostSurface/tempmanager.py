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

import osgeo.gdal as gdal
import osgeo.ogr as ogr
from gdalconst import *
from qgis.core import *

def create_temp_files(settings, prog_funct):
    if prog_funct:
        prog_funct(0, "Creating temporary files...")
    # Get friction file metadata.
    friction_file = QgsMapLayerRegistry.instance().mapLayer(settings["surface_raster"]).source()
    friction_meta = get_raster_metadata(self, friction_file)
    if friction_meta == None:
        return (False, "Unable to read metadata for friction file.")
    # Now, if ent_layer is a vector layer, rasterize the layer.
    ent_layer = QgsMapLayerRegistry.instance().mapLayer(settings["ent_layer"])

    # No! First reproject!!
    ent_file = ent_layer.source()
    if ent_layer.type() == QgsMapLayer.VectorLayer:
         ent_file = rasterize(ent_file, friction_meta)
         if ent_file == None:
             return (False, "Unable to rasterize the vector file.")
    

def get_raster_metadata(rst_file):
    friction_ds = gdal.Open(rst_file, GA_ReadOnly)
    if friction_ds:
        geo_t = friction_ds.GetGeoTransform()
        if geo_t:
            mt = {
                "proj": friction_ds.GetProjection(),
                "x-size": dataset.RasterXSize,
                "y-size": dataset.RasterYSize,
                "top-left-x": geo_t[0],
                "w-e res": geo_t[1],
                "rot1": get_t[2],
                "top-left-y": geo_t[3],
                "rot2": geo_t[4],
                "top-left-y": geo_t[5]
            }
            friction_ds = None
            return mt
    # If you are here, no metadata was taken.
    friction_ds = None
    return None



def rasterize(vector_file, dest_meta):
    v_ds = ogr.Open(vector_file)
    v_layer = v_ds.GetLayer(0)
    srs = v_layer.
    x_min, x_max, y_min, y_max = v_layer.GetExtent()
    v_ds = None









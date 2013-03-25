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

import sys, os, traceback

import numpy

from qgis.core import *
import osgeo.gdal as gdal
import osgeo.ogr as ogr
from gdalconst import *

class CostAnalyzer:

    int_nodata = -2147483648
    float_nodata = -1.0

    def __init__(self, settings, progress_funct=None, caller=None):
        # progress_funct must have 2 arguments: value (progress percentage) and message.
        # caller must be None ore have a boolean 'aborted' attribute, used to abort if required.
        self.settings = settings
        self.caller = caller
        self.progress_funct = progress_funct
        self.temp_filenames = []
        self.cost_ds = None
        self.allocation_ds = None
        self.friction_ds = None
        self.rank_ds = None
        self.cleaned = False

    def proceed(self):
        # Test if analysis can proceed or if there is an aborting request.
        ok = False if not self.caller or self.caller.aborted==True else True
        if not ok:
            self.cleanup()
        return ok

    def cleanup(self):
        if not self.cleaned:
            # Clean-up code.
            self.cost_ds = None
            self.allocation_ds = None
            self.friction_ds = None
            self.rank_ds = None
            for f in self.temp_filenames:
                try:
                    os.remove(f)
                    pass
                except:
                    pass
            self.cleaned = True

    def prog(self, message):
        # Register progress.
        if self.progress_funct:
            self.progress_funct(message)

    def get_free_file_name(self, extension = None):
        # Gets a free file name.
        tmp_folder = os.path.split(self.settings["cost_file"])[0]
        found = False
        i = 0
        while True:
            if extension:
                complete_name = "tmp{0}.{1}".format(str(i), extension)
            else:
                complete_name = "tmp{0}".format(str(i))
            complete_path = os.path.join(tmp_folder, complete_name)
            if not os.path.exists(complete_path):
                return complete_path.encode("utf-8")
            i += 1

    def get_step(self, iterations):
        # This method answers to the question:
        # How many iterations are equal to the 1% of the total number of iterations?
        # Or, if iterations < 100, 
        # Results are truncated.
        if iterations >= 100:
            how_many = iterations / 100
            lt_100 = False
        else:
            how_many = 100 / iterations
            lt_100 = False
        return (how_many, lt_100)

    def check_increment(self, val, step_info):
        # This method returns 0 if no increment happened,
        # else, returns the increment step.
        # val is a counter that must be resetted every time.
        # It is the number of iterations after the previous increment.
        # the current process increments of a certain percentage.
        # step_info is the restult of a call to get_step.
        how_many, lt_100 = step_info
        if lt_100:
            ck = val * how_many
        else:
            ck = val / how_many
        return ck

    def open_new_ds(self, file_name, metadata, bands, data_type):
        # Creates a new GeoTiff file and returns a reference
        driver = gdal.GetDriverByName('GTiff')
        dst_ds = driver.Create(file_name, metadata["x-size"], metadata["y-size"], bands, self.get_gdal_datatype(data_type))
        if dst_ds:
            dst_ds.SetGeoTransform( [ metadata["top-left-x"], metadata["w-e-res"], metadata["rot1"], metadata["top-left-y"], metadata["rot2"], metadata["n-s-res"] ] )
            dst_ds.SetProjection(metadata["proj_wkt"])
            return dst_ds
        else:
            raise Exception("Unable to create the GDAL raster data source.")

    def create_ds(self, file_name, metadata, bands, data_type=int, def_value=0, fill=True):
        # Creates a new GeoTiff file, fills it with a defalut value if needed and closes the datasource.
        dst_ds = self.open_new_ds(file_name, metadata, bands, data_type)
        if fill:
            arr = numpy.empty( [ metadata["y-size"], metadata["x-size"] ], dtype=data_type )
            arr.fill(def_value)
            for i in range(bands):
                dst_ds.GetRasterBand(i + 1).WriteArray(arr)
            dst_ds = None
        dst_ds = None

    def open_new_ds(self, file_name, metadata, bands, data_type):
        # Creates a new GeoTiff file and returns a reference
        driver = gdal.GetDriverByName('GTiff')
        dst_ds = driver.Create(file_name, metadata["x-size"], metadata["y-size"], bands, self.get_gdal_datatype(data_type))
        if dst_ds:
            dst_ds.SetGeoTransform( [ metadata["top-left-x"], metadata["w-e-res"], metadata["rot1"], metadata["top-left-y"], metadata["rot2"], metadata["n-s-res"] ] )
            dst_ds.SetProjection(metadata["proj_wkt"])
            return dst_ds
        else:
            raise Exception("Unable to create the GDAL raster data source.")

    def get_gdal_datatype(self, python_dt):
        if python_dt == int or python_dt == long:
            return GDT_Int32
        elif python_dt == float:
            return GDT_Float64
        else:
            raise NotImplementedError()

    def analyze(self):
        # This is the main method!
        # Check if proceed or not at each time-consuming instruction.
        try:
            gdal.AllRegister()
            s = self.settings
            if self.proceed():
                metadata = self.get_raster_metadata(s["friction_source"])
                self.cols = metadata["x-size"]
                self.rows = metadata["y-size"]
                if self.cols < 3 or self.rows < 3:
                    raise Exception("The friction raster must have at least 3x3 pixels.")
            if self.proceed():
                self.rasterize_entities(metadata)
                if not s["ent_is_vector"]:
                    ent_metadata = self.get_raster_metadata(s["ent_file"])
                    if not (metadata == ent_metadata):
                        raise Exception("Entities and friction file must have the same projection, coordinates, extension and resolution!")
            if self.proceed():
                self.prog("Creating the empty raster of costs...")
                self.create_ds(s["cost_file"], metadata, 1, float, self.float_nodata)
                self.prog("Raster of costs created.")
            if self.proceed() and s["perform_allocation"]:
                self.prog("Creating the empty raster of allocations...")
                self.create_ds(s["allocation_file"], metadata, 1, float, self.float_nodata)
                self.prog("Raster of allocations created.")
            if self.proceed():
                self.write_starting_points()
            if self.proceed():
                if s["use_ram"]:
                    self.execute_iterations_in_memory()
                else:
                    self.execute_iterations()
            if s["perform_allocation"]:
                return (s["cost_file"], s["allocation_file"])
            else:
                return s["cost_file"]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            message = "Error: {0}\nType: {1}\nFile: {2}\nLine: {3}\n\n{4}".format(str(e), str(exc_type), fname, str(exc_tb.tb_lineno), traceback.format_exc())
            raise Exception(message)
        finally:
            self.cleanup()

    def get_raster_metadata(self, rst_file):
        self.prog("Getting friction file metadata...")
        ds = gdal.Open(rst_file, GA_ReadOnly)
        if ds:
            geo_t = ds.GetGeoTransform()
            if geo_t:
                mt = {
                    "proj": ds.GetProjection(),
                    "x-size": ds.RasterXSize,
                    "y-size": ds.RasterYSize,
                    "top-left-x": geo_t[0],
                    "w-e-res": geo_t[1],
                    "rot1": geo_t[2],
                    "top-left-y": geo_t[3],
                    "rot2": geo_t[4],
                    "n-s-res": geo_t[5],
                    "proj_wkt": ds.GetProjectionRef()
                }
                ds = None
                return mt
            self.prog("Metadata taken.")
        # If you are here, no metadata was taken.
        ds = None
        raise Exception("Unable to read metadata from the friction file.")

    def rasterize_entities(self, metadata):
        allocate = self.settings["perform_allocation"]
        ent_multipliers = self.settings["ent_multipliers"]
        if not self.settings["ent_is_vector"]:
            ent_file = self.settings["ent_source"]
            if allocate:
                ent_band = int(self.settings["id_field"])
            else:
                ent_band = 1
        else:
            ent_file = self.get_free_file_name("tif")
            ent_band = 1
            if allocate:
                field_param = self.settings["id_field"]
            else:
                field_param = None
            self.prog("Rasterizing entities Ids...")
            self.rasterize_attribute(metadata, ent_file, field_param)
            self.prog("Rasterization completed.")
        if ent_multipliers and ent_multipliers != "[]":
            if not self.settings["ent_is_vector"]:
                self.prog("Copying rank file...")
                # TODO: Ottiene un nome di file libero con la stessa estensione del precedente. Infatti su rank bisogna scrivere!!!!!
                rank_file = ent_file
                rank_band = int(self.settings["ent_multipliers"])
            else:
                rank_file = self.get_free_file_name("tif")
                rank_band = 1
                self.prog("Rasterizing ranks...")
                self.rasterize_attribute(metadata, rank_file, self.settings["ent_multipliers"], float)
                self.prog("Rasterization completed.")
        else:
            rank_file = None
            rank_band = None
        self.settings["ent_file"] = ent_file
        self.settings["ent_band"] = ent_band
        self.settings["rank_file"] = rank_file
        self.settings["rank_band"] = rank_band

    def rasterize_attribute(self, metadata, file_name, field_name=None, dtype=int):
        driver = gdal.GetDriverByName('GTiff')
        dst_ds = self.open_new_ds(file_name, metadata, 1, dtype)
        if dst_ds:
            self.temp_filenames.append(file_name)
        source_ds = ogr.Open(self.settings["ent_source"])
        source_layer = source_ds.GetLayer(0)
        if dst_ds and source_ds:
            opts = []
            if self.settings["all_touched"]:
                opts.append('ALL_TOUCHED')
            if field_name:
                opts.append('ATTRIBUTE=' + field_name)
            gdal.RasterizeLayer(dst_ds, [1], source_layer, options=opts)
            source_ds = None
            dst_ds = None
        else:
            dst_ds = None
            source_ds = None
            raise Exception("Unable to read the entities vector file or the temporary raster file.\nTry with another format.")

    def write_starting_points(self):
        # Writes starting points on cost and (if required) allocation rasters.
        # Starting points have cost = 0 and alloc = self.settings["id_field"].
        self.prog("Writing starting points...")
        allocate = self.settings["perform_allocation"]
        entities_file = self.settings["ent_file"]
        entities_band_num = self.settings["ent_band"]
        ent_ds = gdal.Open(entities_file, GA_ReadOnly)
        if not ent_ds:
            raise Exception("Unable to read the raster entities file or the rasterized vector file.")
        ent_band = ent_ds.GetRasterBand(entities_band_num)
        cost_ds = gdal.Open(self.settings["cost_file"], GA_Update)
        if not cost_ds:
            raise Exception("Unable to open the raster of costs.")
        cost_band = cost_ds.GetRasterBand(1)
        if allocate:
            alloc_ds = gdal.Open(self.settings["allocation_file"], GA_Update)
            if not alloc_ds:
                raise Exception("Unable to open the raster of allocations.")
            alloc_band = alloc_ds.GetRasterBand(1)
        cols = self.cols
        rows = self.rows
        # Initialize the array of the active pixels.
        self.active_pixels = numpy.empty((rows, cols), bool)
        for y in range(rows):
            curr_row = ent_band.ReadAsArray(0, y, cols, 1)
            if allocate:
                alloc_band.WriteArray(curr_row, 0, y)
            np_arr = numpy.array(curr_row)
            np_float = np_arr.astype(numpy.float32)
            np_float[np_float <= 0.0] = -1.0
            non_empty_cells = np_float > 0.0
            np_float[non_empty_cells] = 0.0
            self.active_pixels[y] = non_empty_cells[0]
            cost_band.WriteArray(np_float, 0, y)
        ent_ds = None
        cost_ds = None
        if allocate:
            alloc_ds = None
        self.prog("All the starting points were written!")

    def get_3_rows(self, central_row_index):
        # Gets three rows from the friction raster,
        # three rows from the cost raster and, if needed,
        # three rows from the allocation raster
        # and ONE row from the rank raster.
        if central_row_index == 0:
            start_row = 0
            height = 2
        elif central_row_index == self.rows - 1:
            start_row = central_row_index - 1
            height = 2
        else:
            start_row = central_row_index - 1
            height = 3
        friction_rows = self.friction_ds.GetRasterBand(1).ReadAsArray(0, start_row, self.cols, height)
        cost_rows = self.cost_ds.GetRasterBand(1).ReadAsArray(0, start_row, self.cols, height)
        if self.allocation_ds:
            alloc_rows = self.allocation_ds.GetRasterBand(1).ReadAsArray(0, start_row, self.cols, height)
        else:
            alloc_rows = None
        if self.rank_ds:
            rank_rows = self.rank_ds.GetRasterBand(1).ReadAsArray(0, start_row, self.cols, height)
        else:
            rank_rows = None
        return (friction_rows, cost_rows, alloc_rows, rank_rows)

    def save_3_rows(self, central_row_index, cost_array, allocation_array, rank_array):
        if central_row_index == 0:
            start_row = 0
        else:
            start_row = central_row_index - 1
        self.cost_ds.GetRasterBand(1).WriteArray(cost_array, 0, start_row)
        if not (allocation_array == None):
            self.allocation_ds.GetRasterBand(1).WriteArray(allocation_array, 0, start_row)
        if not (rank_array == None):
            self.rank_ds.GetRasterBand(1).WriteArray(rank_array, 0, start_row)

    def calculate_neighbors(self, central_row_index, arrays_tuple):
        # May change pixel values in cost_array and allocation_array and MUST activate changed pixels.
        # Deactivates central pixel. Returns the following values:
        # 1. A bool value that tells if the costo or allocation arrays were modified.
        # 2. the cost array
        # 3. The allocation array (None if the array doesn't exist).
        modified = False
        if central_row_index == 0:
            array_offset = 0
            central_row = 0
            rows = 2
            range_rows = range(0, 2)
        elif central_row_index == self.rows - 1:
            array_offset = central_row_index - 1
            central_row = 1
            rows = 2
            range_rows = range(0, 2)
        else:
            array_offset = central_row_index - 1
            central_row = 1
            rows = 3
            range_rows = range(0, 3)
        friction_rows, cost_rows, alloc_rows, rank_rows = arrays_tuple
        cols = self.cols
        active_pixels = self.active_pixels
        cols_range = range(cols)
        reverse_cols_range = range(cols-1, -1, -1)
        do_it_reverse = False
        while (self.active_pixels[central_row_index].any()):
            if do_it_reverse == False:
                curr_range = cols_range
            else:
                curr_range = reverse_cols_range
            for col in curr_range:
                if active_pixels[central_row_index][col]:
                    # Get current pixel's values.
                    px_friction = friction_rows[central_row][col]
                    if px_friction >= 0:
                        px_cost = cost_rows[central_row][col]
                        if not (alloc_rows == None):
                            px_alloc = alloc_rows[central_row][col]
                        if col == 0:
                            range_cols = range(0, 2)
                        elif col == cols - 1:
                            range_cols = range(col - 1, col + 1)
                        else:
                            range_cols = range(col - 1, col + 2)
                        for nb_r in range_rows:
                            for nb_c in range_cols:
                                # Check if the pixel is the current starting pixel.
                                if not (nb_r == central_row and nb_c == col):
                                    nb_friction = friction_rows[nb_r][nb_c]
                                    # If friction < 0, the pixel is not considered.
                                    if nb_friction >= 0:
                                        nb_prev_cost = cost_rows[nb_r][nb_c]
                                        if (nb_r == central_row or nb_c == col):
                                            # Vertical or horizontal pixel.
                                            if rank_rows == None:
                                                nb_new_cost = px_cost + (px_friction + nb_friction) / 2.0
                                            else:
                                                px_rank = rank_rows[central_row][col]
                                                nb_new_cost = px_cost + (px_friction + nb_friction / px_rank) / 2.0
                                        else:
                                            # Diagonal pixel.
                                            if rank_rows == None:
                                                nb_new_cost = px_cost + 1.414214*(px_friction + nb_friction) / 2.0
                                            else:
                                                px_rank = rank_rows[central_row][col]
                                                nb_new_cost = px_cost + (px_friction + nb_friction / px_rank) / 2.0
                                        if nb_prev_cost < 0 or nb_new_cost < nb_prev_cost:
                                            cost_rows[nb_r][nb_c] = nb_new_cost
                                            if not (alloc_rows == None):
                                                alloc_rows[nb_r][nb_c] = px_alloc
                                            if not (rank_rows == None):
                                                rank_rows[nb_r][nb_c] = px_rank
                                            real_row_index = array_offset + nb_r
                                            active_pixels[real_row_index][nb_c] = True
                                            modified = True
                # Deactivate current pixel!
                active_pixels[central_row_index][col] = False
                # Change scanning direction.
            do_it_reverse = not do_it_reverse
        return modified, cost_rows, alloc_rows, rank_rows

    def execute_iterations(self):
        allocate = self.settings["perform_allocation"]
        rank_file = self.settings["rank_file"]
        self.prog("Calculating costs. Slow but very very VERY accurate: it may take a lot of time!")
        self.cost_ds = gdal.Open(self.settings["cost_file"], GA_Update)
        if allocate:
            self.allocation_ds = gdal.Open(self.settings["allocation_file"], GA_Update)
        self.friction_ds = gdal.Open(self.settings["friction_source"], GA_ReadOnly)
        if rank_file:
            self.rank_ds = gdal.Open(rank_file, GA_Update)
        rows = self.rows
        cols = self.cols
        rows_range = range(rows)
        reverse_rows_range = range(rows-1, -1, -1)
        do_it = True
        # Cycles will alternate the direction of scan.
        do_it_reverse = False
        while do_it:
            # If no new pixels will be activated, don't do another loop.
            do_it = False
            if do_it_reverse == False:
                curr_range = rows_range
            else:
                curr_range = reverse_rows_range
            for row in curr_range:
                # Verify if the row has active pixels:
                if self.active_pixels[row].any():
                    arrays_tuple = self.get_3_rows(row)
                    modified, cost_array, allocation_array, rank_array = self.calculate_neighbors(row, arrays_tuple)
                    self.save_3_rows(row, cost_array, allocation_array, rank_array)
                    if do_it == False and modified == True:
                        do_it = True
            do_it_reverse = not do_it_reverse
        self.cost_ds = None
        self.allocation_ds = None
        self.friction_ds = None
        self.rank_ds = None
        self.prog("Accumulated costs calculated!")

    def load_data_in_memory(self):
        self.prog("Loading data...")
        rows = self.rows
        cols = self.cols
        self.friction_ds = gdal.Open(self.settings["friction_source"], GA_ReadOnly)
        friction_band = self.friction_ds.GetRasterBand(1)
        self.friction_data = friction_band.ReadAsArray(0, 0, cols, rows)
        self.cost_ds = gdal.Open(self.settings["cost_file"], GA_Update)
        cost_band = self.cost_ds.GetRasterBand(1)
        self.cost_data = cost_band.ReadAsArray(0, 0, cols, rows)
        if self.settings["perform_allocation"]:
            self.allocation_ds = gdal.Open(self.settings["allocation_file"], GA_Update)
            alloc_band = self.allocation_ds.GetRasterBand(1)
            self.allocation_data = alloc_band.ReadAsArray(0, 0, cols, rows)
        else:
            self.allocation_ds = None
            self.allocation_data = None
        rank_file = self.settings["rank_file"]
        if rank_file:
            self.rank_ds = gdal.Open(rank_file, GA_Update)
            rank_band = self.rank_ds.GetRasterBand(1)
            self.rank_data = rank_band.ReadAsArray(0, 0, cols, rows)
        else:
            self.rank_ds = None
            self.rank_data = None
        self.prog("Data loaded.")

    def save_in_memory_data(self):
        self.prog("Saving data...")
        self.friction_ds = None
        self.rank_ds = None
        self.cost_ds.GetRasterBand(1).WriteArray(self.cost_data, 0, 0)
        self.cost_ds = None
        if self.settings["perform_allocation"]:
            self.allocation_ds.GetRasterBand(1).WriteArray(self.allocation_data, 0, 0)
            allocation_ds = None
        self.prog("Data correctly saved.")

    def execute_iterations_in_memory(self):
        rows = self.rows
        self.load_data_in_memory()
        self.prog("Calculating costs. Slow but very very VERY accurate: it may take a lot of time!")
        rows_range = range(rows)
        reverse_rows_range = range(rows-1, -1, -1)
        do_it = True
        # Cycles will alternate the direction of scan.
        do_it_reverse = False
        while do_it:
            # If no new pixels will be activated, don't do another loop.
            do_it = False
            if do_it_reverse == False:
                curr_range = rows_range
            else:
                curr_range = reverse_rows_range
            for row in curr_range:
                # Verify if the row has active pixels:
                if self.active_pixels[row].any():
                    modified = self.calculate_neighbors_in_memory(row)
                    if modified == True:
                        do_it = True
            do_it_reverse = not do_it_reverse
        self.prog("Accumulated costs calculated!")
        self.save_in_memory_data()

    def calculate_neighbors_in_memory(self, central_row_index):
        # May change pixel values in cost_array and allocation_array and MUST activate changed pixels.
        # Deactivates central pixel. Returns the following values:
        # 1. A bool value that tells if the costo or allocation arrays were modified.
        modified = False
        rows = self.rows
        cols = self.cols
        friction_data = self.friction_data
        cost_data = self.cost_data
        alloc_data = self.allocation_data
        rank_data = self.rank_data
        if central_row_index == 0:
            # First row
            row_range_start = 0
            row_range_end = 2
        elif central_row_index == self.rows - 1:
            # Last row
            row_range_start = central_row_index - 1
            row_range_end = central_row_index + 1
        else:
            row_range_start = central_row_index - 1
            row_range_end = central_row_index + 2
        range_rows = range(row_range_start, row_range_end)
        cols_range = range(cols)
        reverse_cols_range = range(cols-1, -1, -1)
        do_it_reverse = False
        do_it_again = True
        while (do_it_again):
            if do_it_reverse == False:
                curr_range = cols_range
            else:
                curr_range = reverse_cols_range
            for col in curr_range:
                if self.active_pixels[central_row_index][col]:
                    # Get current pixel's values.
                    px_friction = friction_data[central_row_index][col]
                    if px_friction >= 0:
                        px_cost = cost_data[central_row_index][col]
                        if not (alloc_data == None):
                            px_alloc = alloc_data[central_row_index][col]
                        if col == 0:
                            r_cols = range(0, 2)
                        elif col == cols - 1:
                            r_cols = range(col - 1, col + 1)
                        else:
                            r_cols = range(col - 1, col + 2)
                        for nb_r in range_rows:
                            for nb_c in r_cols:
                                # Check if the pixel is the current starting pixel.
                                if not (nb_r == central_row_index and nb_c == col):
                                    nb_friction = friction_data[nb_r][nb_c]
                                    # If friction < 0, the pixel is not considered.
                                    if nb_friction >= 0:
                                        nb_prev_cost = cost_data[nb_r][nb_c]
                                        if (nb_r == central_row_index or nb_c == col):
                                            # Vertical or horizontal pixel.
                                            if rank_data == None:
                                                nb_new_cost = px_cost + (px_friction + nb_friction) / 2.0
                                            else:
                                                px_rank = rank_data[central_row_index][col]
                                                nb_new_cost = px_cost + (px_friction + nb_friction / px_rank) / 2.0
                                        else:
                                            # Diagonal pixel.
                                            if rank_data == None:
                                                nb_new_cost = px_cost + 1.414214*(px_friction + nb_friction) / 2.0
                                            else:
                                                px_rank = rank_data[central_row_index][col]
                                                nb_new_cost = px_cost + 1.414214*(px_friction + nb_friction / px_rank) / 2.0
                                        if nb_prev_cost < 0 or nb_new_cost < nb_prev_cost:
                                            cost_data[nb_r][nb_c] = nb_new_cost
                                            if not (alloc_data == None):
                                                alloc_data[nb_r][nb_c] = px_alloc
                                            if not (rank_data == None):
                                                rank_data[nb_r][nb_c] = px_rank
                                            self.active_pixels[nb_r][nb_c] = True
                                            modified = True
                    # Deactivate current pixel!
                    self.active_pixels[central_row_index][col] = False
                    # Change scanning direction.
                do_it_reverse = not do_it_reverse
                do_it_again = self.active_pixels[central_row_index].any()
        return modified

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
from gdalconst import *
from numpy import *
import time

iter_num = 0



def wcost(source_rst, friction_rst, cost_rst):
    start_time = time.time()
    gdal.AllRegister()
    source_ds = gdal.Open(source_rst, GA_ReadOnly)
    if source_ds is None:
        print "Impossibile caricare il file", source_rst
        return
    fri_ds = gdal.Open(friction_rst, GA_ReadOnly)
    if fri_ds is None:
        print "Impossibile caricare il file", fri_rst
        return
    cols = source_ds.RasterXSize
    rows = source_ds.RasterYSize
    print "XSize: ", cols, "YSize:", rows
    transform = source_ds.GetGeoTransform()
    projection = source_ds.GetProjectionRef()
    cost_ds = create_cost_rst(cost_rst, cols, rows, transform, projection)
    set_starting_points(source_ds, cost_ds)
    active_pixels = first_iteration(source_ds, fri_ds, cost_ds)
    while len(active_pixels) > 0:
        active_pixels = n_iteration(source_ds, fri_ds, cost_ds, active_pixels)
    source_ds = None
    fri_ds = None
    cost_ds = None
    end_time = time.time()
    print "Time elapsed: ", end_time - start_time

def create_cost_rst(file_name, cols, rows, transform, projection):
    driver = gdal.GetDriverByName('GTiff')
    cost_ds = driver.Create(file_name, cols, rows, 2, gdal.GDT_Float32)
    cost_ds.SetGeoTransform(transform)
    cost_ds.SetProjection(projection)
    # Sets all values to -1:
    rst_data = zeros((rows, cols), dtype=float)
    cost_ds.GetRasterBand(1).WriteArray(rst_data)
    rst_data = empty((rows, cols), dtype=float)
    rst_data.fill(-1.0)
    cost_ds.GetRasterBand(2).WriteArray(rst_data)
    return cost_ds

def get_pixel_neighbors(ds, x, y, bands_num):
    # Per ogni vicino, restituisci una tupla con x, y, b1, b2 e on_diagonal
    max_x = ds.RasterXSize - 1
    max_y = ds.RasterYSize - 1
    x_size = 3
    y_size = 3
    if x == max_x:
        x_size -= 1
    if x == 0:
        x_offset = x
        x_size -= 1
    else:
        x_offset = x - 1
    if y == max_y:
        y_size -= 1
    if y == 0:
        y_offset = y
        y_size -= 1
    else:
        y_offset = y - 1
    bands_data = []
    for bct in range(1, bands_num + 1):
        the_band = ds.GetRasterBand(bct)
        bands_data.append(the_band.ReadAsArray(x_offset, y_offset, x_size, y_size))
    returned_pixels = []
    for ny in range(y_size):
        for nx in range(x_size):
            vals = []
            for bc in range(bands_num):
                vals.append(bands_data[bc][ny, nx])
            real_x = x_offset + nx
            real_y = y_offset + ny
            if real_x == x or real_y == y:
                is_diagonal = False
            else:
                is_diagonal = True
            returned_pixels.append([real_x, real_y, vals, is_diagonal])
    return returned_pixels

def save_pixel(ds, pixel):
    for i in range(len(pixel[2])):
        band = ds.GetRasterBand(i + 1)
        curr_val = pixel[2][i]
        band.WriteArray(array([[curr_val]]), pixel[0], pixel[1])
    
def compute_neigbors_cost(cost_ds, friction_ds, x, y):
    cost_pixels = get_pixel_neighbors(cost_ds, x, y, 2)
    friction_pixels = get_pixel_neighbors(friction_ds, x, y, 1)
    # Get starting point friction value:
    for pindex in range(len(friction_pixels)):
        f_pixel = friction_pixels[pindex]
        c_pixel = cost_pixels[pindex]
        # Find the starting point and get friction, cost and id
        if f_pixel[0] == x and f_pixel[1] == y:
            origin_id = c_pixel[2][1]
            origin_cost = c_pixel[2][0]
            origin_friction = f_pixel[2][0]
            break
    # Compute cost for each pixel:
    activated_pixels = []
    for c_pixel_index in range(len(cost_pixels)):
        c_pixel = cost_pixels[c_pixel_index]
        if not (c_pixel[0] == x and c_pixel[1] == y):
            curr_cost = c_pixel[2][0]
            px_friction_val = friction_pixels[c_pixel_index][2][0]
            # if is diagonal
            if c_pixel[3]:
                new_cost = origin_cost + 1.414214 * (origin_friction + px_friction_val) / 2
            else:
                new_cost = origin_cost + (origin_friction + px_friction_val) / 2
            # Quando aggiorni il pixel?
            # Quando il costo precedente è < 0 (cioè no data) o quando è maggiore del nuovo costo
            if curr_cost < 0 or curr_cost > new_cost:
                activated_pixels.append((c_pixel[0], c_pixel[1], [new_cost, origin_id]))
    return activated_pixels

def set_starting_points(source_ds, cost_ds):
    cols = source_ds.RasterXSize
    rows = source_ds.RasterYSize
    src_b1 = source_ds.GetRasterBand(1)
    cost_b1 = cost_ds.GetRasterBand(1)
    cost_b2 = cost_ds.GetRasterBand(2)
    r_rows = range(rows)
    for i in r_rows:
        output_b2 = src_b1.ReadAsArray(0, i, cols, 1)
        output_b1 = output_b2.copy()
        b10 = output_b1[0]
        for z in range(len(b10)):           
            if b10[z] == 0:
                output_b1[0, z] = -1.0
            else:
                output_b1[0, z] = 0
        cost_b2.WriteArray(output_b2, 0, i)
        cost_b1.WriteArray(output_b1, 0, i)

def first_iteration(source_ds, friction_ds, cost_ds):
    global iter_num
    iter_num += 1
    #print ""
    #print "Iterazione #", iter_num
    #print "Punti attivati iniziali: 0"
    cols = source_ds.RasterXSize
    rows = source_ds.RasterYSize
    src_b1 = source_ds.GetRasterBand(1)
    r_rows = range(rows)
    candidate_pixel = None
    activated_pixels = []
    for y in r_rows:
        curr_row = src_b1.ReadAsArray(0, y, cols, 1)[0]
        for x in range(cols):           
            if not curr_row[x] == 0:
                new_pixels = compute_neigbors_cost(cost_ds, friction_ds, x, y)
                for np in new_pixels:
                    # Il nuovo pixel potrebbe essere già presente in lista, con un costo maggiore o minore.
                    # Se quello in lista ha un costo maggiore, va sostituito.
                    px_found = False
                    for apl in range(len(activated_pixels)):
                         ap = activated_pixels[apl]
                         if np[0] == ap[0] and np[1] == ap[1]:
                             px_found = True
                             if np[2][0] < ap[2][0]:
                                 activated_pixels[apl] = np
                                 save_pixel(cost_ds, np)
                    if not px_found:
                        activated_pixels.append(np)
                        save_pixel(cost_ds, np)
    #print "Punti attivati finali:", len(activated_pixels)
    return activated_pixels

def n_iteration(source_ds, friction_ds, cost_ds, activated_pixels):
    global iter_num
    iter_num += 1
    #print ""
    #print "Iterazione #", iter_num
    #print "Punti attivati passati:", len(activated_pixels)
    ord_px = sorted(activated_pixels, key=lambda x: x[2][0])
    # Trova i punti da cui calcolare i vicini.
    # Si tratta del primo punto, che ha il costo più basso, e
    # dei successivi finché hanno lo stesso costo del primo.
    first_px_cost = ord_px[0][2][0]
    indx = 1
    list_len = len(ord_px)
    while indx < list_len and ord_px[indx][2][0] == first_px_cost:
        indx += 1
    origins = ord_px[:indx]
    #print "Punti di origine considerati: ", len(origins)
    # Elimina altrettanti valori da ord_px
    activated_pixels = ord_px[indx:]
    created_n = 0
    edited_n = 0
    #print "Lunghezza activated_pixels prima del ciclo:", len(activated_pixels)
    #print "Variabile nuovi punti creati prima del ciclo:", created_n
    #print "Variabile nuovi punti modificati prima del ciclo:", edited_n
    for or_px in origins:
        new_pixels = compute_neigbors_cost(cost_ds, friction_ds, or_px[0], or_px[1])
        #print "Punti trovati dal pixel di origine corrente: ", len(new_pixels)
        for np in new_pixels:
            # Verifica che non si tratti del punto di origne.
            if not (or_px[0] == np[0] and or_px[1] == np[1]):
                # Il nuovo pixel potrebbe essere già presente in lista, con un costo maggiore o minore.
                # Se quello in lista ha un costo maggiore, va sostituito.
                px_found = False
                for apl in range(len(activated_pixels)):
                    ap = activated_pixels[apl]
                    if np[0] == ap[0] and np[1] == ap[1]:
                        # Il punto è già in lista, va sostituito"
                        px_found = True
                        if np[2][0] < ap[2][0]:
                            activated_pixels[apl] = np
                            save_pixel(cost_ds, np)
                            edited_n += 1
                if not px_found:
                    # il punto no era in lista.
                    activated_pixels.append(np) 
                    save_pixel(cost_ds, np)
                    created_n += 1
    #print "Nuovi punti creati:", created_n
    #print "Punti modificati:", edited_n
    #print "Tot. punti attivati a fine ciclo:", len(activated_pixels)
    return activated_pixels

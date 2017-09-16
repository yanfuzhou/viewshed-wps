import os
import sys
import math
import time
import logging
import subprocess
import numpy as np
from osgeo import osr
from osgeo import gdal
from datetime import datetime
from bresenham import bresenham
from pyproj import Proj, transform
from mvc.controller.schema.ogc.epsg import code
from setting import WCS_VERSION, DEM_10METERS, DEM_30METERS

log = logging.getLogger(__name__)


def raster_viewshed(observer, observer_height, target_offset, radius, swath, earth_curvature, refraction, k, use_swath,
                    earth_radius, esri, geotiff, tmpdir, basename):
    start_time = time.time()
    log.info('Started at: %s' % str(datetime.now()))
    viewshed_vector = generating_viewshed(observer, observer_height, target_offset, radius, swath, earth_curvature,
                                          refraction, k, use_swath, earth_radius, esri, geotiff, tmpdir, basename)
    log.info("Finished at: %ss" % round((time.time() - start_time), 3))
    return viewshed_vector


def generating_viewshed(observer, observer_height, target_offset, radius, swath, earth_curvature, refraction, k,
                        use_swath, earth_radius, esri, geotiff, tmpdir, basename):
    viewshed_raster = os.path.join(tmpdir, basename + 'vs')
    viewshed_vector = os.path.join(tmpdir, basename + 'jn')
    geotransform, matrix = read_image(geotiff)
    viewpoint = transform_coords(geotransform, observer[0], observer[1])
    viewlines = calculate_viewlines(geotransform, observer, radius, use_swath, swath, viewpoint)
    sectors = extract_masks(viewlines, viewpoint)
    sectors = calculate_viewshed(sectors, viewpoint, matrix, geotransform, earth_radius, observer, observer_height,
                                 earth_curvature, target_offset, refraction, k, esri)
    mask = aggregate_masks(sectors)
    array = generate_mask(mask, get_zeros(matrix.shape))
    array2raster(viewshed_raster, (geotransform[0], geotransform[3]), geotransform[1], geotransform[5], array)
    polygonize_raster(viewshed_raster, viewshed_vector, observer, observer_height)
    os.remove(viewshed_raster)
    return viewshed_vector


def polygonize_raster(viewshed_raster, viewshed_vector, observer, observer_height):
    cmd = ['gdal_polygonize.py', '-mask', viewshed_raster, viewshed_raster, '-f', 'GEOJSON', viewshed_vector]
    p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode != 0:
        log.info(sys.stderr, 'ERROR: %s' % err)
        sys.exit(-1)
    log.info('OBSERVER: Viewpoint=(%s,%s), height=%sm' % (observer[0], observer[1], observer_height))
    log.info('VIEWSHED: %s' % viewshed_vector)


def array2raster(new_raster_fn, raster_origin, pixel_width, pixel_height, array):
    if os.path.exists(new_raster_fn):
        os.remove(new_raster_fn)
    cols = array.shape[1]
    rows = array.shape[0]
    origin_x = raster_origin[0]
    origin_y = raster_origin[1]
    driver = gdal.GetDriverByName('GTiff')
    out_raster = driver.Create(new_raster_fn, cols, rows, 1, gdal.GDT_Byte)
    out_raster.SetGeoTransform((origin_x, pixel_width, 0, origin_y, 0, pixel_height))
    outband = out_raster.GetRasterBand(1)
    outband.WriteArray(array)
    out_raster_srs = osr.SpatialReference()
    out_raster_srs.ImportFromEPSG(int(code[1]))
    out_raster.SetProjection(out_raster_srs.ExportToWkt())
    outband.FlushCache()


def generate_mask(indices, zeros):
    for i in indices:
        zeros[i[1]][i[0]] = 1.0
    return zeros


def aggregate_masks(sectors):
    mask = set()
    for sector in sectors:
        for p in sector:
            mask.add(p)
    return list(mask)


def line_of_sight(line, array, vp, ha, empty, pxw, pxh, target_offset, earth_curvature, observer_height, earth_radius,
                  refraction, k, esri):
    half = list()
    half.append(line[0])
    d0 = get_distance(line[0], vp)
    max_slope = get_slope(get_height(line[0], array) - get_earth_curvature(line[0], pxw, pxh, vp, earth_curvature,
                                                                           observer_height, earth_radius, esri) +
                          get_refraction(d0, refraction, k, earth_radius) + target_offset, ha, d0)
    empty[line[0][1]][line[0][0]] = max_slope
    for p in line[1:]:
        if np.isnan(empty[p[1]][p[0]]):
            d = get_distance(p, vp)
            slope = get_slope(get_height(p, array) - get_earth_curvature(p, pxw, pxh, vp, earth_curvature,
                                                                         observer_height, earth_radius, esri) +
                              get_refraction(d, refraction, k, earth_radius) + target_offset, ha, d)
            empty[p[1]][p[0]] = slope
        else:
            slope = empty[p[1]][p[0]]
        if slope >= max_slope:
            max_slope = slope
            half.append(p)
    return half


def get_distance(p1, p2):
    return math.sqrt(pow((p2[0] - p1[0]), 2) + pow((p2[1] - p1[1]), 2))


def get_earth_curvature(p, pxw, pxh, vp, earth_curvature, observer_height, earth_radius, esri):
    h1 = 0.0
    if earth_curvature:
        d0 = math.sqrt(pow((p[0] - vp[0]) * pxw, 2) + pow((p[1] - vp[1]) * pxh, 2))
        if esri:
            h1 = pow(d0, 2) / (2 * earth_radius)
        else:
            d1 = math.sqrt(pow(observer_height, 2) + 2 * earth_radius * observer_height)
            h1 = math.sqrt(pow((d0 - d1), 2) + pow(earth_radius, 2)) - earth_radius
    return h1


def get_slope(hp, ha, d):
    return (hp - ha) / d


def get_refraction(d, refraction, k, earth_radius):
    h = 0.0
    if refraction:
        h = (k * pow(d, 2)) / (2 * earth_radius)
    return h


def interpolate_coords(geotransform, e, _p, p1, p2):
    p = pixel_offset2coord(geotransform, _p[0], _p[1])
    e_x, e_y = transform(p1, p2, x=e[0], y=e[1])
    p_x, p_y = transform(p1, p2, x=p[0], y=p[1])
    nx = (p_y + (e_x / e_y) * p_x) / (e_y / e_x + e_x / e_y)
    ny = (e_y / e_x) * nx
    x, y = transform(p2, p1, x=nx, y=ny)
    return x, y


def get_empty(a):
    a[a == 0] = np.NaN
    return a


def get_zeros(shape):
    return np.zeros(shape)


def get_bilinear_height(geotransform, pp, array, pt):
    n = get_neighbors(geotransform, pp, array)
    h = get_height(pp, array)
    for n_p in n:
        if pt == (n_p[0], n_p[1]):
            h = n_p[2]
    if pt[0] > n[0][0] and pt[1] > n[0][1]:
        h = bilinear_interpolation(pt, n[0][0], n[0][1], n[0][2], n[2][0], n[2][1], n[2][2], n[3][2], n[1][2])
    elif pt[0] < n[0][0] and pt[1] > n[0][1]:
        h = bilinear_interpolation(pt, n[5][0], n[5][1], n[5][2], n[3][0], n[3][1], n[3][2], n[4][2], n[0][2])
    elif pt[0] < n[0][0] and pt[1] < n[0][1]:
        h = bilinear_interpolation(pt, n[6][0], n[6][1], n[6][2], n[0][0], n[0][1], n[0][2], n[5][2], n[7][2])
    elif pt[0] > n[0][0] and pt[1] < n[0][1]:
        h = bilinear_interpolation(pt, n[7][0], n[7][1], n[7][2], n[1][0], n[1][1], n[1][2], n[0][2], n[8][2])
    else:
        pass
    return h


def bilinear_interpolation(p, x1, y1, q11, x2, y2, q22, q12, q21):
    r1 = (q21 - q11) * ((p[0] - x1) / (x2 - x1)) + q11
    r2 = (q22 - q12) * ((p[0] - x1) / (x2 - x1)) + q12
    h = (r2 - r1) * ((p[1] - y1) / (y2 - y1)) + r1
    return h


def get_height(p, array):
    return array[p[1]][p[0]]


def get_neighbors(geotransform, vp, array):
    neighbors = list()
    x0, y0 = pixel_offset2coord(geotransform, vp[0], vp[1])
    z0 = array[vp[1]][vp[0]]
    p0 = (x0, y0, z0)
    x1, y1 = pixel_offset2coord(geotransform, vp[0] + 1, vp[1])
    z1 = array[vp[1]][vp[0] + 1]
    p1 = (x1, y1, z1)
    x2, y2 = pixel_offset2coord(geotransform, vp[0] + 1, vp[1] + 1)
    z2 = array[vp[1] + 1][vp[0] + 1]
    p2 = (x2, y2, z2)
    x3, y3 = pixel_offset2coord(geotransform, vp[0], vp[1] + 1)
    z3 = array[vp[1] + 1][vp[0]]
    p3 = (x3, y3, z3)
    x4, y4 = pixel_offset2coord(geotransform, vp[0] - 1, vp[1] + 1)
    z4 = array[vp[1] + 1][vp[0] - 1]
    p4 = (x4, y4, z4)
    x5, y5 = pixel_offset2coord(geotransform, vp[0] - 1, vp[1])
    z5 = array[vp[1]][vp[0] - 1]
    p5 = (x5, y5, z5)
    x6, y6 = pixel_offset2coord(geotransform, vp[0] - 1, vp[1] - 1)
    z6 = array[vp[1] - 1][vp[0] - 1]
    p6 = (x6, y6, z6)
    x7, y7 = pixel_offset2coord(geotransform, vp[0], vp[1] - 1)
    z7 = array[vp[1] - 1][vp[0]]
    p7 = (x7, y7, z7)
    x8, y8 = pixel_offset2coord(geotransform, vp[0] + 1, vp[1] - 1)
    z8 = array[vp[1] - 1][vp[0] + 1]
    p8 = (x8, y8, z8)
    neighbors.append(p0)
    neighbors.append(p1)
    neighbors.append(p2)
    neighbors.append(p3)
    neighbors.append(p4)
    neighbors.append(p5)
    neighbors.append(p6)
    neighbors.append(p7)
    neighbors.append(p8)
    return neighbors


def pixel_offset2coord(geotransform, x_offset, y_offset):
    origin_x = geotransform[0]
    origin_y = geotransform[3]
    pixel_width = geotransform[1]
    pixel_height = geotransform[5]
    coord_x = origin_x + pixel_width * x_offset
    coord_y = origin_y + pixel_height * y_offset
    return coord_x, coord_y


def calculate_viewshed(sectors, viewpoint, array, geotransform, earth_radius, observer, observer_height,
                       earth_curvature, target_offset, refraction, k, esri):
    pxw = (math.pi * abs(geotransform[1]) * earth_radius) / 180.0
    pxh = (math.pi * abs(geotransform[5]) * earth_radius) / 180.0
    ha = get_bilinear_height(geotransform, viewpoint, array, observer) + observer_height
    empty = get_empty(get_zeros(array.shape))
    t_los = list()
    for sector in sectors:
        los = line_of_sight(sector, array, viewpoint, ha, empty, pxw, pxh, target_offset, earth_curvature,
                            observer_height, earth_radius, refraction, k, esri)
        los.append(viewpoint)
        t_los.append(sorted(los))
    return t_los


def extract_masks(lines, viewpoint):
    sectors = list()
    for l in lines:
        sector = list(bresenham(l[0], l[1], l[2], l[3]))
        sector.remove(viewpoint)
        sectors.append(sector)
    return sectors


def get_aeqd(lon, lat):
    return Proj(proj='aeqd', ellps='WGS84', datum='WGS84', lat_0=lat, lon_0=lon, units='m', preserve_units=True)


def calculate_viewlines(geotransform, observer, radius, use_swath, swath, vp):
    p1 = Proj(init='epsg:' + code[1])
    p2 = get_aeqd(observer[0], observer[1])
    lines = list()
    if use_swath:
        theta = 0.0
        while theta < math.degrees(math.pi) - 1.0:
            left = math.radians(theta) + (math.pi / 2)
            right = math.radians(theta) - (math.pi / 2)
            l_x, l_y = transform(p2, p1, x=radius * math.cos(left), y=radius * math.sin(left))
            r_x, r_y = transform(p2, p1, x=radius * math.cos(right), y=radius * math.sin(right))
            l_u, l_v = transform_coords(geotransform, l_x, l_y)
            r_u, r_v = transform_coords(geotransform, r_x, r_y)
            lines.append((vp[0], vp[1], l_u, l_v))
            lines.append((vp[0], vp[1], r_u, r_v))
            theta += swath
    else:
        f = 1 - radius
        ddf_x = 1
        ddf_y = -2 * radius
        x = 0
        y = radius
        u1, v1 = transform(p2, p1, x=0.0, y=radius)
        u2, v2 = transform(p2, p1, x=0.0, y=-radius)
        u3, v3 = transform(p2, p1, x=radius, y=0)
        u4, v4 = transform(p2, p1, x=-radius, y=0)
        _u1, _v1 = transform_coords(geotransform, u1, v1)
        _u2, _v2 = transform_coords(geotransform, u2, v2)
        _u3, _v3 = transform_coords(geotransform, u3, v3)
        _u4, _v4 = transform_coords(geotransform, u4, v4)
        lines.append((vp[0], vp[1], _u1, _v1))
        lines.append((vp[0], vp[1], _u2, _v2))
        lines.append((vp[0], vp[1], _u3, _v3))
        lines.append((vp[0], vp[1], _u4, _v4))
        while x < y:
            if f >= 0:
                y -= 1
                ddf_y += 2
                f += ddf_y
            x += 1
            ddf_x += 2
            f += ddf_x
            a1, b1 = transform(p2, p1, x=x, y=y)
            a2, b2 = transform(p2, p1, x=-x, y=y)
            a3, b3 = transform(p2, p1, x=x, y=-y)
            a4, b4 = transform(p2, p1, x=-x, y=-y)
            a5, b5 = transform(p2, p1, x=y, y=x)
            a6, b6 = transform(p2, p1, x=-y, y=x)
            a7, b7 = transform(p2, p1, x=y, y=-x)
            a8, b8 = transform(p2, p1, x=-y, y=-x)
            _a1, _b1 = transform_coords(geotransform, a1, b1)
            _a2, _b2 = transform_coords(geotransform, a2, b2)
            _a3, _b3 = transform_coords(geotransform, a3, b3)
            _a4, _b4 = transform_coords(geotransform, a4, b4)
            _a5, _b5 = transform_coords(geotransform, a5, b5)
            _a6, _b6 = transform_coords(geotransform, a6, b6)
            _a7, _b7 = transform_coords(geotransform, a7, b7)
            _a8, _b8 = transform_coords(geotransform, a8, b8)
            lines.append((vp[0], vp[1], _a1, _b1))
            lines.append((vp[0], vp[1], _a2, _b2))
            lines.append((vp[0], vp[1], _a3, _b3))
            lines.append((vp[0], vp[1], _a4, _b4))
            lines.append((vp[0], vp[1], _a5, _b5))
            lines.append((vp[0], vp[1], _a6, _b6))
            lines.append((vp[0], vp[1], _a7, _b7))
            lines.append((vp[0], vp[1], _a8, _b8))
    return lines


def transform_coords(geotransform, longitude, latitude):
    return int(round(((longitude - geotransform[0]) / abs(geotransform[1])), 0)), \
           int(round(((geotransform[3] - latitude) / abs(geotransform[5])), 0))
    
    
def read_image(geotiff):
    try:
        raster = gdal.Open(geotiff)
        geotransform = raster.GetGeoTransform()
        log.info("[ METADATA ] =  x_min=%s, pixel_width=%s, y_max=%s, pixel_height=%s" % (geotransform[0],
                                                                                          geotransform[1],
                                                                                          geotransform[3],
                                                                                          geotransform[5]))
        max_distance = math.ceil(math.sqrt(2 * geotransform[1] * geotransform[1]))
        log.info("[ MAX DISTANCE ] = %s", max_distance)
        log.info("[ RASTER BAND COUNT ]: %s", raster.RasterCount)
        for band in range(raster.RasterCount):
            band += 1
            log.info("[ GETTING BAND ]: %s", band)
            srcband = raster.GetRasterBand(band)
            if srcband is None:
                log.info("ERROR: can't get band")
                break
            stats = srcband.GetStatistics(True, True)
            if stats is None:
                log.info("ERROR: can't get statistics")
                break
            matrix = srcband.ReadAsArray()
            log.info("[ DEMENSION ] Rows=%s, Columns=%s", matrix.shape[0], matrix.shape[1])
            log.info("[ STATS ] =  Minimum=%s, Maximum=%s, Mean=%s, StdDev=%s" % (stats[0],
                                                                                  stats[1],
                                                                                  stats[2],
                                                                                  stats[3]))
            log.info("[ NO DATA VALUE ] = %s", srcband.GetNoDataValue())
            log.info("[ SCALE ] = %s", srcband.GetScale())
            log.info("[ UNIT TYPE ] = %s", srcband.GetUnitType())
            ctable = srcband.GetColorTable()
            if ctable is None:
                log.info('No ColorTable found')
            else:
                log.info("[ COLOR TABLE COUNT ] = ", ctable.GetCount())
                for i in range(0, ctable.GetCount()):
                    entry = ctable.GetColorEntry(i)
                    if not entry:
                        continue
                    log.info("[ COLOR ENTRY RGB ] = ", ctable.GetColorEntryAsRGB(i, entry))
            return geotransform, matrix
    except RuntimeError, e:
        log.info('Unable to open INPUT.tif')
        log.info(e)
        sys.exit(1)


def viewshed_payload(min_x, min_y, max_x, max_y, resolution):
    layer = DEM_30METERS
    if resolution == 10:
        layer = DEM_10METERS
    querystring = {
        "service": "WCS",
        "version": WCS_VERSION,
        "request": "GetCoverage",
        "CoverageId": layer.replace(':', '__'),
        "subset": ["Long(" + str(min_x) + "," + str(max_x) + ")", "Lat(" + str(min_y) + "," + str(max_y) + ")"],
        "Format": "image/tiff"
    }
    return querystring

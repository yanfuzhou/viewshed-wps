import os
import json
import uuid
import shutil
import logging
import requests
import tempfile
from setting import GEOSERVER_URL
from pyproj import Proj, transform
from mvc.controller.schema.ogc.epsg import code
from mvc.modeller.properties import PROP_DEFAULT
from mvc.controller.schema.ogc.epsg import WGS84
from mvc.modeller.algorithm import viewshed_payload, raster_viewshed, get_aeqd

log = logging.getLogger(__name__)


class ServiceRegister(object):
    def __init__(self):
        self.services = json.loads(str('['
                                       '{"service": "viewshed", "projection": "' + WGS84 + '"}'
                                       ']'))


class ViewShed(object):
    prop_defaults = PROP_DEFAULT

    def __init__(self, x, y, **kwargs):
        self.x = x
        self.y = y
        self.distance = None
        self.height = None
        self.offset = None
        self.swath = None
        self.curvature = None
        self.refraction = None
        self.k = None
        self.use_swath = None
        self.earth_radius = None
        self.resolution = None
        self.esri = None
        for prop, default in ViewShed.prop_defaults.items():
            setattr(self, prop, kwargs.get(prop, default))

    def analysis(self):
        p1 = Proj(init='epsg:' + code[1])
        p2 = get_aeqd(self.x, self.y)
        buffer_distance = self.distance * 1.1
        min_x, min_y = transform(p2, p1, x=0.0 - buffer_distance, y=0.0 - buffer_distance)
        max_x, max_y = transform(p2, p1, x=0.0 + buffer_distance, y=0.0 + buffer_distance)
        querystring = viewshed_payload(min_x, min_y, max_x, max_y, self.resolution)
        response = requests.get(url=GEOSERVER_URL, stream=True, params=querystring)
        if response.status_code is 200:
            tmpdir = tempfile.gettempdir()
            basename = str(uuid.uuid4())
            rasterfile = os.path.join(tmpdir, basename)
            with open(rasterfile, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            vectorfile = raster_viewshed(observer=(self.x, self.y), observer_height=self.height,
                                         target_offset=self.offset, radius=self.distance, swath=self.swath,
                                         earth_curvature=self.curvature, refraction=self.refraction, k=self.k,
                                         use_swath=self.use_swath, earth_radius=self.earth_radius, esri=self.esri,
                                         geotiff=rasterfile, tmpdir=tmpdir, basename=basename)
            with open(vectorfile, 'r') as data:
                result = json.loads(data.read())
            data.close()
            os.remove(rasterfile)
            os.remove(vectorfile)
            return result

import os

# GeoServer settings
DEM_30METERS = 'demo:srtm1v3elevation'
DEM_10METERS = 'demo:ned13elevation'
WCS_VERSION = '2.0.1'
GEOSERVER_HOST = None
if os.uname()[0] == 'Darwin':
    GEOSERVER_HOST = 'localhost'
    GEOSERVER_URL = 'http://' + GEOSERVER_HOST + '/geoserver/wcs'
if os.uname()[0] == 'Linux':
    GEOSERVER_HOST = 'docker.for.mac.localhost'
    GEOSERVER_URL = 'http://' + GEOSERVER_HOST + '/geoserver/wcs'

# Flask settings
FLASK_DEBUG = False  # Do not use debug mode in production

# flask-restplus settings
RESTPLUS_SWAGGER_UI_DOC_EXPANSION = 'list'
RESTPLUS_VALIDATE = True
RESTPLUS_MASK_SWAGGER = False
RESTPLUS_ERROR_404_HELP = False

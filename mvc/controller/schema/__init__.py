from mvc.controller.flaskapi import api
from flask_restplus import fields
from mvc.controller.schema.ogc import crs_properties

wps = api.model('wps', {
    'service': fields.String(required=True, readOnly=True, description="WPS name"),
    'projection': fields.String(required=True, readOnly=True, description="Use EPSG/OGC standard")
})

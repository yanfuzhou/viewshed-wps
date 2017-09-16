import logging
from flask import request
from mvc.modeller import ViewShed
from flask_restplus import Resource
from mvc.controller.schema import wps
from mvc.controller.flaskapi import api
from mvc.modeller import ServiceRegister
from mvc.modeller.validator import validate_coords
from mvc.controller.parser import viewshed_arguments
from mvc.controller.parser.label import VIEWSHED_LABEL

ns = api.namespace('wps', description='Perform web spatial analysis')
log = logging.getLogger(__name__)


@ns.route('/')
class GetWPSCapabilities(Resource):
    @api.marshal_list_with(wps)
    @api.response(201, 'WPS is running!')
    def get(self):
        """
        Returns capabilities.
        """
        return ServiceRegister().services


@ns.route('/viewshed')
class ViewshedMethod(Resource):
    @api.expect(viewshed_arguments, validate=True)
    @api.response(201, 'Viewshed successfully created!')
    def get(self):
        """
        Returns viewshed analysis result.
        """
        args = viewshed_arguments.parse_args(request)
        coordinates = args.get(VIEWSHED_LABEL['coordinates'])
        distance = args.get(VIEWSHED_LABEL['distance'], 1000.0)
        height = args.get(VIEWSHED_LABEL['height'], 1.70)
        offset = args.get(VIEWSHED_LABEL['offset'])
        swath = args.get(VIEWSHED_LABEL['swath'])
        curvature = args.get(VIEWSHED_LABEL['curvature'])
        refraction = args.get(VIEWSHED_LABEL['refraction'])
        k = args.get(VIEWSHED_LABEL['k'])
        use_swath = args.get(VIEWSHED_LABEL['use_swath'])
        earth_radius = args.get(VIEWSHED_LABEL['earth_radius'])
        resolution = args.get(VIEWSHED_LABEL['resolution'])
        esri = args.get(VIEWSHED_LABEL['esri'])
        if args.get('distance') is not None:
            distance = args.get('distance')
        if args.get('height') is not None:
            height = args.get('height')
        if args.get('offset') is not None:
            offset = args.get('offset')
        if args.get('swath') is not None:
            swath = args.get('swath')
        if args.get('curvature') is not None:
            curvature = args.get('curvature')
        if args.get('refraction') is not None:
            refraction = args.get('refraction')
        if args.get('k') is not None:
            k = args.get('k')
        if args.get('use_swath') is not None:
            use_swath = args.get('use_swath')
        if args.get('earth_radius') is not None:
            earth_radius = args.get('earth_radius')
        if args.get('resolution') is not None:
            resolution = args.get('resolution')
        if args.get('esri') is not None:
            esri = args.get('esri')
        if ',' in coordinates:
            if validate_coords(coordinates):
                if 500.0 <= distance <= 5000.0:
                    x = float(coordinates.split(',')[0])
                    y = float(coordinates.split(',')[1])
                    viewshed = ViewShed(x=x, y=y, distance=distance, height=height, offset=offset, swath=swath,
                                        curvature=curvature, refraction=refraction, k=k, use_swath=use_swath,
                                        earth_radius=earth_radius, resolution=resolution, esri=esri)
                    return viewshed.analysis()
                else:
                    return {"message": "view distance must be between 500.0 and 5000.0"}
            else:
                return {"message": "invalid literal for coordinates"}
        else:
            return {"message": "longitude and latitude must be comma separated"}

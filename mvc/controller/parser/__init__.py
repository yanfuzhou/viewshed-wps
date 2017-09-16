from label import VIEWSHED_LABEL
from flask_restplus import reqparse

viewshed_arguments = reqparse.RequestParser()
viewshed_arguments.add_argument(VIEWSHED_LABEL['coordinates'], type=str, required=True,
                                help='longitude, latitude', location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['distance'], type=float, required=False, default=1000.0,
                                help='view distance (meter), default to 1000.0, minimum to 500.0, maximum to 5000.0',
                                location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['height'], type=float, required=False, default=1.70,
                                help='observer height from ground (meter), default to 1.70', location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['offset'], type=float, required=False, default=0.0,
                                help='target offset from ground (meter), default to 0.0', location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['swath'], type=float, required=False, default=0.15,
                                help='azimuth step range (angle in degree), such as 360/0.15 = 2400 steps, '
                                     'default to 0', location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['curvature'], type=bool, required=False, default=False,
                                help='considering earth curvature (false or true), default to false', location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['refraction'], type=bool, required=False, default=False,
                                help='considering atmospheric refraction (false or true), default to false',
                                location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['k'], type=float, required=False, default=0.13,
                                help='atmospheric refraction factor, default to 0.13, '
                                     'require refraction to be set to true', location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['use_swath'], type=bool, required=False, default=True,
                                help='if set to false, a full 360 degree scanning of line of sight will be used '
                                     '(false or true), default to true. *Caution: set to false will increase '
                                     'computation exponentially, which will be slow.', location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['earth_radius'], type=float, required=False, default=6371000.0,
                                help='earth radius (meter), default to 6371000.0, require curvature to be set to true',
                                location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['resolution'], type=int, required=False, default=30,
                                help='DEM resolution, currently only support 10|30 meters in North America',
                                location='args')
viewshed_arguments.add_argument(VIEWSHED_LABEL['esri'], type=bool, required=False, default=False,
                                help="ESRI's method to calculate earth curvature (false or true), default to false, "
                                     "require curvature to be set to true",
                                location='args')

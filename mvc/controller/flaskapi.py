import logging
from flask_restplus import Api
from setting import FLASK_DEBUG

log = logging.getLogger(__name__)

api = Api(version="2.0 (Victoria's secret)", title='Viewshed WPS',
          description='<a href="https://en.wikipedia.org/wiki/Viewshed">Viewshed</a> '
                      'web processing service built on top of '
                      '<a href="https://pypi.python.org/pypi/GDAL">GDAL</a> '
                      'by using python binding/wrapper.')


@api.errorhandler
def default_error_handler(e):
    print(e)
    message = 'An unhandled exception occurred.'
    log.exception(message)
    if not FLASK_DEBUG:
        return {'message': message}, 500

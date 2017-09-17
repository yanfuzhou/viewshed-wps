import os
import logging.config
from mvc.controller.flaskapi import api
from flask import Flask, Blueprint, send_from_directory
from mvc.controller.namespace.wps import ns as viewshed_namespace
from setting import RESTPLUS_SWAGGER_UI_DOC_EXPANSION, RESTPLUS_VALIDATE, RESTPLUS_MASK_SWAGGER, \
    RESTPLUS_ERROR_404_HELP, FLASK_DEBUG

uri = 'gdal'
logging.config.fileConfig('logging.conf')
log = logging.getLogger(__name__)
app = Flask(__name__)
log.info('>>>>> Starting development server at http://{}'.format('localhost:4000/' + uri + '/ <<<<<'))
app.config['SWAGGER_UI_DOC_EXPANSION'] = RESTPLUS_SWAGGER_UI_DOC_EXPANSION
app.config['RESTPLUS_VALIDATE'] = RESTPLUS_VALIDATE
app.config['RESTPLUS_MASK_SWAGGER'] = RESTPLUS_MASK_SWAGGER
app.config['ERROR_404_HELP'] = RESTPLUS_ERROR_404_HELP
control = Blueprint(uri, __name__, url_prefix='/' + uri)
api.init_app(control)
api.add_namespace(viewshed_namespace)
app.register_blueprint(control)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/x-icon')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=FLASK_DEBUG)

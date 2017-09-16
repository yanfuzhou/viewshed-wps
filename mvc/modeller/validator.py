import logging

log = logging.getLogger(__name__)


def validate_coords(coordinates):
    try:
        float(coordinates.split(',')[0])
        float(coordinates.split(',')[1])
        return True
    except Exception as e:
        log.info(e)
        return False

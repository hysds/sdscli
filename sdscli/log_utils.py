from future import standard_library
standard_library.install_aliases()
import logging


log_format = "[%(asctime)s: %(levelname)s/%(name)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.WARNING)
logger = logging.getLogger('sdscli')

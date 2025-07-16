from future import standard_library
standard_library.install_aliases()
from sdscli.adapters.hysds.fabfile import *


#####################################
# add custom fabric functions below
#####################################

def test():
    """Test fabric function."""

    run('whoami')

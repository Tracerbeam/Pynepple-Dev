import os

from . import constants

def get_asset_path(name):
    """Returns the full path to the asset in question."""
    return os.path.join(constants.ROOT_DIR, 'assets', name)

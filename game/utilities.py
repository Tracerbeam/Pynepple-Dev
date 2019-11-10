import os

from . import constants
from . import gameobjects

def get_asset_path(name):
    """Returns the full path to the asset in question."""
    return os.path.join(constants.ROOT_DIR, 'assets', name)

def str_to_gameobject(objname):
    result = objname
    obj = getattr(gameobjects, objname)
    if issubclass(obj, gameobjects.GameObject):
        result = obj
    return result

import json

from .gameobjects import GameObject, GameGroup
from .utilities import get_asset_path, str_to_gameobject


class Level():
    def __init__(self, gameobjects=[]):
        self.gameobjects = GameGroup()
        for gameobject_kwargs in gameobjects:
            self.gameobjects.add(self._create_gameobject(**gameobject_kwargs))

    def _create_gameobject(self, klass=GameObject, location=(0,0), children=[]):
        gameobject = klass(*location)
        for child_kwargs in children:
            gameobject.children.add(self._create_gameobject(**child_kwargs))
        return gameobject

    def _json_to_init_kwargs(json):
        if 'class' in json:
            json['klass'] = str_to_gameobject(json['class'])
            del json['class']
        if 'location' in json:
            json['location'] = tuple(json['location'])
        return json

    @classmethod
    def load_from_file(self, filename):
        with open(get_asset_path(filename), 'r') as levelfile:
            data = json.load(
                levelfile,
                object_hook=self._json_to_init_kwargs
            )
        return Level(**data)

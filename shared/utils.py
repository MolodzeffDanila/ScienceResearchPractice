import math
from rcrs_core.entities.building import Building
from rcrs_core.entities.human import Human
from rcrs_core.worldmodel.entityID import EntityID


def from_id_list_to_entity_id(int_list):
    return [EntityID(id) for id in int_list]

def from_entity_id_to_id_list(entity_id_list):
    return [entity_id.get_value() for entity_id in entity_id_list]

def get_distance(point1, point2):
    return math.hypot(point1.get_x() - point2.get_x(), point1.get_y() - point2.get_y())

def civilians_to_json(civilians: list[Human]):
    return list(map(lambda civ: {
        "id": civ.get_id().get_value(),
        "position": civ.get_position().get_value(),
        "hp": civ.get_hp(),
        "buriness": civ.get_buriedness()
    }, civilians))

def burning_to_json(burning: list[Building]):
    return list(map(lambda civ: {
        "id": civ.get_id().get_value(),
        "fireness": civ.get_fieryness(),
        'x': civ.get_x(),
        'y': civ.get_y()
    }, burning))

def building_priority(building, my_x, my_y):
    distance = abs(building['x'] - my_x) + abs(building['y'] - my_y)
    if building['fireness'] == 1:
        danger = 0
    elif building['fireness'] == 2:
        danger = 1
    elif building['fireness'] == 3:
        danger = 2
    else:
        danger = 3

    return (danger, distance)
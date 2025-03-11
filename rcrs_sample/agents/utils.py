from rcrs_core.worldmodel.entityID import EntityID


def from_id_list_to_entity_id(int_list):
    return [EntityID(id) for id in int_list]

def from_entity_id_to_id_list(entity_id_list):
    return [entity_id.get_value() for entity_id in entity_id_list]
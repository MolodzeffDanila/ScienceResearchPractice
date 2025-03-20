from rcrs_core.agents.agent import Agent
from rcrs_core.connection import URN
from rcrs_core.entities.civilian import Civilian

class AmbulanceCenterAgent(Agent):
    def __init__(self, pre):
        Agent.__init__(self, pre)
        self.name = 'AmbulanceCenterAgent'

    def precompute(self):
        self.Log.info('precompute finshed')

    def get_requested_entities(self):
        return [URN.Entity.AMBULANCE_CENTRE]

    def think(self, timestep, change_set, heard):
        entities = self.world_model.get_entities()

        civilians = [entity for entity in entities if isinstance(entity, Civilian)]
        #print("AMB\n", civilians)

from rcrs_core.agents.agent import Agent
from rcrs_core.connection import URN
from rcrs_core.constants import kernel_constants
from rcrs_core.entities.building import Building
from rcrs_core.entities.human import Human
from rcrs_core.worldmodel.entityID import EntityID


class AmbulanceTeamAgent(Agent):
    def __init__(self, pre):
        Agent.__init__(self, pre)
        self.name = 'AmbulanceTeamAgent'
    
    def precompute(self):
        self.Log.info('precompute finshed')

    def get_requested_entities(self):
        return [URN.Entity.AMBULANCE_TEAM]
    
    def think(self, time_step, change_set, heard):
        #self.Log.info(time_step)
        if time_step == self.config.get_value(kernel_constants.IGNORE_AGENT_COMMANDS_KEY):
            self.send_subscribe(time_step, [1, 2])

        mudak = self.get_civilians()

        entities = self.world_model.get_entities()
        dom = self.world_model.get_entity(EntityID(945))
        buildings = [entity for entity in entities if
                     isinstance(entity, Building) and entity.fieryness.value > 0]

        my_path = self.random_walk()

        # self.send_load(time_step, target)
        # self.send_unload(time_step)
        # self.send_say(time_step, 'HELP')
        # self.send_speak(time_step, 'HELP meeeee police', 1)
        self.send_move(time_step, my_path)
        # self.send_rest(time_step)

    def get_civilians(self):
        civilians = []
        for entity in self.world_model.get_entities():
            if isinstance(entity, Human) and entity.get_urn() == URN.Entity.CIVILIAN:
                civilians.append(entity)
        return civilians
     
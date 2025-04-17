import heapq

import math
from rcrs_core.agents.agent import Agent
from rcrs_core.connection import URN
from rcrs_core.constants import kernel_constants
from rcrs_core.entities.building import Building
from rcrs_core.entities.human import Human
from rcrs_core.entities.refuge import Refuge
from rcrs_core.worldmodel.entityID import EntityID

from src.agents.node import Node


class AmbulanceTeamAgent(Agent):
    def __init__(self, pre):
        Agent.__init__(self, pre)
        self.name = 'AmbulanceTeamAgent'
        self.loaded = False
        self.refuge = None
    
    def precompute(self):
        self.Log.info('precompute finshed')

    def get_requested_entities(self):
        return [URN.Entity.AMBULANCE_TEAM]
    
    def think(self, time_step, change_set, heard):
        if time_step == self.config.get_value(kernel_constants.IGNORE_AGENT_COMMANDS_KEY):
            self.send_subscribe(time_step, [0,1,2,3])

        civilians = self.get_civilians()

        print(heard)

        refugeees = self.get_refuges()
        if refugeees:
            self.refuge = refugeees[0]

        if not civilians:
            return

        #if self.loaded:
        #    path = self.find_way(self.refuge.get_id())
        #    self.send_move(time_step, path)

        if self.location().get_id().get_value() == civilians[0].get_position().get_value():
            self.loaded = True
            self.send_load(time_step, civilians[0].get_id())
        else:
            path = self.find_way(civilians[0].get_position())
            self.send_move(time_step, path)
        # self.send_load(time_step, target)
        # self.send_unload(time_step)
        # self.send_say(time_step, 'HELP')
        # self.send_speak(time_step, 'HELP meeeee police', 1)
        # self.send_move(time_step, my_path)
        # self.send_rest(time_step)

    def get_civilians(self):
        civilians = []
        for entity in self.world_model.get_entities():
            if (isinstance(entity, Human)
                    and entity.get_urn() == URN.Entity.CIVILIAN
                    #and entity.get_hp() > 0
                    and entity.get_buriedness() > 0
            ):
                civilians.append(entity)
        return civilians

    def get_refuges(self):
        refuges = []
        for entity in self.world_model.get_entities():
            if isinstance(entity, Refuge):
                refuges.append(entity)

        x = self.me().get_x()
        y = self.me().get_y()
        refuges = sorted(refuges, key=lambda b: abs(b.get_x() - x) + abs(b.get_y() - y))
        return refuges

    def find_way(self, entity_id):
        target = self.world_model.get_entity(entity_id)
        start_node = self.location()

        path = self._a_star(start_node, target)
        return path

    def _a_star(self, start_node, target_node):
        open_list = []

        start_node = Node(start_node)
        target_node = Node(target_node)

        heapq.heappush(open_list, start_node)

        closed_set = set()

        while open_list:
            current_node = heapq.heappop(open_list)

            if current_node.id == target_node.id:
                path = []
                while current_node is not None:
                    path.append(current_node.id.get_value())
                    current_node = current_node.parent
                return path[::-1]

            closed_set.add(current_node.id)

            neighbors = [Node(neigh) for neigh in self.get_neighbors(current_node.entity)]

            for neighbor in neighbors:
                if neighbor.get_id() in closed_set:
                    continue

                new_g = current_node.g + self.get_distance(current_node, neighbor)
                if nfo := next((n for n in open_list if n.get_id() == neighbor.get_id()), None):
                    if new_g < nfo.g:
                        nfo.g = new_g
                        nfo.h = math.sqrt((target_node.get_x() - nfo.get_x()) ** 2 + (target_node.get_y() - nfo.get_y()) ** 2)
                        nfo.f = nfo.g + nfo.h
                        nfo.parent = current_node
                        heapq.heapify(open_list)
                else:
                    neighbor.g = new_g
                    neighbor.h = math.sqrt((target_node.get_x() - neighbor.get_x()) ** 2 + (target_node.get_y() - neighbor.get_y()) ** 2)
                    neighbor.f = neighbor.g + neighbor.h
                    neighbor.parent = current_node
                    heapq.heappush(open_list, neighbor)

    def get_distance(self, point1, point2):
        return math.hypot(point1.get_x() - point2.get_x(), point1.get_y() - point2.get_y())

    def get_neighbors(self, node):
        neighbors = [self.world_model.get_entity(neigh) for neigh in node.get_neighbours()]
        return list(filter(lambda x: x is not None, neighbors))
     
import requests
from rcrs_core.agents.agent import Agent
from rcrs_core.constants import kernel_constants
from rcrs_core.connection import URN
from rcrs_core.entities.blockade import Blockade
from rcrs_core.entities.building import Building
from rcrs_core.entities.human import Human
from rcrs_core.entities.road import Road
import sys
import heapq
import math
from itertools import chain

from rcrs_core.worldmodel.entityID import EntityID

from server.constants import SERVER_HOST
from shared.node import Node
from shared.reqs import get_civilians_from_server
from shared.utils import from_id_list_to_entity_id, civilians_to_json, burning_to_json, get_distance


class PoliceForceAgent(Agent):
    def __init__(self, pre):
        Agent.__init__(self, pre)
        self.name = 'PoliceForceAgent'
        self.visited_houses = set()
        self.broken_blockades = set()
        self.recent_blockade_repair_cost = -1

    def precompute(self):
        self.Log.info('precompute finshed')

    def get_requested_entities(self):
        return [URN.Entity.POLICE_FORCE]

    def get_blockades(self):
        blockades = [entity for entity in self.world_model.get_entities() if isinstance(entity, Blockade)]
        return blockades

    def get_neighbors(self, node):
        neighbors = [self.world_model.get_entity(neigh) for neigh in node.get_neighbours()]
        return list(filter(lambda x: x is not None, neighbors))

    def think(self, time_step, change_set, heard):
        if time_step == self.config.get_value(kernel_constants.IGNORE_AGENT_COMMANDS_KEY):
            self.send_subscribe(time_step, [1,2,3])

        buildings = self.get_sorted_buildings()
        civilians_view = self.get_civilians()
        burning = self.get_burning_buildings()

        if burning:
            requests.post(f'{SERVER_HOST}/burning', json=burning_to_json(burning))

        if civilians_view:
            requests.post(f'{SERVER_HOST}/civilians', json=civilians_to_json(civilians_view))

        #Стейт со спасением людей
        """civilians = civilians_to_json(civilians_view) + get_civilians_from_server().json()

        if civilians:
            civ_id = EntityID(civilians[0]['position'])
            if isinstance(self.location(), Building):
                self.send_clear(time_step, civ_id)
            else:
                path = self.find_way(civ_id)
                self.move_nearest_blockade_on_path(time_step, path)
                self.send_move(time_step, path)"""

        if not buildings:
            self.not_found_building_state(time_step)
            return
        if isinstance(self.location(), Building):
            self.visited_houses.add(self.location())

            buildings = buildings[1:]
            if not buildings:
                self.not_found_building_state(time_step)
                return
            path = self.find_way(buildings[0].get_id())
            self.send_move(time_step, path)
        else:
            path = self.find_way(buildings[0].get_id())
            self.move_nearest_blockade_on_path(time_step, path)
            self.send_move(time_step, path)

    def get_civilians(self):
        civilians = []
        for entity in self.world_model.get_entities():
            if (isinstance(entity, Human)
                    and entity.get_urn() == URN.Entity.CIVILIAN
                    and entity.get_buriedness() > 0
            ):
                civilians.append(entity)
        return civilians

    def get_burning_buildings(self):
        entities = self.world_model.get_entities()
        buildings = [entity for entity in entities if isinstance(entity, Building) and entity.fieryness.value > 0]
        return buildings

    def not_found_building_state(self, time_step):
        blockade = self.get_nearest_blockade()

        if blockade:
            self.move_nearest_blockade(time_step, blockade)
        return

    def move_nearest_blockade(self, time_step, blockade_id):
        x = self.me().get_x()
        y = self.me().get_y()

        blockade = self.world_model.get_entity(blockade_id)
        path = self.find_way(blockade.get_position())
        dx = abs(blockade.get_x() - x)
        dy = abs(blockade.get_y() - y)

        distance = math.hypot(dx, dy)
        if distance < float(self.config.get_value('clear.repair.distance')):
            if self.recent_blockade_repair_cost == blockade.get_repaire_cost():
                self.broken_blockades.add(blockade)
            else:
                self.recent_blockade_repair_cost = blockade.get_repaire_cost()
                self.send_clear(time_step, blockade.get_id())
        else:
            self.send_move(time_step, path)
        return

    def move_nearest_blockade_on_path(self, time_step, path):
        if isinstance(self.location(), Road):
            target = self.get_nearest_blockade_on_path(path)
            if target:
                self.send_clear(time_step, target)
        return

    def get_sorted_buildings(self):
        x = self.me().get_x()
        y = self.me().get_y()

        entities = self.world_model.get_entities()
        buildings = [entity for entity in entities if
                     isinstance(entity, Building) and entity not in self.visited_houses
                     and self.is_build_has_blockaded_roads(entity)]
        buildings.sort(key=lambda b: abs(b.get_x() - x) + abs(b.get_y() - y))
        return buildings

    def is_build_has_blockaded_roads(self, building):
        neighs = self.get_neighbors(building)
        for neigh in neighs:
            blockades = neigh.get_blockades()
            if blockades or blockades:
                return True
        return False

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

                new_g = current_node.g + get_distance(current_node, neighbor)
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

    def get_nearest_blockade_on_path(self, path):
        best_distance = sys.maxsize
        best = None
        x = self.me().get_x()
        y = self.me().get_y()

        blockades = self.location().get_blockades()
        path = [self.world_model.get_entity(p) for p in from_id_list_to_entity_id(path)]
        path_blockades = list(chain.from_iterable(p.get_blockades() for p in path))

        all_blockades = blockades + path_blockades
        for b in all_blockades:
            blockade = self.world_model.get_entity(b)
            if blockade:
                dx = abs(blockade.get_x() - x)
                dy = abs(blockade.get_y() - y)
                distance = math.hypot(dx, dy)
                if distance < best_distance and distance < float(self.config.get_value('clear.repair.distance')):
                    best_distance = distance
                    best = blockade.get_id()
        return best

    def get_nearest_blockade(self):
        best_distance = sys.maxsize
        best_blockade = None
        x = self.me().get_x()
        y = self.me().get_y()

        blockades = [entity for entity in self.world_model.get_entities()
                     if isinstance(entity, Blockade) and
                     entity not in self.broken_blockades]

        for blockade in blockades:
            dx = abs(blockade.get_x() - x)
            dy = abs(blockade.get_y() - y)
            distance = math.hypot(dx, dy)
            if distance < best_distance and blockade.get_repaire_cost() > 6:
                best_distance = distance
                best_blockade = blockade.get_id()

        return best_blockade


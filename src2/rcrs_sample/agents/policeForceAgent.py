import requests
import sys
import heapq
import math
from itertools import chain

from rcrs_core.agents.agent import Agent
from rcrs_core.constants import kernel_constants
from rcrs_core.connection import URN
from rcrs_core.entities.blockade import Blockade
from rcrs_core.entities.building import Building
from rcrs_core.entities.human import Human
from rcrs_core.entities.road import Road
from rcrs_core.worldmodel.entityID import EntityID

from server.constants import SERVER_HOST
from shared.node import Node
from shared.reqs import get_civilians_from_server, delete_civilian
from shared.utils import from_id_list_to_entity_id, civilians_to_json, burning_to_json, get_distance

class PoliceForceAgent(Agent):
    def __init__(self, pre):
        Agent.__init__(self, pre)
        self.name = 'PoliceForceAgent'
        self.visited_houses = set()
        self.blockades = set()
        self.recent_blockade_repair_cost = -1
        self.civilians = []

    def precompute(self):
        self.Log.info('precompute finished')

    def get_requested_entities(self):
        return [URN.Entity.POLICE_FORCE]

    def think(self, time_step, change_set, heard):
        if time_step == self.config.get_value(kernel_constants.IGNORE_AGENT_COMMANDS_KEY):
            self.send_subscribe(time_step, [1,2,3])

        buildings = self.get_sorted_buildings()
        burning = self.get_burning_buildings()

        blockades_to_not_touch_json = requests.get(f'{SERVER_HOST}/blockades').json()
        for b in blockades_to_not_touch_json:
            self.blockades.add(EntityID(b['id']))

        if burning:
            requests.post(f'{SERVER_HOST}/burning', json=burning_to_json(burning))

        civilians_view = self.get_civilians()

        if civilians_view:
            requests.post(f'{SERVER_HOST}/civilians', json=civilians_to_json(civilians_view))

        x, y = self.me().get_x(), self.me().get_y()

        civilians = [civ for civ in get_civilians_from_server() if (civ['x'] - x) ** 2 + (civ['y'] - y) ** 2 < 30000]

        civilians.sort(key=lambda civ: (civ['x'] - x) ** 2 + (civ['y'] - y) ** 2)

        if civilians:
            if isinstance(self.location(), Building):
                delete_civilian(civilians[0]['id'])
            cur_civ_pos = EntityID(civilians[0]['position'])
            path = self.find_way(cur_civ_pos)
            self.move_nearest_blockade_on_path(time_step, path)
            self.send_move(time_step, path)

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
        return [e for e in self.world_model.get_entities() if isinstance(e, Human)
                and e.get_urn() == URN.Entity.CIVILIAN
                and isinstance( self.world_model.get_entity(e.get_position()), Building)]

    def get_burning_buildings(self):
        return [e for e in self.world_model.get_entities() if isinstance(e, Building) and e.fieryness.value > 0]

    def not_found_building_state(self, time_step):
        blockade_id = self.get_nearest_blockade()
        if blockade_id:
            self.move_nearest_blockade(time_step, blockade_id)
        else:
            path = self.random_walk()
            self.send_move(time_step, path)

    def move_nearest_blockade(self, time_step, blockade_id):
        x, y = self.me().get_x(), self.me().get_y()
        blockade = self.world_model.get_entity(blockade_id)
        path = self.find_way(blockade.get_position())
        dx, dy = abs(blockade.get_x() - x), abs(blockade.get_y() - y)
        distance = math.hypot(dx, dy)

        if distance < float(self.config.get_value('clear.repair.distance')):
            if self.recent_blockade_repair_cost == blockade.get_repaire_cost():
                self.blockades.add(blockade.get_id())
                agent_id = self.me().get_id().get_value()
                requests.post(f'{SERVER_HOST}/blockades', json={"id": blockade.get_id().get_value(), "agent": agent_id})
            else:
                self.recent_blockade_repair_cost = blockade.get_repaire_cost()
                self.send_clear(time_step, blockade.get_id())
        else:
            self.send_move(time_step, path, blockade.get_x(), blockade.get_y())

    def move_nearest_blockade_on_path(self, time_step, path):
        if isinstance(self.location(), Road):
            target = self.get_nearest_blockade_on_path(path)
            if target:
                agent_id = self.me().get_id().get_value()
                requests.post(f'{SERVER_HOST}/blockades', json={"id": target.get_value(), "agent": agent_id})
                self.send_clear(time_step, target)

    def get_sorted_buildings(self):
        x, y = self.me().get_x(), self.me().get_y()
        buildings = [e for e in self.world_model.get_entities()
                     if isinstance(e, Building)
                     and e not in self.visited_houses
                     and self.is_build_has_blockaded_roads(e)]
        buildings.sort(key=lambda b: abs(b.get_x() - x) + abs(b.get_y() - y))
        return buildings

    def is_build_has_blockaded_roads(self, building):
        return any(neigh.get_blockades() for neigh in self.get_neighbors(building))

    def get_neighbors(self, node):
        return [self.world_model.get_entity(neigh) for neigh in node.get_neighbours() if self.world_model.get_entity(neigh)]

    def find_way(self, entity_id):
        start = Node(self.location())
        target = Node(self.world_model.get_entity(entity_id))
        open_list = [start]
        closed_set = set()

        while open_list:
            current = heapq.heappop(open_list)
            if current.id == target.id:
                path = []
                while current:
                    path.append(current.id.get_value())
                    current = current.parent
                return path[::-1]
            closed_set.add(current.id)

            for neighbor in [Node(n) for n in self.get_neighbors(current.entity)]:
                if neighbor.get_id() in closed_set:
                    continue
                new_g = current.g + get_distance(current, neighbor)
                if nfo := next((n for n in open_list if n.get_id() == neighbor.get_id()), None):
                    if new_g < nfo.g:
                        nfo.g = new_g
                        nfo.h = get_distance(nfo, target)
                        nfo.f = nfo.g + nfo.h
                        nfo.parent = current
                        heapq.heapify(open_list)
                else:
                    neighbor.g = new_g
                    neighbor.h = get_distance(neighbor, target)
                    neighbor.f = neighbor.g + neighbor.h
                    neighbor.parent = current
                    heapq.heappush(open_list, neighbor)

    def get_nearest_blockade_on_path(self, path):
        best = None
        x = self.me().get_x()
        y = self.me().get_y()

        blockades = self.location().get_blockades()
        path = [self.world_model.get_entity(p) for p in from_id_list_to_entity_id(path)]
        path_blockades = list(chain.from_iterable(p.get_blockades() for p in path if p))

        all_blockades = blockades + path_blockades

        candidates = []
        for b in all_blockades:
            blockade = self.world_model.get_entity(b)
            if blockade:
                dx = blockade.get_x() - x
                dy = blockade.get_y() - y
                distance = math.hypot(dx, dy)
                if distance < float(self.config.get_value('clear.repair.distance')):
                    candidates.append((distance, blockade.get_id()))

        if candidates:
            candidates.sort(key=lambda t: t[0])  # Сортировка только по расстоянию
            best = candidates[0][1]

        return best

    def get_nearest_blockade(self):
        best_distance = sys.maxsize
        best_blockade = None
        x = self.me().get_x()
        y = self.me().get_y()

        blockades = [entity for entity in self.world_model.get_entities()
                     if isinstance(entity, Blockade) and
                     entity.get_id() not in self.blockades]

        for blockade in blockades:
            dx = abs(blockade.get_x() - x)
            dy = abs(blockade.get_y() - y)
            distance = math.hypot(dx, dy)
            if distance < best_distance and blockade.get_repaire_cost() > 5:
                best_distance = distance
                best_blockade = blockade.get_id()

        return best_blockade
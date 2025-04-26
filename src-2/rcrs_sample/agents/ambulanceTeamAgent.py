import heapq
import math
import requests

from rcrs_core.agents.agent import Agent
from rcrs_core.connection import URN
from rcrs_core.constants import kernel_constants
from rcrs_core.entities.building import Building
from rcrs_core.entities.human import Human
from rcrs_core.entities.refuge import Refuge
from rcrs_core.worldmodel.entityID import EntityID

from server.constants import SERVER_HOST
from shared.utils import civilians_to_json
from src.agents.node import Node


class AmbulanceTeamAgent(Agent):
    def __init__(self, pre):
        super().__init__(pre)
        self.name = 'AmbulanceTeamAgent'
        self.loaded = False
        self.refuge = None
        self.target_civilian = None

    def precompute(self):
        self.Log.info('Precompute finished')

    def get_requested_entities(self):
        return [URN.Entity.AMBULANCE_TEAM]

    def think(self, time_step, change_set, heard):
        # Подписка на радиоканалы
        if time_step == self.config.get_value(kernel_constants.IGNORE_AGENT_COMMANDS_KEY):
            self.send_subscribe(time_step, [0, 1, 2, 3])

        # Обновляем список гражданских и отправляем на сервер
        civilians = self.get_civilians()
        if civilians:
            requests.post(f'{SERVER_HOST}/civilians', json=civilians_to_json(civilians))

        # Найдём ближайшее убежище один раз
        if not self.refuge:
            refuges = self.get_refuges()
            if refuges:
                self.refuge = refuges[0]

        # Если уже загружен, едем в убежище
        if self.loaded:
            if self.location().get_id() == self.refuge.get_id():
                self.send_unload(time_step)
                self.loaded = False
                self.target_civilian = None
            else:
                path = self.find_way(self.refuge.get_id())
                self.send_move(time_step, path)
            return

        # Поиск цели, если нет
        if not self.target_civilian and civilians:
            self.target_civilian = civilians[0]

        if not self.target_civilian:
            return

        civ = self.target_civilian
        civ_pos = civ.get_position()

        if self.location().get_id() == civ_pos:
            if civ.get_buriedness() > 0:
                self.send_rescue(time_step, civ.get_id())
            else:
                self.send_load(time_step, civ.get_id())
                self.loaded = True
        else:
            path = self.find_way(civ_pos)
            self.send_move(time_step, path)

    def get_civilians(self):
        civilians = []
        for entity in self.world_model.get_entities():
            if (isinstance(entity, Human)
                    and entity.get_urn() == URN.Entity.CIVILIAN
                    and entity.get_buriedness() > 0
                    and entity.get_hp() > 0):
                civilians.append(entity)

        # Сортировка по расстоянию
        x, y = self.me().get_x(), self.me().get_y()
        civilians.sort(key=lambda c: abs(c.get_x() - x) + abs(c.get_y() - y))
        return civilians

    def get_refuges(self):
        refuges = []
        for entity in self.world_model.get_entities():
            if isinstance(entity, Refuge):
                refuges.append(entity)
        # Сортировка по расстоянию
        x, y = self.me().get_x(), self.me().get_y()
        refuges.sort(key=lambda r: abs(r.get_x() - x) + abs(r.get_y() - y))
        return refuges

    def find_way(self, entity_id: EntityID):
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
                while current_node:
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
                        nfo.h = self.get_distance(nfo, target_node)
                        nfo.f = nfo.g + nfo.h
                        nfo.parent = current_node
                        heapq.heapify(open_list)
                else:
                    neighbor.g = new_g
                    neighbor.h = self.get_distance(neighbor, target_node)
                    neighbor.f = neighbor.g + neighbor.h
                    neighbor.parent = current_node
                    heapq.heappush(open_list, neighbor)

        return []

    def get_distance(self, point1, point2):
        return math.hypot(point1.get_x() - point2.get_x(), point1.get_y() - point2.get_y())

    def get_neighbors(self, node):
        return [self.world_model.get_entity(nid) for nid in node.get_neighbours() if self.world_model.get_entity(nid)]

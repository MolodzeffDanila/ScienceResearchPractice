from rcrs_core.agents.agent import Agent
from rcrs_core.constants import kernel_constants
from rcrs_core.connection import URN
from rcrs_core.entities.blockade import Blockade
from rcrs_core.entities.building import Building
from rcrs_core.entities.road import Road
from rcrs_core.entities.human import Human
from rcrs_core.entities.refuge import Refuge
import math
import sys
import heapq
from itertools import chain

from rcrs_core.worldmodel.entityID import EntityID

from src.agents.node import Node
from src.agents.utils import from_id_list_to_entity_id, from_entity_id_to_id_list


class PoliceForceAgent(Agent):
    def __init__(self, pre):
        Agent.__init__(self, pre)
        self.name = 'PoliceForceAgent'
        self.found_refuge = False
        self.refuge = None
        self.visited_roads = set()  # Множество для хранения посещенных дорог
        self.roads_to_explore = None
        self.state = "FIND_REFUGE"

    def precompute(self):
        self.Log.info('precompute finished')

    def get_requested_entities(self):
        return [URN.Entity.POLICE_FORCE]

    def get_civilians(self):
        civilians = []
        for entity in self.world_model.get_entities():
            if isinstance(entity, Human) and entity.get_urn() == URN.Entity.CIVILIAN:
                civilians.append(entity)
        return civilians

    def get_refugees(self):
        refuges = []
        for entity in self.world_model.get_entities():
            if isinstance(entity, Refuge) and entity.get_urn() == URN.Entity.REFUGE:
                refuges.append(entity)
        return refuges

    def think(self, time_step, change_set, heard):
        self.Log.info(time_step)

        if time_step == self.config.get_value(kernel_constants.IGNORE_AGENT_COMMANDS_KEY):
            self.send_subscribe(time_step, [1, 2])
        #print(heard) Приходит что-то супернепонятное, но услышать агентов можно

        self.visited_roads.add(self.location().get_id())

        print(self.world_model.get_entity(EntityID(263)).get_blockades())

        if self.state == "FIND_REFUGE":
            self.find_refuge_state(time_step)
        if self.state == "CLEAR":
            self.clear_blockade_state(time_step)
        if self.state == "MOVE_NEXT":
            self.move_to_next_state(time_step)

    def clear_blockade_state(self, time_step):
        target = self.get_nearest_blockade_on_path(self.roads_to_explore)
        if isinstance(self.location(), Building):
            roads = self.get_neighbors(self.location())
            self.roads_to_explore = roads
            self.move_to_next_state(time_step)
            return
        if target:
            self.send_clear(time_step, target)
            return
        else:
            blockades = self.world_model.get_entity(EntityID(self.roads_to_explore[0])).get_blockades()
            blockades_sorted = sorted(blockades, key=lambda b: self.get_distance(self.world_model.get_entity(b), self.location()))
            if not blockades:
                self.state = 'MOVE_NEXT'
                self.Log.info("From clear to move")
                self.visited_roads.add(self.roads_to_explore[0])
                self.roads_to_explore = self.roads_to_explore[1:]
                self.move_to_next_state(time_step)
            else:
                current_road_id = self.location().get_id().get_value()
                blockade_entity = self.world_model.get_entity(blockades_sorted[0])
                self.send_move(time_step, [current_road_id], blockade_entity.get_x(), blockade_entity.get_y())

    def move_to_next_state(self, time_step):
        if self.roads_to_explore:
            current_road_id = self.location().get_id().get_value()
            blockade = self.get_nearest_blockade()
            self.send_move(time_step, [self.roads_to_explore[0]])
            if current_road_id == self.roads_to_explore[0] or blockade:
                self.state = 'CLEAR'
                self.Log.info('From Move to Clear')
                self.clear_blockade_state(time_step)
        else:
            self.roads_to_explore = self.explore_roads()

    def get_nearest_refuge_road(self):
        best_distance = sys.maxsize
        best = None

        x = self.me().get_x()
        y = self.me().get_y()

        refuges = self.get_refugees()

        for ref in refuges:
            dx = abs(ref.get_x() - x)
            dy = abs(ref.get_y() - y)
            distance = math.hypot(dx, dy)
            if distance < best_distance:
                best_distance = distance
                best = ref

        ref_neighs = self.get_neighbors(best)
        best_distance = sys.maxsize

        best_road = None
        for ref in ref_neighs:
            dx = abs(ref.get_x() - x)
            dy = abs(ref.get_y() - y)
            distance = math.hypot(dx, dy)
            if distance < best_distance:
                best_distance = distance
                best_road = ref
        return best_road.get_id()

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

        blockades = [entity for entity in self.world_model.get_entities() if isinstance(entity, Blockade)]

        for blockade in blockades:
            dx = abs(blockade.get_x() - x)
            dy = abs(blockade.get_y() - y)
            distance = math.hypot(dx, dy)
            if distance < best_distance:
                best_distance = distance
                best_blockade = blockade.get_id()

        return best_blockade

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

    def get_neighbors(self, node):
        neighbors = [self.world_model.get_entity(neigh) for neigh in node.get_neighbours()]
        return list(filter(lambda x: x is not None, neighbors))

    def get_distance(self, node1, node2):
        dx = abs(self.world_model.get_entity(node1.get_id()).get_x() - self.world_model.get_entity(node2.get_id()).get_x())
        dy = abs(self.world_model.get_entity(node1.get_id()).get_y() - self.world_model.get_entity(node2.get_id()).get_y())
        return dx + dy

    def explore_roads(self):
        # Выполним поиск в глубину (DFS) всех дорог, начиная с текущей
        roads_to_explore = []
        self._dfs(self.location(), roads_to_explore)
        return from_entity_id_to_id_list(roads_to_explore)

    def _dfs(self, current_road, roads_to_explore):
        # Добавляем текущую дорогу в список
        roads_to_explore.append(current_road.get_id())

        # Рекурсивно исследуем соседей
        neighbors = self.get_neighbors(current_road)
        for neighbor in neighbors:
            if isinstance(neighbor, Road):
                # Мы не проверяем visited_roads для обхода в глубину, но учитываем текущий обход
                if neighbor.get_id() not in roads_to_explore and neighbor.get_id() not in self.visited_roads:
                    self._dfs(neighbor, roads_to_explore)

    def find_refuge_state(self, time_step):
        if self.refuge is not None and self.location().get_id().get_value() == self.refuge.get_value():
            self.found_refuge = True
            self.state = "MOVE_NEXT"
            self.Log.info('From refuge to Clear')
        if not self.found_refuge:
            self.refuge = self.get_nearest_refuge_road()
            path = self.find_way(self.refuge)
            if isinstance(self.location(), Road):
                target = self.get_nearest_blockade_on_path(path)
                if target:
                    self.send_clear(time_step, target)
                    return
            self.send_move(time_step, path)
            self.visited_roads.add(self.location().get_id().get_value())


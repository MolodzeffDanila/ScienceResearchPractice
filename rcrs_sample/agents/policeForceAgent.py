from rcrs_core.agents.agent import Agent
from rcrs_core.constants import kernel_constants
from rcrs_core.connection import URN
from rcrs_core.entities.blockade import Blockade
from rcrs_core.entities.road import Road
from rcrs_core.entities.human import Human
from rcrs_core.entities.refuge import Refuge
import math
import sys
import heapq
from itertools import chain

from rcrs_core.worldmodel.entityID import EntityID

from rcrs_sample.agents.node import Node
from rcrs_sample.agents.utils import from_id_list_to_entity_id


class PoliceForceAgent(Agent):
    def __init__(self, pre):
        Agent.__init__(self, pre)
        self.name = 'PoliceForceAgent'
        self.found_refuge = False
        self.refuge = None
    
    def precompute(self):
        self.Log.info('precompute finshed')

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

        if self.refuge is not None and self.location().get_id().get_value() == self.refuge.get_value():
            self.found_refuge = True

        if not self.found_refuge:
            self.refuge = self.get_nearest_refuge_road()
            path = self.find_way(self.refuge)
            if isinstance(self.location(), Road):
                target = self.get_nearest_blockade_on_path(path)
                if target:
                    self.send_clear(time_step, target)
                    return
            self.send_move(time_step, path)
        else:
            nearest_blockade = self.get_nearest_blockade()
            path = self.find_way(nearest_blockade)
            if path:
                self.send_move(time_step, path)
                self.send_clear(time_step, nearest_blockade)
                return

        # self.send_say(time_step, 'HELP')
        # self.send_speak(time_step, 'HELP meeeee police', 1)

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

        # Получаем все Blockade на карте
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
        #blockades = [entity for entity in self.world_model.get_entities() if entity.get_urn() == URN.Entity.BLOCKADE]
        #for blockade in blockades:
            #print(blockade.repair_cost.get_value(), self.world_model.get_entity(blockade.get_position()))
        start_node = self.location()

        path = self._a_star(start_node, target)
        return path

    def _a_star(self, start_node, target_node):
        open_list = []

        start_node = Node(start_node)
        target_node = Node(target_node)

        heapq.heappush(open_list, start_node)

        # Инициализируем множество посещенных узлов
        closed_set = set()

        while open_list:
            current_node = heapq.heappop(open_list)

            # Если текущий узел является конечным
            if current_node.id == target_node.id:
                # Восстанавливаем путь от конечного узла до начального
                path = []
                while current_node is not None:
                    path.append(current_node.id.get_value())
                    current_node = current_node.parent
                return path[::-1]

            # Добавляем текущий узел в множество посещенных узлов
            closed_set.add(current_node.id)

            neighbors = [Node(neigh) for neigh in self.get_neighbors(current_node.entity)]

            for neighbor in neighbors:
                # Если соседний узел уже был посещен, пропускаем его
                if neighbor.get_id() in closed_set:
                    continue

                new_g = current_node.g + self.get_distance(current_node, neighbor)
                # Если соседний узел уже находится в очереди с приоритетами
                if nfo := next((n for n in open_list if n.get_id() == neighbor.get_id()), None):
                    # Если новое расстояние до соседнего узла меньше, чем старое, обновляем значения g, h и f
                    if new_g < nfo.g:
                        nfo.g = new_g
                        nfo.h = math.sqrt((target_node.get_x() - nfo.get_x()) ** 2 + (target_node.get_y() - nfo.get_y()) ** 2)
                        nfo.f = nfo.g + nfo.h
                        nfo.parent = current_node
                        # Обновляем приоритет соседнего узла в очереди с приоритетами
                        heapq.heapify(open_list)
                else:
                    # Иначе добавляем соседний узел в очередь с приоритетами и вычисляем значения g, h и f
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

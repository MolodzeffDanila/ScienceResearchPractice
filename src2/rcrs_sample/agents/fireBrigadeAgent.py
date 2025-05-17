import heapq
from itertools import chain

import math
from rcrs_core.agents.agent import Agent
from rcrs_core.commands.Command import Command
from rcrs_core.connection import URN, RCRSProto_pb2
from rcrs_core.constants import kernel_constants
from rcrs_core.entities.building import Building
from rcrs_core.entities.refuge import Refuge
from rcrs_core.entities.road import Road
from rcrs_core.worldmodel.entityID import EntityID

from server.constants import SERVER_HOST
from shared.reqs import get_burning_from_server
from shared.utils import burning_to_json, building_priority, from_id_list_to_entity_id
from src.agents.node import Node
import requests

WATER_OUT = 1000

class FireBrigadeAgent(Agent):
    def __init__(self, pre):
        Agent.__init__(self, pre)
        self.name = "firebrigadeAgent"
        self.water = 1000
        self.going_to_refuge = False
        self.broken_blockades = []
    
    def precompute(self):
        self.Log.info('precompute finshed')
    
    def get_requested_entities(self):
        return [URN.Entity.FIRE_BRIGADE]

    def think(self, time_step, change_set, heard):
        if time_step < int(self.config.get_value(kernel_constants.IGNORE_AGENT_COMMANDS_KEY)):
            self.send_subscribe(time_step, [0, 1, 2, 3])
            self.send_rest(time_step)
            return

        self.water = self.world_model.get_entity(self.get_id()).get_water()

        if self.going_to_refuge:
            if self.water >= 1000:  # допустим, полная заправка
                self.going_to_refuge = False  # заправился, снова тушим
            else:
                refuges = self.get_refuges()
                if refuges:
                    refuge = refuges[0]
                    path = self.find_way(refuge.get_id())
                    self.send_move(time_step, path)
                else:
                    self.send_rest(time_step)
                return

        if self.water == 0:
            self.going_to_refuge = True
            refuges = self.get_refuges()
            if refuges:
                refuge = refuges[0]
                path = self.find_way(refuge.get_id())
                self.move_nearest_blockade_on_path(time_step, path)
                self.send_move(time_step, path)
            else:
                self.send_rest(time_step)
            return

        x, y = self.me().get_x(), self.me().get_y()

        entities = self.world_model.get_entities()
        buildings = self.get_burning_buildings()

        if buildings:
            requests.post(f'{SERVER_HOST}/burning', json=burning_to_json(buildings))

        burning = get_burning_from_server().json() + burning_to_json(buildings)
        burning = [b for b in burning if b['fireness'] <= 3]
        burning.sort(key=lambda b: building_priority(b, x, y))

        if burning:
            target_building = self.world_model.get_entity(EntityID(burning[0]['id']))
            path = self.find_way(target_building.get_id())

            dx = target_building.get_x() - x
            dy = target_building.get_y() - y
            dist = math.hypot(dx, dy)

            if dist < float(self.config.get_value('fire.extinguish.max-distance')):
                water_to_use = min(self.water, WATER_OUT)
                self.send_extinguish(
                    time_step,
                    target_building.get_id(),
                    target_building.get_x(),
                    target_building.get_y(),
                    water=water_to_use
                )
                return
            self.move_nearest_blockade_on_path(time_step, path)
            self.send_move(time_step, path)

    def get_burning_buildings(self):
        return [e for e in self.world_model.get_entities() if isinstance(e, Building) and e.get_fieryness() > 0]

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

    def get_refuges(self):
        refuges = []
        for entity in self.world_model.get_entities():
            if isinstance(entity, Refuge):
                refuges.append(entity)
        x, y = self.me().get_x(), self.me().get_y()
        refuges.sort(key=lambda r: abs(r.get_x() - x) + abs(r.get_y() - y))
        return refuges

    def move_nearest_blockade_on_path(self, time_step, path):
        if isinstance(self.location(), Road):
            target = self.get_nearest_blockade_on_path(path)
            if target:
                self.send_clear(time_step, target)

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

    def send_extinguish(self, time_step: int, target: EntityID, target_x: int, target_y: int, water: int = WATER_OUT):
        cmd = AKExtinguish(self.get_id(), time_step, target, target_x, target_y, water)
        msg = cmd.prepare_cmd()
        self.send_msg(msg)
            
class AKExtinguish(Command):

    def __init__(self, agent_id: EntityID, time: int, target: EntityID, target_x: int,
                 target_y: int, water: int) -> None:
        super().__init__()
        self.urn = URN.Command.AK_EXTINGUISH
        self.agent_id = agent_id
        self.target = target
        self.time = time
        self.target_x = target_x
        self.target_y = target_y
        self.water = water

    def prepare_cmd(self):
        msg = RCRSProto_pb2.MessageProto()
        msg.urn = self.urn
        msg.components[URN.ComponentControlMSG.AgentID].entityID = self.agent_id.get_value()
        msg.components[URN.ComponentControlMSG.Time].intValue = self.time
        msg.components[URN.ComponentCommand.Target].entityID = self.target.get_value()
        msg.components[URN.ComponentCommand.DestinationX].intValue = self.target_x
        msg.components[URN.ComponentCommand.DestinationY].intValue = self.target_y
        msg.components[URN.ComponentCommand.Water].intValue = self.water
        return msg

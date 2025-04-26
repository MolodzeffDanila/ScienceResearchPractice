import heapq

import math
from rcrs_core.agents.agent import Agent
from rcrs_core.commands.Command import Command
from rcrs_core.connection import URN, RCRSProto_pb2
from rcrs_core.constants import kernel_constants
from rcrs_core.entities.building import Building
from rcrs_core.worldmodel.entityID import EntityID

from server.constants import SERVER_HOST
from shared.reqs import get_burning_from_server
from shared.utils import burning_to_json
from src.agents.node import Node
import requests

WATER_OUT = 1000

class FireBrigadeAgent(Agent):
    def __init__(self, pre):
        Agent.__init__(self, pre)
        self.name = "firebrigadeAgent"
        self.water = 1000
    
    def precompute(self):
        self.Log.info('precompute finshed')
    
    def get_requested_entities(self):
        return [URN.Entity.FIRE_BRIGADE]

    def think(self, time_step, change_set, heard):
        if time_step < int(self.config.get_value(kernel_constants.IGNORE_AGENT_COMMANDS_KEY)):
            self.send_subscribe(time_step, [0,1,2,3])
            self.send_rest(time_step)
            return

        self.water = self.world_model.get_entity(self.get_id()).get_water()

        x = self.me().get_x()
        y = self.me().get_y()

        entities = self.world_model.get_entities()
        buildings = [entity for entity in entities if isinstance(entity, Building)]
        buildings = [build for build in buildings if build.fieryness.value > 0]


        if buildings:
            aa = get_burning_from_server()
            print(aa)
            print(aa.json())
            burning = aa.json() + burning_to_json(buildings)
            burning.sort(key=lambda b: abs(b['x'] - x) + abs(b['y'] - y))

            print(burning)

        if buildings:
            requests.post(f'{SERVER_HOST}/burning', json=burning_to_json(buildings))

        if buildings:
            path = self.find_way(buildings[0].get_id())

            dx = buildings[0].get_x() - x
            dy = buildings[0].get_y() - y

            dist = math.hypot(dx, dy)

            if dist < float(self.config.get_value('fire.extinguish.max-distance')):
                #self.send_speak(time_step,f'Ext: {buildings[0].get_id().get_value()}',2)
                self.send_extinguish(
                    time_step,
                    buildings[0].get_id(),
                    buildings[0].get_x(),
                    buildings[0].get_y(),
                )
                return
            self.send_move(time_step, path)

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

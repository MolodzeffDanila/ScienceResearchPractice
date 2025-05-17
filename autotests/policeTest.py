import unittest
from unittest.mock import MagicMock, patch

from rcrs_core.connection import URN
from rcrs_core.entities.blockade import Blockade
from rcrs_core.entities.building import Building
from rcrs_core.entities.road import Road
from rcrs_core.worldmodel.entityID import EntityID

from src2.rcrs_sample.agents.policeForceAgent import PoliceForceAgent


class TestPoliceForceAgent(unittest.TestCase):
    def setUp(self):
        self.agent = PoliceForceAgent(pre=True)
        self.agent.world_model = MagicMock()
        self.agent.location = MagicMock()
        self.agent.get_neighbors = MagicMock()
        self.agent.me = MagicMock()
        self.agent.config = MagicMock()
        self.agent.config.get_value = MagicMock(return_value='5000')
        self.agent.send_subscribe = MagicMock()
        self.agent.send_move = MagicMock()
        self.agent.send_clear = MagicMock()
        self.agent.send_rest = MagicMock()
        self.agent.not_found_building_state = MagicMock()

    # Тест find_way
    def test_find_way_direct(self):
        start = MagicMock()
        target = MagicMock()
        target.get_id.return_value.get_value.return_value = 100

        self.agent.location.return_value = start
        self.agent.world_model.get_entity.return_value = target
        self.agent.get_neighbors.return_value = []

        path = self.agent.find_way(target.get_id())
        self.assertEqual(path, None)

    # Тест получения видимых зданий
    def test_get_sorted_buildings(self):
        self.agent.me.return_value.get_x.return_value = 0
        self.agent.me.return_value.get_y.return_value = 0

        b1 = MagicMock(spec=Building)
        b2 = MagicMock(spec=Building)
        b1.get_x.return_value = 100
        b1.get_y.return_value = 100
        b2.get_x.return_value = 50
        b2.get_y.return_value = 50
        self.agent.visited_houses = set()

        self.agent.world_model.get_entities.return_value = [b1, b2]
        self.agent.is_build_has_blockaded_roads = MagicMock(return_value=True)

        sorted_buildings = self.agent.get_sorted_buildings()
        self.assertEqual(sorted_buildings, [b2, b1])

    # Тест ближайшего завала
    def test_get_nearest_blockade(self):
        self.agent.me.return_value.get_x.return_value = 0
        self.agent.me.return_value.get_y.return_value = 0

        b1 = MagicMock(spec=Blockade)
        b1.get_x.return_value = 30
        b1.get_y.return_value = 40
        b1.get_repaire_cost.return_value = 10
        b1.get_id.return_value = 'b1'

        b2 = MagicMock(spec=Blockade)
        b2.get_x.return_value = 100
        b2.get_y.return_value = 100
        b2.get_repaire_cost.return_value = 5
        b2.get_id.return_value = 'b2'

        self.agent.blockades = set()
        self.agent.world_model.get_entities.return_value = [b1, b2]

        result = self.agent.get_nearest_blockade()
        self.assertEqual(result, 'b1')

    # Тест Подключения к севрверу
    @patch('src2.rcrs_sample.agents.policeForceAgent.requests')
    def test_think_subscribe_at_initial_time(self, mock_requests):
        self.agent.config.get_value = MagicMock(return_value=1)
        self.agent.think(time_step=1, change_set=None, heard=None)
        self.agent.send_subscribe.assert_called_once()

    # Тест случая без зданий и гражданских
    @patch('src2.rcrs_sample.agents.policeForceAgent.requests')
    def test_think_no_buildings_triggers_not_found(self, mock_requests):
        self.agent.get_sorted_buildings = MagicMock(return_value=[])
        self.agent.get_burning_buildings = MagicMock(return_value=[])
        self.agent.get_civilians = MagicMock(return_value=[])

        self.agent.think(time_step=2, change_set=None, heard=None)
        self.agent.not_found_building_state.assert_called_once()

    # Тест поиска следующего здания
    @patch('src2.rcrs_sample.agents.policeForceAgent.requests')
    def test_think_building_and_location_is_building(self, mock_requests):
        building1 = MagicMock(spec=Building)
        building1.get_id.return_value = MagicMock(get_value=lambda: 1)
        building2 = MagicMock(spec=Building)
        building2.get_id.return_value = MagicMock(get_value=lambda: 2)

        self.agent.get_sorted_buildings = MagicMock(return_value=[building1, building2])
        self.agent.get_burning_buildings = MagicMock(return_value=[])
        self.agent.get_civilians = MagicMock(return_value=[])
        self.agent.location = MagicMock(return_value=MagicMock(spec=Building))
        self.agent.find_way = MagicMock(return_value=[1, 2])
        self.agent.send_move = MagicMock()
        self.agent.send_subscribe = MagicMock()
        self.agent.not_found_building_state = MagicMock()
        self.agent.config.get_value = MagicMock(return_value=0)
        self.agent.get_id = MagicMock(return_value=MagicMock(get_value=lambda: 123))

        self.agent.think(time_step=4, change_set=None, heard=None)

        self.agent.send_move.assert_called_once_with(4, [1, 2])

    # Тест поиска следующей цели на Дороге
    @patch('src2.rcrs_sample.agents.policeForceAgent.requests')
    def test_think_building_and_location_is_road(self, mock_requests):
        building = MagicMock(spec=Building)
        self.agent.get_sorted_buildings = MagicMock(return_value=[building])
        self.agent.get_burning_buildings = MagicMock(return_value=[])
        self.agent.get_civilians = MagicMock(return_value=[])
        self.agent.location.return_value = MagicMock(return_value=MagicMock(spec=Road))
        self.agent.find_way = MagicMock(return_value=[1, 2])
        self.agent.move_nearest_blockade_on_path = MagicMock()

        self.agent.think(time_step=4, change_set=None, heard=None)
        self.agent.send_move.assert_called_once()
        self.agent.move_nearest_blockade_on_path.assert_called_once()

    # Тест поиска гражданского
    @patch('src2.rcrs_sample.agents.policeForceAgent.requests')
    def test_think_with_civilians(self, mock_requests):
        civ = MagicMock()
        civ.get_id.return_value.get_value.return_value = 123
        civ.get_buriedness.return_value = 10
        civ.get_urn.return_value = URN.Entity.CIVILIAN

        self.agent.get_sorted_buildings = MagicMock(return_value=[])
        self.agent.get_burning_buildings = MagicMock(return_value=[])
        self.agent.get_civilians = MagicMock(return_value=[civ])

        self.agent.think(time_step=3, change_set=None, heard=None)
        mock_requests.post.assert_called()

    # Тест расчистки завала
    @patch('src2.rcrs_sample.agents.policeForceAgent.requests')
    def test_think_with_blockade_detected(self, mock_requests):
        building = MagicMock(spec=Building)

        blockade = MagicMock(spec=Blockade)
        blockade_id = MagicMock(EntityID(3))
        blockade.get_id.return_value = blockade_id
        blockade.get_repaire_cost.return_value = 10
        blockade.get_position.return_value = MagicMock()
        blockade.get_x.return_value = 0
        blockade.get_y.return_value = 0

        # Агент стоит рядом с завалом
        self.agent.me.return_value.get_x.return_value = 0
        self.agent.me.return_value.get_y.return_value = 0

        self.agent.location.return_value = MagicMock(spec=Road)
        self.agent.get_sorted_buildings = MagicMock(return_value=[building])
        self.agent.get_burning_buildings = MagicMock(return_value=[])
        self.agent.not_found_building_state = MagicMock()
        self.agent.get_civilians = MagicMock(return_value=[])
        self.agent.get_nearest_blockade_on_path = MagicMock(return_value=blockade_id)
        self.agent.world_model.get_entity = MagicMock(return_value=blockade)
        self.agent.find_way = MagicMock(return_value=[1, 2])
        self.agent.send_clear = MagicMock()
        self.agent.send_move = MagicMock()
        self.agent.send_subscribe = MagicMock()

        # Условие: расстояние < repair.distance
        self.agent.config.get_value = MagicMock(side_effect=lambda key: '5000' if key == 'clear.repair.distance' else 1)

        self.agent.recent_blockade_repair_cost = -1  # не совпадает => вызов send_clear

        self.agent.think(time_step=3, change_set=None, heard=None)

        self.agent.send_clear.assert_called_once_with(3, blockade_id)


if __name__ == '__main__':
    unittest.main()

import unittest
from unittest.mock import MagicMock, patch
from rcrs_core.worldmodel.entityID import EntityID
from rcrs_core.entities.refuge import Refuge
from rcrs_core.entities.building import Building
from rcrs_core.entities.road import Road

from src2.rcrs_sample.agents.fireBrigadeAgent import FireBrigadeAgent


class FireBrigadeAgentTest(unittest.TestCase):
    def setUp(self):
        self.agent = FireBrigadeAgent(pre=None)
        self.agent.world_model = MagicMock()
        self.agent.config = MagicMock()
        self.agent.me = MagicMock()
        self.agent.send_subscribe = MagicMock()
        self.agent.send_rest = MagicMock()
        self.agent.send_move = MagicMock()
        self.agent.send_extinguish = MagicMock()
        self.agent.send_clear = MagicMock()
        self.agent.location = MagicMock()
        self.agent.get_id = MagicMock(return_value=EntityID(1))

    def test_get_refuges_returns_sorted_refuges(self):
        refuge1 = MagicMock(spec=Refuge)
        refuge1.get_x.return_value = 100
        refuge1.get_y.return_value = 200

        refuge2 = MagicMock(spec=Refuge)
        refuge2.get_x.return_value = 300
        refuge2.get_y.return_value = 400

        non_refuge = MagicMock()
        self.agent.me().get_x.return_value = 0
        self.agent.me().get_y.return_value = 0

        self.agent.world_model.get_entities.return_value = [refuge2, refuge1, non_refuge]
        type(refuge1).urn = 'urn:rescuecore2.standard:entity:refuge'
        type(refuge2).urn = 'urn:rescuecore2.standard:entity:refuge'

        with patch('rcrs_core.entities.refuge.Refuge', (lambda *args, **kwargs: Refuge)):
            self.assertEqual(
                self.agent.get_refuges()[0], refuge1,
                "get_refuges() должен возвращать ближайший убежище первым"
            )

    @patch('src2.rcrs_sample.agents.fireBrigadeAgent.get_burning_from_server')
    @patch('src2.rcrs_sample.agents.fireBrigadeAgent.requests.post')
    def test_think_water_zero_goes_to_refuge(self, mock_post, mock_get_burning):
        mock_self_entity = MagicMock()
        mock_self_entity.get_water.return_value = 0
        self.agent.world_model.get_entity.return_value = mock_self_entity

        self.agent.going_to_refuge = False

        refuge = MagicMock(spec=Refuge)
        refuge.get_id.return_value = EntityID(42)
        self.agent.get_refuges = MagicMock(return_value=[refuge])

        self.agent.find_way = MagicMock(return_value=[1, 2, 3])

        mock_road = MagicMock(spec=Road)
        mock_road.get_blockades.return_value = []
        self.agent.location = MagicMock(return_value=mock_road)

        self.agent.think(5, change_set={}, heard={})

        self.agent.send_move.assert_called_once_with(5, [1, 2, 3])
        self.assertTrue(self.agent.going_to_refuge, "Агент должен установить going_to_refuge=True при отсутствии воды")

    @patch('src2.rcrs_sample.agents.fireBrigadeAgent.get_burning_from_server')
    @patch('src2.rcrs_sample.agents.fireBrigadeAgent.requests.post')
    def test_think_extinguishes_fire(self, mock_post, mock_get_burning):
        building = MagicMock(spec=Building)
        building.get_id.return_value = EntityID(55)
        building.get_x.return_value = 100
        building.get_y.return_value = 100
        building.get_fieryness.return_value = 1

        self.agent.me().get_x.return_value = 95
        self.agent.me().get_y.return_value = 95
        self.agent.config.get_value.side_effect = lambda k: '10' if k == 'fire.extinguish.max-distance' else '0'

        self.agent.world_model.get_entities.return_value = [building]

        mock_get_burning.return_value.json.return_value = []

        self.agent.find_way = MagicMock(return_value=[1, 2, 3])

        mock_self_entity = MagicMock()
        mock_self_entity.get_water.return_value = 1000
        self.agent.world_model.get_entity.side_effect = lambda \
            eid: building if eid.get_value() == 55 else mock_self_entity

        self.agent.water = 1000
        self.agent.going_to_refuge = False

        self.agent.think(5, change_set={}, heard={})

        self.agent.send_extinguish.assert_called_once()
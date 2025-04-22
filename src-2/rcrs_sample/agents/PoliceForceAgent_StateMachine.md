# StateMachine для PoliceForceAgent

```python
class PoliceState(Enum):
    SEARCHING = 1
    MOVING_TO_TARGET = 2
    CLEARING_BLOCKADE = 3
    IDLE = 4

class PoliceForceAgent(Agent):
    def __init__(self, pre):
        super().__init__(pre)
        self.state = PoliceState.SEARCHING
        self.target_building = None

    def think(self, time_step, change_set, heard):
        if self.state == PoliceState.SEARCHING:
            self.handle_searching(time_step)
        elif self.state == PoliceState.MOVING_TO_TARGET:
            self.handle_moving_to_target(time_step)
        elif self.state == PoliceState.CLEARING_BLOCKADE:
            self.handle_clearing(time_step)
        elif self.state == PoliceState.IDLE:
            self.handle_idle(time_step)

    def handle_searching(self, time_step):
        buildings = self.get_sorted_buildings()
        if buildings:
            self.target_building = buildings[0]
            self.state = PoliceState.MOVING_TO_TARGET

    def handle_moving_to_target(self, time_step):
        if self.target_building:
            path = self.find_way(self.target_building.get_id())
            self.send_move(time_step, path)
            if self.location().get_id() == self.target_building.get_id():
                self.state = PoliceState.CLEARING_BLOCKADE

    def handle_clearing(self, time_step):
        blockade = self.get_nearest_blockade()
        if blockade:
            self.move_nearest_blockade(time_step, blockade)
        else:
            self.state = PoliceState.SEARCHING

    def handle_idle(self, time_step):
        # Например, можно искать новых гражданских, или ждать сигналов от других агентов
        pass
```

Этот шаблон можно расширять и подключать к существующей логике.
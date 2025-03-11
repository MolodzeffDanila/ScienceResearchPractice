class Node:
    def __init__(self, entity):
        self.id = entity.get_id()
        self.entity = entity
        self.parent = None # Родительский узел, используется для восстановления пути
        self.g = 0  # Расстояние от начального узла до текущего узла
        self.h = 0  # Примерное расстояние от текущего узла до конечного узла
        self.f = 0 # Сумма g и h

    def get_x(self):
        return self.entity.get_x()

    def get_y(self):
        return self.entity.get_y()

    def get_id(self):
        return self.entity.get_id()

    def __lt__(self, other):
        return self.f < other.f

    # Переопределяем оператор равенства для сравнения узлов
    def __eq__(self, other):
        return self.get_id() == other.get_id()
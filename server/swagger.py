from flask import Flask
from flask_restx import Api, fields

app = Flask("centralized")

api = Api(
    app,
    version="1.0",
    title="RCRS API",
    description="API для симуляции спасательных агентов",
    doc="/",
    default="Requests",
)

burning_model = api.model("Burning", {
    "id": fields.Integer(required=True, description="Уникальный идентификатор здания"),
    "fireness": fields.Integer(required=True, description="Степень возгорания (0 — нет огня, 3 — сильный пожар)"),
    "x": fields.Integer(required=True, description="Координата X"),
    "y": fields.Integer(required=True, description="Координата Y")
})

civilian_model = api.model("Civilian", {
    "id": fields.Integer(required=True, description="Идентификатор гражданского"),
    "position": fields.Integer(required=True, description="Позиция гражданского в симуляции"),
    "hp": fields.Integer(required=True, description="Очки здоровья (HP) гражданского"),
    "buriness": fields.Integer(required=True, description="Насколько гражданский завален (0 — не завален, 100 — полностью)")
})

visited_model = api.model("Visited", {
    "id": fields.Integer(required=True, description="Идентификатор здания"),
    "position": fields.Integer(required=True, description="Позиция посещённого здания")
})

blockade_assignment_model = api.model("Blockade", {
    "agent": fields.Integer(required=True, description="ID агента"),
    "id": fields.Integer(required=True, description="ID завала"),
})


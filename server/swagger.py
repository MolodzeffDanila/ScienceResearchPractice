from flask import Flask
from flask_restx import Api, fields

app = Flask("centralized")

api = Api(
    app,
    version="1.0",
    title="RCRS API",
    description="API для симуляции спасательных агентов",
    doc="/",  # чтобы Swagger был доступен сразу по корню
    default="Requests",
)

burning_model = api.model("Burning", {
    "id": fields.Integer(required=True, description="Уникальный идентификатор здания"),
    "fireness": fields.Integer(required=True, description="Степень возгорания (0 — нет огня, 3 — сильный пожар)")
})

civilian_model = api.model("Civilian", {
    "id": fields.Integer(required=True, description="Идентификатор гражданского"),
    "position": fields.String(required=True, description="Позиция гражданского в симуляции"),
    "hp": fields.Integer(required=True, description="Очки здоровья (HP) гражданского"),
    "buriness": fields.Integer(required=True, description="Насколько гражданский завален (0 — не завален, 100 — полностью)")
})

visited_model = api.model("Visited", {
    "id": fields.Integer(required=True, description="Идентификатор здания"),
    "position": fields.String(required=True, description="Позиция посещённого здания")
})


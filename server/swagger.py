from flask import Flask
from flask_restx import Api, fields

app = Flask("centralized")

api = Api(app, version="1.0", title="RCRS API", description="API для симуляции спасательных агентов")

burning_model = api.model("Burning", {
        "id": fields.Integer(required=True),
        "fireness": fields.Integer(required=True),
    })
civilian_model = api.model("Civilian", {
        "id": fields.Integer(required=True),
        "position": fields.String(required=True),
        "hp": fields.Integer(required=True),
        "buriness": fields.Integer(required=True),
})

visited_model = api.model("Visited", {
        "id": fields.Integer(required=True),
        "position": fields.String(required=True),
})

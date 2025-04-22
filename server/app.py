from flask import Flask, request, jsonify
from flask_restx import Resource
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from db_setup import Burning, Civilians, SessionLocal, clear_all_data
from server.db_setup import Visited
from server.dto import CivilianInput, BurningInput
from server.swagger import burning_model, api, civilian_model, visited_model, app


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@api.route("/burning")
class BurningResource(Resource):
    @api.marshal_list_with(burning_model)
    def get(self):
        session = SessionLocal()
        try:
            burning = session.query(Burning).all()
            return burning
        finally:
            session.close()

    @api.expect([burning_model])
    def post(self):
        session = SessionLocal()
        try:
            data = request.get_json()
            burning_data = [BurningInput(**burn) for burn in data]

            for burn in burning_data:
                new_burning = Burning(
                    id=burn.id,
                    fireness=burn.fireness,
                )
                session.merge(new_burning)
            session.commit()
            return jsonify({"status": "success"}), 201

        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            session.close()


@api.route("/civilians")
class CiviliansResource(Resource):
    @api.marshal_list_with(civilian_model)
    def get(self):
        session = SessionLocal()
        try:
            return session.query(Civilians).all()
        finally:
            session.close()

    @api.expect([civilian_model])
    def post(self):
        session = SessionLocal()
        try:
            data = request.get_json()
            civilians_data = [CivilianInput(**civ) for civ in data]

            for civ in civilians_data:
                civilian = Civilians(
                    id=civ.id,
                    position=civ.position,
                    hp=civ.hp,
                    buriness=civ.buriness
                )
                session.merge(civilian)
            session.commit()
            return jsonify({"status": "success"}), 201

        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400
        except Exception as e:
            session.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            session.close()


@api.route("/visited")
class VisitedResource(Resource):
    @api.marshal_list_with(visited_model)
    def get(self):
        session = SessionLocal()
        try:
            return session.query(Visited).all()
        finally:
            session.close()

    @api.expect(visited_model)
    def post(self):
        data = request.get_json()
        session = SessionLocal()
        try:
            building = Visited(
                id=data['id'],
                position=data['position']
            )
            session.merge(building)
            session.commit()
            return jsonify({'status': 'merged'}), 200

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            session.close()


def run_app():
    app.run(
        debug=True,
        use_reloader=False,
        host="127.0.0.1",
        port=5000
    )


if __name__ == "__main__":
    clear_all_data()
    run_app()

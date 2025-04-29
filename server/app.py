from flask import request, jsonify
from flask_restx import Resource
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from db_setup import Burning, Civilians, SessionLocal, clear_all_data, Base, engine
from server.db_setup import Visited, Blockade
from server.dto import CivilianInput, BurningInput
from server.swagger import burning_model, api, civilian_model, visited_model, app, blockade_assignment_model, \
    civilian_delete_model


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@api.route("/burning")
class BurningResource(Resource):
    @api.doc(description="Получить список всех горящих зданий")
    @api.marshal_list_with(burning_model)
    def get(self):
        session = SessionLocal()
        try:
            burning = session.query(Burning).all()
            return burning
        finally:
            session.close()

    @api.doc(description="Добавить или обновить данные о горящих зданиях")
    @api.expect([burning_model], validate=True)
    @api.response(201, "Данные успешно добавлены")
    @api.response(400, "Ошибка валидации")
    @api.response(500, "Ошибка сервера")
    def post(self):
        session = SessionLocal()
        try:
            data = request.get_json()
            burning_data = [BurningInput(**burn) for burn in data]

            for burn in burning_data:
                new_burning = Burning(
                    id=burn.id,
                    fireness=burn.fireness,
                    x=burn.x,
                    y=burn.y
                )
                session.merge(new_burning)
            session.commit()
            return {"status": "success"}, 201

        except ValidationError as e:
            return {"error": e.errors()}, 400
        except Exception as e:
            session.rollback()
            return {"error": str(e)}, 500
        finally:
            session.close()


@api.route("/civilians")
class CiviliansResource(Resource):
    @api.doc(description="Получить список всех гражданских")
    @api.marshal_list_with(civilian_model)
    def get(self):
        session = SessionLocal()
        try:
            return session.query(Civilians).all()
        finally:
            session.close()

    @api.doc(description="Добавить или обновить данные о гражданских")
    @api.expect([civilian_model], validate=True)
    @api.response(201, "Данные успешно добавлены")
    @api.response(400, "Ошибка валидации")
    @api.response(500, "Ошибка сервера")
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
                    buriness=civ.buriness,
                    x=civ.x,
                    y=civ.y
                )
                session.merge(civilian)
            session.commit()

            return {"status": "merged"}, 201

        except ValidationError as e:
            return {"error": e.errors()}, 400

        except Exception as e:
            session.rollback()
            return {"error": str(e)}, 500

        finally:
            session.close()

@api.route("/civilians/delete")
class CiviliansDeleteResource(Resource):
    @api.doc(description="Удалить гражданского по ID через POST-запрос")
    @api.expect([civilian_delete_model])
    @api.response(200, "Удалено успешно")
    @api.response(400, "ID не передан")
    @api.response(404, "Гражданский не найден")
    @api.response(500, "Ошибка сервера")
    def post(self):
        session = SessionLocal()
        try:
            data = request.get_json()

            if not data or 'id' not in data:
                return {"error": "ID is required"}, 400

            civ_id = data['id']
            civilian = session.query(Civilians).filter(Civilians.id == civ_id).first()

            if civilian:
                session.delete(civilian)
                session.commit()
                return {"status": "deleted"}, 200
            else:
                return {"error": "Civilian not found"}, 404

        except Exception as e:
            session.rollback()
            return {"error": str(e)}, 500

        finally:
            session.close()


@api.route("/visited")
class VisitedResource(Resource):
    @api.doc(description="Получить список посещённых зданий")
    @api.marshal_list_with(visited_model)
    def get(self):
        session = SessionLocal()
        try:
            return session.query(Visited).all()
        finally:
            session.close()

    @api.doc(description="Добавить или обновить информацию о посещённом здании")
    @api.expect(visited_model, validate=True)
    @api.response(200, "Запись обновлена")
    @api.response(500, "Ошибка базы данных")
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

@api.route("/blockades")
class BlockadeResource(Resource):
    @api.expect(blockade_assignment_model)
    @api.response(200, "Запись обновлена")
    @api.response(500, "Ошибка базы данных")
    def post(self):
        data = request.get_json()
        session = SessionLocal()

        try:
            assignment = Blockade(
                agent=data["agent"],
                id=data["id"],
            )
            session.merge(assignment)
            session.commit()
            return jsonify({'status': 'merged'})

        except SQLAlchemyError as e:
            session.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            session.close()

    @api.doc(description="Получить список взятых в работу завалов")
    @api.marshal_list_with(blockade_assignment_model)
    def get(self):
        session = SessionLocal()
        assignments = session.query(Blockade).all()
        result = [{
            "agent": a.agent,
            "id": a.id,
        } for a in assignments]
        session.close()
        return result, 200



def run_app():
    app.run(
        debug=True,
        use_reloader=False,
        host="127.0.0.1",
        port=5000
    )


if __name__ == "__main__":
    #Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    clear_all_data()
    run_app()

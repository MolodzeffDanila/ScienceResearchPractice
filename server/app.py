from flask import Flask, request

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db_setup import Base, Burning, Civilians
from server.db_setup import Visited

app = Flask('centralized')

engine = create_engine('sqlite:///database.db?check_same_thread=False')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.get("/burning")
def get_burning_buildings():
    return session.query(Burning).all()

@app.post("/burning")
def add_burning():
    building = Burning(
        id = request.form['id'],
        fireness = request.form['fireness']
    )
    session.add(building)
    session.commit()

@app.get("/civilians")
def get_civilians():
    return session.query(Civilians).all()

@app.post("/civilians")
def add_civilian():
    civ = Civilians(
        id = request.form['id'],
        position = request.form['positions'],
        hp = request.form['hp'],
        buriness = request.form['buriness']
    )
    session.add(civ)
    session.commit()

@app.get("/visited")
def get_visited():
    return session.query(Visited).all()

@app.post("/visited")
def add_visited():
    visited = Visited(
        id = request.form['id'],
        position = request.form['position']
    )
    session.add(visited)
    session.commit()

if __name__ == '__main__':
    app.debug = True
    app.run(port=5000)
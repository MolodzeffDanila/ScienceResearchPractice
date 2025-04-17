from flask import Flask, g
import sqlite3

app = Flask('centralized')

DATABASE = './tables/database.db'

@app.route("/")
def hello_world():
    cursor = get_db().cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS burning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fireness INTEGER
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS civilians (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        position INTEGER,
        hp INTEGER,
        buriness INTEGER
    )
    ''')
    return "<p>Hello, World!</p>"

@app.get("/burning")
def get_burning_buildings():
    pass

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
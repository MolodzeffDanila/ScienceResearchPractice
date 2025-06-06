from pydantic import BaseModel, ValidationError

class CivilianInput(BaseModel):
    id: int
    position: int
    hp: int
    buriness: int
    x: int
    y: int

class BurningInput(BaseModel):
    id: int
    fireness: int
    x: int
    y: int
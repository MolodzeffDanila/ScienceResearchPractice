import requests

from server.constants import SERVER_HOST


def get_civilians_from_server():
    return requests.get(f'{SERVER_HOST}/civilians')

def get_burning_from_server():
    return requests.get(f'{SERVER_HOST}/burning')

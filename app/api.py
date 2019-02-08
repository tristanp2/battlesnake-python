import json
from bottle import HTTPResponse

def ping_response():
    return HTTPResponse(
        status=200
        )

def start_response(color):
    return HTTPResponse(
            status=200,
            headers={
                "Content-Type": "application/json"
            },
            body=json.dumps({
                "color": color
            })
        )
def move_response(move):
    return HTTPResponse(
            status=200,
            headers={
                "Content-Type": "application/json"
            },
            body=json.dumps({
                "move": move
            })
        )
def end_response():
    return HTTPResponse(
            status=200
        )

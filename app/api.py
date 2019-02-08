import json
from bottle import HTTPResponse

def ping_response():
    print('sending ping response')
    return HTTPResponse(
        status=200
        )

def start_response(color):
    print('sending start response')
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
    print('sending move response')
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
    print('sending end response')
    return HTTPResponse(
            status=200
        )

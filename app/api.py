import json
from bottle import HTTPResponse

def convert_move_data(data):
    new_data = {}
    if not 'object' in data:
        return data
    else:
        new_data['game'] = {'id': data['id']}
        new_data['board'] = {'height': data['height'],'width': data['width'], 'food': data['food']['data']}
        new_data['turn'] = data['turn']
        new_data['you'] = data['you']
        new_data['you']['body'] = data['you']['body']['data']
        snakes = data['snakes']['data']
        for snake in snakes:
            snake['body'] = snake['body']['data']
        
        new_data['board']['snakes'] = snakes
        return new_data

        
        

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
            body=json.dumps(color)
        )
def move_response(move):
    print('sending move response')
    return HTTPResponse(
            status=200,
            headers={
                "Content-Type": "application/json"
            },
            body=json.dumps(move)
        )
def end_response():
    print('sending end response')
    return HTTPResponse(
            status=200
        )

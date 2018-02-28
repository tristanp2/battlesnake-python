from __future__ import print_function
import bottle
import os
import random
from search import AStar, in_dict
from time import clock



@bottle.route('/')
def static():
    return "the server is running"


@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root='static/')


@bottle.post('/start')
def start():
    data = bottle.request.json
    game_id = data.get('game_id')
    board_width = data.get('width')
    board_height = data.get('height')

    head_url = '%s://%s/static/head.png' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    # TODO: Do things with data

    return {
        'color': '#00FF00',
        'taunt': '{} ({}x{})'.format(game_id, board_width, board_height),
        'head_url': head_url
    }

def parse_point(point_obj):
    return (point_obj["x"],point_obj["y"])

def get_direction(src, dest):
    (x1,y1) = src
    (x2,y2) = dest
    dx = x2 - x1
    dy = y2 - y1
    if dx > 0:  return "right"
    if dx < 0:  return "left"
    if dy > 0:  return "down"

    return "up"

@bottle.post('/move')
def move():
    tick_start = clock()
    data = bottle.request.json

    food = data["food"]["data"]
    height = data["height"]
    my_id = data["you"]["id"]
    snakes = data["snakes"]["data"]
    obstacles = {}


    head_pos = None
    for snake in snakes:
        body_data = snake["body"]["data"]
        if snake.get("id") == my_id:
            our_snake = snake
            head_pos = parse_point(body_data[0])
            body_data = body_data[1:]

        for obj in body_data:
            new_point = parse_point(obj)
            print("Adding {} to obstacles".format(new_point))
            obstacles[new_point] = None 
    
    if in_dict(obstacles, head_pos):
        del obstacles[head_pos]

    print("Obstacles: ", obstacles.keys())
    
    if head_pos == None:
        print("we dead")
    else:
        path_finder = AStar(height, head_pos, obstacles)

    target = parse_point(food[0])

    path = path_finder.search(target)
    dest = path[-2]
    print("moving from {} to {}".format(head_pos,dest))
    direction = get_direction(head_pos,dest)
    print(direction)
    tick_end = clock()
    tick_duration = tick_end - tick_start
    print("Elapsed: {}ms".format(tick_duration*1000))
    return {
        'move': direction,
        'taunt': 'battlesnake-python!'
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '0.0.0.0'),
        port=os.getenv('PORT', '8080'),
        debug = True)

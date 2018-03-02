from __future__ import print_function
import bottle
import os
import random
import json
from search import AStar, in_dict, get_neighbours
from time import clock



@bottle.route('/')
def static():
    return "the server is running"


@bottle.route('/static/<path:path>')
def static(path):
    return bottle.static_file(path, root='static/')

board_width = 0
board_height = 0

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
        'color': '#DD00DD',
        'taunt': '{} ({}x{})'.format(game_id, board_width, board_height),
        'head_url': head_url,
        'head_type': 'safe',
        'tail_type': 'small-rattle'
    }

def parse_point(point_obj):
    return (point_obj["x"],point_obj["y"])

#assumes head is first in list
def extend_head(body_points, board_size):
    body_points = list(body_points)
    head = body_points[0]
    neighbours = get_neighbours(head,board_size)
    body_set = set(body_points)
    extension = []
    for neighbour in neighbours:
        if neighbour not in body_set:
            extension.append(neighbour)
            body_points.insert(0,neighbour)

    print("extension of {}: {}".format(head, extension))
    return extension

#assumes tail is last in list
def shrink_tail(body_points):
    return body_points[:-1]

#converts list of point dicts to list of tuples
def parse_body_data(body_data):
    return map(parse_point, body_data)

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
    try:
        info = json.load(open("info.json","r"))
    except:
        info = {}
        info["ticks"] = 0

    print("tick:",info["ticks"])
    info["ticks"] += 1



    food = data["food"]["data"]
    board_width  = data["width"]
    board_height = data["height"]
    board_size = (board_width, board_height)
    my_id = data["you"]["id"]
    snakes = data["snakes"]["data"]

    #should change this to a set
    obstacles = set()
    extended_obstacles = set()
    head_pos = None
    for snake in snakes:
        body_points = parse_body_data(snake["body"]["data"])
        if snake.get("id") == my_id:
            our_snake = snake
            head_pos = body_points[0]
            body_points = body_points[1:]
        else:
            #TODO:in future, heads should only be extended based on certain criteria:
            #       - in certain range of our head
            #       - owning snake is as big as our snake
            extended_obstacles.update(extend_head(body_points,board_size))

            #TODO:tail positions should only be removed when the owning snake's head is not
            # one space away from food. this also goes for our snake
            tail_pos = body_points[-1]
            if tail_pos in extended_obstacles:
                extended_obstacles.remove(tail_pos)

        obstacles.update(body_points)
    
    if head_pos in obstacles:
        obstacles.remove(head_pos)
    if head_pos in extended_obstacles:
        extended_obstacles.remove(head_pos)

    extended_obstacles = extended_obstacles.union(obstacles)

    print("head: ", head_pos)
    print("Obstacles: ", obstacles)
    print("ExtendedObstacles: ", extended_obstacles)
    
    if head_pos == None:
        print("we dead")
    else:
        path_finder = AStar((board_width, board_height), head_pos)

    target = parse_point(food[0])
    print("target: ", target)

    #prefer to avoid entering extended obstacles
    #TODO: remove extended head positions from obstacles if the head belongs
    #   to a smaller snake
    #       in future, the following code will be last resort, after no valid targets are found
    dest = None
    backup_dest = None
    path = path_finder.search(target, extended_obstacles)
    if path == None:
        print("second pathfind attempt")
        path = path_finder.search(target, obstacles)

    if target in extended_obstacles or path == None:
        print("find new target!!!")
        neighbours = get_neighbours(head_pos, board_size)
        for neighbour in neighbours:
            if neighbour not in extended_obstacles:
                dest = neighbour
                break
            elif neighbour not in obstacles:
                backup_dest = neighbour
    else:
        dest = path[-2]

    if dest == None and backup_dest != None:
        print("using backup dest")
        dest = backup_dest
    elif dest == None and backup_dest == None:
        print("we r fuked")

    print("moving from {} to {}".format(head_pos,dest))
    direction = get_direction(head_pos,dest)
    print(direction)
    tick_end = clock()
    tick_duration = tick_end - tick_start
    print("Elapsed: {}ms".format(tick_duration*1000))
    
    json.dump(info, open("info.json","w"))
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

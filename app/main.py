from __future__ import print_function
import bottle
import os
import random
import json
from search import AStar, in_dict, get_neighbours, manhattan_dist, flood_fill
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

    #setup persistent info
    info = {}
    info["ticks"] = 0
    import socket
    taunt = socket.gethostname()
    info["taunt"] = taunt


    json.dump(info, open('info.json', 'w'))
    print("info file created")

    

    return {
        'color': '#DD00DD',
        'secondary_color': '0000FF',
        'taunt': taunt,
        'head_url': head_url,
        'head_type': 'safe',
        'tail_type': 'small-rattle'
    }

def sample_surrounding_pos(pos, board_size, dist = 3):
    width,height = board_size
    (x,y) = board_size
    x0 = pos[0] - dist
    x1 = pos[0] + dist
    y0 = pos[1] - dist
    y1 = pos[1] + dist
    x00 = pos[0] - dist/2
    x01 = pos[0] + dist/2
    y00 = pos[1] - dist/2
    y01 = pos[1] + dist/2
    
    ret_list = []

    if x0 > 0:
        ret_list.append((x0,y))
    if x1 < width:
        ret_list.append((x1,y))
    if y0 > 0:
        ret_list.append((x,y0))
    if y1 < height:
        ret_list.append((x,y1))

    if x00 > 0:
        if y00 > 0:
            ret_list.append((x00,y00))
        if y01 < height:
            ret_list.append((x00,y01))
    if x01 < width:
        if y00 > 0:
            ret_list.append((x01,y00))
        if y01 < height:
            ret_list.append((x01,y01))

    return ret_list 

def find_most_open_sampled_pos(pos, board_size, obstacles, dist = 3):
    sampled = sample_surrounding_pos(pos, board_size, dist)
    best_open = -1
    best_pos = ()
    
    for sample in sampled:
        samp_open = flood_fill(sample, board_size, obstacles)
        if samp_open > best_open:
            best_pos = sample
            best_open = samp_open

    return (best_pos, best_open)
        

def find_closest_pos_dist(pos, pos_list):
    min_dist = 10000
    ret_pos = None
    for targ_pos in pos_list:
        dist = manhattan_dist(pos, targ_pos)
        if dist < min_dist:
            min_dist = dist
            ret_pos = targ_pos
    return (ret_pos, min_dist)

def find_closest_dist(pos, pos_list):
    return find_closest_pos_dist(pos,pos_list)[1]
    
def find_closest_pos(pos, pos_list):
    return find_closest_pos_dist(pos,pos_list)[0]

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
def parse_point_list(body_data):
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
        #get information saved from previous tick
        info = json.load(open("info.json","r"))
    except:
        #if no information was saved, initialize info
        print("No json info found")
        info = {}
        info["ticks"] = 0
        info["taunt"] = "debug"

    print("tick:",info["ticks"])
    info["ticks"] += 1
    taunt = info["taunt"]


    foods = parse_point_list(data["food"]["data"])
    board_width  = data["width"]
    board_height = data["height"]
    board_size = (board_width, board_height)
    my_snake = data["you"]
    my_id = my_snake["id"]
    my_body = parse_point_list(my_snake["body"]["data"])
    my_head_pos = my_body[0]
    my_tail_pos = my_body[-1]
    my_health = my_snake["health"]
    my_size = len(my_body)
    snakes = data["snakes"]["data"]

    closest_to_food = {}
    for food in foods:
        closest_to_food[food] = {}
        closest_to_food[food]["dist"] = 10000

    #obstacles gathering loop
    obstacles = set()
    extended_obstacles = set()
    for snake in snakes:
        body_points = parse_point_list(snake["body"]["data"])
        if snake.get("id") == my_id:
            body_points = body_points[1:]

            food_pos, food_dist = find_closest_pos_dist(my_head_pos, foods)
            if food_dist < closest_to_food[food_pos]["dist"]:
                closest_to_food[food_pos]["dist"] = food_dist
                closest_to_food[food_pos]["id"] = snake.get("id")

            if food_dist > 1:
                body_points = body_points[:-1]
        else:
            #TODO: moving into a head extension of a smaller snake might be a really good offensive move
            #       need to make sure to not get into shit while doing it though
            #heads should only be extended based on certain criteria:
            #       - in certain range of our head
            #       - owning snake is as big as our snake
            head_pos = body_points[0]
            snake_dist = find_closest_dist(my_head_pos, body_points)
            snake_size = len(body_points)
            food_pos, food_dist = find_closest_pos_dist(head_pos, foods)
            if food_dist < closest_to_food[food_pos]["dist"]:
                closest_to_food[food_pos]["dist"] = food_dist
                closest_to_food[food_pos]["id"] = snake.get("id")

            if snake_dist < 5 and snake_size >= my_size:
                extended_obstacles.update(extend_head(body_points,board_size))

            #tail positions should only be removed when the owning snake's head is not
            # one space away from food. this also goes for our snake
            tail_pos = body_points[-1]
            if food_dist >  1:
                body_points = body_points[:-1]

        obstacles.update(body_points)
    
    print(closest_to_food)
    closest_food_pos, closest_food_dist = find_closest_pos_dist(my_head_pos, foods)
    print(closest_food_pos, closest_food_dist)
    if my_health > 40 and closest_food_dist > closest_to_food[closest_food_pos]["dist"]:
        target = my_tail_pos
    else:
        target = closest_food_pos

    #only reason these might be needed is if some extension obstacle happens to be our head pos
    if my_head_pos in obstacles:
        print("WTFFFFFFFF")
        obstacles.remove(my_head_pos)
    if my_head_pos in extended_obstacles:
        extended_obstacles.remove(my_head_pos)

    extended_obstacles = extended_obstacles.union(obstacles)

    print("head: ", my_head_pos)
    
    path_finder = AStar((board_width, board_height), my_head_pos)

    print("target: ", target)

    #prefer to avoid entering extended obstacles
    #       in future, the following code will be last resort, after no valid targets are found
    #TODO:  Need to find way to quantify openness of region of space to determine how safe it is
    #       Maybe average number of open neighbours per space?
    dest = None
    backup_dest = None
    path = path_finder.search(target, extended_obstacles)
    if path == None:
        print("second pathfind attempt")
        path = path_finder.search(target, obstacles)
    openness = flood_fill(target,board_size,extended_obstacles)

    print("target openness: ", openness)
    if target in extended_obstacles or path == None:
        print("find new target!!!")
        neighbours = get_neighbours(my_head_pos, board_size)
        print("finding valid space in: ", neighbours)
        for neighbour in neighbours:
            if neighbour not in extended_obstacles:
                dest = neighbour
                break
            elif neighbour not in obstacles:
                backup_dest = neighbour
    elif openness < my_size*2:
        print("heading to deadend?")
        target, openness = find_most_open_sampled_pos(my_head_pos, board_size, extended_obstacles)
        
        path = path_finder.search(target, extended_obstacles)
        if path == None:
            sampled = sample_surrounding_pos(my_head_pos, board_size)
            dest = None
            print("sampled: ", sampled)
            for sample in sampled:
                openness = flood_fill(sample, board_size, extended_obstacles)
                print(sample, ": ", openness)
                if sample != target and sample not in extended_obstacles:
                    path = path_finder.search(sample, extended_obstacles)
                    if path != None:
                        dest = path[-2]
    else:
        dest = path[-2]

    if dest == None and backup_dest != None:
        print("using backup dest")
        dest = backup_dest
    elif dest == None and backup_dest == None:
        print("we r fuked")


    print("moving from {} to {}".format(my_head_pos,dest))
    direction = get_direction(my_head_pos,dest)
    print(direction)
    tick_end = clock()
    tick_duration = tick_end - tick_start
    print("Elapsed: {}ms".format(tick_duration*1000))
    
    json.dump(info, open("info.json","w"))
    return {
        'move': direction,
        'taunt': taunt
    }


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '0.0.0.0'),
        port=os.getenv('PORT', '8080'),
        debug = True)

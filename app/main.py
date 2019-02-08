from __future__ import print_function
import bottle
import os
import random
import json
from search import AStar, in_dict, get_neighbours, manhattan_dist, flood_fill
from time import clock


taunts = [
          'Go on, prove me wrong. Destroy the fabric of the universe. See if I care.',
          'He had delusions of adequacy.',
          'There\'s nothing wrong with you that reincarnation won\'t cure.',
          'I didn\'t attend the funeral, but I sent a nice letter saying I approved of it',
          'I have never killed a man, but I have read many obituaries with great pleasure.',
          'He had no enemies, but was intensely disliked by his friends.'
          ]

@bottle.route('/')
def static():
    return 'the server is running'


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

    head_url = '%s://%s/static/head.gif' % (
        bottle.request.urlparts.scheme,
        bottle.request.urlparts.netloc
    )

    #setup persistent info
    info = {}
    info['ticks'] = 0
    import socket
    taunt = socket.gethostname()
    info['taunt'] = taunt


    json.dump(info, open('info.json', 'w'))
    print('info file created')

    return {
        'color': '#DD00DD',
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
    return (point_obj['x'],point_obj['y'])

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

    print('extension of {}: {}'.format(head, extension))
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
    if dx > 0:  return 'right'
    if dx < 0:  return 'left'
    if dy > 0:  return 'down'

    return 'up'

@bottle.post('/move')
def move():
    tick_start = clock()
    data = bottle.request.json
    
    FOOD_THRESHOLD = 60
    PECKISH_THRESHOLD = 80

    try:
        #get information saved from previous tick
        info = json.load(open('info.json','r'))
    except:
        #if no information was saved, initialize info
        print('No json info found')
        info = {}
        info['ticks'] = 0
        info['taunt'] = 'debug'

    print('tick:',info['ticks'])
    info['ticks'] += 1
    taunt = info['taunt']


    foods = parse_point_list(data['board']['food'])
    num_food = len(foods)
    board_width  = data['board']['width']
    board_height = data['board']['height']
    board_size = (board_width, board_height)
    my_snake = data['you']
    my_id = my_snake['id']
    my_body = parse_point_list(my_snake['body'])
    my_head_pos = my_body[0]
    my_tail_pos = my_body[-1]
    my_health = my_snake['health']
    my_size = len(my_body)
    snakes = data['board']['snakes']
    num_snakes = len(snakes)

    closest_to_food = {}
    for food in foods:
        closest_to_food[food] = {}
        closest_to_food[food]['dist'] = 10000

    #obstacles gathering loop
    obstacles = set()
    extended_obstacles = set()
    head_extension_debug = []
    for snake in snakes:
        body_points = parse_point_list(snake['body'])
        if snake.get('id') == my_id:
            food_pos, food_dist = find_closest_pos_dist(my_head_pos, foods)
            if food_dist < closest_to_food[food_pos]['dist']:
                closest_to_food[food_pos]['dist'] = food_dist
                closest_to_food[food_pos]['id'] = snake.get('id')

            if food_dist > 1:
                body_points = body_points[:-1]
        else:
            #TODO: moving into a head extension of a smaller snake might be a really good offensive move
            #       need to make sure to not get into shit while doing it though
            #heads should only be extended based on certain criteria:
            #       - in certain range of our head
            #       - owning snake is as big as our snake
            head_pos = body_points[0]
            snake_dist = manhattan_dist(my_head_pos, head_pos)
            snake_size = len(body_points)
            food_pos, food_dist = find_closest_pos_dist(head_pos, foods)
            if food_dist < closest_to_food[food_pos]['dist']:
                closest_to_food[food_pos]['dist'] = food_dist
                closest_to_food[food_pos]['id'] = snake.get('id')

            if snake_dist == 2 and snake_size < my_size:
                #offense!
                pass
            elif snake_dist < 5:
                extension = extend_head(body_points,board_size)
                head_extension_debug.extend(extension)
                extended_obstacles.update(extension)

            if manhattan_dist(my_head_pos, head_pos) < 3 and (head_pos[0] == 0 or head_pos[1] == 0):
                print('ATTACCHCCHCK')

            #tail positions should only be removed when the owning snake's head is not
            # one space away from food. this also goes for our snake
            tail_pos = body_points[-1]
            if food_dist >  1:
                body_points = body_points[:-1]

        obstacles.update(body_points)
    
    print('tailpos obst: ', my_tail_pos in extended_obstacles)
    closest_food_pos, closest_food_dist = find_closest_pos_dist(my_head_pos, foods)
    print('head extensions: ',  head_extension_debug)
    if (num_food > num_snakes and my_health > FOOD_THRESHOLD) or (num_food <= num_snakes and my_health > PECKISH_THRESHOLD):
        target = my_tail_pos
    else:
        target = closest_food_pos

    extended_obstacles = extended_obstacles.union(obstacles)
    pathfind_extended_obstacles = extended_obstacles - set([my_head_pos])
    pathfind_obstacles = obstacles - set([my_head_pos])
    space_cost = {}
    for x in range(board_width):
        for y in range(board_height):
            pos = (x,y)
            if pos not in pathfind_obstacles:
                neighbours = get_neighbours(pos, board_size) 
                cost = 5
                for n in neighbours:
                    if n not in extended_obstacles:
                        cost -= 1
                space_cost[pos] = max(cost,0)
                

    print('head: ', my_head_pos)
    path_finder = AStar((board_width, board_height), my_head_pos)

    print('target: ', target)

    print(my_tail_pos)
    #prefer to avoid entering extended obstacles
    #       in future, the following code will be last resort, after no valid targets are found
    dest = None
    backup_dest = None
    path = path_finder.search(target, pathfind_extended_obstacles, space_cost)
    if path == None:
        print('second pathfind attempt')
        path = path_finder.search(target, pathfind_obstacles, space_cost)

    if target in extended_obstacles or path == None:
        print('find new target!!!')
        neighbours = get_neighbours(my_head_pos, board_size)
        best_open = -1
        best_dest = None
        print('finding valid space in: ', neighbours)
        for neighbour in neighbours:
            print(neighbour)
            if neighbour not in extended_obstacles:
                openness = flood_fill(neighbour, board_size, extended_obstacles)
                print(neighbour,openness)
                if openness > best_open:
                    best_dest = neighbour
                    best_open = openness
                break
            elif neighbour not in obstacles:
                print('backup')
                backup_dest = neighbour
        dest = best_dest
        print('most open is: ', best_open,best_dest)
    else:
        dest = path[-2]


    if dest == None and backup_dest != None:
        print('using backup dest')
        dest = backup_dest
    elif dest == None and backup_dest == None:
        print('we r fuked')
    print('obst: ', extended_obstacles)
    if dest == my_tail_pos:
        openness = my_size*2
    else:
        openness = flood_fill(dest,board_size,extended_obstacles)
    if openness < my_size*2:
        print('heading to deadend?')
        neighbours = get_neighbours(my_head_pos, board_size)
        best_open = -1
        best_dest = None
        print('checking neighbours...')
        for neighbour in neighbours:
            if neighbour not in extended_obstacles:
                print(neighbour, 'is potential move')
                openness = flood_fill(neighbour, board_size, extended_obstacles)
                if openness > best_open:
                    best_open = openness
                    best_dest = neighbour
            else:
                print(neighbour, ' in obstacles')

        if best_dest == None:
            for neighbour in neighbours:
                if neighbour not in obstacles:
                    dest = neighbour
                    break
        else:
            dest = best_dest

    print(my_head_pos in extended_obstacles)
    print('dest openness: ', flood_fill(dest, board_size, extended_obstacles))

    print('moving from {} to {}'.format(my_head_pos,dest))
    direction = get_direction(my_head_pos,dest)
    print(direction)
    tick_end = clock()
    tick_duration = tick_end - tick_start
    print('Elapsed: {}ms'.format(tick_duration*1000))
    
    json.dump(info, open('info.json','w'))
    
    n_dead = len(snakes) % len(taunts)
    return {
        'move': direction,
    }

@bottle.post('\end')
def end():
    return True

@bottle.post('\ping')
def ping():
    return True


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    bottle.run(
        application,
        host=os.getenv('IP', '0.0.0.0'),
        port=os.getenv('PORT', '8080'),
        debug = True)

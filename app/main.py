from __future__ import print_function
import bottle
import os
import random
import json
from search import AStar, in_dict, get_neighbours, manhattan_dist, flood_fill
from api import ping_response, start_response, move_response, end_response, convert_move_data
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

    return start_response({'color': '#AADDAA'})

directions = ['up','down','left','right']
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
def extend_head(body_points, board_size, my_head_pos):
    body_points = list(body_points)
    head = body_points[0]
    head_dist = min(3, manhattan_dist(head, my_head_pos))

    body_set = set(body_points)
    neighbours = get_neighbours(head,board_size)
    direction = get_direction(body_points[1], body_points[0])
    extension = []

    for i in range(1, head_dist):
        x, y = head
        if direction == 'up':
            extension.append((x, y - i))
            extension.append((x - i//2, y))
            extension.append((x + i//2, y))
        elif direction == 'right':
            extension.append((x + i, y))
            extension.append((x, y + i//2))
            extension.append((x, y - i//2))
        elif direction == 'down':
            extension.append((x, y + i))
            extension.append((x - i//2, y))
            extension.append((x + i//2, y))
        else:
            extension.append((x - i,  y))
            extension.append((x, y + i//2))
            extension.append((x, y - i//2))

    for point in extension:
        body_set.add(point)

    for neighbour in neighbours:
        if neighbour not in body_set:
            extension.append(neighbour)
            body_points.insert(0,neighbour)

    print('extension of {}: {}'.format(head, extension))
    return extension

#assumes tail is last in list
def shrink_tail(body_points):
    return body_points[:-1]

def shrink_me(my_body):
    head = my_body[0]
    tail = my_body[-1]
    snake_len = len(my_body)
    new_body = []
    removed = []

    # don't shrink until after first food
    if snake_len <= 3:
        return (my_body, removed)

    # want to exclude body points that will be empty spaces by the time their pos is reached
    # i.e further from head than they are from tail
    for (i, point) in enumerate(my_body):
        head_dist = manhattan_dist(head, point)
        tail_dist = snake_len - i - 1

        if head_dist <= tail_dist:
            new_body.append(point)
        else:
            removed.append(point)

    return (new_body, removed)

def unshrink_me(my_body, removed, food_pos):
    original_body = my_body + removed
    removed_len = len(removed)
    head = original_body[0]
    tail = original_body[-1]
    new_body = my_body

    head_dist = manhattan_dist(head, food_pos)
    print('head dist from food', head_dist) 
    for (i, point) in enumerate(removed):
        dist = removed_len - i - 1
        print(point)
        print('dist: ', dist)

        if head_dist >= dist:
            new_body.append(point)
    return new_body

def shrink_snake(snake_body, my_head_pos):
    min_dist = 0
    for point in snake_body:
        dist = manhattan_dist(my_head_pos, point)
        if dist < min_dist:
            min_dist = dist

    print('min_dist: ', min_dist) 
    if min_dist == 0:
        return snake_body
    elif min_dist  < len(snake_body):
        return snake_body[:-(min_dist-1)]
    else:
        return [snake_body[0]]
def same_sign(num1, num2):
    return (num1 >= 0 and num2 >= 0) or (num1 < 0 and num2 < 0)
def p2_outside_p1(refpoint, point, centerpoint):
    rx, ry = refpoint
    x, y = point
    cx, cy = centerpoint

    drx = cx - rx
    dry = cy - ry

    dx = cx - x
    dy = cy - y

    ref_dist = manhattan_dist(refpoint, centerpoint)
    dist = manhattan_dist(point, centerpoint)


    if same_sign(drx, dx) and same_sign(dry, dy):
        if ref_dist < dist:
            return True
    return False

            

        

#converts list of point dicts to list of tuples
def parse_point_list(body_data):
    return map(parse_point, body_data)

def get_next_pos_in_direction(p, direction):
    x, y = p
    if direction == 'up':
        return (x, y - 1)
    elif direction == 'right':
        return (x + 1, y)
    elif direction == 'down':
        return (x, y + 1)
    elif direction == 'left':
        return (x - 1, y)

def in_bounds(p, board_size):
    w, h = board_size
    x, y = p
    if x < 0 or x > w - 1 or y < 0 or y > h -1:
        return False
    return True

def get_predicted_snake_pos(snake_body, board_size, obstacles):
    head = snake_body[0]
    neck = snake_body[1]

    direction = get_direction(neck, head)

    dest = get_next_pos_in_direction(head, direction)
    
    i = 0
    while dest not in obstacles and not in_bounds(dest, board_size) or i > 3:
        d = directions[i]
        dest = get_next_pos_in_direction(head, d)
        i += 1
    
    return dest
    
    

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
    data = convert_move_data(bottle.request.json)
    
    FOOD_THRESHOLD = 70

    try:
        #get information saved from previous tick
        info = json.load(open('info.json','r'))
    except:
        #if no information was saved, initialize info
        print('No json info found')
        info = {}
        info['ticks'] = 0
        info['taunt'] = 'debug'

    print('------------------------')
    print('tick:',info['ticks'])
    info['ticks'] += 1
    taunt = info['taunt']


    foods = parse_point_list(data['board']['food'])
    num_food = len(foods)
    board_width  = data['board']['width']
    board_height = data['board']['height']
    center_pos = (board_width // 2, board_height // 2)
    board_size = (board_width, board_height)
    my_snake = data['you']
    my_id = my_snake['id']
    my_body = parse_point_list(my_snake['body'])
    my_head_pos = my_body[0]
    my_tail_pos = my_body[-1]
    print('head: ', my_head_pos, '\ttail: ', my_tail_pos)
    my_health = my_snake['health']
    my_size = len(my_body)
    snakes = data['board']['snakes']
    snakes_dict = {}
    snake_extension_dict = {}
    num_snakes = len(snakes)

    closest_to_food = {}
    for food in foods:
        closest_to_food[food] = {}
        closest_to_food[food]['dist'] = 10000

    #obstacles gathering loop
    obstacles = set()
    extended_obstacles = set()
    head_extension_debug = []
    attack_candidates = []
    for snake in snakes:
        body_points = parse_point_list(snake['body'])
        if snake.get('id') == my_id:
            print('my body points ', body_points)
            body_points,removed = shrink_me(body_points)
            food_pos, food_dist = find_closest_pos_dist(my_head_pos, foods)
            if food_pos > 1:
                print('removing tail pos from body')
                try:
                    body_points.remove(my_tail_pos)
                except:
                    print('tail pos not in body')
            if food_pos != None and food_dist < closest_to_food[food_pos]['dist']:
                closest_to_food[food_pos]['dist'] = food_dist
                closest_to_food[food_pos]['id'] = snake.get('id')
            my_body = body_points
            snake['body'] = body_points
            snakes_dict[snake['id']] = snake
            print('my shrunk body points ', body_points)
            print('my removed body points', removed)

        else:
            #print('body points before shrink: ', body_points)
            body_points = shrink_snake(body_points, my_head_pos)
            #print('body points after shrink: ', body_points)
            head_pos = body_points[0]
            snake_dist = manhattan_dist(my_head_pos, head_pos)
            snake_size = len(body_points)
            food_pos, food_dist = find_closest_pos_dist(head_pos, foods)
            if food_pos != None and food_dist < closest_to_food[food_pos]['dist']:
                closest_to_food[food_pos]['dist'] = food_dist
                closest_to_food[food_pos]['id'] = snake.get('id')

            outer_check = p2_outside_p1(my_head_pos, head_pos, center_pos) 
            print('{} outside of {}? {}'.format(head_pos, my_head_pos, outer_check)) 
            if snake_dist < 5 and snake_size < my_size and outer_check:
                direction = get_direction(body_points[1], head_pos)

                if direction == 'up':
                    targ = (head_pos[0], head_pos[1] - 1)
                elif direction == 'right':
                    targ = (head_pos[0] + 1, head_pos[1])
                elif direction == 'down':
                    targ = (head_pos[0], head_pos[1] + 1)
                else:
                    targ = (head_pos[0] - 1, head_pos[1]) 

                attack_candidates.append(snake['id'])

            other_head = head_pos
            snake['body'] = body_points
            snakes_dict[snake['id']] = snake
            extension = extend_head(body_points,board_size, my_head_pos)
            snake_extension_dict[snake['id']] = extension
            head_extension_debug.extend(extension)
            extended_obstacles.update(extension)

        obstacles.update(body_points)
    
    print('tailpos obst: ', my_tail_pos in extended_obstacles)
    closest_food_pos, closest_food_dist = find_closest_pos_dist(my_head_pos, foods)
    target_ext = []
    print('head extensions: ',  head_extension_debug)
    if closest_food_pos != None:
        print('closest food openness: ', flood_fill(closest_food_pos, board_size, obstacles), ' pos: ', closest_food_pos)
    if ((closest_food_pos != None and flood_fill(closest_food_pos, board_size, obstacles) > 2*my_size or my_health < 0.6*FOOD_THRESHOLD) and  
        ((my_health <= FOOD_THRESHOLD and 
        (closest_to_food[closest_food_pos]['id'] == my_id or 
        (closest_to_food[closest_food_pos]['id'] != my_id and 
        closest_to_food[closest_food_pos]['dist'] > my_size))) or 
        (closest_to_food[closest_food_pos]['dist'] <= 3 and closest_to_food[closest_food_pos]['id'] == my_id))):

        target = closest_food_pos
        target_type = 'food'

        #add back one body point to account for possible lengthening by eating
    elif num_snakes == 2:
        for snake in snakes_dict.values():
            if snake['id'] != my_id:
                target_snake = snake
                break

        target_body = target_snake['body']
        target_type = 'attack'
        target = get_predicted_snake_pos([get_predicted_snake_pos(target_body, board_size, obstacles)] + target_body,
            board_size, obstacles)
        extended_obstacles -= set(snake_extension_dict[target_snake['id']])
            
    elif len(attack_candidates) > 0:
        print('attempting attack')
        print('attack candidates: ', attack_candidates)
        min_dist = 1000
        min_dist_point = None
        edge_point = None
        for sid in attack_candidates:
            snake = snakes_dict[sid]
            snake_body = snake['body']
            ptarget = get_predicted_snake_pos(snake_body, board_size, obstacles)
            dist = manhattan_dist(my_head_pos, ptarget)
            if dist < min_dist:
                min_dist = dist
                min_dist_point = ptarget
        
        target_type = 'attack'
        target = min_dist_point
        print('selection: ', target, '  dist: ', manhattan_dist(my_head_pos, target))
    else:
        target_type = 'tail'
        target = my_tail_pos
    
    print('target: ', target_type, manhattan_dist(my_head_pos, my_tail_pos), manhattan_dist(my_head_pos, target))
    if (len(removed) > 0 and target_type == 'food' and 
        manhattan_dist(my_head_pos, target) <= manhattan_dist(my_head_pos, my_tail_pos)):

        print('unshrinking body. before: ', my_body)
        my_body = unshrink_me(my_body, removed, target)
        print('after: ', my_body)
        obstacles.update(my_body)
        updated_openness = flood_fill(target, board_size, obstacles)
        if updated_openness < my_size * 2:
            target = my_tail_pos
            obstacles -= set([target])

    elif my_health == 100:
        obstacles.add(my_tail_pos)
    obstacles = obstacles - set(target_ext)
    extended_obstacles = extended_obstacles.union(obstacles) - set(target_ext)
    pathfind_extended_obstacles = extended_obstacles - set([my_head_pos])
    pathfind_obstacles = obstacles - set([my_head_pos])
    space_cost = {}
    for y in range(board_height):
        for x in range(board_width):
            pos = (x,y)
            if pos not in pathfind_obstacles:
                neighbours = get_neighbours(pos, board_size) 
                cost = 5
                for n in neighbours:
                    if n not in extended_obstacles:
                        cost -= 1
                space_cost[pos] = max(cost,0) * manhattan_dist(pos, center_pos) ** 3
                print('\t', space_cost[pos], end='')
            else:
                print('\tINF', end='')
        print()
                

    print('head: ', my_head_pos)
    path_finder = AStar((board_width, board_height), my_head_pos)

    print('target: ', target)

    #prefer to avoid entering extended obstacles
    #       in future, the following code will be last resort, after no valid targets are found
    dest = None
    backup_dest = None
    # print('pathfind: ', pathfind_extended_obstacles)
    path = path_finder.search(target, pathfind_extended_obstacles, space_cost)
    if path == None:
        print('no path. second pathfind attempt')
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
            elif neighbour not in obstacles:
                print('backup')
                backup_dest = neighbour
                print('backup openness ', flood_fill(neighbour, board_size, extended_obstacles))
            else:
                print(neighbour, ' in both obst and ext obst')
        dest = best_dest
        print('most open is: ', best_open,best_dest)
    else:
        dest = path[-2]


    if dest == None and backup_dest != None:
        print('using backup dest')
        dest = backup_dest
    elif dest == None and backup_dest == None:
        print('we r fuked')
    if dest == my_tail_pos:
        openness = my_size*2
    else:
        openness = flood_fill(dest,board_size,extended_obstacles)
    if openness < my_size*2:
        print('heading to deadend?')
        if target_type != 'tail':
            print('attempting to target tail')
            path = path_finder.search(my_tail_pos, pathfind_obstacles, space_cost)
            dest = None
            if path != None:
                print('tail path found')
                dest = path[-2]

        if dest == None:           
            neighbours = get_neighbours(my_head_pos, board_size)
            best_open = -1
            best_dest = None
            print('checking neighbours...')
            for neighbour in neighbours:
                if neighbour not in obstacles:
                    print(neighbour, 'is potential move')
                    openness = flood_fill(neighbour, board_size, obstacles)
                    print('openness: ', openness)
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

    print('dest openness: ', flood_fill(dest, board_size, extended_obstacles))

    print('moving from {} to {}'.format(my_head_pos,dest))
    direction = get_direction(my_head_pos,dest)
    print(direction)
    tick_end = clock()
    tick_duration = tick_end - tick_start
    print('Elapsed: {}ms'.format(tick_duration*1000))
    
    json.dump(info, open('info.json','w'))
    
    n_dead = len(snakes) % len(taunts)
    print('------------------------')
    return move_response({'move': direction})

@bottle.post('/end')
def end():
    data = bottle.request.json
    return end_response()

@bottle.post('/ping')
def ping():
    return ping_response()


# Expose WSGI app (so gunicorn can find it)
application = bottle.default_app()

if __name__ == '__main__':
    try:
        config = json.load(open('config.json', 'r'))
    except:
        config = {}
        config['PORT'] = '8080'
        config['HOST'] = '0.0.0.0'
    bottle.run(
        application,
        host=os.getenv('IP', config['HOST']),
        port=os.getenv('PORT', config['PORT']),
        debug = True)

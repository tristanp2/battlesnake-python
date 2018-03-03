from __future__ import print_function
from Queue import PriorityQueue, Queue

INF = 100000
def in_dict(dictionary, key):
    try:
        dictionary[key]
    except KeyError:
        return False
    else:
        return True
def get_neighbours(pos, board_size):
    (x,y) = pos
    (width,height) = board_size
    x0 = x-1
    x1 = x+1
    y0 = y-1
    y1 = y+1
    neighbours = []
    if x0 >= 0:
        neighbours.append((x0,y))
    if y0 >= 0:
        neighbours.append((x,y0))
    if x1 < width:
        neighbours.append((x1,y))
    if y1 < height:
        neighbours.append((x,y1))
    return neighbours


def manhattan_dist(src, dest):
    (x1,y1) = src
    (x2,y2) = dest
    return abs(x2-x1) + abs(y2-y1)

#this is used to modify PQ priorities from by accessing object ref through dictionary
#honestly don't know if this screws with the priority queue at all, but it seems to be working
#well so far
class Container:
    def __init__(self, value):
        self.value = value
    def __lt__(self,other):
        return self.value < other.value

class AStar:


    def __init__(self, size, pos):
        (self.width, self.height) = size;
        self.pos = pos;
    
    #currently uses dicts in a few places where it should use sets
    def search(self, goal, obstacles):
        evaluated = {}

        open_set_pq = PriorityQueue()
        open_set_pq.put((Container(0), self.pos)) 
        open_set = {}
        open_set[self.pos] = 0
        #cost of getting to these nodes from start
        f_score = {}
        f_score[self.pos] = 0
        g_score = {}
        came_from = {}
        

        for x in range(self.width):
            for y in range(self.height):
                pos = (x,y)
                f_score[pos] = Container(INF)
                came_from[pos] = None
                g_score[pos] = Container(INF)

        g_score[self.pos] = Container(self.heuristic(self.pos, goal))
        #print("finding path {} --> {}".format(self.pos,goal))
        i = 0
        while not open_set_pq.empty():
            i += 1
            (current_score, current_pos) = open_set_pq.get()

            #print("current: ", current_pos)
            if current_pos == goal:
                print("Num_iterations: ",i)
                return self.reconstruct_path(came_from, current_pos)
             
            evaluated[current_pos] = current_score.value
            neighbours = self.get_neighbours(current_pos)
            for neighbour in neighbours:
                if in_dict(evaluated,neighbour):
                    continue
                elif neighbour in obstacles:
                    continue
                elif not in_dict(g_score,neighbour):
                    continue


                if not in_dict(open_set, neighbour):
                    open_set[neighbour] = f_score.get(neighbour)
                    open_set_pq.put((f_score.get(neighbour),neighbour))
                    
                tentative_g_score = g_score[current_pos].value + 1
                if tentative_g_score >= g_score[neighbour].value:
                    continue

                came_from[neighbour] = current_pos
                g_score[neighbour].value = tentative_g_score
                f_score[neighbour].value = tentative_g_score + self.heuristic(neighbour,goal)
                open_set_pq.put((f_score[neighbour],neighbour))


    def reconstruct_path(self, came_from, current):
        total_path = [current]
        while True:
            current = came_from[current]
            if(current == None):
                break
            total_path.append(current)
        return total_path

        
    def get_neighbours(self, pos):
        return get_neighbours(pos, (self.width,self.height))

    def heuristic(self,start, end):
        return manhattan_dist(start,end)

def flood_fill(pos, board_size, obstacles):
    found =set()
    q = Queue()
    found.add(pos)
    q.put(pos)
    
    while not q.empty():
        pos = q.get()
        neighbours = get_neighbours(pos, board_size)
        for neighbour in neighbours:
            if neighbour not in found and neighbour not in obstacles:
                found.add(neighbour)
                q.put(neighbour)

    return len(found)

if __name__=='__main__':
    search = AStar(10,(0,0),{})
    print(search.search((5,5)))



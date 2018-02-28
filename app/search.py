import math
from queue import PriorityQueue


def in_dict(dictionary, key):
    try:
        dictionary[key]
    except KeyError:
        return False
    else:
        return True

class Container:
    def __init__(self, value):
        self.value = value
    def __lt__(self,other):
        return self.value < other.value

class AStar:
    #this is used to modify PQ priorities from dictionary access


    def __init__(self, size, pos, obstacles):
        self.board_size = size;
        self.pos = pos;
        self.obstacles = obstacles
    
    def search(self, goal):
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
        

        for x in range(self.board_size):
            for y in range(self.board_size):
                pos = (x,y)
                f_score[pos] = Container(math.inf)
                came_from[pos] = None
                g_score[pos] = Container(math.inf)

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
                elif in_dict(self.obstacles,neighbour):
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
        (x,y) = pos
        x0 = x-1
        x1 = x+1
        y0 = y-1
        y1 = y+1
        if x0 < 0:
            x0=0
        if y0 < 0:
            y0=0
        if x1 >= self.board_size:
            x1 = self.board_size - 1
        if y1 >= self.board_size:
            y1 = self.board_size - 1

        return [(x0,y),(x1,y),(x,y0),(x,y1)]

    def heuristic(self,start, end):
        (x1,y1) = start
        (x2,y2) = end
        return abs(x2-x1) + abs(y2-y1)


if __name__=='__main__':
    search = AStar(10,(0,0),{})
    print(search.search((5,5)))



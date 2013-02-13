import sys
import traceback
import random
import time
import numpy as np

from collections import defaultdict
from math import sqrt
from constants import *
from toolkit import *

class Ants():
    def __init__(self):
        self.cols = None
        self.rows = None
        self.map = None
        self.hill_list = {}
        self.ant_list = {}
        self.dead_list = defaultdict(list)
        self.food_list = []
        self.visible_food_list = []
        self.turntime = 0
        self.loadtime = 0
        self.turn_start_time = None
        self.visible = None
        self.viewradius2 = 0
        self.attackradius2 = 0
        self.spawnradius2 = 0
        self.turns = 0
        self.turn = -1

    def setup(self, data):
        "Parse initial input and setup starting game state"
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                key = tokens[0]
                if key == 'cols':
                    self.cols = int(tokens[1])
                elif key == 'rows':
                    self.rows = int(tokens[1])
                elif key == 'player_seed':
                    random.seed(int(tokens[1]))
                elif key == 'turntime':
                    self.turntime = int(tokens[1])
                elif key == 'loadtime':
                    self.loadtime = int(tokens[1])
                elif key == 'viewradius2':
                    self.viewradius2 = int(tokens[1])
                elif key == 'attackradius2':
                    self.attackradius2 = int(tokens[1])
                elif key == 'spawnradius2':
                    self.spawnradius2 = int(tokens[1])
                elif key == 'turns':
                    self.turns = int(tokens[1])
        
        self.setup_arrays()
    
    def setup_arrays(self):            
        self.map = np.ndarray((self.rows, self.cols), dtype = np.int8)
        self.map.fill(UNSEEN)

        self.visible = np.zeros((self.rows, self.cols), dtype = np.bool)
        self._vision_setup([self.attackradius2, self.attackradius2, self.viewradius2])

        self.water_mask = np.ones((self.rows, self.cols), dtype = np.bool)
        
        self.explore = np.ndarray((self.rows, self.cols), dtype = np.float)
        
        self.food = np.zeros((self.rows, self.cols))
        self.last_seen = np.zeros((self.rows, self.cols))        
        self.combat_enemy = np.zeros((self.rows, self.cols))
        self.hills = np.zeros((self.rows, self.cols))

        self.ants = np.ones((self.rows , self.cols))

        self.combat_influence = np.zeros((20, self.rows, self.cols))
        self.combat_total = np.zeros((self.rows, self.cols))
        self.pop = 0
       
    def reset_arrays(self):
        # reset food
        self.food.fill(0)
        # reset ants
        self.ants.fill(1)
        # reset evade
        self.combat_enemy.fill(0)
        # reset combat
        self.combat_total.fill(0)
        # reset hills
        self.hills.fill(0)
    
    def clear_data(self):
        # clear hill, ant and food data
        for row, col in self.ant_list.keys():
            self.map[row,col] = LAND
        self.ant_list = {}
        for row, col in self.dead_list.keys():
            self.map[row,col] = LAND
        self.dead_list = defaultdict(list)
        self.visible_food_list = []
        
    def update(self, data):
        "Parse engine input and update the game state"
        # start timer
        self.turn_start_time = time.clock()
        self.reset_arrays()
        self.clear_data()
        
        # stores all visible hills
        visible_hill_list = {}
        
        # update map and create new ant and food lists
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                if len(tokens) == 2:
                    if tokens[0] == 'turn':
                        self.turn = int(tokens[1])
                elif len(tokens) >= 3:
                    row = int(tokens[1])
                    col = int(tokens[2])
                    if tokens[0] == 'w':
                        self.map[row,col] = WATER
                        self.water_mask[row, col] = False  #######
                        
                    elif tokens[0] == 'f':
                        self.map[row,col] = FOOD
                        self.visible_food_list.append((row, col))
                                                
                    else:                      
                        owner = int(tokens[3])
                        if tokens[0] == 'a':
                            self.map[row,col] = owner
                            self.ant_list[(row, col)] = owner
                            if owner == 0:  ###########
                                self.last_seen[row, col] += (MAX_NUM - self.last_seen[row, col])/100
                                self.ants[row, col] -= 0.95
                            else:
                                self.combat_enemy[row, col] = MAX_NUM
                                
                                            
                        elif tokens[0] == 'd':
                            self.dead_list[(row, col)].append(owner)
                        elif tokens[0] == 'h':
                            owner = int(tokens[3])
                            visible_hill_list[(row, col)] = owner
                        
        self._update_visible()
        self.pop = len(self.my_ants())
        self.update_food()
        self.update_hills(visible_hill_list)
        self.update_combat()
    
    def update_food(self):
        # Update food
        new_food = []
        for pos in self.food_list:
            if self.visible[pos]:
                self.map[pos] = LAND
            else:
                # Assume still there
                new_food.append(pos)
                self.food[pos] = MAX_NUM ########
                
        for pos in self.visible_food_list:
            self.map[pos] = FOOD
            self.food[pos] = MAX_NUM ######
            
        self.food_list = new_food + self.visible_food_list
    
    def update_hills(self, visible_hill_list):
        # Update hills
        for pos, owner in self.hill_list.items():
            if self.visible[pos] and pos not in visible_hill_list:
                del self.hill_list[pos]
            else:
                if owner != 0:
                    self.hills[pos] = MAX_NUM

        self.hill_list.update(visible_hill_list)
    
    def update_combat(self):
        # Update combat
        self._update_visible('combat', self.ant_list.items(), self.combat_influence)
        self.combat_mask = np.zeros((20, self.rows, self.cols), dtype = np.bool)
        self.combat_area = np.zeros((self.rows, self.cols), dtype = np.bool)
        for i in range(20):
            self.combat_total += self.combat_influence[i]
            if i > 0:
                self.combat_influence[i] = spread(self.combat_influence[i])
                self.combat_mask[i] |= self.combat_influence[i].astype(np.bool)
                self.combat_area |= self.combat_influence[i].astype(np.bool)
        
        self.combat_fighting = np.zeros((20, self.rows, self.cols))
        for i in range(20):
            self.combat_fighting[i] = self.combat_total - self.combat_influence[i] 

        players = []
        for (row, col), owner in self.ant_list.items():
            if owner not in players:
                players.append(owner)

        self.combat_best = np.zeros((self.rows, self.cols))
        players.remove(MY_ANT)

        if players:
            self.combat_best = self.combat_fighting[players.pop()]
            for owner in players:
                mask = self.combat_mask[owner]
                self.combat_best[mask] = np.minimum(self.combat_best[mask], self.combat_fighting[owner][mask])

        self.combat_status = (self.combat_fighting[0] < self.combat_best)
##        for ant_loc in self.dead_list:
##            debug('an ant belonging to player {} died at {}'.format(self.dead_list[ant_loc], ant_loc))
##            debug('the combat values were {} and {} for the enemy and you respectively'.format(self.combat_best[ant_loc[0], ant_loc[1]], self.combat_fighting[MY_ANT, ant_loc[0], ant_loc[1]]))
    
    def time_remaining(self):
        return self.turntime - int(1000 * (time.clock() - self.turn_start_time))
    
    def issue_order(self, ant_loc, dir_or_dest = None):
        "Issue an order by either (ant_loc, dir) or (ant_loc, dest) pair"
        if dir_or_dest == None:
            # Compatibility with old pack
            ant_loc, dir_or_dest = ant_loc
        if isinstance(dir_or_dest, str):
            direction = dir_or_dest
        elif len(dir_or_dest) == 2:
            direction = self.direction(ant_loc, dir_or_dest)[0]
        else:
            raise ValueError("Invalid order " + str((ant_loc, dir_or_dest)))
        sys.stdout.write('o %s %s %s\n' % (ant_loc[0], ant_loc[1], direction))
        sys.stdout.flush()
        
    def finish_turn(self):
        "Finish the turn by writing the go line"
        sys.stdout.write('go\n')
        sys.stdout.flush()
        
    def my_hills(self):
        return [loc for loc, owner in self.hill_list.items()
                    if owner == MY_ANT]

    def enemy_hills(self):
        return [(loc, owner) for loc, owner in self.hill_list.items()
                    if owner != MY_ANT]
        
    def my_ants(self):
        'return a list of all my ants'
        return [(row, col) for (row, col), owner in self.ant_list.items()
                    if owner == MY_ANT]

    def enemy_ants(self):
        'return a list of all visible enemy ants'
        return [((row, col), owner)
                    for (row, col), owner in self.ant_list.items()
                    if owner != MY_ANT]

    def food(self):
        "Return a list of all known food locations (visible or not)"
        return self.food_list[:]

    def passable(self, loc):
        "True if seen and not water"
        row, col = loc
        return self.map[row,col] not in (WATER, UNSEEN)
    
    def unoccupied(self, loc):
        "True if no ants are at the location"
        row, col = loc
        return self.map[row,col] in (LAND, DEAD, HILL, MY_HILL)

    def neighbours(self, pos):
        "Returns the four neighbours of a position"
        return [((pos[0]-1)%self.rows, pos[1]),
                (pos[0], (pos[1]+1)%self.cols),
                ((pos[0]+1)%self.rows, pos[1]),
                (pos[0], (pos[1]-1)%self.cols)]

    def neighbours_and_dirs(self, pos):
        "Returns four position, direction pairs"
        return ((((pos[0]-1)%self.rows, pos[1]), 'n'),
                ((pos[0], (pos[1]+1)%self.cols), 'e'),
                (((pos[0]+1)%self.rows, pos[1]), 's'),
                ((pos[0], (pos[1]-1)%self.cols), 'w'))
        
    def diffuse_field(self, field, maximum = True, mask = True):
        if maximum:
            return np.maximum(field, surroundings(field)/self.neighbour_num) * self.water_mask
        elif not mask:
            return np.maximum(field, surroundings(field)/self.neighbour_num)
        else:
            return (surroundings(field)/self.neighbour_num) * self.water_mask
        
    def diffuse_all(self):
        self.explore = np.copy(self.last_seen)
        self.neighbour_num = np.maximum((surroundings(self.water_mask & 1)), 1)
        self.combat_friend = (1 - self.ants) * MAX_NUM * self.combat_area * 10 * self.water_mask
                    
        for step in range(35):
            self.food = self.diffuse_field(self.food)
            self.food *= self.ants
            #self.combat_friend *= self.ants

        for step in range(30):
            self.hills = self.diffuse_field(self.hills)
            
        for step in range(45):
            self.explore = self.diffuse_field(self.explore)

        for step in range(20):
            self.combat_friend = self.diffuse_field(self.combat_friend) * self.combat_area
            self.combat_enemy = self.diffuse_field(self.combat_enemy) * self.combat_area
            
        self.explore = (2 * MAX_NUM - 1 * self.explore) * self.water_mask

    def score(self, loc):
        return 2 * self.food[loc] + 1 * self.hills[loc] + self.explore[loc] + 0.001 * self.combat_friend[loc] #+ 0.5 * self.combat_enemy[loc]
                        
    def output_move(self, loc, orders):
        if not self.combat_status[loc]:
            best = -float('inf')
        else:
            best = self.score(loc)
            
        direction = ''
        for neighbour, dir in self.neighbours_and_dirs(loc):
            row, col = neighbour
            if self.unoccupied(neighbour):
                if self.combat_status[neighbour] or not self.combat_area[neighbour]:
                    cost = self.score(neighbour)

                    if cost > best and\
                       neighbour not in orders and loc not in orders.values() and\
                       self.unoccupied(neighbour):
                        best = cost
                        direction = dir
                        self.combat_friend[neighbour] += MAX_NUM
                        self.combat_friend = self.diffuse_field(self.combat_friend) * self.combat_area

        return direction
    
    def destination(self, loc, direction):
        "Calculate a new location given the direction and wrap correctly"
        row, col = loc
        d_row, d_col = AIM[direction]
        return ((row + d_row) % self.rows, (col + d_col) % self.cols)        

    def distance(self, loc1, loc2):
        "Calculate the closest distance between two locations"
        row1, col1 = loc1
        row2, col2 = loc2
        d_col = min(abs(col1 - col2), self.cols - abs(col1 - col2))
        d_row = min(abs(row1 - row2), self.rows - abs(row1 - row2))
        return d_row + d_col
    
    def _vision_setup(self, sqr_radii):
        '''
        Radii should be supplied in the following order:
        my_disc, attack_disc, vision_disc
        '''
        self.my_disc = self.attack_disc = self.vision_disc = None
        discs = []
        
        for sqr_radius in sqr_radii:
            viewradius = int(sqrt(sqr_radius))
            diameter = viewradius * 2 + 1
            disc = np.zeros((diameter, diameter), dtype = np.bool)

            # Precalculate a circular mask used in _update_visible
            for y, x in np.ndindex(*disc.shape):
                if (viewradius - y)**2 + (viewradius - x)**2 <= sqr_radius:
                    disc[y, x] = True

            discs.append(disc)

        [self.my_disc, self.attack_disc, self.vision_disc] = discs

    def _update_visible(self, visible_type = 'normal', loc_list = None, return_mask = None):
        if visible_type == 'normal':
            return_mask = self.visible
            loc_list = self.my_ants()
            sqr_radius = self.viewradius2
            disc_mask = self.vision_disc
            
            viewradius = int(sqrt(sqr_radius))
            diameter = viewradius * 2 + 1
            return_mask.fill(False)
        else:
            return_mask.fill(0)
        
        for a_row, a_col in loc_list:
            if visible_type != 'normal':
                owner = a_col
                a_row, a_col = a_row
                temp_mask = return_mask[owner]

                if owner == 0:
                    sqr_radius = self.attackradius2
                    disc_mask = self.my_disc
                else:
                    sqr_radius = self.attackradius2
                    disc_mask = self.attack_disc
                
                viewradius = int(sqrt(sqr_radius))
                diameter = viewradius * 2 + 1
                    
            else:
                temp_mask = return_mask
                
            top = (a_row - viewradius) % self.rows
            left = (a_col - viewradius) % self.cols
            # Height/width of the top and left parts of vision disc (which might actually
            # be draw at the bottom or right of the map) -- rest of vision disc wraps over.
            toph = min(diameter, self.rows - top)
            leftw = min(diameter, self.cols - left)
            if toph == diameter and leftw == diameter:
                temp_mask[top:top+toph, left:left+leftw] += disc_mask
            else:
                bottomh = diameter - toph
                rightw = diameter - leftw

                temp_mask[top:top+toph, left:left+leftw] += disc_mask[:toph, :leftw]
                temp_mask[:bottomh, left:left+leftw] += disc_mask[toph:, :leftw]
                temp_mask[top:top+toph, :rightw] += disc_mask[:toph, leftw:]
                temp_mask[:bottomh, :rightw] += disc_mask[toph:, leftw:]

        if visible_type == 'normal':
            # Any non-land UNSEEN tiles have already been changed to whatever in update()
            self.map[(self.map == UNSEEN) & self.visible] = LAND    

    def render_text_map(self):
        """Return a pretty text representation of the map"""

        icons = 'abcdefghijABCDEFGHIJ0123456789   #*,!'
        lookup = np.ndarray(len(icons), '|S1', buffer = icons)
        result = lookup[self.map]

        # Visible land gets . rest gets ,
        result[(self.visible) & (self.map == LAND)] = '.'

        for pos, owner in self.hill_list.iteritems():
            if self.map[pos] >= ANTS:
                # hill already destroyed if owner not the same as ant owner
                result[pos] = lookup[self.map[pos] + 10]
            else:
                result[pos] = lookup[owner + 20]

        tmp = ''
        for row in result:
            tmp += '# ' + row.view(('S', row.shape[0]))[0] + '\n'
        return tmp

    # static methods are not tied to a class and don't have self passed in
    # this is a python decorator
    @staticmethod
    def run(bot):
        "Parse input, update game state and call the bot classes do_turn method"
        ants = Ants()
        map_data = ''
        while(True):
            try:
                current_line = sys.stdin.readline().rstrip('\r\n') # string new line char
                if current_line.lower() == 'ready':
                    ants.setup(map_data)
                    bot.do_setup(ants)
                    ants.finish_turn()
                    map_data = ''
                elif current_line.lower() == 'go':
                    ants.update(map_data)
                    # call the do_turn method of the class passed in
                    bot.do_turn(ants)
                    ants.finish_turn()
                    map_data = ''
                else:
                    map_data += current_line + '\n'
            except EOFError:
                break
            except KeyboardInterrupt:
                raise
            except:
                # don't raise error or return so that bot attempts to stay alive
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()


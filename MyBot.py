#!/usr/bin/env python
from ants import *
from toolkit import *

class MyBot:
    def __init__(self):
        # define class level variables, will be remembered between turns
        pass
    
    def do_setup(self, ants):
        # initialize data structures after learning the game settings
        pass
    
    def do_turn(self, ants):
        # track all moves, prevent collisions
        def do_move_direction(loc, direction):
            new_loc = ants.destination(loc, direction)
            ants.issue_order((loc, direction))
            self.orders[new_loc] = loc
            return True

        if ants.pop == 0:
            return
        
        self.orders = {}
        ants.diffuse_all()
        for ant_loc in ants.my_ants():
            direction = ants.output_move(ant_loc, self.orders)
            if direction:
                do_move_direction(ant_loc, direction)
            if ants.time_remaining() < 20:
                return

       # debug('You finished this turn with {} ms to spare.'.format(ants.time_remaining()))
        
if __name__ == '__main__':
    # psyco will speed up python a little, but is not needed
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    
    try:
        Ants.run(MyBot())

    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

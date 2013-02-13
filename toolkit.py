#tool kit

import sys
import numpy as np

from math import sqrt

def debug(*msgs):
    text = ' '.join(str(m) for m in msgs) + '\n'
    sys.stderr.write(text)
    sys.stderr.flush()
    
def spread(field, contract = False):
    left = fastroll(field, 1, 1)
    right = fastroll(field, -1, 1)
    up = fastroll(field, 1, 0)
    down = fastroll(field, -1, 0)

    for mask in [left, right, up, down]:
        if contract:
            field = np.minimum(mask, field)
        else:
            field = np.maximum(mask, field)

    return field

def surroundings(field, operation = lambda a, b, c, d: a + b + c + d):
    left = fastroll(field, 1, 1)
    right = fastroll(field, -1, 1)
    up = fastroll(field, 1, 0)
    down = fastroll(field, -1, 0)
    
    return operation(left, right, up, down)

def ants_count(loc, sqr_radius, disc, map):
    count = np.copy(disc)
    count = count.astype(np.int8)
    count.fill(0)
    
    a_row, a_col = loc
    viewradius = int(sqrt(sqr_radius))
    diameter = viewradius * 2 + 1
    
    rows, cols = map.shape
    
    top = (a_row - viewradius) % rows
    left = (a_col - viewradius) % cols
    # Height/width of the top and left parts of vision disc (which might actually
    # be draw at the bottom or right of the map) -- rest of vision disc wraps over.
    toph = min(diameter, rows - top)
    leftw = min(diameter, cols - left)
    if toph == diameter and leftw == diameter:
        count += (map[top:top+toph, left:left+leftw] == 0)
    else:
        bottomh = diameter - toph
        rightw = diameter - leftw

        count[:toph, :leftw] += (map[top:top+toph, left:left+leftw] == 0)
        count[toph:, :leftw] += (map[:bottomh, left:left+leftw] == 0)
        count[:toph, leftw:] += (map[top:top+toph, :rightw] == 0)
        count[toph:, leftw:] += (map[:bottomh, :rightw] == 0)
        
    return np.sum(count)
    
def fastroll(array, dist, axis):
    """
    Numpy's np.roll is implemented extremely inefficiently. This is a 2-10x faster replacement!
    """
    prefix = [slice(None)] * axis
    dist %= array.shape[axis]
    
    ret = np.empty_like(array)
    ret[prefix + [slice(dist, None)]] = array[prefix + [slice(None, -dist)]]
    ret[prefix + [slice(0, dist)]] = array[prefix + [slice(-dist, None)]]
    
    return ret

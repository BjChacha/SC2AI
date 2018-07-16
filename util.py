import random

def num_float_in(num, f, num_min, num_max):
    f *= 100
    num += (random.randrange(-f, f) / 100) + 1
    if num < num_min: num = num_min
    if num > num_max: num = num_max
    return num

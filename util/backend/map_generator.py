import random

def generate_blocked_tiles(seed, width=60, height=40):
    random.seed(seed)

    # Weighted tile distribution based on tag_game.js
    tile_weights = [
        (-1, 50), (13, 3), (32, 2), (127, 1),
        (108, 1), (109, 2), (110, 2),
        (166, 0.25), (167, 0.25)
    ]

    weighted_pool = []
    for index, weight in tile_weights:
        weighted_pool.extend([index] * int(weight * 100))

    blocked_ids = {13, 32, 127, 108, 109, 110, 166, 167}
    blocked_tiles = set()

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            tile = random.choice(weighted_pool)
            if tile in blocked_ids:
                blocked_tiles.add((x, y))

    # Add outer borders
    for x in range(width):
        blocked_tiles.add((x, 0))
        blocked_tiles.add((x, height - 1))
    for y in range(height):
        blocked_tiles.add((0, y))
        blocked_tiles.add((width - 1, y))


    # Collect all free tiles (excluding 2-tile border and blocked)
    free_tiles = [
        (x, y)
        for x in range(2, width - 2)
        for y in range(2, height - 2)
        if (x, y) not in blocked_tiles
    ]

    return blocked_tiles, free_tiles
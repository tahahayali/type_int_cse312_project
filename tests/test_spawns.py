import unittest
from util.backend.map_generator import generate_blocked_tiles

class TestSpawnTiles(unittest.TestCase):
    def test_no_spawn_on_blocked_tile(self):
        seed = 12345  # Can test other seeds too
        blocked, free = generate_blocked_tiles(seed)

        for tile in free:
            self.assertNotIn(tile, blocked, f"Tile {tile} is both free and blocked!")

if __name__ == '__main__':
    unittest.main()

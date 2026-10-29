"""Screen size and layout coordinates for THE LAST CONVOY (no pygame needed)."""
import random

WIDTH, HEIGHT, FPS = 1000, 680, 60

# Minimap card on the convoy screen (x, y, width, height) and its scale relative to the highway map.
MINI_CARD = (556, 520, 412, 128)
MINI_SCALE = 0.36

# Vehicle table and preview card on the vehicle screen.
TABLE_X, TABLE_W = 30, 632
COL_NAME, COL_STATUS = 42, 180
COL_NUMBERS = [266 + 56 * k for k in range(7)]
ROW_Y0, ROW_H = 306, 39
CARD = (672, 274, 298, 340)

# Fixed background-zombie positions used by the convoy scene.
_zombie_rng = random.Random(7)
ZOMBIE_SLOTS = sorted(
    ((_zombie_rng.randint(690, 960), _zombie_rng.randint(300, 334)) for _ in range(18)),
    key=lambda slot: -slot[0],
)

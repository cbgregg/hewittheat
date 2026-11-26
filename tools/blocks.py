"""Block-by-block looks for downtown, set building by building from the owner's flyover recording
(used as reference only: colours, storeys, roofs, what stands where). Keys are footprint indices
in data/world.json; tools/citygen.py applies them, and writes data/extras.json for the game.

Per building: wall (a tex/b facade), tint, roof, rtint, shop, fl (storeys), stripe=(second colour,
segment length[, every Nth segment]) for fronts that alternate colour, awn (awning colour), special='construction'.
SPLIT cuts one footprint north to south where the recording shows several buildings on it."""

B = {
    # ---- Pacific Ave, north side, Grand to Rucker: four-storey apartments, blue and white fronts over a dark base
    5979: dict(wall='f_panel', tint='#8ea9cc', stripe=('#e9e9e4', 150), roof='r_membrane', rtint='#e6e6e2', shop='shop_modern', fl=4),
    5980: dict(wall='f_panel', tint='#e9e9e4', stripe=('#8ea9cc', 150), roof='r_membrane', rtint='#e6e6e2', shop='shop_modern', fl=4),
    5948: dict(wall='f_panel', tint='#8ea9cc', stripe=('#e9e9e4', 150), roof='r_membrane', rtint='#e6e6e2', shop='shop_modern', fl=4),
    5981: dict(wall='f_panel', tint='#e9e9e4', roof='r_membrane', rtint='#e6e6e2', shop='shop_modern', fl=4),
    5983: dict(wall='f_panel', tint='#8ea9cc', stripe=('#e9e9e4', 150), roof='r_membrane', rtint='#e6e6e2', shop='shop_modern', fl=4),
    5982: dict(wall='f_panel', tint='#e9e9e4', stripe=('#8ea9cc', 150), roof='r_membrane', rtint='#e6e6e2', shop='shop_modern', fl=4),
    # ---- Rucker Ave, west side, Pacific to Wall
    4630: dict(wall='f_concrete', tint='#dcdcd6', roof='r_membrane', rtint='#e2e2de', shop='shop_modern', fl=2),
    4608: dict(wall='f_brick_dark', tint='#6a6c70', roof='r_gravel', rtint='#7a5a48', shop='shop_modern', fl=2, awn='#2a2c30'),
    # ---- Rucker and Pacific, north-east corner: tan two-storey with a dark side wall
    462: dict(wall='f_stucco', tint='#d9caa4', roof='r_gravel', rtint='#9a9890', shop=None, fl=2),
    # ---- Grand Ave, west side, California to Hewitt
    1626: dict(wall='f_brick_red', tint='#b5654a', roof='r_gravel', rtint='#8a8882', shop='shop_brick', fl=2, awn='#3a5a3a'),
    6342: dict(wall='f_brick_red', tint='#b5654a', roof='r_gravel', rtint='#8a8882', shop='shop_brick', fl=2, awn='#3a5a3a'),
    1634: dict(wall='f_brick_red', tint='#b5654a', roof='r_gravel', rtint='#8a8882', shop='shop_brick', fl=2, awn='#3a5a3a'),
    5809: dict(wall='f_panel', tint='#aab2b6', stripe=('#4f9a98', 70, 3), roof='r_membrane', rtint='#e2e2de', shop='shop_modern', fl=5),
    5810: dict(wall='f_panel', tint='#e4e4e0', stripe=('#d9682c', 60, 4), roof='r_membrane', rtint='#eeeeea', shop='shop_modern', fl=6, awn='#d9682c'),
    # ---- Grand Ave, east side at California: long single-storey white building
    1635: dict(wall='f_cmu', tint='#e6e6e0', roof='r_membrane', rtint='#f0f0ec', shop=None, fl=1.3),
}

# footprint: [(from, to, look)] as fractions of its north-south length, north first
SPLIT = {
    4674: [(0.0, 0.56, dict(special='construction', fl=5)),
           (0.56, 0.80, dict(wall='f_brick_red', tint='#a8503c', roof='r_gravel', rtint='#8f8f8c', shop=None, fl=2)),
           (0.80, 1.0, dict(wall='f_metal', tint='#2f6fb5', roof='r_seam', rtint='#9aa4ad', shop=None, fl=1.3))],
}

# street trees: (street, from cross street, to cross street, side of the street, how many, size)
TREES = [
    ('Rucker Ave', 'Pacific Ave', 'Wall St', 'W', 7, 1.0),
    ('Rucker Ave', 'Pacific Ave', 'Wall St', 'E', 6, 0.75),
    ('Pacific Ave', 'Grand Ave', 'Rucker Ave', 'N', 7, 0.7),
    ('Rucker Ave', '32nd St', 'Pacific Ave', 'W', 4, 0.9),
    ('Grand Ave', 'California St', 'Hewitt Ave', 'W', 6, 0.75),
    ('Grand Ave', 'California St', 'Hewitt Ave', 'E', 3, 0.7),
    ('Hewitt Ave', 'W Marine View Dr', 'Grand Ave', 'N', 4, 0.7),
]

# cleared lots: (x0, y0, x1, y1) in world units, fenced
SITES = [
    # Pacific Ave, south side, Grand to Rucker: graded dirt lot with machines working
    dict(box=(12160, 15180, 13000, 15380), fence='#e8641e', props=[('excavator', 12760, 15285, 0.4, 1.0)]),
    dict(box=(12160, 15380, 12590, 15700), fence=None, props=[('excavator', 12400, 15500, 2.2, 1.0)]),
]

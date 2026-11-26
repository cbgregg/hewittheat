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
    # ---- Broadway, west side, 33rd to 34th: the cream and white buildings toward Lombard
    6337: dict(wall='f_panel', tint='#e6dfd0', stripe=('#c8652a', 70, 4), roof='r_membrane', rtint='#eeeeea', shop=None, fl=4),
    1183: dict(wall='f_panel', tint='#e9e6de', roof='r_membrane', rtint='#eeeeea', shop=None, fl=4),
    1188: dict(wall='f_panel', tint='#e9e6de', roof='r_membrane', rtint='#eeeeea', shop=None, fl=3),
    # ---- Broadway, east side, 32nd to 33rd
    1127: dict(wall='f_stucco', tint='#d9a25e', roof='r_gravel', rtint='#b9a888', shop=None, fl=1.3),
    1136: dict(wall='f_cmu', tint='#4f9a98', roof='r_membrane', rtint='#d8d8d4', shop=None, fl=1.3),
    1126: dict(wall='f_metal', tint='#b9c6d2', roof='r_seam', rtint='#aebccb', shop=None),
    1150: dict(wall='f_brick_red', tint='#a8553f', roof='r_gravel', rtint='#8a8882', shop='shop_brick', fl=2),
    1151: dict(wall='f_brick_red', tint='#a8553f', roof='r_gravel', rtint='#8a8882', shop=None, fl=1.3),
    # ---- Rockefeller and Wall: brick church with the green spire, and the small white buildings in the lot east of it
    4556: dict(wall='f_brick_red', tint='#8f4d3c', roof='r_shingle', rtint='#4a4d52', shop=None, pitched=True, spire=('#4f8a6f', 150)),
    4514: dict(wall='f_stucco', tint='#ecece6', roof='r_membrane', rtint='#eeeeea', shop=None, fl=1.3),
    4533: dict(wall='f_stucco', tint='#ecece6', roof='r_membrane', rtint='#eeeeea', shop=None, fl=1.3),
    # ---- Wetmore and Wall: the dark glass city offices
    4539: dict(wall='f_glass', tint='#4a5058', roof='r_membrane', rtint='#c9c9c6', shop=None),
    # ---- Hewitt and Oakes, north-west: long brick building with the pale blue metal roof
    4311: dict(wall='f_brick_red', tint='#8f4d3c', roof='r_seam', rtint='#b9cfe0', shop='shop_brick', fl=2),
    # ---- the arena's pale blue roof
    5768: dict(rtint='#a9c4dc'),
}

# footprints the recording shows as open ground (removed from the model and from the collision map)
GONE = [485, 5910]

# buildings the recording shows that the footprint data lacks: corner points, storeys, look
ADD = [
    # Broadway and 33rd, south-west corner: white five-storey apartments with dark window strips
    dict(poly=[(20120, 17830), (20470, 17830), (20470, 18160), (20120, 18160)], fl=5,
         wall='f_panel', tint='#eeeeea', stripe=('#5a5f66', 60, 3), roof='r_membrane', rtint='#f2f2ee', shop='shop_modern'),
    # mid-block on Broadway: tan brick four-storey, and the white-roofed building behind it
    dict(poly=[(20300, 18270), (20480, 18270), (20480, 18760), (20300, 18760)], fl=4,
         wall='f_brick_buff', tint='#c9b08a', roof='r_membrane', rtint='#eeeeea', shop=None),
    dict(poly=[(20040, 18290), (20290, 18290), (20290, 18560), (20040, 18560)], fl=3,
         wall='f_stucco', tint='#e0d8c6', roof='r_membrane', rtint='#f2f2ee', shop=None),
]

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
    ('Broadway', '33rd St', '34th St', 'W', 6, 0.6),
    ('Rockefeller Ave', 'Hewitt Ave', 'Wall St', 'W', 4, 0.8),
    ('Hewitt Ave', 'Rockefeller Ave', 'Oakes Ave', 'S', 6, 0.8),
    ('Hewitt Ave', 'Rockefeller Ave', 'Oakes Ave', 'N', 4, 0.7),
    ('Hewitt Ave', 'Wetmore Ave', 'Rockefeller Ave', 'S', 5, 0.8),
    ('Hewitt Ave', 'Wetmore Ave', 'Rockefeller Ave', 'N', 4, 0.7),
    ('Oakes Ave', 'California St', 'Hewitt Ave', 'W', 5, 0.9),
]

# open lots: (x0, y0, x1, y1) in world units, ground colour, optional fence, machines
SITES = [
    # Pacific Ave, south side, Grand to Rucker: graded dirt lot with machines working
    dict(box=(12160, 15180, 13000, 15700), color='#8c7656', fence='#e8641e',
         props=[('excavator', 12480, 15330, 0.5, 1.0), ('excavator', 12700, 15520, 2.4, 1.0)]),
    # Broadway and 34th, north-west corner: mown grass lot
    dict(box=(20110, 18880, 20470, 19140), color='#4f7a34', fence=None, props=[]),
]

# skybridges the footprint data draws as ground-level walls: the two footprints they belong to, the kerb-to-kerb
# span that becomes an open bridge (corner points), and its floor and roof heights above the street
BRIDGES = [
    # Wetmore Ave north of California St: the office block on the west side to the parking garage on the east
    dict(a=4235, a_keep=('x<', 16150), b=4238, b_keep=('x>', 16369), quad=[(16150, 10585), (16371, 10603), (16369, 10634), (16150, 10617)], z0=50, z1=88),
]
B.update({4238: dict(wall='f_garage', tint='#d8d6d0', roof='r_parking', rtint='#ffffff', shop=None)})


"""Block-by-block looks for downtown, set building by building from the owner's flyover recording
(used as reference only: colours, storeys, roofs, what stands where). Keys are footprint indices
in data/world.json; tools/citygen.py applies them, and writes data/extras.json for the game.

Per building: wall (a tex/b facade), tint, roof, rtint, shop, fl (storeys), stripe=(second colour,
segment length[, every Nth segment]) for fronts that alternate colour, awn (awning colour), special='construction'.
hft = measured roof height in feet, shopon = compass sides that get a storefront ('S', 'WS'), blank = sides that are
windowless party or alley walls, pent = rooftop penthouse (see citygen).
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
    # ---- the arena's pale blue roof
    5768: dict(rtint='#a9c4dc', hft=71),  # curved roof: LiDAR 95th percentile, not the mean
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



# ---------------------------------------------------------------------------------------------------------------
# Hewitt Ave, Colby to Oakes: set from the building dossiers (tools/dossier.py hewitt_colby_oakes).
# Evidence per building is in data/dossier/hewitt_colby_oakes.json. What each value rests on:
#   hft      county LiDAR roofprint mean height + 3 ft of parapet
#   roof     county 2024 / city 2022 aerials (3 in per pixel)
#   groups   several city footprints under one roof in the aerials are given one look, so they read as one building
#   tint     brick textures carry their own colour, so brick tints stay near white and only shift the shade
#   wall     W = seen (wall visible in an aerial or a street photo), R = public record (register listing),
#            D = inferred from the Hewitt National Historic District setting, the use code and the roof; needs a street photo
# ---------------------------------------------------------------------------------------------------------------
WHITE_R, LIGHT_R, GREY_R, DARK_R = ('r_membrane', '#f0f1ee'), ('r_membrane', '#c4c7c1'), ('r_gravel', '#a3a59d'), ('r_gravel', '#585c58')


def grp(ids, roof, **kw):
    for i in ids:
        B[i] = dict(kw, roof=roof[0], rtint=roof[1])


# --- Colby to Wetmore, north side
# 2825 Colby (office use, 5 storeys, 55 ft): pale precast frame over a tall glazed ground floor (W: street photo); stepped light roof
grp([4273], LIGHT_R, wall='f_concrete', tint='#fbf8f0', shop='shop_modern', shopon='WS', blank='N', hft=60)
# --- Colby to Wetmore, south side
# 1602 Hewitt (bank use): 3-storey ribbed concrete podium on Colby (W: street photo) under a 10-storey white tower with a dark penthouse (W: 2022 aerial)
grp([4388], ('r_membrane', '#a5a8a0'), wall='f_concrete', tint='#d2cfc6', shop=None, hft=42)
grp([6024], ('r_membrane', '#dcdeda'), wall='f_panel', tint='#f6f5f0', shop=None, hft=98, pent=(95, 90, 26, '#5a5d60', -75, -45), units=False)
# 1618-1620 Hewitt and 2902-2908 Wetmore: one 4-storey block (47 ft), dark roof, green corner awning (W: 2024 aerial); wall D
grp([4390, 4391, 4405, 4422], DARK_R, wall='f_brick_red', tint='#f3e6df', shop='shop_brick', shopon='NE', blank='SW', awn='#2f6b55', hft=50)

# --- Wetmore to Rockefeller, north side
# 1701 Hewitt and 2825-2831 Wetmore (bank use): six footprints, one 2-storey building (31 ft), pale roof, pale walls and cornice (W: 2022 aerial)
grp([4295, 4312, 4317, 4334, 4336, 5972], LIGHT_R, wall='f_brick_buff', tint='#fffaf0', shop='shop_buff', shopon='WS', blank='NE', hft=34)
# 1705-1707 Hewitt (retail): four footprints, one 2-storey building (33 ft), dark roof, pale cornice band on Hewitt (W); wall D
grp([5971, 5973, 5970, 4338], DARK_R, wall='f_brick_red', tint='#ffffff', shop='shop_brick', shopon='S', blank='NEW', awn='#2a2c30', hft=36)
# 1709 Hewitt (restaurant): 2 storeys (32 ft), dark roof; wall D
grp([5969, 4340], DARK_R, wall='f_brick_red', tint='#e2d6d2', shop='shop_brick', shopon='S', blank='NEW', awn='#7a2f2a', hft=35)
# 1711 Hewitt (amusement / secondhand): wide 2-storey hall (26 ft), dark roof, pale canopy along the front (W: 2022 aerial); wall D
grp([4301], DARK_R, wall='f_stucco', tint='#efe8d8', shop='shop_modern', shopon='S', blank='NEW', awn='#7fb5ae', hft=29)
# 1715-1717 Hewitt (bar, offices): narrow 2-storey (28 ft), grey roof; wall D
grp([4328, 4303], GREY_R, wall='f_brick_dark', tint='#f0ece8', shop='shop_brick', shopon='S', blank='NEW', hft=31)
# 1719-1721 Hewitt and 2826-2828 Rockefeller (offices): four footprints, one 6-storey block (68 ft), white roof with light wells,
# pale ornamented parapet (W: 2022 aerial)
grp([4305, 4322, 4332, 4348], WHITE_R, wall='f_brick_buff', tint='#ffffff', shop='shop_buff', shopon='SE', blank='NW', hft=72)
# --- Wetmore to Rockefeller, south side
# 1702 Hewitt (bank): free-standing 2-storey (28 ft), white roof with ductwork, red-brown brick (W: 2022 aerial)
grp([4393], WHITE_R, wall='f_brick_red', tint='#ffffff', shop=None, hft=31)
# 1712 Hewitt (restaurant): 2 storeys (27 ft), grey gravel roof; wall D
grp([4394], GREY_R, wall='f_brick_red', tint='#fff0e2', shop='shop_brick', shopon='N', blank='EWS', awn='#2a2c30', hft=30)
# 1714-1716 Hewitt (retail): one 2-storey building (29 ft at the street, lower at the back), pale roof; wall D
grp([4395, 4397], LIGHT_R, wall='f_brick_buff', tint='#eee6d6', shop='shop_buff', shopon='N', blank='EWS', hft=30)

# --- Rockefeller to Oakes, north side
# Commerce Building, 1801 Hewitt (R: National Register, built 1910; apartments): five footprints, 6 storeys (70 ft), grey gravel roof
grp([4346, 4347, 4339, 4325, 4306], GREY_R, wall='f_brick_buff', tint='#f6ecd8', shop='shop_buff', shopon='SW', blank='NE', hft=73)
# Morrow Building, 2823 Rockefeller (R: Everett Register): 2-3 storeys (34 ft), dark roof
grp([4290], DARK_R, wall='f_brick_red', tint='#ecdcd4', shop='shop_brick', shopon='W', blank='NES', hft=37)
# 1805 Hewitt (bar / retail): narrow 3-storey (35 ft), weathered grey roof with skylights; wall D
grp([4331, 4307], GREY_R, wall='f_brick_red', tint='#e2d6d2', shop='shop_brick', shopon='S', blank='NEW', awn='#2a2c30', hft=38)
# 1809 and 1811 Hewitt (electrical supplies): 2-storey (26 ft) and 1-storey (19 ft), both with bright white roofs; wall D
grp([4309], WHITE_R, wall='f_brick_red', tint='#e2d6d2', shop='shop_brick', shopon='S', blank='NW', hft=29)
grp([4311], WHITE_R, wall='f_brick_red', tint='#e2d6d2', shop='shop_brick', shopon='S', hft=21)
# --- Rockefeller to Oakes, south side
# 1804 Hewitt (31-50 apartments): 5 storeys (58 ft), pale roof with light wells; wall D
grp([4398], LIGHT_R, wall='f_brick_red', tint='#f3e6df', shop='shop_brick', shopon='NW', blank='E', hft=61)
# 1804-1806 Hewitt (12-15 apartments over shops): 3 storeys (30 ft), dark roofs; wall D
grp([4399], DARK_R, wall='f_brick_buff', tint='#e9dfcc', shop='shop_buff', shopon='N', blank='EWS', hft=34)
grp([4400, 4409], DARK_R, wall='f_brick_red', tint='#ecdcd4', shop='shop_brick', shopon='N', blank='EWS', awn='#3a5a3a', hft=33)
# 1808-1810 Hewitt (secondhand shops): single storey (13 ft), dark roof; wall D
grp([4401, 4402], DARK_R, wall='f_brick_dark', tint='#e4e6ea', shop='shop_modern', shopon='N', blank='EWS', hft=17)
# Watson's Bakery, 1812 Hewitt (R: Everett Register): 2 storeys (25 ft), white roof, red brick with a maroon parapet cap (W: 2022 aerial)
grp([4403, 4412], WHITE_R, wall='f_brick_red', tint='#f6e2da', shop='shop_brick', shopon='N', blank='W', hft=28)


# ---------------------------------------------------------------------------------------------------------------
# Wetmore Ave, end to end (23rd St to 37th St): from the dossiers wetmore_n, wetmore_c1, wetmore_c2, wetmore_s1, wetmore_s2.
# Heights, flat-roof colours, grouping and street sides come from the whole-map pass (data/dossier/auto.json).
# Set here: what the aerials show beyond that. Wall basis as above: W seen, R record, D inferred.
# ---------------------------------------------------------------------------------------------------------------
# parking as painted in the county 2024 aerial: (street, from y, to y, side with the 45 degree stalls); the other side is parallel
PARKING = [
    ('Wetmore Ave', 7508, 8936, 'E'), ('Wetmore Ave', 8936, 10424, 'E'), ('Wetmore Ave', 10424, 11924, 'E'),
    ('Wetmore Ave', 11924, 13464, 'W'), ('Wetmore Ave', 13464, 14943, 'W'),
]
SH_DARK, SH_MID, SH_BROWN, SH_LIGHT = '#4a4d52', '#6e7074', '#6b584c', '#a9adb0'
_SIDING = ['#d9d4c4', '#8c9096', '#e6e2d6', '#6f8aa3', '#b9a88c', '#a7abae', '#7d8c75', '#8fa6b5']


def gabled(ids, roof):
    """the aerial shows a pitched shingle roof: a house-form building (apartments or offices in a house), not a flat-roofed block. Siding colour is D."""
    for i in ids:
        B[i] = dict(wall='f_siding', tint=_SIDING[i % len(_SIDING)], roof='r_shingle', rtint=roof, pitched=True, shop=None, units=False)


# --- 22nd to 26th St: apartments and a church among houses
gabled([2795, 5954, 3319, 3975, 3990, 4002, 4018, 4032], SH_DARK)
gabled([2856, 3148, 3933], SH_BROWN)
B[2885] = dict(wall='f_siding', tint='#e6e2d6', roof='r_shingle', rtint=SH_DARK, pitched=True, shop=None, units=False)   # 2228 Wetmore, church: cross-gabled dark roof (W)
# --- 2600 block (26th St to Everett Ave)
gabled([4121, 4124], SH_DARK)                                                                    # 2623-2625: offices and a garage in gabled buildings (W roof)
B[4127] = dict(wall='f_cmu', tint='#cfcabd', roof='r_gravel', rtint='#4d4f4c', shop=None)        # 2631, auto repair: dark flat roof, tan shed at the back (W roof)
B[4072] = dict(wall='f_stucco', tint='#e4dfd2', shop=None)                                       # 2612, medical: L-shaped single storey round a car park
grp([4078], GREY_R, wall='f_cmu', tint='#d8d5cc', shop=None)                                     # 2605, contractor: plain single storey
grp([4083], LIGHT_R, wall='f_stucco', tint='#e9e4d6', shop='shop_modern', shopon='W')
grp([4087, 4090], LIGHT_R, wall='f_stucco', tint='#ddd8ca', shop='shop_modern', shopon='W')      # 2609-2611: one single-storey shop building
# Apex Art and Culture Center, 1611 Everett Ave (built 1921 for the Knights of Columbus, later the Masonic Temple). R: the register nomination
# gives red "burlap brick" on the Everett and Wetmore fronts, three storeys, and a roof overhang on brackets; the aerial shows that overhang in red tile (W)
B[4123] = dict(wall='f_brick_red', tint='#f6e2da', roof='r_membrane', rtint='#f0f1ee', shop='shop_brick', shopon='SE', awn='#a5553c', hft=48)
# --- 2700 block (Everett Ave to California St)
grp([4145], DARK_R, wall='f_brick_red', tint='#f3e6df', shop='shop_brick', shopon='WN', blank='S', hft=35)     # 2701: 3 storeys (32 ft), dark roof
grp([4154], GREY_R, wall='f_brick_dark', tint='#f0ece8', shop='shop_brick', shopon='W', blank='NS', hft=27)    # 2709: narrow 2-storey
# 2721: new apartment block with a rooftop solar array and a courtyard cut into the east side (W). No LiDAR yet (built after the survey):
# 4 storeys / 44 ft is estimated from the shadow it casts on 2709
B[6373] = dict(wall='f_panel', tint='#eceae4', stripe=('#5a5f66', 70, 3), roof='r_membrane', rtint='#d8dad6', shop='shop_modern', shopon='W', hft=44, units=False)
grp([4188], DARK_R, wall='f_brick_red', tint='#e2d6d2', shop='shop_brick', shopon='W', blank='NS', hft=31)
grp([4195], GREY_R, wall='f_concrete', tint='#efece4', shop='shop_modern', shopon='WS', hft=56)                 # 2731, offices: 4 storeys (53 ft), grey roof with plant
# --- 2800 block (California St to Hewitt Ave)
# Port Gardner Building, 2802 Wetmore: built 1929 as Rumbaugh's department store, later the Bon Marche, now Funko's headquarters and shop.
# R: Historic Everett's walking tour gives a cream-taupe ornamental terra cotta exterior; 5 storeys, white roof (W)
grp([4235, 4243], WHITE_R, wall='f_concrete', tint='#f4ead6', shop='shop_buff', shopon='NE', blank='S', hft=56)
grp([4257], DARK_R, wall='f_brick_dark', tint='#e4e6ea', shop='shop_modern', shopon='E', blank='NS', hft=17)
grp([4263], DARK_R, wall='f_brick_red', tint='#ecdcd4', shop='shop_brick', shopon='E', blank='N', hft=34)           # 2818: 2 storeys, dark ribbed roof (W)
grp([4253, 4260], GREY_R, wall='f_brick_red', tint='#f6e2da', shop='shop_brick', shopon='W', blank='NS', hft=55)    # IOOF Hall, 2813-2815 (R: built 1912, contributing to the Hewitt historic district, brick): 4 storeys (52 ft), weathered roof with a skylight grid (W)
# 2817 Salvation Army (1918), 2819 Robinson Building (about 1947), 2821 (1909): names and dates from the district nomination (R); walls D
grp([4266], LIGHT_R, wall='f_brick_buff', tint='#eee6d6', shop='shop_buff', shopon='W', blank='NS', hft=33)
grp([4271], LIGHT_R, wall='f_stucco', tint='#e9e4d6', shop='shop_modern', shopon='W', blank='NS', hft=22)
grp([4286], GREY_R, wall='f_brick_dark', tint='#f0ece8', shop='shop_brick', shopon='W', blank='NS', hft=20)
# --- 2900 block (Hewitt Ave to Wall St)
B[6385] = dict(wall='f_cmu', tint='#d0d0cc', roof='r_membrane', rtint='#9a9c96', shop=None, hft=10, units=False)   # car park attendant's booth
grp([4498], DARK_R, wall='f_brick_dark', tint='#e4e6ea', shop='shop_modern', shopon='W', blank='S', hft=17)
grp([4502], WHITE_R, wall='f_stucco', tint='#efe8d8', shop='shop_modern', shopon='W', blank='NS', hft=15)      # 2925, restaurant
grp([4511], WHITE_R, wall='f_stucco', tint='#e4dfd2', shop='shop_modern', shopon='W', blank='NS', hft=17)
grp([4532], GREY_R, wall='f_brick_red', tint='#f3e6df', shop='shop_brick', shopon='W', blank='NS', hft=17)
grp([4543, 4551, 4557], LIGHT_R, wall='f_cmu', tint='#dcd9d0', shop=None, blank='N', hft=21)                    # 2931-2933, printing works: one single-storey building
# --- 3000 block (Wall St to Pacific Ave)
# 3002 Wetmore, Everett City Hall of 1929, now police and council chamber. R: the National Register form gives Art Deco, four storeys,
# buff brick with terra cotta, flat roof, built up in setbacks; brown gravel roofs in the aerial (W)
B[6095] = dict(wall='f_brick_buff', tint='#f4e8cc', roof='r_gravel', rtint='#6f6654', shop=None, hft=46, pent=(150, 190, 12, '#e6dcc2', -30, -20))
B[5992] = dict(wall='f_brick_buff', tint='#f2f2f2', roof='r_membrane', rtint='#f0f0ec', shop=None, hft=25)       # 3028, municipal court: 2 storeys, white roof (W)
# --- south of Pacific Ave: flat-roofed blocks keep the measured looks; these are the house-form ones
gabled([5816, 4789, 4814, 4867, 4894, 4908, 4910, 5900, 5228, 5284, 5314, 5342, 5416, 5440, 5465, 5524, 5670, 5950], SH_MID)
gabled([4745], SH_BROWN)
gabled([4882], SH_LIGHT)                                                                         # 3314: pale grey gabled roof (W)
# Bank of Everett of 1963, now the Cope Gillette Theatre, 2730 Wetmore (Everett Register). R: mid-century, arches on slender white columns,
# gold Italian glass tile and large clear and amber windows, an umbrella-shell roof overhang. Drawn as amber glazing under a white overhang
B[4200] = dict(wall='f_glass', tint='#e3c06a', roof='r_membrane', rtint='#f2f2ee', shop=None, awn=None, hft=24)
# Everett Municipal Building (the Wall Street Building until 2024), 2930 Wetmore. R: ten floors, 147 ft, finished in 1983. The glass colour is still from the flyover notes
B[4539] = dict(B.get(4539, {}), hft=147)

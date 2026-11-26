# Hewitt Heat

An open-world driving game set in real downtown Everett, WA. It runs in the browser with no build step.

## Run it locally

```bash
npx serve .            # or: python3 -m http.server 8000
```

## What is real

- Streets, alleys and their names: City of Everett street centerlines
- 6,399 building footprints: City of Everett building footprints
- Terrain: City of Everett 2 ft contours
- Water, piers, parks, bus stops, landmarks, historic register: City of Everett GIS layers
- Building heights: measured from shadows in the city's 2022 aerial photo where possible, estimated from the use code otherwise

The aerial imagery itself is not in this repository.

## Google Photorealistic 3D Tiles (optional)

Open MAP, paste a Google Map Tiles API key and press "Use Google 3D". The key stays in your browser's local storage.
Restrict the key to this site's referrer and to the Map Tiles API. Append `?gz=<units>` to the URL to adjust the vertical offset (10 units = 1 m, default 220).

## Credits

- Map data: City of Everett GIS (gismaps.everettwa.gov)
- three.js (MIT), 3DTilesRendererJS by NASA-AMMOS (Apache-2.0), Draco decoder (Apache-2.0)
- Soldier and Michelle characters: three.js example models (Mixamo characters, under Adobe's Mixamo terms)
- Ready Player Me avatar: three.js example model (Ready Player Me terms)
- CesiumMan: Khronos glTF sample asset (CC BY 4.0, Cesium)
- Vehicles and facade textures: the Sketchfab CC BY 4.0 models credited in the Breachpoint README
- Ground textures and sky: CC0 from ambientCG and Poly Haven

## Story

The story is a seven-chapter screenplay (data/story.json): 114 voiced lines, dialogue scenes cut with wide, over-the-shoulder, close-up and low-angle shots, radio chatter during missions, a prologue and an epilogue. It is fiction. Every character, company and radio broadcast in them is invented and none of them depicts a real person. The city issues the story plays with (library hours, the downtown ballpark budget, historic buildings left to decay, license plate cameras) are real topics in Everett.

## Sketchfab models (CC BY 4.0)

Each model was simplified and had its textures reduced for the web.

- "Illinois '90 Police cruiser - Low poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/illinois-90-police-cruiser-low-poly-model-dc81625478a744649b210c7f248b0b6a
- "Illinois '90 Taxi #1 - Low poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/illinois-90-taxi-1-low-poly-model-72d91f4bce814818b3cd1f2de60f8ef2
- "Shvan '92 Ambulance - Low Poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/shvan-92-ambulance-low-poly-model-2856dd3c61f940909dced9a5c0379484
- "LCT 3000 '95 - Low poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/lct-3000-95-low-poly-model-663a0953c038434a918cb85725c88ffa
- "Phoenix 455 '71 - Low poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/phoenix-455-71-low-poly-model-955edc733c6d44fabc0ad7c246a15896
- "Fairheaven LT '80 - Low poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/fairheaven-lt-80-low-poly-model-e2678da920cc4be68dbc193727919ffb
- "Kiri '86 - Low poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/kiri-86-low-poly-model-5c17c582ef9549798f694b660feea42a
- "Fairheaven SW '84 - Low poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/fairheaven-sw-84-low-poly-model-aa0becb6e854422596cac6b21bf79787
- "Riverside '88 - Low poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/riverside-88-low-poly-model-8509a7f82665442592627940b7a1cfab
- "Illinois '90 - Low poly model" by Daniel Zhabotinsky (CC Attribution), https://sketchfab.com/3d-models/illinois-90-low-poly-model-d604871eee5b4181bb298163b0b675b7
- "Low-Poly G17" by TastyTony (CC Attribution), https://sketchfab.com/3d-models/low-poly-g17-60efc54ac59e47d18bdff94b2f5144ff
- "Low-Poly HK MP5" by TastyTony (CC Attribution), https://sketchfab.com/3d-models/low-poly-hk-mp5-80980f757c2c463ebc73460a31611652
- "Low-Poly Remington 870" by TastyTony (CC Attribution), https://sketchfab.com/3d-models/low-poly-remington-870-8766498ce778479aa03c3b6078937510
- "Low-Poly AK-47 Type 2" by TastyTony (CC Attribution), https://sketchfab.com/3d-models/low-poly-ak-47-type-2-a7260926fb0a40f8bba5f651b03d23f1

## Audio

Voice lines and sound effects were generated with ElevenLabs, using stock library voices only.

## Beyond downtown

With Google 3D Tiles on, ground height comes from the Google mesh, so ramps, bridge decks and underpasses are driveable and the world continues past the edge of the downtown map. The MAP screen has a travel menu for Snohomish County towns. County boundary, highways and place names: U.S. Census Bureau TIGER/Line (public domain).

## Built city model

Downtown no longer depends on Google 3D Tiles or aerial photos. Google tiles are off unless the player presses "Use Google 3D" in the MAP screen.

- `data/city.glb`: all 6,399 City of Everett footprints as one textured model (walls snapped to whole window bays and floors, storefront ground floors, parapets, rooftop units, hip roofs on houses, the port dome, the county parking garage).
- `tex/b/`: 21 materials (brick, glass, concrete, panel, siding, storefronts, roofs). Each one is modelled as geometry and rendered in Blender Cycles. None is a photograph.
- Materials and colours per building follow reference notes taken from flyover video of downtown. No imagery from Google or Apple is used in any asset.
- If `data/city.glb` fails to load, the game falls back to its generated buildings.

Rebuild:

```bash
pip install bpy pillow
python3 tools/textures.py tex/b                 # render the material set in Blender
python3 tools/citygen.py . data/city.glb quant  # build the game model
python3 tools/citygen.py . /tmp/stage/data/city_full.glb   # full-precision copy for Blender (textures in /tmp/stage/tex/b)
python3 tools/render_city.py /tmp/stage/data/city_full.glb . renders   # Blender stills
```

## Street props and people

The box placeholders for street lamps, signals, bus stops and trees are replaced with instanced models, and hydrants, picnic tables and trash barrels are added along streets and at bus stops. The placeholder figure is no longer used for pedestrians. If a model fails to load the game falls back to the old shapes.

All from Sketchfab under CC BY 4.0, modified for the game (re-based, scaled, textures reduced):

| Model | Author |
|---|---|
| Street lamp (low poly) | pinokio21 |
| Traffic Light | Pieter Ferreira |
| Bus Stop Shelter | R3indeer |
| Lowpoly Tree | dionne |
| Stylized Pine Tree Tree | Batuhan13 |
| Fire Hydrant [Low Poly] | Islide |
| Low-Poly Wooden Bench | Memorie |
| Photorealistic Trash Can (LOW POLY) | Derfmode |
| Low Poly Male, Low Poly Female (no longer shown; kept as spare models, re-dressed by `tools/people_prep.py`) | Loves_Art |

`tools/sketchfab_dl.py` and `tools/sketchfab_prep.py` rebuild them; the Sketchfab token is read from the `SKF` environment variable and is not stored in this repository.

Shadows use a 4096 map on desktop, and window glass on the building materials picks up sun glints.

## Opening chapters and voices

Two chapters now open the story: WELCOME BACK (the booted car and the walk to Pruitt's office) and 90 MINUTES (towing cars the moment their meters expire). Chapter data is in `data/story.json`; their lines are in `data/vo_w1.json` and `data/vo_w2.json`.

Danny, Marge, Pruitt and the lot attendant use custom ElevenLabs voices designed from written briefs (saved on the account as "HH Danny" and so on), and every existing line by those characters was re-recorded with them. The other characters still use their earlier voices. `tools/voices_design.py` and `tools/voices_synth.py` rebuild the audio; the key is read from the `ELEVEN` environment variable.

Mouths follow the voice audio (see Characters below).

## Interior sets

`models/set_office.glb` is Pruitt's office, modelled in Blender (`tools/build_office.py`). A chapter with `"set":"office"` in `data/story.json` plays its briefing inside the set: the two actors are moved into the building, the city shell is hidden for the scene, and everything is restored when it ends. If the player arrives in a car the scene plays outside as before.

`models/set_chamber.glb` is the council chamber (`tools/build_chamber.py`). A chapter can also stage its ending in a set (`"oset"`) and its MEANWHILE scene in one (`"pset"` with `"pat"` naming the landmark). Sets carry their own lights and the sun is dimmed while one is showing.

All nine story voices are now custom designs ("HH" voices on the ElevenLabs account); all 133 story lines use them.

## Characters

The player, the nine story characters, the police officer and four pedestrians are realistic textured people generated with Meshy (text to 3D, then Meshy's rigging and its walk and run clips). Files are `models/hh_<name>.b64.txt`, about 12,000 triangles and one 1024 px texture each.

`tools/people_meshy.py MESHY_OUT_DIR` packs them: it merges the walk and run clips into the rigged model, recomputes smooth normals, and builds a `mouthOpen` shape for each face by lowering the front of the head below that face's lip line (the per-face lip positions are in `MOUTH` in the script). The standing pose is the walk clip averaged over its length. The Meshy key is read from the `MESHY` environment variable when generating and is not stored in this repository.

Mouths are driven by the voice audio: each line's loudness is measured 30 times a second and sets how far the speaker's mouth opens, so it opens on words and closes in pauses and when the line ends. A line with no audio falls back to a generic talking motion.

Only the player, the officer and the four pedestrians load at start. A story character's model loads when its chapter becomes current or when the character is first on screen; a pedestrian stands in for the moment until it arrives.

## Block by block

Downtown is being matched to the owner's flyover recording one block at a time. The recording is reference only (which building stands where, storeys, colours, roofs, trees, cleared lots); nothing is copied from it. `tools/blocks.py` holds the per-building looks, keyed by footprint index, and `tools/blockmap.py` draws an indexed footprint map of any area to work from. `tools/citygen.py` applies them and also writes `data/extras.json` (street trees, site machines, lots that scattered trees keep out of), which the game reads.

Done so far:

| Blocks | What was set |
|---|---|
| Pacific Ave, north side, Grand to Rucker | Four-storey apartment row with alternating blue and white fronts, street trees |
| Pacific Ave, south side, Grand to Rucker | Fenced, graded dirt lot with two excavators |
| Rucker Ave, west side, Pacific to Wall | One footprint split into the blue-doored garage, the brick shop and the building under construction (sheathed walls, open framing); two-storey white and charcoal buildings north of it; street trees both sides |
| Rucker and Pacific, north-east corner | Tan two-storey building |
| Grand Ave, California to Hewitt | Brick market building, white and orange six-storey apartments at Hewitt, grey and teal five-storey block, long white single-storey building opposite, street trees |
| County campus | Administration tower changed to near-black glass |
| Broadway, west side, 33rd to 34th | White five-storey apartments, tan brick building and the white-roofed one behind it added (missing from the footprint data); the corner building the recording shows as a grass lot removed; cream and white buildings toward Lombard |
| Broadway, east side, 32nd to 33rd | Orange-tan and teal single-storey buildings, pale blue warehouse, brick two-storey |
| Rockefeller and Wall | Brick church with a green spire, small white buildings in the lot east of it, dark glass city offices behind |
| Hewitt Ave, Wetmore to Oakes | Street trees both sides, brick building with the pale blue metal roof at Oakes, arena roof pale blue |

`GONE` and `ADD` in `tools/blocks.py` remove or add whole buildings where the recording and the footprint data disagree; citygen then also rewrites the collision map (`data/map.png`, original kept as `data/map_base.png`) so the game's walls match what is drawn.

The excavator is a Meshy-generated model packed by `tools/prop_meshy.py`. The recording is 220 px wide, so signs and window detail cannot be read from it; storeys, colours and massing can.


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

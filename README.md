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

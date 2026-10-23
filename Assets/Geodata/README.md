# Pandori Nijjaran map extracts

Origin: **31.4610594 N, 75.7240654 E**. X points east and Y north in the
Unreal map. One meter is 100 Unreal units. This origin is a locality reference,
not a surveyed marker. The [district post-office page](https://jalandhar.nic.in/public-utility/pandori-nijjran-b-o/)
confirms Pandori Nijjran, Jalandhar-II, PIN 144102.

- `pandori_nijjaran.osm.json`: OpenStreetMap roads, fetched through Overpass
  on 2026-10-23. Query bounds: south 31.453, west 75.714, north 31.469, east 75.734.
- `pandori_nijjaran.buildings.geojson`: Overture Maps buildings, release
  2026-10-21.0, downloaded with overturemaps 1.0.2. 824 source features;
  821 centers lie inside the playable boundary. Provider metadata is preserved.
- `provenance.json`: checksums, bounds, sources, and explicit assumptions.

Attribution: **© OpenStreetMap contributors, Overture Maps Foundation;
Microsoft Global ML Building Footprints; Google Open Buildings**.
The road/building databases and their adaptations are available under
[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
Google Open Buildings attribution is retained under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
See [Overture's source attribution](https://docs.overturemaps.org/attribution/#buildings).
The source-code MIT license does not replace these data licenses.

To fetch a *new* Overture extract into a separate file:

```powershell
python -m pip install overturemaps
overturemaps download --bbox=75.7173,31.4553,75.7308,31.4668 -f geojson --type=building -o new_buildings.geojson
```

The client defaults to the latest release. The checked-in extract is the
reproducible input; refreshing it requires updating provenance and geometry tests.
Mapped outlines are machine-generated and may be inaccurate. Heights, materials,
openings, vegetation and terrain elevation are not measurements. Building
shells have collision and closed exterior walls; visual doors do not provide
surveyed or explorable interiors.

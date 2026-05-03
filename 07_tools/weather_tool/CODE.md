# Weather tool (Open-Meteo)

**[Open-Meteo](https://open-meteo.com/)** serves free forecast data with **no API key**. This script reads **current** **`temperature_2m`**. For a **human place name** in the answer, it can geocode a **`town`** via Open-Meteo’s **[geocoding API](https://open-meteo.com/en/docs/geocoding-api)**; for agents that already have coordinates, it accepts **`latitude`** and **`longitude`** instead.

The reply always includes a **location label** (e.g. **`Berlin, Germany`**) so the model and user see *where* the number applies.

---

## Runnable

Run **[`weather_tool.py`](./weather_tool.py)** with no args (defaults to **Berlin**), a **positional town**, or **`--lat` / `--lon`** together.

```bash
uv run python 07_tools/weather_tool/weather_tool.py
uv run python 07_tools/weather_tool/weather_tool.py Paris
uv run python 07_tools/weather_tool/weather_tool.py --lat 52.52 --lon 13.41
```

---

## Code walkthrough (`weather_tool.py`)

### 1. `WeatherParams`: flexible input, one validation rule

At the schema level **`town`**, **`latitude`**, and **`longitude`** are all optional so the LLM can send either style. A **`model_validator(mode="after")`** enforces the real rule: you must supply a **non-empty town** **or** **both** coordinates. That keeps **`ToolRegistry`** strict without pushing complex `oneOf` logic into JSON Schema.

```python
class WeatherParams(BaseModel):
    town: str | None = Field(
        default=None,
        description="Place name; resolved with Open-Meteo geocoding (first hit)",
    )
    latitude: float | None = Field(
        default=None,
        description="WGS84 latitude (use with longitude if you do not pass town)",
    )
    longitude: float | None = Field(
        default=None,
        description="WGS84 longitude (use with latitude if you do not pass town)",
    )

    @model_validator(mode="after")
    def town_or_coords(self) -> Self:
        has_town = bool(self.town and self.town.strip())
        has_coords = self.latitude is not None and self.longitude is not None
        if has_town or has_coords:
            return self
        raise ValueError("Set non-empty town, or both latitude and longitude")
```

**Takeaway:** **`Field(description=...)`** teaches the model the fields; **`model_validator`** teaches your runtime the **combinations** that are legal.

---

### 2. `resolve`: geocode vs raw coordinates

If **`town`** is set, we delegate to **`_geocode_town`**. Otherwise we assert coordinates exist (guaranteed after validation) and build a short numeric label like **`48.85, 2.35`** for the reply text.

```python
    def resolve(self) -> tuple[float, float, str]:
        """Return latitude, longitude, and a human label for the forecast point."""
        if self.town and self.town.strip():
            return _geocode_town(self.town.strip())
        assert self.latitude is not None and self.longitude is not None
        lat, lon = self.latitude, self.longitude
        place = f"{lat:.2f}, {lon:.2f}"
        return lat, lon, place
```

**Takeaway:** returning **`(lat, lon, place)`** keeps **`weather_current_c`** focused on HTTP + parsing; location policy stays in one method.

---

### 3. `_geocode_town`: first search hit → label

We request a **single** result (query parameter **`count=1`**) to keep behavior predictable. The display string prefers **`"Name, Country"`** when **`country`** is present.

```python
def _geocode_town(town: str) -> tuple[float, float, str]:
    r = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": town, "count": 1},
        timeout=10.0,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or []
    if not results:
        raise ValueError(f"No geocoding results for: {town}")
    hit = results[0]
    lat = float(hit["latitude"])
    lon = float(hit["longitude"])
    name = hit.get("name") or town
    country = hit.get("country") or ""
    place = f"{name}, {country}" if country else name
    return lat, lon, place
```

**Takeaway:** ambiguous names (“Springfield”) always resolve to **Open-Meteo’s first hit** - in production you would disambiguate (list choices, ask the user, or use structured geocoder metadata).

---

### 4. Forecast GET and user-facing string

**`resolve`** supplies WGS84 coordinates for the **forecast** endpoint. The final line embeds **`place`** so the model’s context clearly ties temperature to geography.

```python
def weather_current_c(params: WeatherParams) -> str:
    lat, lon, place = params.resolve()
    url = "https://api.open-meteo.com/v1/forecast"
    r = httpx.get(
        url,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m",
        },
        timeout=10.0,
    )
    r.raise_for_status()
    data = r.json()
    t = data.get("current", {}).get("temperature_2m")
    if t is None:
        return f"No temperature in response for {place}"
    return f"Current temperature in {place}: {t} °C"
```

**Takeaway:** two HTTP calls (geocode + forecast) only run when **`town`** is used; coordinate-only calls skip geocoding.

---

### 5. CLI: positional town vs `--lat` / `--lon`

**`argparse`** mirrors the model: either both coordinate flags, or a town (defaulting to **Berlin** when nothing is passed). Mismatched flags (**`--lat`** without **`--lon`**) call **`p.error`** so the user gets a clear message.

```python
    p.add_argument(
        "town",
        nargs="?",
        default=None,
        help="Place name (geocoded). Default: Berlin if you omit town and coordinates.",
    )
    p.add_argument("--lat", type=float, default=None, help="Latitude (with --lon, skips town)")
    p.add_argument("--lon", type=float, default=None, help="Longitude (with --lat, skips town)")
    args = p.parse_args()
    if args.lat is not None or args.lon is not None:
        if args.lat is None or args.lon is None:
            p.error("--lat and --lon must be used together")
        print(weather_current_c(WeatherParams(latitude=args.lat, longitude=args.lon, town=None)))
    else:
        town = args.town if args.town else "Berlin"
        print(weather_current_c(WeatherParams(town=town)))
```

**Takeaway:** CLI defaults (**Berlin**) match the “run with no args” story in the chapter README; **`WeatherParams`** itself has no default town so programmatic callers must be explicit.

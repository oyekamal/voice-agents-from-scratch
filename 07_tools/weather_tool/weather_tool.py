"""Fetch current temperature with Open-Meteo (no API key)."""

from __future__ import annotations

import httpx
from pydantic import BaseModel, Field, model_validator
from typing import Self


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

    def resolve(self) -> tuple[float, float, str]:
        """Return latitude, longitude, and a human label for the forecast point."""
        if self.town and self.town.strip():
            return _geocode_town(self.town.strip())
        assert self.latitude is not None and self.longitude is not None
        lat, lon = self.latitude, self.longitude
        place = f"{lat:.2f}, {lon:.2f}"
        return lat, lon, place


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


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Current temperature (Open-Meteo forecast + geocoding).")
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

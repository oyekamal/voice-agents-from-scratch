"""Shared ToolRegistry for chapter 07 (tool_router, llm_tool_loop, projects)."""

from __future__ import annotations

import sys
from pathlib import Path

_CH07 = Path(__file__).resolve().parent
if str(_CH07) not in sys.path:
    sys.path.insert(0, str(_CH07))

from voice_agents.tools.registry import ToolRegistry

from calculator_tool.calculator_tool import CalcParams, calculator_eval
from time_tool.time_tool import TimeParams, time_now
from weather_tool.weather_tool import WeatherParams, weather_current_c
from web_search_tool.web_search_tool import SearchParams, web_search_lite


def build_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("weather", WeatherParams, lambda m: weather_current_c(m))
    r.register("search", SearchParams, lambda m: web_search_lite(m))
    r.register("calc", CalcParams, lambda m: calculator_eval(m))
    r.register("time", TimeParams, lambda m: time_now(m))
    return r

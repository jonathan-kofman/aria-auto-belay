#!/usr/bin/env python3
"""
generate_map.py — 3D Landmark & F1 Circuit STL Generator

Fetches free public geodata and generates print-ready STL files,
same concept as printpal.io.

Data sources (no API keys required):
  Geometry:  OpenStreetMap via Overpass API   — openstreetmap.org
  Elevation: OpenTopoData SRTM 90m            — opentopodata.org

Usage:
    python generate_map.py "Monaco F1"
    python generate_map.py "Eiffel Tower"
    python generate_map.py "Grand Canyon"
    python generate_map.py --list
    python generate_map.py "Monaco F1" --base-mm 150 --z-scale 2
    python generate_map.py --lat 48.8584 --lon 2.2945 --radius 600 "Custom"
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Callable

import numpy as np
import requests

ROOT    = Path(__file__).resolve().parent
OUT_DIR = ROOT / "outputs" / "stl" / "maps"

# ─── Preset locations ─────────────────────────────────────────────────────────
# type: "buildings" | "f1" | "terrain"
# z_scale: vertical exaggeration (buildings=1, terrain=3-5, f1=2)

PRESETS: dict[str, dict] = {
    # ── World landmarks ───────────────────────────────────────────────────────
    "eiffel tower":            {"lat":  48.8584, "lon":   2.2945, "radius_m":   600, "type": "buildings", "z_scale": 1.0},
    "colosseum":               {"lat":  41.8902, "lon":  12.4922, "radius_m":   400, "type": "buildings", "z_scale": 1.0},
    "big ben":                 {"lat":  51.5007, "lon":  -0.1246, "radius_m":   350, "type": "buildings", "z_scale": 1.2},
    "burj khalifa":            {"lat":  25.1972, "lon":  55.2744, "radius_m":   800, "type": "buildings", "z_scale": 1.0},
    "sagrada familia":         {"lat":  41.4036, "lon":   2.1744, "radius_m":   350, "type": "buildings", "z_scale": 1.2},
    "sydney opera house":      {"lat": -33.8568, "lon": 151.2153, "radius_m":   500, "type": "buildings", "z_scale": 1.0},
    "empire state building":   {"lat":  40.7484, "lon": -73.9967, "radius_m":   500, "type": "buildings", "z_scale": 1.0},
    "cn tower":                {"lat":  43.6426, "lon": -79.3871, "radius_m":   400, "type": "buildings", "z_scale": 1.0},
    "notre dame":              {"lat":  48.8530, "lon":   2.3499, "radius_m":   300, "type": "buildings", "z_scale": 1.2},
    "taj mahal":               {"lat":  27.1751, "lon":  78.0421, "radius_m":   500, "type": "buildings", "z_scale": 1.0},
    "chrysler building":       {"lat":  40.7516, "lon": -73.9755, "radius_m":   400, "type": "buildings", "z_scale": 1.0},
    "acropolis":               {"lat":  37.9715, "lon":  23.7267, "radius_m":   600, "type": "buildings", "z_scale": 2.0},
    "st pauls cathedral":      {"lat":  51.5138, "lon":  -0.0984, "radius_m":   350, "type": "buildings", "z_scale": 1.2},
    "pompidou centre":         {"lat":  48.8606, "lon":   2.3522, "radius_m":   400, "type": "buildings", "z_scale": 1.0},
    "stonehenge":              {"lat":  51.1789, "lon":  -1.8262, "radius_m":   300, "type": "buildings", "z_scale": 1.5},
    "machu picchu":            {"lat": -13.1631, "lon": -72.5450, "radius_m":  1500, "type": "terrain",   "z_scale": 2.5},
    "angkor wat":              {"lat":  13.4125, "lon": 103.8670, "radius_m":  1500, "type": "buildings", "z_scale": 1.2},
    "petra":                   {"lat":  30.3285, "lon":  35.4444, "radius_m":  2000, "type": "terrain",   "z_scale": 2.0},
    "hagia sophia":            {"lat":  41.0086, "lon":  28.9802, "radius_m":   300, "type": "buildings", "z_scale": 1.2},
    "parthenon":               {"lat":  37.9715, "lon":  23.7267, "radius_m":   400, "type": "buildings", "z_scale": 2.0},
    "tower of london":         {"lat":  51.5081, "lon":  -0.0759, "radius_m":   300, "type": "buildings", "z_scale": 1.2},
    "buckingham palace":       {"lat":  51.5014, "lon":  -0.1419, "radius_m":   500, "type": "buildings", "z_scale": 1.0},
    "louvre":                  {"lat":  48.8606, "lon":   2.3376, "radius_m":   600, "type": "buildings", "z_scale": 1.0},
    "vatican":                 {"lat":  41.9029, "lon":  12.4534, "radius_m":   800, "type": "buildings", "z_scale": 1.2},
    "duomo milan":             {"lat":  45.4641, "lon":   9.1919, "radius_m":   400, "type": "buildings", "z_scale": 1.2},
    "manhattan":               {"lat":  40.7549, "lon": -73.9840, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "dubai marina":            {"lat":  25.0805, "lon":  55.1403, "radius_m":  1500, "type": "buildings", "z_scale": 1.0},
    "petronas towers":         {"lat":   3.1579, "lon": 101.7116, "radius_m":   500, "type": "buildings", "z_scale": 1.0},
    "tokyo skytree":           {"lat":  35.7101, "lon": 139.8107, "radius_m":   600, "type": "buildings", "z_scale": 1.0},
    "space needle":            {"lat":  47.6205, "lon":-122.3493, "radius_m":   400, "type": "buildings", "z_scale": 1.0},
    "golden gate bridge":      {"lat":  37.8199, "lon":-122.4783, "radius_m":  1500, "type": "terrain",   "z_scale": 1.5},
    "brooklyn bridge":         {"lat":  40.7061, "lon": -73.9969, "radius_m":   600, "type": "buildings", "z_scale": 1.0},
    "niagara falls":           {"lat":  43.0822, "lon": -79.0748, "radius_m":  2000, "type": "terrain",   "z_scale": 1.5},
    "victoria falls":          {"lat": -17.9243, "lon":  25.8572, "radius_m":  2000, "type": "terrain",   "z_scale": 1.5},
    "mount rushmore":          {"lat":  43.8791, "lon":-103.4591, "radius_m":  1500, "type": "terrain",   "z_scale": 1.5},
    "statue of liberty":       {"lat":  40.6892, "lon": -74.0445, "radius_m":   400, "type": "buildings", "z_scale": 1.2},
    "colosseum rome":          {"lat":  41.8902, "lon":  12.4922, "radius_m":   400, "type": "buildings", "z_scale": 1.0},
    "westminster":             {"lat":  51.4994, "lon":  -0.1245, "radius_m":   600, "type": "buildings", "z_scale": 1.2},

    # ── F1 circuits ───────────────────────────────────────────────────────────
    "monaco":                  {"lat":  43.7347, "lon":   7.4213, "radius_m":  1500, "type": "f1",        "z_scale": 2.0},
    "silverstone":             {"lat":  52.0786, "lon":  -1.0169, "radius_m":  3000, "type": "f1",        "z_scale": 3.0},
    "monza":                   {"lat":  45.6156, "lon":   9.2811, "radius_m":  3000, "type": "f1",        "z_scale": 3.0},
    "spa":                     {"lat":  50.4372, "lon":   5.9714, "radius_m":  4500, "type": "f1",        "z_scale": 2.5},
    "spa francorchamps":       {"lat":  50.4372, "lon":   5.9714, "radius_m":  4500, "type": "f1",        "z_scale": 2.5},
    "suzuka":                  {"lat":  34.8431, "lon": 136.5407, "radius_m":  3000, "type": "f1",        "z_scale": 2.5},
    "interlagos":              {"lat": -23.7036, "lon": -46.6997, "radius_m":  2500, "type": "f1",        "z_scale": 3.0},
    "nurburgring":             {"lat":  50.3356, "lon":   6.9475, "radius_m":  5000, "type": "f1",        "z_scale": 2.0},
    "bahrain":                 {"lat":  26.0325, "lon":  50.5106, "radius_m":  3000, "type": "f1",        "z_scale": 2.0},
    "abu dhabi":               {"lat":  24.4672, "lon":  54.6031, "radius_m":  3000, "type": "f1",        "z_scale": 2.0},
    "hungary":                 {"lat":  47.5830, "lon":  19.2526, "radius_m":  2500, "type": "f1",        "z_scale": 3.0},
    "hungaroring":             {"lat":  47.5830, "lon":  19.2526, "radius_m":  2500, "type": "f1",        "z_scale": 3.0},
    "imola":                   {"lat":  44.3439, "lon":  11.7167, "radius_m":  2500, "type": "f1",        "z_scale": 3.0},
    "zandvoort":               {"lat":  52.3888, "lon":   4.5457, "radius_m":  2000, "type": "f1",        "z_scale": 2.0},
    "cota":                    {"lat":  30.1328, "lon": -97.6411, "radius_m":  3500, "type": "f1",        "z_scale": 2.5},
    "austin":                  {"lat":  30.1328, "lon": -97.6411, "radius_m":  3500, "type": "f1",        "z_scale": 2.5},
    "las vegas strip":         {"lat":  36.1699, "lon":-115.1398, "radius_m":  3500, "type": "f1",        "z_scale": 2.0},
    "singapore":               {"lat":   1.2914, "lon": 103.8639, "radius_m":  2500, "type": "f1",        "z_scale": 2.0},
    "montreal":                {"lat":  45.5058, "lon": -73.5228, "radius_m":  2500, "type": "f1",        "z_scale": 2.5},
    "mexico city f1":          {"lat":  19.4042, "lon": -99.0907, "radius_m":  3000, "type": "f1",        "z_scale": 2.0},
    "miami":                   {"lat":  25.9580, "lon": -80.2389, "radius_m":  2500, "type": "f1",        "z_scale": 2.0},
    "jeddah":                  {"lat":  21.6319, "lon":  39.1044, "radius_m":  3000, "type": "f1",        "z_scale": 2.0},
    "baku":                    {"lat":  40.3725, "lon":  49.8533, "radius_m":  3000, "type": "f1",        "z_scale": 2.0},
    "azerbaijan":              {"lat":  40.3725, "lon":  49.8533, "radius_m":  3000, "type": "f1",        "z_scale": 2.0},
    "melbourne":               {"lat": -37.8497, "lon": 144.9680, "radius_m":  2500, "type": "f1",        "z_scale": 2.0},
    "albert park":             {"lat": -37.8497, "lon": 144.9680, "radius_m":  2500, "type": "f1",        "z_scale": 2.0},
    "shanghai":                {"lat":  31.3389, "lon": 121.2198, "radius_m":  3000, "type": "f1",        "z_scale": 2.0},
    "barcelona":               {"lat":  41.5700, "lon":   2.2611, "radius_m":  3000, "type": "f1",        "z_scale": 3.0},
    "catalunya":               {"lat":  41.5700, "lon":   2.2611, "radius_m":  3000, "type": "f1",        "z_scale": 3.0},
    "austria":                 {"lat":  47.2197, "lon":  14.7647, "radius_m":  2500, "type": "f1",        "z_scale": 3.0},
    "red bull ring":           {"lat":  47.2197, "lon":  14.7647, "radius_m":  2500, "type": "f1",        "z_scale": 3.0},
    "portimao":                {"lat":  37.2272, "lon":  -8.6267, "radius_m":  2500, "type": "f1",        "z_scale": 3.0},
    "algarve":                 {"lat":  37.2272, "lon":  -8.6267, "radius_m":  2500, "type": "f1",        "z_scale": 3.0},
    "paul ricard":             {"lat":  43.2506, "lon":   5.7914, "radius_m":  3500, "type": "f1",        "z_scale": 2.5},
    "le mans":                 {"lat":  47.9567, "lon":   0.2072, "radius_m":  8000, "type": "f1",        "z_scale": 2.0},
    "daytona":                 {"lat":  29.1858, "lon": -81.0711, "radius_m":  2000, "type": "f1",        "z_scale": 2.0},
    "laguna seca":             {"lat":  36.5844, "lon":-121.7536, "radius_m":  2000, "type": "f1",        "z_scale": 3.0},
    "hockenheim":              {"lat":  49.3278, "lon":   8.5656, "radius_m":  3000, "type": "f1",        "z_scale": 2.5},
    "sepang":                  {"lat":   2.7606, "lon": 101.7381, "radius_m":  3000, "type": "f1",        "z_scale": 2.0},
    "istanbul park":           {"lat":  40.9517, "lon":  29.4050, "radius_m":  2500, "type": "f1",        "z_scale": 3.0},

    # ── Natural terrain & geography ───────────────────────────────────────────
    "grand canyon":            {"lat":  36.0544, "lon":-112.1401, "radius_m":  8000, "type": "terrain",   "z_scale": 1.0},
    "mount fuji":              {"lat":  35.3606, "lon": 138.7274, "radius_m":  8000, "type": "terrain",   "z_scale": 1.0},
    "vesuvius":                {"lat":  40.8217, "lon":  14.4264, "radius_m":  5000, "type": "terrain",   "z_scale": 1.2},
    "mount vesuvius":          {"lat":  40.8217, "lon":  14.4264, "radius_m":  5000, "type": "terrain",   "z_scale": 1.2},
    "mount everest":           {"lat":  27.9881, "lon":  86.9250, "radius_m": 12000, "type": "terrain",   "z_scale": 0.8},
    "everest":                 {"lat":  27.9881, "lon":  86.9250, "radius_m": 12000, "type": "terrain",   "z_scale": 0.8},
    "matterhorn":              {"lat":  45.9763, "lon":   7.6586, "radius_m":  5000, "type": "terrain",   "z_scale": 1.0},
    "yellowstone":             {"lat":  44.4280, "lon":-110.5885, "radius_m": 10000, "type": "terrain",   "z_scale": 1.5},
    "rocky mountains":         {"lat":  40.3428, "lon":-105.6836, "radius_m":  6000, "type": "terrain",   "z_scale": 3.0},
    "rockies":                 {"lat":  39.5501, "lon":-105.7821, "radius_m": 20000, "type": "terrain",   "z_scale": 0.8},
    "alps":                    {"lat":  46.8182, "lon":   8.2275, "radius_m": 15000, "type": "terrain",   "z_scale": 0.8},
    "swiss alps":              {"lat":  46.8182, "lon":   8.2275, "radius_m": 15000, "type": "terrain",   "z_scale": 0.8},
    "mont blanc":              {"lat":  45.8326, "lon":   6.8652, "radius_m":  8000, "type": "terrain",   "z_scale": 0.9},
    "kilimanjaro":             {"lat":  -3.0674, "lon":  37.3556, "radius_m": 10000, "type": "terrain",   "z_scale": 0.9},
    "mount kenya":             {"lat":  -0.1521, "lon":  37.3084, "radius_m":  8000, "type": "terrain",   "z_scale": 1.0},
    "andes":                   {"lat": -32.6532, "lon": -70.0109, "radius_m": 20000, "type": "terrain",   "z_scale": 0.7},
    "aconcagua":               {"lat": -32.6532, "lon": -70.0109, "radius_m": 10000, "type": "terrain",   "z_scale": 0.9},
    "himalayas":               {"lat":  28.0000, "lon":  84.0000, "radius_m": 25000, "type": "terrain",   "z_scale": 0.6},
    "k2":                      {"lat":  35.8825, "lon":  76.5133, "radius_m": 10000, "type": "terrain",   "z_scale": 0.8},
    "denali":                  {"lat":  63.0695, "lon":-151.0074, "radius_m": 10000, "type": "terrain",   "z_scale": 0.9},
    "mount whitney":           {"lat":  36.5785, "lon":-118.2923, "radius_m":  6000, "type": "terrain",   "z_scale": 1.0},
    "death valley":            {"lat":  36.5054, "lon":-117.0794, "radius_m": 12000, "type": "terrain",   "z_scale": 1.2},
    "sahara":                  {"lat":  23.4162, "lon":  25.6628, "radius_m": 20000, "type": "terrain",   "z_scale": 2.0},
    "iceland":                 {"lat":  64.9631, "lon": -19.0208, "radius_m": 20000, "type": "terrain",   "z_scale": 1.2},
    "etna":                    {"lat":  37.7510, "lon":  14.9934, "radius_m":  6000, "type": "terrain",   "z_scale": 1.2},
    "mount st helens":         {"lat":  46.1912, "lon":-122.1944, "radius_m":  8000, "type": "terrain",   "z_scale": 1.0},
    "yosemite":                {"lat":  37.7456, "lon":-119.5936, "radius_m": 10000, "type": "terrain",   "z_scale": 1.2},
    "bryce canyon":            {"lat":  37.5930, "lon":-112.1871, "radius_m":  6000, "type": "terrain",   "z_scale": 1.5},
    "zion":                    {"lat":  37.2982, "lon":-113.0263, "radius_m":  5000, "type": "terrain",   "z_scale": 1.5},
    "dolomites":               {"lat":  46.4102, "lon":  11.8440, "radius_m": 10000, "type": "terrain",   "z_scale": 1.0},
    "fjords norway":           {"lat":  60.4720, "lon":   7.0699, "radius_m": 10000, "type": "terrain",   "z_scale": 1.2},
    "scottish highlands":      {"lat":  57.1200, "lon":  -4.7100, "radius_m": 15000, "type": "terrain",   "z_scale": 1.5},
    "ben nevis":               {"lat":  56.7969, "lon":  -5.0035, "radius_m":  5000, "type": "terrain",   "z_scale": 1.5},
    "snowdon":                 {"lat":  53.0685, "lon":  -4.0762, "radius_m":  4000, "type": "terrain",   "z_scale": 1.8},
    "mount olympus":           {"lat":  40.0859, "lon":  22.3583, "radius_m":  6000, "type": "terrain",   "z_scale": 1.2},
    "uluru":                   {"lat": -25.3444, "lon": 131.0369, "radius_m":  5000, "type": "terrain",   "z_scale": 2.0},
    "ayers rock":              {"lat": -25.3444, "lon": 131.0369, "radius_m":  5000, "type": "terrain",   "z_scale": 2.0},
    "table mountain":          {"lat": -33.9628, "lon":  18.4098, "radius_m":  5000, "type": "terrain",   "z_scale": 1.5},
    "mount cook":              {"lat": -43.5950, "lon": 170.1418, "radius_m":  8000, "type": "terrain",   "z_scale": 1.0},
    "volcanic crater":         {"lat":  19.4213, "lon":-155.2860, "radius_m":  6000, "type": "terrain",   "z_scale": 1.5},
    "kilauea":                 {"lat":  19.4213, "lon":-155.2860, "radius_m":  6000, "type": "terrain",   "z_scale": 1.5},
    "mount rainier":           {"lat":  46.8523, "lon":-121.7603, "radius_m":  8000, "type": "terrain",   "z_scale": 1.0},
    "mount hood":              {"lat":  45.3735, "lon":-121.6959, "radius_m":  6000, "type": "terrain",   "z_scale": 1.2},

    # ── Cities (urban density maps) ───────────────────────────────────────────
    "paris":                   {"lat":  48.8566, "lon":   2.3522, "radius_m":  3000, "type": "buildings", "z_scale": 1.0},
    "london":                  {"lat":  51.5074, "lon":  -0.1278, "radius_m":  3000, "type": "buildings", "z_scale": 1.0},
    "new york":                {"lat":  40.7549, "lon": -73.9840, "radius_m":  3000, "type": "buildings", "z_scale": 1.0},
    "nyc":                     {"lat":  40.7549, "lon": -73.9840, "radius_m":  3000, "type": "buildings", "z_scale": 1.0},
    "tokyo":                   {"lat":  35.6762, "lon": 139.6503, "radius_m":  3000, "type": "buildings", "z_scale": 1.0},
    "dubai":                   {"lat":  25.2048, "lon":  55.2708, "radius_m":  3000, "type": "buildings", "z_scale": 1.0},
    "hong kong":               {"lat":  22.3193, "lon": 114.1694, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "shanghai city":           {"lat":  31.2304, "lon": 121.4737, "radius_m":  3000, "type": "buildings", "z_scale": 1.0},
    "chicago":                 {"lat":  41.8781, "lon": -87.6298, "radius_m":  2500, "type": "buildings", "z_scale": 1.0},
    "san francisco":           {"lat":  37.7749, "lon":-122.4194, "radius_m":  2000, "type": "buildings", "z_scale": 1.5},
    "los angeles":             {"lat":  34.0522, "lon":-118.2437, "radius_m":  3000, "type": "buildings", "z_scale": 1.0},
    "toronto":                 {"lat":  43.6532, "lon": -79.3832, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "sydney":                  {"lat": -33.8688, "lon": 151.2093, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "rome":                    {"lat":  41.9028, "lon":  12.4964, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "amsterdam":               {"lat":  52.3676, "lon":   4.9041, "radius_m":  1500, "type": "buildings", "z_scale": 1.0},
    "berlin":                  {"lat":  52.5200, "lon":  13.4050, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "madrid":                  {"lat":  40.4168, "lon":  -3.7038, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "moscow":                  {"lat":  55.7558, "lon":  37.6176, "radius_m":  2500, "type": "buildings", "z_scale": 1.0},
    "istanbul city":           {"lat":  41.0082, "lon":  28.9784, "radius_m":  2000, "type": "buildings", "z_scale": 1.2},
    "singapore city":          {"lat":   1.3521, "lon": 103.8198, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "seoul":                   {"lat":  37.5665, "lon": 126.9780, "radius_m":  2500, "type": "buildings", "z_scale": 1.2},
    "osaka":                   {"lat":  34.6937, "lon": 135.5023, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "beijing":                 {"lat":  39.9042, "lon": 116.4074, "radius_m":  2500, "type": "buildings", "z_scale": 1.0},
    "mumbai":                  {"lat":  19.0760, "lon":  72.8777, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "cairo":                   {"lat":  30.0444, "lon":  31.2357, "radius_m":  2500, "type": "buildings", "z_scale": 1.0},
    "rio de janeiro":          {"lat": -22.9068, "lon": -43.1729, "radius_m":  3000, "type": "terrain",   "z_scale": 2.0},
    "cape town":               {"lat": -33.9249, "lon":  18.4241, "radius_m":  3000, "type": "terrain",   "z_scale": 2.0},
    "vienna":                  {"lat":  48.2082, "lon":  16.3738, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "prague":                  {"lat":  50.0755, "lon":  14.4378, "radius_m":  1500, "type": "buildings", "z_scale": 1.2},
    "edinburgh":               {"lat":  55.9533, "lon":  -3.1883, "radius_m":  1500, "type": "buildings", "z_scale": 1.5},
    "lisbon":                  {"lat":  38.7223, "lon":  -9.1393, "radius_m":  2000, "type": "buildings", "z_scale": 1.5},
    "athens":                  {"lat":  37.9838, "lon":  23.7275, "radius_m":  2000, "type": "buildings", "z_scale": 1.5},
    "budapest":                {"lat":  47.4979, "lon":  19.0402, "radius_m":  2000, "type": "buildings", "z_scale": 1.2},
    "zurich":                  {"lat":  47.3769, "lon":   8.5417, "radius_m":  1500, "type": "buildings", "z_scale": 1.5},
    "copenhagen":              {"lat":  55.6761, "lon":  12.5683, "radius_m":  1500, "type": "buildings", "z_scale": 1.0},
    "stockholm":               {"lat":  59.3293, "lon":  18.0686, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "mexico city":             {"lat":  19.4326, "lon": -99.1332, "radius_m":  2500, "type": "buildings", "z_scale": 1.0},
    "buenos aires":            {"lat": -34.6037, "lon": -58.3816, "radius_m":  2500, "type": "buildings", "z_scale": 1.0},
    "washington dc":           {"lat":  38.9072, "lon": -77.0369, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "boston":                  {"lat":  42.3601, "lon": -71.0589, "radius_m":  1500, "type": "buildings", "z_scale": 1.0},
    "seattle":                 {"lat":  47.6062, "lon":-122.3321, "radius_m":  2000, "type": "buildings", "z_scale": 1.5},
    "miami city":              {"lat":  25.7617, "lon": -80.1918, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "las vegas city":          {"lat":  36.1699, "lon":-115.1398, "radius_m":  2000, "type": "buildings", "z_scale": 1.0},
    "vancouver":               {"lat":  49.2827, "lon":-123.1207, "radius_m":  2000, "type": "buildings", "z_scale": 1.5},

    # ── MotoGP / motorsport circuits ─────────────────────────────────────────
    "mugello":                 {"lat":  43.9975, "lon":  11.3714, "radius_m":  3000, "type": "f1",        "z_scale": 3.0},
    "phillip island":          {"lat": -38.5027, "lon": 145.2300, "radius_m":  2500, "type": "f1",        "z_scale": 2.5},
    "jerez":                   {"lat":  36.7083, "lon":  -6.0336, "radius_m":  2500, "type": "f1",        "z_scale": 2.5},
    "assen":                   {"lat":  52.9606, "lon":   6.5235, "radius_m":  2500, "type": "f1",        "z_scale": 2.0},
    "misano":                  {"lat":  43.9603, "lon":  12.6937, "radius_m":  2000, "type": "f1",        "z_scale": 2.5},
    "brands hatch":            {"lat":  51.3611, "lon":   0.2625, "radius_m":  2000, "type": "f1",        "z_scale": 3.0},
    "donington park":          {"lat":  52.8306, "lon":  -1.3756, "radius_m":  2000, "type": "f1",        "z_scale": 2.5},
    "oulton park":             {"lat":  53.1707, "lon":  -2.5960, "radius_m":  2000, "type": "f1",        "z_scale": 3.0},
    "snetterton":              {"lat":  52.4657, "lon":   0.9367, "radius_m":  2000, "type": "f1",        "z_scale": 2.0},
    "bathurst":                {"lat": -33.4418, "lon": 149.5528, "radius_m":  4000, "type": "f1",        "z_scale": 3.0},
    "nurburgring nordschleife":{"lat":  50.3356, "lon":   6.9475, "radius_m":  8000, "type": "f1",        "z_scale": 2.0},
    "pikes peak":              {"lat":  38.8405, "lon":-105.0442, "radius_m": 15000, "type": "terrain",   "z_scale": 1.0},
}


# ─── Coordinate utilities ─────────────────────────────────────────────────────

M_PER_DEG_LAT = 111320.0  # metres per degree latitude (constant)

def _m_per_deg_lon(lat_deg: float) -> float:
    return M_PER_DEG_LAT * math.cos(math.radians(lat_deg))

def latlon_to_xy_m(lat: float, lon: float, clat: float, clon: float) -> tuple[float, float]:
    """WGS84 → local (x=east, y=north) in metres using equirectangular projection."""
    x = (lon - clon) * _m_per_deg_lon(clat)
    y = (lat - clat) * M_PER_DEG_LAT
    return x, y

def bbox_deg(clat: float, clon: float, radius_m: float) -> tuple[float, float, float, float]:
    """Bounding box [S, W, N, E] in degrees for a given centre + radius."""
    dlat = radius_m / M_PER_DEG_LAT
    dlon = radius_m / _m_per_deg_lon(clat)
    return clat - dlat, clon - dlon, clat + dlat, clon + dlon


# ─── Elevation fetching ───────────────────────────────────────────────────────

_TOPO_URL   = "https://api.opentopodata.org/v1/srtm90m"
_BATCH_SIZE = 100  # OpenTopoData free tier limit


def fetch_elevation_grid(
    clat: float, clon: float, radius_m: float, grid_n: int = 20
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Sample elevation at grid_n × grid_n points centred on (clat, clon).
    Returns (elev_m [ny, nx], x_mm [nx], y_mm [ny]) where x/y are print-scale mm.

    Uses OpenTopoData SRTM 90m — free, no key, global coverage.
    Falls back to flat terrain (zero elevation) on API error.
    """
    dlat = radius_m / M_PER_DEG_LAT
    dlon = radius_m / _m_per_deg_lon(clat)

    lats = np.linspace(clat - dlat, clat + dlat, grid_n)
    lons = np.linspace(clon - dlon, clon + dlon, grid_n)
    lon_grid, lat_grid = np.meshgrid(lons, lats)  # [ny, nx]

    # Build flat list of (lat, lon) for API
    pts = [(float(lat_grid[r, c]), float(lon_grid[r, c]))
           for r in range(grid_n) for c in range(grid_n)]

    elevs_flat: list[float] = []
    try:
        for start in range(0, len(pts), _BATCH_SIZE):
            batch = pts[start:start + _BATCH_SIZE]
            loc_str = "|".join(f"{la},{lo}" for la, lo in batch)
            resp = requests.get(
                _TOPO_URL,
                params={"locations": loc_str},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            for r in data["results"]:
                elevs_flat.append(float(r["elevation"] or 0.0))
            if start + _BATCH_SIZE < len(pts):
                time.sleep(1.1)  # respect 1 req/sec rate limit
    except Exception as exc:
        print(f"  [elevation] API error ({exc}) — using flat terrain")
        elevs_flat = [0.0] * len(pts)

    elev_m = np.array(elevs_flat, dtype=float).reshape(grid_n, grid_n)
    return elev_m, lats, lons   # elev_m[row=y, col=x]


# ─── Overpass API ─────────────────────────────────────────────────────────────

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def _overpass(query: str, timeout: int = 40) -> dict:
    try:
        resp = requests.post(
            _OVERPASS_URL,
            data={"data": query},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"  [OSM] Overpass error: {exc}")
        return {"elements": []}


def fetch_osm_buildings(S: float, W: float, N: float, E: float) -> dict:
    q = f"""
[out:json][timeout:30];
(
  way["building"]({S},{W},{N},{E});
);
out body;
>;
out skel qt;
"""
    return _overpass(q)


def fetch_osm_track(S: float, W: float, N: float, E: float) -> dict:
    # Primary: dedicated race track tags
    # Secondary: street circuits (Monaco, Singapore, etc.) — query the
    #   "Grand Prix" / "Formula 1" named relations plus access=no roads
    #   that form the circuit, and any road segment tagged motorsport.
    q = f"""
[out:json][timeout:60];
(
  way["highway"="raceway"]({S},{W},{N},{E});
  way["landuse"="raceway"]({S},{W},{N},{E});
  way["leisure"="track"]["sport"~"motor"]({S},{W},{N},{E});
  way["sport"="motor_racing"]({S},{W},{N},{E});
  way["motorsport"="yes"]({S},{W},{N},{E});
  relation["sport"="motor_racing"]({S},{W},{N},{E});
  relation["name"~"[Ff]ormula|[Gg]rand [Pp]rix|[Ff]1|[Ff]-1|[Mm]oto[Gg][Pp]"]({S},{W},{N},{E});
  way["junction"="roundabout"]["name"~"[Hh]airpin|[Cc]asino|[Ll]oews|[Rr]ascasse"]({S},{W},{N},{E});
);
out body;
>;
out skel qt;
"""
    result = _overpass(q)
    # Flatten relation members (ways) into elements list
    extra_way_ids: set[int] = set()
    for el in result.get("elements", []):
        if el.get("type") == "relation":
            for m in el.get("members", []):
                if m.get("type") == "way":
                    extra_way_ids.add(m["id"])
    if extra_way_ids:
        id_list = ",".join(str(i) for i in sorted(extra_way_ids))
        extra = _overpass(f"[out:json][timeout:30];\nway(id:{id_list});\nout body;\n>;\nout skel qt;")
        result["elements"] = result.get("elements", []) + extra.get("elements", [])
    return result


# ─── OSM data parsing ─────────────────────────────────────────────────────────

def _node_map(elements: list[dict]) -> dict[int, tuple[float, float]]:
    return {e["id"]: (e["lat"], e["lon"]) for e in elements if e["type"] == "node"}


def _way_coords(way: dict, nodes: dict[int, tuple[float, float]]) -> list[tuple[float, float]]:
    """Return list of (lat, lon) for a way's node refs."""
    return [nodes[ref] for ref in way.get("nodes", []) if ref in nodes]


# ─── Mesh builders ────────────────────────────────────────────────────────────

def _elev_interpolator(
    elev_m: np.ndarray, lats: np.ndarray, lons: np.ndarray
) -> Callable[[float, float], float]:
    """Return a bilinear interpolation function elev(lat, lon) → metres."""
    from numpy import clip, searchsorted

    def _interp(lat: float, lon: float) -> float:
        r = float(np.interp(lat, lats, np.arange(len(lats))))
        c = float(np.interp(lon, lons, np.arange(len(lons))))
        r0, c0 = int(clip(r, 0, elev_m.shape[0] - 2)),  int(clip(c, 0, elev_m.shape[1] - 2))
        r1, c1 = r0 + 1, c0 + 1
        dr, dc = r - r0, c - c0
        return float(
            elev_m[r0, c0] * (1 - dr) * (1 - dc)
            + elev_m[r1, c0] * dr * (1 - dc)
            + elev_m[r0, c1] * (1 - dr) * dc
            + elev_m[r1, c1] * dr * dc
        )
    return _interp


def build_terrain_mesh(
    elev_m: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    clat: float, clon: float,
    print_scale: float,   # mm per metre
    z_scale: float,
    base_thickness_mm: float = 5.0,
) -> "trimesh.Trimesh":
    """Watertight terrain + solid base mesh in print-scale mm."""
    import trimesh

    ny, nx = elev_m.shape
    # Build local mm coordinates
    x_mm = np.array([(lon - clon) * _m_per_deg_lon(clat) * print_scale for lon in lons])
    y_mm = np.array([(lat - clat) * M_PER_DEG_LAT       * print_scale for lat in lats])

    # Normalise elevations: shift so min = 0, then apply z_scale
    e_min = elev_m.min()
    e_scaled = (elev_m - e_min) * z_scale * print_scale  # mm

    verts = []
    faces = []

    # ── Top surface (terrain) ──────────────────────────────────────────────
    for r in range(ny):
        for c in range(nx):
            verts.append([x_mm[c], y_mm[r], base_thickness_mm + e_scaled[r, c]])

    n_top = ny * nx

    # Top triangles
    for r in range(ny - 1):
        for c in range(nx - 1):
            a = r * nx + c
            b = r * nx + c + 1
            d = (r + 1) * nx + c
            e = (r + 1) * nx + c + 1
            faces += [[a, b, e], [a, e, d]]

    # ── Bottom surface (flat base z=0) ─────────────────────────────────────
    for r in range(ny):
        for c in range(nx):
            verts.append([x_mm[c], y_mm[r], 0.0])

    # Bottom triangles (reversed normals — face downward)
    for r in range(ny - 1):
        for c in range(nx - 1):
            a = n_top + r * nx + c
            b = n_top + r * nx + c + 1
            d = n_top + (r + 1) * nx + c
            e = n_top + (r + 1) * nx + c + 1
            faces += [[a, e, b], [a, d, e]]

    # ── Side walls ─────────────────────────────────────────────────────────
    def _wall_strip(top_idxs, bot_idxs):
        nonlocal faces
        n = len(top_idxs)
        for i in range(n - 1):
            t0, t1 = top_idxs[i], top_idxs[i + 1]
            b0, b1 = bot_idxs[i], bot_idxs[i + 1]
            faces += [[t0, b0, t1], [t1, b0, b1]]

    # South edge (r=0)
    _wall_strip(
        [r * nx + c for c in range(nx) for r in [0]],          # top
        [n_top + c for c in range(nx)],                          # bot
    )
    # North edge (r=ny-1)
    _wall_strip(
        [(ny - 1) * nx + c for c in range(nx - 1, -1, -1)],
        [n_top + (ny - 1) * nx + c for c in range(nx - 1, -1, -1)],
    )
    # West edge (c=0)
    _wall_strip(
        [r * nx for r in range(ny - 1, -1, -1)],
        [n_top + r * nx for r in range(ny - 1, -1, -1)],
    )
    # East edge (c=nx-1)
    _wall_strip(
        [r * nx + nx - 1 for r in range(ny)],
        [n_top + r * nx + nx - 1 for r in range(ny)],
    )

    mesh = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
    return mesh


def build_building_mesh(
    footprint_mm: list[tuple[float, float]],
    base_z_mm: float,
    height_mm: float,
) -> "trimesh.Trimesh | None":
    """Watertight extruded building footprint."""
    import trimesh
    from trimesh.creation import triangulate_polygon

    n = len(footprint_mm)
    if n < 3:
        return None

    verts: list[list[float]] = []
    faces: list[list[int]] = []

    # Close the polygon if needed
    if footprint_mm[0] != footprint_mm[-1]:
        footprint_mm = footprint_mm + [footprint_mm[0]]
    pts = footprint_mm[:-1]  # remove duplicate last
    n = len(pts)
    if n < 3:
        return None

    # Bottom ring
    for x, y in pts:
        verts.append([x, y, base_z_mm])
    # Top ring
    for x, y in pts:
        verts.append([x, y, base_z_mm + height_mm])

    # Side walls
    for i in range(n):
        j = (i + 1) % n
        faces += [[i, j, n + j], [i, n + j, n + i]]

    # Top / bottom caps: simple fan from first vertex
    for i in range(1, n - 1):
        faces.append([n, n + i, n + i + 1])      # top (CCW from above)
        faces.append([0, i + 1, i])              # bottom (CW from above)

    mesh = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
    mesh.fix_normals()
    return mesh


def build_track_ribbon(
    way_coords_mm: list[tuple[float, float]],
    half_w_mm: float,
    z_mm: float | list[float],
    thickness_mm: float = 1.5,
) -> "trimesh.Trimesh | None":
    """
    Generate a ribbon mesh from a list of (x, y) centreline points.
    z_mm may be a scalar (flat ribbon) or a per-point list (terrain-following).
    Each segment gets a quad; the ribbon is extruded down by thickness_mm.
    Works without shapely — pure numpy perpendicular offsets.
    """
    import trimesh

    pts = np.array(way_coords_mm, dtype=float)
    if len(pts) < 2:
        return None

    # Build per-point z array
    n_pts = len(pts)
    if isinstance(z_mm, (int, float)):
        z_arr = np.full(n_pts, float(z_mm))
    else:
        z_list = list(z_mm)
        if len(z_list) < n_pts:
            z_list += [z_list[-1]] * (n_pts - len(z_list))
        z_arr = np.array(z_list[:n_pts], dtype=float)

    verts: list[list[float]] = []
    faces: list[list[int]] = []
    top_left, top_right = [], []

    for i, p in enumerate(pts):
        if i == 0:
            d = pts[1] - pts[0]
        elif i == len(pts) - 1:
            d = pts[-1] - pts[-2]
        else:
            d = pts[i + 1] - pts[i - 1]
        norm = np.linalg.norm(d)
        if norm < 1e-9:
            d = np.array([1.0, 0.0])
        else:
            d = d / norm
        perp = np.array([-d[1], d[0]])  # 90° left
        left  = p + perp * half_w_mm
        right = p - perp * half_w_mm
        top_left.append(left)
        top_right.append(right)

    n = len(pts)
    base_idx = 0

    # Top surface (terrain-following z)
    for i in range(n):
        zi   = float(z_arr[i])
        zbot = zi - thickness_mm
        verts.append([top_left[i][0],  top_left[i][1],  zi])    # 4i
        verts.append([top_right[i][0], top_right[i][1], zi])    # 4i+1
        verts.append([top_left[i][0],  top_left[i][1],  zbot])  # 4i+2
        verts.append([top_right[i][0], top_right[i][1], zbot])  # 4i+3

    for i in range(n - 1):
        tl0, tr0, bl0, br0 = 4*i, 4*i+1, 4*i+2, 4*i+3
        tl1, tr1, bl1, br1 = 4*(i+1), 4*(i+1)+1, 4*(i+1)+2, 4*(i+1)+3
        # Top quad
        faces += [[tl0, tr0, tr1], [tl0, tr1, tl1]]
        # Bottom quad (reversed)
        faces += [[bl0, br1, br0], [bl0, bl1, br1]]
        # Left wall
        faces += [[tl0, tl1, bl1], [tl0, bl1, bl0]]
        # Right wall
        faces += [[tr0, br0, br1], [tr0, br1, tr1]]

    if len(verts) == 0:
        return None

    mesh = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces))
    mesh.fix_normals()
    return mesh


# ─── Nominatim geocoding fallback ────────────────────────────────────────────

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# OSM class/type → (loc_type, z_scale, radius_m)
_NOMINATIM_TYPE_MAP = [
    # natural peaks and mountains
    ({"natural": {"peak", "ridge", "volcano", "cliff", "fell"}},           "terrain", 1.2,  6000),
    # large natural areas
    ({"natural": {"wood", "grassland", "heath", "wetland", "water"}},      "terrain", 1.5, 12000),
    ({"natural": set()},                                                    "terrain", 1.5,  8000),
    # landuse
    ({"landuse": {"forest", "farmland", "meadow", "orchard"}},             "terrain", 1.5, 10000),
    # leisure tracks
    ({"leisure": {"track"}},                                                "f1",      2.5,  3000),
    ({"highway": {"raceway"}},                                              "f1",      2.5,  3000),
    # man-made / tourism landmarks
    ({"tourism": {"attraction", "artwork", "viewpoint", "museum"}},        "buildings", 1.0,  600),
    ({"historic": set()},                                                   "buildings", 1.2,  500),
    ({"amenity": set()},                                                    "buildings", 1.0,  400),
    # places: city/town → larger radius
    ({"place": {"city", "town"}},                                           "buildings", 1.0, 2500),
    ({"place": {"suburb", "neighbourhood", "village"}},                     "buildings", 1.0, 1000),
    ({"place": {"island", "islet"}},                                        "terrain",   1.5, 8000),
    ({"place": {"continent", "country", "state", "region", "county"}},     "terrain",   0.7,25000),
]


def _nominatim_lookup(
    query: str,
    radius_m: float | None,
    loc_type: str | None,
    z_scale: float | None,
) -> tuple[float | None, float | None, float, str, float]:
    """Query Nominatim for any place name. Returns (lat, lon, radius_m, loc_type, z_scale)."""
    try:
        resp = requests.get(
            _NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": "aria-map-generator/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
    except Exception as exc:
        print(f"  [geocode] Nominatim error: {exc}")
        return None, None, radius_m or 5000.0, loc_type or "terrain", z_scale or 1.0

    if not results:
        print(f"  [geocode] No results for '{query}'")
        return None, None, radius_m or 5000.0, loc_type or "terrain", z_scale or 1.0

    hit  = results[0]
    lat  = float(hit["lat"])
    lon  = float(hit["lon"])
    cls  = hit.get("class", "")
    typ  = hit.get("type", "")
    bb   = hit.get("boundingbox")  # [S, N, W, E] as strings

    print(f"  [geocode] Found: {hit.get('display_name','?')[:80]}  class={cls} type={typ}")

    # Estimate radius from bounding box if not supplied
    if radius_m is None and bb:
        try:
            s, n, w, e = float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])
            lat_span = (n - s) * M_PER_DEG_LAT
            lon_span = (e - w) * _m_per_deg_lon(lat)
            radius_m = max(500.0, min(25000.0, max(lat_span, lon_span) / 2.0))
        except Exception:
            radius_m = 5000.0

    # Determine loc_type and z_scale from OSM class/type
    if loc_type is None or z_scale is None:
        _ltype, _z, _r = "terrain", 1.5, radius_m or 5000.0
        for mapping, mt, mz, mr in _NOMINATIM_TYPE_MAP:
            for mcls, mtypes in mapping.items():
                if mcls == cls and (not mtypes or typ in mtypes):
                    _ltype, _z, _r = mt, mz, mr
                    break
            else:
                continue
            break
        if loc_type is None:
            loc_type = _ltype
        if z_scale is None:
            z_scale = _z
        if radius_m is None:
            radius_m = _r

    return lat, lon, radius_m or 5000.0, loc_type or "terrain", z_scale or 1.5


# ─── Main generation pipeline ─────────────────────────────────────────────────

def generate(
    label: str,
    *,
    lat: float | None        = None,
    lon: float | None        = None,
    radius_m: float | None   = None,
    loc_type: str | None     = None,
    base_mm: float           = 120.0,
    z_scale: float | None    = None,
    base_thickness_mm: float = 5.0,
    grid_n: int              = 20,
    out_dir: Path            = OUT_DIR,
) -> Path:
    """
    Generate a 3D map STL for a preset or custom lat/lon.

    Parameters
    ----------
    label         : preset name (case-insensitive) or custom label
    lat, lon      : override coordinates (required if not a preset)
    radius_m      : coverage radius in metres (overrides preset)
    loc_type      : "buildings" | "f1" | "terrain" (overrides preset)
    base_mm       : long side of the printed model in mm
    z_scale       : vertical exaggeration (default from preset or 1.0)
    base_thickness : solid base height in mm
    grid_n        : terrain elevation grid resolution (grid_n × grid_n)
    """
    import trimesh

    key = label.lower().strip()
    preset = PRESETS.get(key)
    if preset is None:
        # Fuzzy match: strip common suffixes then try every PRESETS key as substring
        _stripped = key
        for _suffix in (" f1", " circuit", " grand prix", " gp", " track", " race"):
            if _stripped.endswith(_suffix):
                _stripped = _stripped[: -len(_suffix)].strip()
        preset = PRESETS.get(_stripped)
        if preset is None:
            # Try: any preset key that starts with or contains the input word(s)
            for _pk, _pv in PRESETS.items():
                if _pk.startswith(_stripped) or _stripped in _pk:
                    preset = _pv
                    key = _pk
                    break
    if preset is None:
        preset = {}

    clat     = lat       or preset.get("lat")
    clon     = lon       or preset.get("lon")
    radius   = radius_m  or preset.get("radius_m", 1000.0)
    ltype    = loc_type  or preset.get("type", "buildings")
    z        = z_scale   or preset.get("z_scale", 1.0)

    # Enforce minimum z_scale so details are always visible
    _Z_MIN = {"buildings": 2.5, "terrain": 2.0, "f1": 2.0}
    z = max(z, _Z_MIN.get(ltype, 2.0))

    if clat is None or clon is None:
        # Geocode via Nominatim (free, no key)
        print(f"[map] '{label}' not in presets — trying Nominatim geocoding...")
        clat, clon, radius, ltype, z = _nominatim_lookup(label, radius, ltype, z)
        if clat is None:
            raise ValueError(
                f"Could not find '{label}'. Try --lat/--lon/--radius, or --list for presets."
            )

    slug = key.replace(" ", "_").replace("/", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.stl"

    # print-scale: how many mm per metre in the real world
    print_scale = base_mm / (2.0 * radius)  # mm/m  (diameter fits in base_mm)

    print(f"\n[map] Generating: {label}")
    print(f"[map] Centre: {clat:.4f}, {clon:.4f}  radius: {radius}m  scale: 1:{1/print_scale:.0f}")
    print(f"[map] Type: {ltype}  z_scale: {z}  base: {base_mm}mm")

    # Auto-increase grid resolution for terrain/f1 types
    if ltype in ("terrain", "f1") and grid_n < 40:
        grid_n = 40
    elif ltype == "buildings" and grid_n < 30:
        grid_n = 30

    S, W, N, E = bbox_deg(clat, clon, radius)

    # ── Elevation grid ────────────────────────────────────────────────────────
    print(f"[map] Fetching elevation grid ({grid_n}×{grid_n})...")
    elev_m, lats, lons = fetch_elevation_grid(clat, clon, radius, grid_n)
    elev_fn = _elev_interpolator(elev_m, lats, lons)

    # ── Terrain mesh ──────────────────────────────────────────────────────────
    print("[map] Building terrain mesh...")
    terrain = build_terrain_mesh(
        elev_m, lats, lons, clat, clon,
        print_scale, z, base_thickness_mm,
    )
    meshes = [terrain]

    # ── Feature meshes ────────────────────────────────────────────────────────
    if ltype == "buildings":
        print("[map] Fetching OSM buildings...")
        osm = fetch_osm_buildings(S, W, N, E)
        nodes = _node_map(osm["elements"])
        ways  = [e for e in osm["elements"] if e["type"] == "way"]
        print(f"[map] {len(ways)} buildings found")

        e_min = elev_m.min()
        built = 0
        for way in ways:
            tags   = way.get("tags", {})
            coords = _way_coords(way, nodes)
            if len(coords) < 3:
                continue

            # Height: use explicit tag, else estimate from levels, else 10m default
            if "height" in tags:
                try:
                    height_m = float(tags["height"].split()[0])
                except ValueError:
                    height_m = 10.0
            elif "building:levels" in tags:
                height_m = float(tags["building:levels"]) * 3.2
            else:
                height_m = 10.0

            # Convert to local mm
            fp_mm = [
                ((lo - clon) * _m_per_deg_lon(clat) * print_scale,
                 (la - clat) * M_PER_DEG_LAT       * print_scale)
                for la, lo in coords
            ]
            # Terrain base at centroid
            c_lat = sum(la for la, lo in coords) / len(coords)
            c_lon = sum(lo for la, lo in coords) / len(coords)
            terrain_here_m = elev_fn(c_lat, c_lon)
            base_z = base_thickness_mm + (terrain_here_m - e_min) * z * print_scale
            height_mm = height_m * print_scale * z

            if height_mm < 1.2:
                height_mm = 1.2  # minimum visible height (was 0.3 — too small)

            mesh = build_building_mesh(fp_mm, base_z, height_mm)
            if mesh is not None and len(mesh.faces) > 0:
                meshes.append(mesh)
                built += 1

        print(f"[map] {built} buildings meshed")

    elif ltype == "f1":
        print("[map] Fetching OSM track geometry...")
        osm   = fetch_osm_track(S, W, N, E)
        nodes = _node_map(osm["elements"])
        ways  = [e for e in osm["elements"] if e["type"] == "way"]
        print(f"[map] {len(ways)} track segments found")

        e_min = elev_m.min()
        # Visual width: real track ~12m; use 8× real for bold printable ribbon; min 4mm
        track_half_w = max(4.0, 12.0 * print_scale * 8.0)

        # Build a fast bilinear interpolator for terrain elevation at any lat/lon
        from scipy.interpolate import RegularGridInterpolator
        _elev_interp = RegularGridInterpolator(
            (lats, lons), elev_m, method="linear", bounds_error=False,
            fill_value=float(elev_m.mean()),
        )

        def _terrain_z(lat: float, lon: float) -> float:
            """Return print-scale z (mm) at a given lat/lon, sitting 0.5mm above terrain."""
            e = float(_elev_interp([[lat, lon]])[0])
            return base_thickness_mm + (e - e_min) * z * print_scale + 1.5

        built = 0
        for way in ways:
            coords = _way_coords(way, nodes)
            if len(coords) < 2:
                continue
            pts_mm = [
                ((lo - clon) * _m_per_deg_lon(clat) * print_scale,
                 (la - clat) * M_PER_DEG_LAT       * print_scale)
                for la, lo in coords
            ]
            # Per-point terrain-following z
            z_per_pt = [_terrain_z(la, lo) for la, lo in coords]
            ribbon = build_track_ribbon(pts_mm, track_half_w, z_per_pt, thickness_mm=2.0)
            if ribbon is not None and len(ribbon.faces) > 0:
                meshes.append(ribbon)
                built += 1

        print(f"[map] {built} track segments meshed  (half-width: {track_half_w:.2f}mm, terrain-following)")

    # "terrain" type: just the terrain mesh, no extra features

    # ── Combine & export ──────────────────────────────────────────────────────
    print(f"[map] Combining {len(meshes)} mesh(es)...")
    combined = trimesh.util.concatenate(meshes)
    combined.export(str(out_path))
    size_kb = out_path.stat().st_size / 1024
    print(f"[map] Exported: {out_path}  ({size_kb:.1f} KB)")
    print(f"[map] Model size: {combined.bounding_box.extents[0]:.1f} × "
          f"{combined.bounding_box.extents[1]:.1f} × "
          f"{combined.bounding_box.extents[2]:.1f} mm")
    return out_path


# ─── CLI ──────────────────────────────────────────────────────────────────────

def _list_presets() -> None:
    print("\nAvailable presets:\n")
    groups = {"buildings": [], "f1": [], "terrain": []}
    for name, p in PRESETS.items():
        groups.get(p["type"], groups["buildings"]).append(name)
    for g, names in groups.items():
        header = {"buildings": "Landmarks (buildings)", "f1": "F1 Circuits", "terrain": "Natural Terrain"}[g]
        print(f"  {header}:")
        for n in names:
            print(f"    python generate_map.py \"{n}\"")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 3D printable STL from public map data (OpenStreetMap + SRTM elevation).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python generate_map.py "Monaco F1"
  python generate_map.py "Eiffel Tower" --base-mm 150
  python generate_map.py "Grand Canyon" --z-scale 0.8
  python generate_map.py --lat 51.5007 --lon -0.1246 --radius 400 "Big Ben area"
  python generate_map.py --list""",
    )
    parser.add_argument("label",        nargs="?", help="Preset name or custom label")
    parser.add_argument("--list",       action="store_true", help="List all presets and exit")
    parser.add_argument("--lat",        type=float, help="Centre latitude (decimal degrees)")
    parser.add_argument("--lon",        type=float, help="Centre longitude (decimal degrees)")
    parser.add_argument("--radius",     type=float, help="Coverage radius in metres")
    parser.add_argument("--type",       choices=["buildings", "f1", "terrain"], dest="loc_type",
                        help="Feature type (default: from preset or 'buildings')")
    parser.add_argument("--base-mm",    type=float, default=120.0,
                        help="Longest side of printed model in mm (default: 120)")
    parser.add_argument("--z-scale",    type=float, help="Vertical exaggeration (default: from preset)")
    parser.add_argument("--grid",       type=int,   default=20,
                        help="Elevation grid resolution N×N (default: 20)")
    parser.add_argument("--base-thick", type=float, default=5.0,
                        help="Solid base thickness in mm (default: 5)")
    args = parser.parse_args()

    if args.list:
        _list_presets()
        return

    if not args.label and args.lat is None:
        parser.print_help()
        sys.exit(1)

    label = args.label or f"custom_{args.lat:.4f}_{args.lon:.4f}"

    out = generate(
        label,
        lat=args.lat,
        lon=args.lon,
        radius_m=args.radius,
        loc_type=args.loc_type,
        base_mm=args.base_mm,
        z_scale=args.z_scale,
        base_thickness_mm=args.base_thick,
        grid_n=args.grid,
    )
    print(f"\nDone. Open in your slicer:\n  {out}\n")


if __name__ == "__main__":
    main()

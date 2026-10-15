#!/usr/bin/env python3
"""Generate refined candidate logo concept SVGs and lockups for Antigravity MCP Orchestrator."""

import math
import subprocess
from pathlib import Path

OUT_DIR = Path("/home/haider/Desktop/MyGithub/design001/branding")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# Concept A: The Levitation Spark
# 4-point Gemini star levitating effortlessly above an antigravity magnetic cradle.
# -------------------------------------------------------------
concept_a_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <title>The Levitation Spark</title>
  <!-- Gemini Spark (Floating Core) -->
  <path d="M 128 36 C 128 66 142 80 172 80 C 142 80 128 94 128 124 C 128 94 114 80 84 80 C 114 80 128 66 128 36 Z" fill="#111827"/>
  <!-- Antigravity Magnetic Cradle -->
  <path d="M 44 140 C 60 196 90 220 128 220 C 166 220 196 196 212 140 C 196 150 168 188 128 188 C 88 188 60 150 44 140 Z" fill="#111827"/>
</svg>"""

# -------------------------------------------------------------
# Concept B: The Orbital Delta (with snapped clean 60°/120° angles)
# -------------------------------------------------------------
# For 60°: dy = dx * tan(60°) = 24 * 1.73205 = 41.57.
# Top: (128, 126.86), Sides: (152, 168.43) and (104, 168.43), Bottom: (128, 210)
concept_b_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <title>The Orbital Delta</title>
  <!-- Outer Antigravity Delta Canopy -->
  <path d="M 128 36 L 216 216 L 176 216 L 128 112 L 80 216 L 40 216 Z" fill="#111827"/>
  <!-- Levitating Floating Diamond Core -->
  <path d="M 128 132 L 150 170.1 L 128 208.2 L 106 170.1 Z" fill="#111827"/>
</svg>"""

# -------------------------------------------------------------
# Concept C: The Gravity Inverter (Balanced optical margins)
# -------------------------------------------------------------
concept_c_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <title>The Gravity Inverter</title>
  <!-- Left Pylon -->
  <path d="M 72 56 C 52 94 48 154 64 208 C 84 200 98 164 98 124 C 98 88 88 68 72 56 Z" fill="#111827"/>
  <!-- Right Pylon -->
  <path d="M 184 56 C 204 94 208 154 192 208 C 172 200 158 164 158 124 C 158 88 168 68 184 56 Z" fill="#111827"/>
  <!-- Central Levitating Node -->
  <circle cx="128" cy="124" r="24" fill="#111827"/>
  <!-- Top Spark Tip -->
  <path d="M 128 44 L 138 68 L 128 92 L 118 68 Z" fill="#111827"/>
</svg>"""

(OUT_DIR / "concept-a.svg").write_text(concept_a_svg)
(OUT_DIR / "concept-b.svg").write_text(concept_b_svg)
(OUT_DIR / "concept-c.svg").write_text(concept_c_svg)

# Helper function to generate clean lockups (viewBox 0 0 768 256)
def make_lockup(symbol_path: str, title: str, subtitle: str, out_file: Path):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 768 256" width="768" height="256">
  <g transform="translate(32, 0)">
    {symbol_path}
  </g>
  <g transform="translate(320, 115)">
    <text font-family="system-ui, -apple-system, 'Inter', 'Segoe UI', Roboto, sans-serif" font-weight="800" font-size="52" fill="#111827" letter-spacing="-1">{title}</text>
    <text y="48" font-family="system-ui, -apple-system, 'Inter', 'Segoe UI', Roboto, sans-serif" font-weight="500" font-size="24" fill="#6B7280" letter-spacing="4">{subtitle}</text>
  </g>
</svg>"""
    out_file.write_text(svg)

# Extract symbols
def extract_inner(svg_content: str):
    start = svg_content.find("<!--")
    end = svg_content.rfind("</svg>")
    return svg_content[start:end]

make_lockup(extract_inner(concept_a_svg), "ANTIGRAVITY", "MCP ORCHESTRATOR", OUT_DIR / "concept-a-lockup.svg")
make_lockup(extract_inner(concept_b_svg), "ANTIGRAVITY", "MCP ORCHESTRATOR", OUT_DIR / "concept-b-lockup.svg")
make_lockup(extract_inner(concept_c_svg), "ANTIGRAVITY", "MCP ORCHESTRATOR", OUT_DIR / "concept-c-lockup.svg")

print("Generated refined concepts and lockups in", OUT_DIR)

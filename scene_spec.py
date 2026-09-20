from __future__ import annotations
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import json
import re


def hex_to_rgb(hex_str: str) -> List[float]:
    """Convert hex color string (#RRGGBB) to linear RGB [r, g, b] in range [0, 1]."""
    if not isinstance(hex_str, str):
        return [0.8, 0.8, 0.8]
    hex_clean = hex_str.lstrip('#')
    if len(hex_clean) == 3:
        hex_clean = ''.join([c * 2 for c in hex_clean])
    if len(hex_clean) != 6:
        return [0.8, 0.8, 0.8]
    try:
        r = int(hex_clean[0:2], 16) / 255.0
        g = int(hex_clean[2:4], 16) / 255.0
        b = int(hex_clean[4:6], 16) / 255.0
        # Convert sRGB to approximate linear for Blender Principled BSDF
        return [pow(r, 2.2), pow(g, 2.2), pow(b, 2.2)]
    except ValueError:
        return [0.8, 0.8, 0.8]


def rgb_to_hex(rgb: List[float]) -> str:
    """Convert RGB list [r, g, b] in [0, 1] to hex #RRGGBB."""
    if not rgb or len(rgb) < 3:
        return "#CCCCCC"
    r = max(0, min(255, int(pow(rgb[0], 1 / 2.2) * 255)))
    g = max(0, min(255, int(pow(rgb[1], 1 / 2.2) * 255)))
    b = max(0, min(255, int(pow(rgb[2], 1 / 2.2) * 255)))
    return f"#{r:02X}{g:02X}{b:02X}"


class MaterialSpec(BaseModel):
    color: str = "#A0A0A0"
    roughness: float = 0.5
    metallic: float = 0.0
    transmission: float = 0.0
    emission_color: str = "#000000"
    emission_strength: float = 0.0

    @field_validator("roughness", mode="before")
    def clamp_roughness(cls, v):
        try:
            return max(0.0, min(1.0, float(v)))
        except (ValueError, TypeError):
            return 0.5

    @field_validator("metallic", mode="before")
    def clamp_metallic(cls, v):
        try:
            return max(0.0, min(1.0, float(v)))
        except (ValueError, TypeError):
            return 0.0

    @field_validator("color", mode="before")
    def validate_color(cls, v):
        if isinstance(v, list) and len(v) >= 3:
            return rgb_to_hex(v[:3])
        if isinstance(v, str) and re.match(r"^#?[0-9a-fA-F]{6}$", v):
            return v if v.startswith('#') else f"#{v}"
        return "#A0A0A0"

    def get_rgb_linear(self) -> List[float]:
        return hex_to_rgb(self.color)


class ObjectSpec(BaseModel):
    id: str = "object_00"
    class_name: str = Field(default="cube", alias="class")
    primitive: str = "cube"
    bbox_2d: List[float] = Field(default_factory=lambda: [0.0, 0.0, 1.0, 1.0])  # [x, y, w, h] normalized 0..1
    position: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])  # [x, y, z] in Blender units (meters)
    rotation: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])  # [rx, ry, rz] in degrees
    scale: List[float] = Field(default_factory=lambda: [1.0, 1.0, 1.0])  # [sx, sy, sz]
    material: MaterialSpec = Field(default_factory=MaterialSpec)
    confidence: float = 0.8
    evidence: str = "VISUAL"  # VISUAL or INFERRED
    relationship: Optional[str] = None  # e.g., "on_top_of:object_01", "on_floor"

    model_config = {
        "populate_by_name": True
    }

    @field_validator("confidence", mode="before")
    def clamp_confidence(cls, v):
        try:
            return max(0.0, min(1.0, float(v)))
        except (ValueError, TypeError):
            return 0.7

    @field_validator("evidence", mode="before")
    def validate_evidence(cls, v):
        if isinstance(v, str) and v.upper() in ["VISUAL", "INFERRED"]:
            return v.upper()
        return "INFERRED"

    @field_validator("scale", mode="before")
    def validate_scale(cls, v):
        if isinstance(v, (int, float)):
            return [float(v), float(v), float(v)]
        if isinstance(v, list) and len(v) == 3:
            return [max(0.01, float(x)) for x in v]
        return [1.0, 1.0, 1.0]

    @field_validator("position", mode="before")
    def validate_pos(cls, v):
        if isinstance(v, list) and len(v) == 3:
            return [float(x) for x in v]
        return [0.0, 0.0, 0.0]

    @field_validator("rotation", mode="before")
    def validate_rot(cls, v):
        if isinstance(v, list) and len(v) == 3:
            return [float(x) for x in v]
        return [0.0, 0.0, 0.0]


class CameraSpec(BaseModel):
    type: str = "perspective"
    position: List[float] = Field(default_factory=lambda: [0.0, -4.5, 2.2])
    target: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.5])
    fov: float = 45.0  # field of view in degrees or lens mm equivalent
    focal_length: Optional[float] = 50.0  # mm
    elevation_deg: float = 20.0

    @field_validator("fov", mode="before")
    def validate_fov(cls, v):
        try:
            val = float(v)
            return max(10.0, min(120.0, val))
        except (ValueError, TypeError):
            return 45.0


class LightItemSpec(BaseModel):
    position: List[float] = Field(default_factory=lambda: [3.0, -3.0, 4.0])
    intensity: float = 500.0  # Watts
    color: str = "#FFFFFF"
    type: str = "POINT"  # POINT, SUN, SPOT, AREA

    def get_rgb_linear(self) -> List[float]:
        return hex_to_rgb(self.color)


class LightingSpec(BaseModel):
    type: str = "three_point"  # three_point, studio, sun, outdoor, ambient
    key_light: LightItemSpec = Field(
        default_factory=lambda: LightItemSpec(position=[3.0, -3.0, 4.0], intensity=600.0, color="#FFF8E7")
    )
    fill_light: Optional[LightItemSpec] = Field(
        default_factory=lambda: LightItemSpec(position=[-3.5, -2.0, 2.5], intensity=250.0, color="#EBF4FF")
    )
    rim_light: Optional[LightItemSpec] = Field(
        default_factory=lambda: LightItemSpec(position=[0.0, 3.5, 3.0], intensity=300.0, color="#FFFFFF")
    )
    ambient_strength: float = 0.2
    ambient_color: str = "#FFFFFF"


class BackgroundSpec(BaseModel):
    color: str = "#E8E8E8"
    has_floor: bool = True
    floor_color: str = "#C8C8C8"
    floor_roughness: float = 0.3
    has_walls: bool = False
    wall_color: str = "#F0F0F0"


class SceneMetadata(BaseModel):
    type: str = "room"  # room, product, object, outdoor, unknown
    background: BackgroundSpec = Field(default_factory=BackgroundSpec)
    camera: CameraSpec = Field(default_factory=CameraSpec)
    lighting: LightingSpec = Field(default_factory=LightingSpec)


class SceneSpec(BaseModel):
    scene: SceneMetadata = Field(default_factory=SceneMetadata)
    objects: List[ObjectSpec] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SceneSpec:
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> SceneSpec:
        clean_str = json_str.strip()
        # Handle markdown ```json blocks if present
        if clean_str.startswith("```"):
            clean_str = re.sub(r"^```(?:json)?\s*", "", clean_str, flags=re.MULTILINE)
            clean_str = re.sub(r"```\s*$", "", clean_str, flags=re.MULTILINE)
        data = json.loads(clean_str.strip())
        return cls.from_dict(data)

    def save(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, filepath: str) -> SceneSpec:
        with open(filepath, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

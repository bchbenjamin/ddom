from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Evidence = Literal["SOURCE", "RUNTIME", "VISUAL", "INFERRED"]


class Fact(BaseModel):
    value: Any
    evidence: Evidence
    confidence: float = Field(ge=0, le=1)
    origin: Optional[str] = None


class Viewport(BaseModel):
    name: str
    width: int
    height: int


class Source(BaseModel):
    kind: Literal["website", "screenshots", "figma"] = "website"
    url: Optional[str] = None
    capturedAt: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    viewports: List[Viewport] = Field(default_factory=list)


class ColorValue(BaseModel):
    hex: str
    role: Optional[str] = None
    usageCount: int = 1


class TypographyValue(BaseModel):
    family: str
    fallbackStack: List[str] = Field(default_factory=list)
    sizePx: float
    weight: int
    lineHeight: Any
    letterSpacing: Optional[str] = None
    role: Optional[str] = None


class BorderValue(BaseModel):
    widthPx: float
    style: str
    color: str


class Tokens(BaseModel):
    colors: List[Fact] = Field(default_factory=list)
    typography: List[Fact] = Field(default_factory=list)
    spacing: List[Fact] = Field(default_factory=list)
    radii: List[Fact] = Field(default_factory=list)
    shadows: List[Fact] = Field(default_factory=list)
    borders: List[Fact] = Field(default_factory=list)


class Component(BaseModel):
    id: str
    kind: str
    occurrences: int = 1
    exemplarSelector: str
    styles: Dict[str, Fact] = Field(default_factory=dict)
    states: Optional[List[str]] = None


class Structure(BaseModel):
    regions: List[Fact] = Field(default_factory=list)
    components: List[Component] = Field(default_factory=list)


class MotionRecord(BaseModel):
    id: str
    trigger: Literal["load", "hover", "focus", "click", "scroll", "viewport-entry", "route"]
    target: str
    from_: Dict[str, str] = Field(default_factory=dict, alias="from")
    to: Dict[str, str] = Field(default_factory=dict)
    durationMs: Fact
    delayMs: Optional[Fact] = None
    easing: Fact
    staggerMs: Optional[float] = None
    loop: Optional[bool] = None
    mechanism: Fact


class InteractionRecord(BaseModel):
    id: str
    target: str
    state: Literal["hover", "focus", "active", "disabled", "selected", "expanded", "open"]
    styleDelta: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    evidence: Evidence
    confidence: float = Field(ge=0, le=1)


class ResponsiveChange(BaseModel):
    at: int
    kind: Literal["grid-to-stack", "nav-collapse", "font-scale", "padding", "visibility", "resize"]
    selector: str
    detail: str


class ResponsiveRecord(BaseModel):
    breakpoints: List[Fact] = Field(default_factory=list)
    changes: List[ResponsiveChange] = Field(default_factory=list)


class IconStroke(BaseModel):
    widthPx: float
    linecap: Optional[str] = None
    linejoin: Optional[str] = None


class IconRecord(BaseModel):
    id: str
    format: Literal["inline-svg", "external-svg", "raster", "icon-font"]
    viewBox: Optional[str] = None
    sizePx: Fact
    stroke: Optional[IconStroke] = None
    fill: Optional[str] = None
    family: Fact
    occurrences: int = 1


class QualityReport(BaseModel):
    extractionCompleteness: float = 0
    sourceEvidenceShare: float = 0
    responsiveCoverage: float = 0
    motionConfidence: float = 0
    componentCoverage: float = 0
    overall: float = 0
    weights: Dict[str, float] = Field(default_factory=dict)


class DDOM(BaseModel):
    schemaVersion: Literal["0.1"] = "0.1"
    id: str
    source: Source
    tokens: Tokens = Field(default_factory=Tokens)
    structure: Structure = Field(default_factory=Structure)
    motion: List[MotionRecord] = Field(default_factory=list)
    interactions: List[InteractionRecord] = Field(default_factory=list)
    responsive: ResponsiveRecord = Field(default_factory=ResponsiveRecord)
    icons: List[IconRecord] = Field(default_factory=list)
    quality: QualityReport = Field(default_factory=QualityReport)
    warnings: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DDOM":
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> "DDOM":
        return cls.from_dict(json.loads(json_str))

    def save(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.to_json())


class MismatchItem(BaseModel):
    category: str
    target: str
    expected: str
    actual: str
    suggestedFix: str


class FidelityReport(BaseModel):
    fidelity: float
    byCategory: Dict[str, float] = Field(default_factory=dict)
    mismatches: List[MismatchItem] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

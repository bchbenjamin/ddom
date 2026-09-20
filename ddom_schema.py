from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import datetime


class EvidenceFact(BaseModel):
    value: Any
    evidence: str = "SOURCE"  # SOURCE | RUNTIME | VISUAL | INFERRED
    confidence: float = 0.95
    origin: Optional[str] = None


class ColorToken(BaseModel):
    value: str
    name: Optional[str] = None
    usage: Optional[str] = None
    evidence: str = "SOURCE"
    confidence: float = 0.95
    origin: Optional[str] = None


class TypographyToken(BaseModel):
    element: Optional[str] = "body"
    fontFamily: Optional[str] = None
    fontSize: Optional[str] = None
    fontWeight: Optional[str] = None
    lineHeight: Optional[str] = None
    evidence: str = "SOURCE"
    confidence: float = 0.95
    origin: Optional[str] = None


class SpacingToken(BaseModel):
    value: str
    usage: Optional[str] = None
    evidence: str = "SOURCE"
    confidence: float = 0.95
    origin: Optional[str] = None


class RadiusToken(BaseModel):
    value: str
    evidence: str = "SOURCE"
    confidence: float = 0.95
    origin: Optional[str] = None


class ShadowToken(BaseModel):
    value: str
    evidence: str = "SOURCE"
    confidence: float = 0.90
    origin: Optional[str] = None


class TokensGroup(BaseModel):
    colors: List[ColorToken] = Field(default_factory=list)
    typography: List[TypographyToken] = Field(default_factory=list)
    spacing: List[SpacingToken] = Field(default_factory=list)
    radii: List[RadiusToken] = Field(default_factory=list)
    shadows: List[ShadowToken] = Field(default_factory=list)


class RegionItem(BaseModel):
    name: str
    type: str = "region"
    count: int = 1
    evidence: str = "SOURCE"
    confidence: float = 0.95
    origin: Optional[str] = None


class ComponentItem(BaseModel):
    name: str
    type: str = "component"
    count: int = 1
    selector: Optional[str] = None
    evidence: str = "SOURCE"
    confidence: float = 0.95
    origin: Optional[str] = None


class StructureGroup(BaseModel):
    regions: List[RegionItem] = Field(default_factory=list)
    components: List[ComponentItem] = Field(default_factory=list)


class MotionItem(BaseModel):
    name: str
    property: Optional[str] = None
    duration: Optional[str] = None
    timing: Optional[str] = None
    evidence: str = "SOURCE"
    confidence: float = 0.85


class InteractionItem(BaseModel):
    selector: str
    state: str = "hover"
    changes: Optional[str] = None
    evidence: str = "SOURCE"
    confidence: float = 0.85


class ResponsiveItem(BaseModel):
    breakpoint: str
    changes: Optional[str] = None
    evidence: str = "SOURCE"
    confidence: float = 0.90


class IconItem(BaseModel):
    name: Optional[str] = "svg"
    count: int = 0
    type: str = "svg"
    evidence: str = "SOURCE"
    confidence: float = 0.95


class ViewportSpec(BaseModel):
    width: int = 1280
    height: int = 800


class SourceSpec(BaseModel):
    kind: str = "website"  # website | visual
    url: str = ""
    capturedAt: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    viewport: ViewportSpec = Field(default_factory=ViewportSpec)


class DDOM(BaseModel):
    schemaVersion: str = "0.1"
    source: SourceSpec = Field(default_factory=SourceSpec)
    tokens: TokensGroup = Field(default_factory=TokensGroup)
    structure: StructureGroup = Field(default_factory=StructureGroup)
    motion: List[MotionItem] = Field(default_factory=list)
    interactions: List[InteractionItem] = Field(default_factory=list)
    responsive: List[ResponsiveItem] = Field(default_factory=list)
    icons: List[IconItem] = Field(default_factory=list)
    quality: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DDOM:
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> DDOM:
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
    fidelity: float  # 0 .. 100
    byCategory: Dict[str, float] = Field(default_factory=dict)
    mismatches: List[MismatchItem] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

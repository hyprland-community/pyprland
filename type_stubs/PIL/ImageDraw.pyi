from collections.abc import Callable as Callable
from collections.abc import Sequence
from types import ModuleType
from typing import Any, AnyStr

from _typeshed import Incomplete

from . import Image as Image
from . import ImageColor as ImageColor
from . import ImageDraw2 as ImageDraw2
from . import ImageFont as ImageFont
from . import ImageText as ImageText
from ._typing import Coords as Coords
from ._typing import _Ink as _Ink

TYPE_CHECKING: bool
Outline: Callable[[], Image.core._Outline]

class ImageDraw:
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont | None
    palette: Incomplete
    _image: Incomplete
    im: Incomplete
    draw: Incomplete
    mode: Incomplete
    ink: Incomplete
    fontmode: str
    fill: bool
    def __init__(self, im: Image.Image, mode: str | None = None) -> None: ...
    def getfont(self) -> ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont: ...
    def _getfont(self, font_size: float | None) -> ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont: ...
    def _getink(self, ink: _Ink | None, fill: _Ink | None = None) -> tuple[int | None, int | None]: ...
    def arc(self, xy: Coords, start: float, end: float, fill: _Ink | None = None, width: int = 1) -> None: ...
    def bitmap(self, xy: Sequence[int], bitmap: Image.Image, fill: _Ink | None = None) -> None: ...
    def chord(
        self, xy: Coords, start: float, end: float, fill: _Ink | None = None, outline: _Ink | None = None, width: int = 1
    ) -> None: ...
    def ellipse(self, xy: Coords, fill: _Ink | None = None, outline: _Ink | None = None, width: int = 1) -> None: ...
    def circle(self, xy: Sequence[float], radius: float, fill: _Ink | None = None, outline: _Ink | None = None, width: int = 1) -> None: ...
    def line(self, xy: Coords, fill: _Ink | None = None, width: int = 0, joint: str | None = None) -> None: ...
    def shape(self, shape: Image.core._Outline, fill: _Ink | None = None, outline: _Ink | None = None) -> None: ...
    def pieslice(
        self, xy: Coords, start: float, end: float, fill: _Ink | None = None, outline: _Ink | None = None, width: int = 1
    ) -> None: ...
    def point(self, xy: Coords, fill: _Ink | None = None) -> None: ...
    def polygon(self, xy: Coords, fill: _Ink | None = None, outline: _Ink | None = None, width: int = 1) -> None: ...
    def regular_polygon(
        self,
        bounding_circle: Sequence[Sequence[float] | float],
        n_sides: int,
        rotation: float = 0,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
    ) -> None: ...
    def rectangle(self, xy: Coords, fill: _Ink | None = None, outline: _Ink | None = None, width: int = 1) -> None: ...
    def rounded_rectangle(
        self,
        xy: Coords,
        radius: float = 0,
        fill: _Ink | None = None,
        outline: _Ink | None = None,
        width: int = 1,
        *,
        corners: tuple[bool, bool, bool, bool] | None = None,
    ) -> None: ...
    def text(
        self,
        xy: tuple[float, float],
        text: AnyStr | ImageText.Text,
        fill: _Ink | None = None,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont | None = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        stroke_fill: _Ink | None = None,
        embedded_color: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
    def multiline_text(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        fill: _Ink | None = None,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont | None = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        stroke_fill: _Ink | None = None,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> None: ...
    def textlength(
        self,
        text: AnyStr,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont | None = None,
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> float: ...
    def textbbox(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont | None = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> tuple[float, float, float, float]: ...
    def multiline_textbbox(
        self,
        xy: tuple[float, float],
        text: AnyStr,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont | ImageFont.TransposedFont | None = None,
        anchor: str | None = None,
        spacing: float = 4,
        align: str = "left",
        direction: str | None = None,
        features: list[str] | None = None,
        language: str | None = None,
        stroke_width: float = 0,
        embedded_color: bool = False,
        *,
        font_size: float | None = None,
    ) -> tuple[float, float, float, float]: ...

def Draw(im: Image.Image, mode: str | None = None) -> ImageDraw: ...
def getdraw(im: Image.Image | None = None) -> tuple[ImageDraw2.Draw | None, ModuleType]: ...
def floodfill(
    image: Image.Image,
    xy: tuple[int, int],
    value: float | tuple[int, ...],
    border: float | tuple[int, ...] | None = None,
    thresh: float = 0,
) -> None: ...
def _compute_regular_polygon_vertices(
    bounding_circle: Sequence[Sequence[float] | float], n_sides: int, rotation: float
) -> list[tuple[float, float]]: ...
def _color_diff(color1: float | tuple[int, ...], color2: float | tuple[int, ...]) -> float: ...

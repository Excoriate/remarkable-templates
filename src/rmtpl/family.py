"""The seam between the toolkit and the kind of template being made.

A *family* is one coherent set of templates — basketball courts today, and
whatever else later. The toolkit owns everything that is true of any reMarkable
template: canvas sizes, opaque rasters, PDF pagination, the manifest xochitl
reads, the install path. A family owns only what is true of its subject: what
to draw, what the dimensions mean, and how to tell whether a drawing came out
right.

Adding a family means adding one package under ``src/rmtpl/families/`` that exposes a
module-level ``FAMILY``. Nothing else in the repository needs to change: the
build, the manifest, the documentation and the checks all iterate over whatever
the registry finds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .devices import Device
from .style import DEFAULT_STYLE, Style

if TYPE_CHECKING:  # pragma: no cover
    from .checks import Report


@dataclass(frozen=True)
class BuiltTemplate:
    """One finished template, as the toolkit needs to see it.

    A family returns these; the toolkit turns them into manifest entries, so no
    family has to know what a manifest entry looks like.
    """

    stem: str                       # file stem, no extension
    display: str                    # name shown in the template picker
    landscape: bool
    canvas: tuple[int, int]
    png: Path
    svg: Path | None = None
    pdf: Path | None = None
    detail: str = ""                # one line for the build log


@dataclass(frozen=True)
class BuildOptions:
    style: Style = DEFAULT_STYLE
    want_pdf: bool = True
    #: Subset of the family's own variants to build; empty means all of them.
    variants: tuple[str, ...] = ()
    #: Family-specific settings, passed through from ``--set key=value``. The
    #: toolkit never interprets these; a family reads the keys it understands
    #: and should say so in its docstring.
    extra: dict[str, str] = field(default_factory=dict)


class TemplateFamily(ABC):
    """One kind of template, and everything specific to it."""

    #: Directory name under ``templates/`` and namespace on the device.
    key: str
    #: Human name, used in listings.
    label: str
    #: One line explaining what the family is for.
    summary: str

    @property
    def category(self) -> str:
        """The template-picker tab these land under."""
        return self.label

    @property
    def variants(self) -> tuple[str, ...]:
        """Names a caller may pass in ``BuildOptions.variants``."""
        return ()

    def expected_stems(self, options: BuildOptions) -> tuple[str, ...]:
        """Every file stem a complete build of ``options`` should produce.

        Declaring this is what lets verification notice a template that is
        *absent*. A checker that only inspects the files it finds will happily
        pass a set with half of it missing, because there is nothing to compare
        the manifest against.

        Return an empty tuple if a family genuinely cannot know in advance.
        """
        return ()

    @abstractmethod
    def build(self, out_dir: Path, device: Device,
              options: BuildOptions) -> list[BuiltTemplate]:
        """Render every template into ``out_dir``/{png,svg,pdf}."""

    def write_docs(self, docs_dir: Path) -> list[Path]:
        """Generate reference documentation. Return the paths written."""
        return []

    def verify(self, report: Report, out_dir: Path, device: Device) -> None:
        """Family-specific checks over what ``build`` produced.

        The toolkit already checks the things that are true of any template.
        This is where a family proves its own drawings are correct — ideally by
        measuring the finished artwork rather than by re-reading the numbers it
        drew from.
        """
        return None

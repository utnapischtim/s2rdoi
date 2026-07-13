# SPDX-FileCopyrightText: 2026 Graz University of Technology.
# SPDX-License-Identifier: MIT

"""Parse xml."""

import html.entities
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import ElementTree, TreeBuilder, tostring
from xml.parsers.expat import ParserCreate


@dataclass
class DoctypeInfo:
    """Holds the parts of a DOCTYPE declaration needed to reconstruct it."""

    name: str
    public_id: str | None
    system_id: str | None

    def as_declaration(self) -> str:
        """Render this info back into a `<!DOCTYPE ...>` declaration string."""
        if self.public_id and self.system_id:
            return (
                f'<!DOCTYPE {self.name} PUBLIC "{self.public_id}" "{self.system_id}">'
            )
        if self.system_id:
            return f'<!DOCTYPE {self.name} SYSTEM "{self.system_id}">'
        return f"<!DOCTYPE {self.name}>"


def make_entity_resolver() -> dict[str, str]:
    """Build a lookup table mapping HTML entity names to their Unicode equivalents."""
    return {name.rstrip(";"): char for name, char in html.entities.html5.items()}


def parse_xml(path: Path) -> tuple[ElementTree, DoctypeInfo | None]:
    """Parse an XML file and return an ElementTree.

    Parse an XML file and return an ElementTree, transparently resolving HTML
    entities (e.g. &reg; -> ®) that would otherwise cause a parse error.

    Ironically the simple solution to handle the &reg; in the xml files
    """
    entity_map = make_entity_resolver()

    target = TreeBuilder()
    parser = ParserCreate()

    parser.StartElementHandler = target.start
    parser.EndElementHandler = target.end
    parser.CharacterDataHandler = target.data
    doctype: DoctypeInfo | None = None

    def start_doctype_handler(
        doctype_name: str,
        system_id: str | None,
        public_id: str | None,
        has_internal_subset: bool,  # noqa: ARG001, FBT001
    ) -> None:
        nonlocal doctype
        doctype = DoctypeInfo(
            name=doctype_name,
            public_id=public_id,
            system_id=system_id,
        )

    parser.StartDoctypeDeclHandler = start_doctype_handler

    def default_handler(data: str) -> None:
        if data.startswith("&") and data.endswith(";"):
            entity_name = data[1:-1]
            resolved = entity_map.get(entity_name, data)
            target.data(resolved)

    parser.DefaultHandler = default_handler

    with path.open("rb") as f:
        parser.ParseFile(f)

    return ElementTree(target.close()), doctype


def write_xml(
    tree: ElementTree,
    path: Path,
    doctype: DoctypeInfo | None = None,
    encoding: str = "utf-8",
) -> None:
    """Write an ElementTree to a file, re-emitting the XML declaration and DOCTYPE.

    `ElementTree.write()` has no support for writing a DOCTYPE, so the
    declaration and doctype line are written manually, followed by the
    serialized tree body.
    """
    root = tree.getroot()
    if root is None:
        msg = "Cannot write an ElementTree with no root element"
        raise ValueError(msg)

    body = tostring(root, encoding=encoding)

    with path.open("wb") as f:
        f.write(
            f'<?xml version="1.0" encoding="{encoding.upper()}"?>\n'.encode(encoding),
        )
        if doctype is not None:
            f.write(doctype.as_declaration().encode(encoding))
            f.write(b"\n")
        f.write(body)

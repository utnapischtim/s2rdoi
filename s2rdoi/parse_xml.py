# SPDX-FileCopyrightText: 2026 Graz University of Technology.
# SPDX-License-Identifier: MIT

"""Parse xml."""

import html.entities
from pathlib import Path
from xml.etree.ElementTree import ElementTree, TreeBuilder
from xml.parsers.expat import ParserCreate


def make_entity_resolver() -> dict[str, str]:
    """Build a lookup table mapping HTML entity names to their Unicode equivalents."""
    return {name.rstrip(";"): char for name, char in html.entities.html5.items()}


def parse_xml(path: Path) -> ElementTree:
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

    def default_handler(data: str) -> None:
        if data.startswith("&") and data.endswith(";"):
            entity_name = data[1:-1]
            resolved = entity_map.get(entity_name, data)
            target.data(resolved)

    parser.DefaultHandler = default_handler

    with path.open("rb") as f:
        parser.ParseFile(f)

    return ElementTree(target.close())

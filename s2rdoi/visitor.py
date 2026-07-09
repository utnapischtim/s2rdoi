# SPDX-FileCopyrightText: 2026 Graz University of Technology.
# SPDX-License-Identifier: MIT

"""Visitor."""

from dataclasses import dataclass, field
from xml.etree.ElementTree import Element


@dataclass
class DataCiteMetadata:
    """DataCiteMetadata."""

    publisher: str | None = None
    titles: list[dict] = field(default_factory=list)
    authors: list[dict[str, str]] = field(default_factory=list)
    publication_year: str | None = None
    publication_month: str | None = None
    resource_type_general: str | None = None
    url: str | None = None

    def dump(self) -> dict:
        """Dump."""
        return {
            "titles": self.titles,
            "creators": self.authors,
            "publisher": self.publisher,
            "publicationYear": self.publication_year,
            "dates": [
                {
                    "date": f"{self.publication_year}-{self.publication_month}",
                    "dateType": "Issued",
                },
            ],
            "types": {
                "resourceTypeGeneral": self.resource_type_general or "Other",
            },
        }


class QName:
    """Local Rewrite for lxml.etree.QName."""

    def __init__(self, node: Element) -> None:
        """Construct for QName."""
        self.node = node

    @property
    def localname(self) -> str:
        """Return localname from node with xpath."""
        return self.node.tag.split("}")[-1]

    @property
    def namespace(self) -> str:
        """Return namespace from node with xpath."""
        return self.node.tag.split("}")[0][1:]


class Visitor:
    """Visitor base class."""

    def process(self, node: Element, record: DataCiteMetadata) -> None:
        """Execute the corresponding method to the tag name."""

        def silently_ignore(_: Element, __: DataCiteMetadata) -> None:
            """Silently ignore element."""

        tag_name = QName(node).localname.replace("-", "_")
        visit_func = getattr(self, f"visit_{tag_name}", silently_ignore)
        visit_func(node, record)

    def visit(self, node: Element, record: DataCiteMetadata) -> None:
        """Entry point for visitor."""
        for child in node:
            self.process(child, record)

    def convert(self, node: Element, record: DataCiteMetadata) -> None:
        """Convert."""
        self.visit(node, record)


class BITSToDataCite(Visitor):
    """Converter between BITS and DataCite."""

    def __init__(self) -> None:
        """Construct."""
        # Temporary state used while collecting a single contrib element
        self._current_contrib: dict[str, str] = {}
        self._current_contrib_type: str = ""
        self._url = {}

    def book_part_wrapper(self, element: Element, record: DataCiteMetadata) -> None:
        """Extract resource type."""
        match element.attrib["content-type"]:
            case "research-article":
                record.resource_type_general = "ConferencePaper"
            case "poster":
                record.resource_type_general = "Poster"
            case "abstract":
                record.resource_type_general = "Text"
            case "demonstration":
                record.resource_type_general = "Other"

        self.visit(element, record)

    def visit_book_part_meta(self, element: Element, record: DataCiteMetadata) -> None:
        """Descends into book-part-meta to reach title-group and contrib-group."""
        self.visit(element, record)

    def visit_title_group(self, element: Element, record: DataCiteMetadata) -> None:
        """Collect the main title; subtitles are intentionally ignored."""
        self.visit(element, record)

    def visit_title(self, element: Element, record: DataCiteMetadata) -> None:
        """Append the text content of a <title> element to titles.

        Empty titles are skipped.
        """
        text = (element.text or "").strip()
        if text:
            record.titles.append({"title": text})

    def visit_contrib_group(self, element: Element, record: DataCiteMetadata) -> None:
        """Descends into contrib-group to collect individual contributors."""
        self.visit(element, record)

    def visit_contrib(self, element: Element, record: DataCiteMetadata) -> None:
        """Process a single <contrib element.

        Only contributors with contrib-type="author" are collected.
        Sets up temporary state for child name elements.
        """
        contrib_type = element.get("contrib-type", "")
        if contrib_type != "author":
            return

        self._current_contrib = {}
        self._current_contrib_type = contrib_type
        self.visit(element, record)

        given = self._current_contrib.get("givenName", "")
        family = self._current_contrib.get("familyName", "")
        full_name = f"{family}, {given}".strip(", ")
        record.authors.append(
            {
                "name": full_name,
            },
        )

        self._current_contrib = {}
        self._current_contrib_type = ""

    def visit_name(self, element: Element, record: DataCiteMetadata) -> None:
        """Descends into <name> to collect surname and given-names."""
        self.visit(element, record)

    def visit_surname(self, element: Element, _: DataCiteMetadata) -> None:
        """Store the surname into the current contributor dict."""
        self._current_contrib["familyName"] = (element.text or "").strip()

    def visit_given_names(self, element: Element, _: DataCiteMetadata) -> None:
        """Store the given names into the current contributor dict."""
        self._current_contrib["givenName"] = (element.text or "").strip()

    def visit_pub_date(self, element: Element, record: DataCiteMetadata) -> None:
        """Collect publication year and month from a <pub-date> element.

        with date-type="publication".
        """
        if element.get("date-type") == "publication":
            self.visit(element, record)

    def visit_year(self, element: Element, record: DataCiteMetadata) -> None:
        """Store the publication year."""
        text = (element.text or "").strip()
        if text:
            record.publication_year = text

    def visit_month(self, element: Element, record: DataCiteMetadata) -> None:
        """Store the publication month (zero-padded to two digits)."""
        text = (element.text or "").strip()
        if text:
            record.publication_month = text.zfill(2)

# SPDX-FileCopyrightText: 2026 Graz University of Technology.
# SPDX-License-Identifier: MIT

"""CLI."""

from pathlib import Path
from typing import cast
from xml.etree.ElementTree import Element, ElementTree

from click import Path as ClickPath
from click import group, option, secho

from .parse_xml import parse_xml
from .utils import (
    DataCiteCredentials,
    build_credentials,
    create_doi,
    insert_doi,
    update_parent,
)


@group()
def main() -> None:
    """DOI registration tool powered by DataCite."""


@main.command("public-doi")
@option(
    "--input-xml",
    required=True,
    type=ClickPath(exists=True, readable=True, path_type=Path),
    help="Path to the BITS XML input file.",
)
@option(
    "--output-xml",
    required=True,
    type=ClickPath(writable=True, path_type=Path),
    help="Path where the updated XML (with DOI injected) will be written.",
)
@option(
    "--parent-xml",
    required=True,
    type=ClickPath(writable=True, path_type=Path),
    help="Path where the updated XML (with DOI injected) will be written.",
)
@option("--publisher", required=True, help="Publisher name for the DataCite record.")
@option(
    "--url-base",
    required=True,
    help="Target url base",
)  # e.g. https://dl.acm.org/doi/
@build_credentials
def public_doi(
    input_xml: Path,
    output_xml: Path,
    parent_xml: Path,
    publisher: str,
    url_base: str,
    credentials: DataCiteCredentials,
) -> None:
    """Register a public DOI for the given XML file and write the updated XML."""
    tree = parse_xml(input_xml)
    root = cast(Element, tree.getroot())

    doi = create_doi(root, publisher, url_base, credentials)
    root, old_doi = insert_doi(root, doi)

    update_parent(parent_xml, old_doi, doi)

    et = ElementTree(root)
    et.write(output_xml, encoding="utf-8")  # , pretty_print=True # lxml

    secho(f"Draft DOI registered: {doi}", fg="green")
    secho(f"Updated XML written to: {output_xml}", fg="green")

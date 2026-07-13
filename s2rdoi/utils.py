# SPDX-FileCopyrightText: 2026 Graz University of Technology.
# SPDX-License-Identifier: MIT

"""Utils."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from os import environ
from pathlib import Path
from typing import Concatenate, cast
from xml.etree.ElementTree import Element, ElementTree

from click import option
from datacite import DataCiteRESTClient

from .parse_xml import parse_xml
from .visitor import BITSToDataCite, DataCiteMetadata


@dataclass
class DataCiteCredentials:
    """Class DataCiteCredentials."""

    username: str
    password: str
    prefix: str
    test: bool


def build_credentials[**P, R](
    func: Callable[Concatenate[DataCiteCredentials, P], R],
) -> Callable[P, R]:
    """Decorate that adds DataCite credential options to a Click command.

    It adds the options to the decorated function and injects a
    DataCiteCredentials instance as the 'credentials' parameter, replacing the
    individual username/password/prefix/test parameters.
    """

    @option("--username", required=True, help="DataCite account username.")
    @option("--password", required=True, help="DataCite account password.")
    @option("--prefix", required=True, help="DataCite DOI prefix (e.g. 10.1234).")
    @option(
        "--test",
        is_flag=True,
        default=False,
        help="Use DataCite test environment.",
    )
    @wraps(func)
    def wrapper(
        *args: P.args,
        username: str,
        password: str,
        prefix: str,
        test: bool,
        **kwargs: P.kwargs,
    ) -> R:
        credentials = DataCiteCredentials(
            username=username,
            password=password,
            prefix=prefix,
            test=test,
        )
        return func(credentials=credentials, *args, **kwargs)

    return wrapper


def get_credentials() -> DataCiteCredentials:
    """Read DataCite credentials from environment variables."""
    missing = [
        v
        for v in ("DATACITE_USERNAME", "DATACITE_PASSWORD", "DATACITE_PREFIX")
        if not environ.get(v)
    ]

    if missing:
        msg = f"Missing required environment variables: {', '.join(missing)}"
        raise OSError(msg)

    test = environ.get("DATACITE_TEST", "").lower() in ["y", "t", "yes", "true", "1"]
    return DataCiteCredentials(
        environ["DATACITE_USERNAME"],
        environ["DATACITE_PASSWORD"],
        environ["DATACITE_PREFIX"],
        test,
    )


def create_doi(
    metadata: Element | None,
    publisher: str,
    url_base: str,
    credentials: DataCiteCredentials,
) -> str:
    """Create DOI."""
    record = DataCiteMetadata(publisher)
    visitor = BITSToDataCite()
    visitor.convert(metadata, record)

    client = DataCiteRESTClient(
        credentials.username,
        credentials.password,
        credentials.prefix,
        credentials.test,
    )

    # the workflow is to first create a generic doi
    doi = client.draft_doi(record.dump())

    # set the url to the doi with the base as the url base
    url = url_base + doi

    client.update_url(doi, url)

    # set the doi public with the given url
    client.show_doi(doi)
    return doi


def insert_doi(metadata: Element, doi: str) -> tuple[Element, str]:
    """Insert the DOI."""
    existing = metadata.find(".//book-part-id[@book-part-id-type='doi']")
    if existing is not None:
        old_doi = cast(str, existing.text)
        existing.text = doi
        return metadata, old_doi

    # Prefer inserting inside <book-part-meta>
    parent = metadata.find(".//book-part-meta")

    if not parent:
        raise RuntimeError

    doi_element = Element("book-part-id", attrib={"book-part-id-type": "doi"})
    doi_element.text = doi
    parent.append(doi_element)

    return metadata, ""


def update_parent(parent: Path, old_doi: str, doi: str) -> None:
    """Update parent."""
    tree = parse_xml(parent)
    root = cast(Element, tree.getroot())

    existing = cast(Element, root.find(f".//ext-link[.='{old_doi}']"))
    existing.text = doi

    et = ElementTree(root)
    et.write(parent, encoding="utf-8")


def rename_xml_and_parent_dir(filepath: Path, replacement: str) -> Path:
    """Rename the parent directory and the XML file on disk."""
    old_dir = filepath.parent
    new_dir = old_dir.parent / replacement

    if new_dir.exists():
        msg = f"Target directory already exists: {new_dir}"
        raise FileExistsError(msg)

    old_dir.rename(new_dir)

    moved_file = new_dir / filepath.name
    new_file = new_dir / f"{replacement}{filepath.suffix}"

    if new_file.exists():
        msg = f"Target file already exists: {new_file}"
        raise FileExistsError(msg)

    moved_file.rename(new_file)

    return new_file

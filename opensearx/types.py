import itertools
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlsplit

import attrs
from stac_fastapi.types import stac as stac_types

stac_version = "1.0.0"


@attrs.define
class Collection:
    id: str
    guidislink: bool
    link: str

    author: Dict[str, str]
    authors: List[Dict[str, str]]
    author_detail: List[Dict[str, str]]

    title: str
    title_detail: Dict[str, Any]

    summary: str
    summary_detail: Dict[str, Any]

    updated: str
    updated_parsed: str
    dc_identifier: str
    echo_datasetid: str
    echo_shortname: str
    echo_versionid: str
    echo_datacenter: str
    echo_organization: str
    echo_coordinatesystem: str

    def to_stac(self):
        return stac_types.Collection(
            {
                "type": "Collection",
                "stac_version": "1.0.0",
                "stac_extensions": [],
                "id": self.id,
                "title": self.title,
                "description": "{{ collection.description }}",
                "links": [],
                "keywords": [],
                "license": "proprietary",
                "extent": {
                    "spatial": {"bbox": ""},
                    "temporal": {"interval": ["1900-01-01", "2100-01-01"]},
                },
                "providers": [],
                "summaries": {},
                "assets": {},
            }
        )


@attrs.define
class Collections:
    entries: List[Collection]

    def to_stac(self):
        return stac_types.Collections(
            collections=[e.to_stac() for e in self.entries],
            links=[],
        )


def geometry_to_bbox(where):
    polygons = where["coordinates"]
    lat, lon = zip(*itertools.chain.from_iterable(polygons))

    return min(lon), min(lat), max(lon), max(lat)


def extract_uid(url):
    components = urlsplit(url)
    params = parse_qs(components.query)
    return "-".join(elem.removesuffix(".nc") for elem in params.get("uid", [url]))


@attrs.define
class Item:
    title: str
    title_detail: dict[str, Any]
    id: str
    guidislink: bool
    link: str
    updated: str
    updated_parsed: Any
    where: dict

    links: list[dict[str, str]]

    summary: str
    summary_detail: dict[str, Any]

    gml_outerboundaryis: Optional[str] = ""
    gml_polygonmember: Optional[str] = ""
    gml_multipolygon: Optional[str] = ""

    def to_stac(self):
        stac_links = {link.pop("rel"): link for link in self.links}
        start_datetime, end_datetime = self.updated.split("/")
        id = extract_uid(self.id)
        return stac_types.Item(
            type="Feature",
            stac_version=stac_version,
            stac_extensions=[],
            geometry=self.where,
            bbox=geometry_to_bbox(self.where),
            id=id,
            assets=stac_links,
            datetime=None,
            properties={"start_datetime": start_datetime, "end_datetime": end_datetime},
            links=[],
        )

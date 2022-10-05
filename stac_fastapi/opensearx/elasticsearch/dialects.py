import base64
import itertools
from datetime import datetime

import attrs
import dateutil
import more_itertools
import pystac
from stac_fastapi.types import errors
from stac_fastapi.types import stac as stac_types


def drop_none(iterable):
    yield from (item for item in iterable if item is not None)


def bbox_from_geometry(geometry):
    from odc.geo import Geometry

    geom = Geometry(geometry)
    return geom.geom.bounds


def bbox_to_envelope_geometry(bbox):
    x0, y0, x1, y1 = bbox

    top_left = [x0, y1]
    bottom_right = [x1, y0]
    envelope = [top_left, bottom_right]

    return {"type": "envelope", "coordinates": envelope}


def decode_search_after(token):
    if token is None:
        return None

    return base64.urlsafe_b64decode(token.encode()).decode().split(",")


def encode_search_after(search_after):
    joined = ",".join(str(_) for _ in search_after)

    return base64.urlsafe_b64encode(joined.encode()).decode()


@attrs.define
class SceneInfo:
    filename = attrs.field()
    year = attrs.field()
    day_of_year = attrs.field()


@attrs.define
class Ifremer:
    session = attrs.field()
    filepatterns = attrs.field(factory=dict)

    prefix = "isi_cersat_naiad_"

    temporal_field_names = ("time_coverage_start", "time_coverage_end")
    spatial_field_name = "geometry"
    sort = list(temporal_field_names) + ["_id"]

    def clean_index_name(self, name):
        return name.removeprefix(self.prefix)

    def index_to_collection(self, index) -> stac_types.Collection:
        id = self.clean_index_name(index["index"])

        spatial_extent = pystac.SpatialExtent([[-180, -90, 180, 90]])
        temporal_extent = pystac.TemporalExtent(
            [[datetime(1900, 1, 1), datetime(2100, 1, 1)]]
        )

        collection = pystac.Collection(
            id=id,
            description=id,
            extent=pystac.Extent(
                spatial=spatial_extent,
                temporal=temporal_extent,
            ),
            title=id,
        )
        collection.links = []

        return collection

    def temporal_filter(self, range_):
        if not range_:
            return []

        # Items have a date range, and the query can have these forms:
        # - a single datetime: in that case find any items that contain that datetime
        # - a interval: find any items that are entirely contained within that item
        if "/" in range_:
            start, end = range_.split("/")
        else:
            start, end = range_, range_

        if start != "..":
            yield {"range": {self.temporal_field_names[0]: {"gte": start}}}

        if end != "..":
            yield {"range": {self.temporal_field_names[1]: {"lte": end}}}

    def spatial_filter(self, bbox, intersects):
        if bbox:
            yield {
                "geo_shape": {
                    self.spatial_field_name: {
                        "shape": bbox_to_envelope_geometry(bbox),
                        "relation": "within",
                    }
                }
            }
        elif intersects:
            yield {
                "geo_shape": {
                    self.spatial_field_name: {
                        "shape": {
                            "type": intersects.type,
                            "coordinates": intersects.coordinates,
                        },
                        "relation": "intersects",
                    }
                }
            }
        else:
            yield None

    def item_id_filter(self, ids):
        if not ids:
            yield None
        else:
            yield {"ids": {"values": ids}}

    async def collections(self) -> stac_types.Collections:
        """
        collections will be stored in index information in the future, but at the moment,
        there's only the names.

        As such, we will pull only the collection name from the database and fill in dummy
        values for everything else.
        """
        # collections are stored in indices
        indices = await self.session.cat.indices(format="json")
        return [self.index_to_collection(index) for index in indices]

    async def collection(self, name) -> stac_types.Collection:
        """get a specific collection by name

        Since there's no way to get just a the info of a single index, we can just
        delegate to `collections`.
        """
        collections = {col.id: col for col in await self.collections()}
        col = collections.get(name)
        if name is None:
            raise errors.NotFoundError(f"could not find collection {name!r}")

        return col

    def fname_to_assets(self, collection, scene_info):
        comparisons = {
            "contains": lambda s: s in scene_info.filename,
        }

        def check_condition(condition):
            if not condition:
                return True

            return all(comparisons[comp](value) for comp, value in condition.items())

        def fill_link(pattern):
            link = pattern.copy()
            file_pattern = link.pop("pattern")
            link["href"] = file_pattern.format(scene=scene_info)

            return link

        patterns = self.filepatterns.get(collection)
        if not patterns:
            return {}

        link_patterns = [
            pattern["links"]
            for pattern in patterns
            if check_condition(pattern.get("condition"))
        ]
        if len(link_patterns) != 1:
            raise ValueError(
                f"patterns do not match filename exactly once: {scene_info.filename}"
            )

        links = [fill_link(link) for link in more_itertools.one(link_patterns)]
        assets = {link["name"]: pystac.Asset(href=link["href"]) for link in links}
        return assets

    def hit_to_item(self, hit):
        collection = self.clean_index_name(hit["_index"])
        id_ = hit["_id"]

        source = hit["_source"]
        fname = source["granule"]

        timestamp = dateutil.parser.parse(source["time_coverage_start"])

        scene_info = SceneInfo(
            fname, timestamp.strftime("%j"), timestamp.strftime("%Y")
        )

        assets = self.fname_to_assets(collection, scene_info)

        return pystac.Item(
            id=id_,
            geometry=source["geometry"],
            datetime=None,
            bbox=bbox_from_geometry(source["geometry"]),
            properties={
                "start_datetime": source["time_coverage_start"],
                "end_datetime": source["time_coverage_end"],
            },
            assets=assets,
        )

    def search_query(self, search_request):
        if search_request.collections:
            indexes = [self.prefix + name for name in search_request.collections]
        else:
            indexes = "_all"

        query = {
            "bool": {
                "filter": list(
                    drop_none(
                        itertools.chain(
                            self.item_id_filter(search_request.ids),
                            self.temporal_filter(search_request.datetime),
                            self.spatial_filter(
                                search_request.bbox, search_request.intersects
                            ),
                        )
                    )
                ),
            }
        }
        if not query["bool"]["filter"]:
            # get all results
            query = None

        return indexes, query

    async def search(self, search_request, token):
        # TODO: use `elasticsearch_dsl`, then extract the query using `.to_dict()`
        indexes, query = self.search_query(search_request)

        search_after = decode_search_after(token)

        result = await self.session.search(
            index=indexes,
            query=query,
            size=search_request.limit,
            track_total_hits=True,
            sort=self.sort,
            search_after=search_after,
        )

        hits = result["hits"]
        all_hits = hits["hits"]

        new_token = encode_search_after(all_hits[-1]["sort"]) if all_hits else None
        items = [self.hit_to_item(hit) for hit in hits["hits"]]

        return new_token, items


dialects = {
    "ifremer": Ifremer,
}

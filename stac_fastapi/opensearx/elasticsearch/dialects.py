import itertools
from datetime import datetime

import attrs
import pystac
from stac_fastapi.types import errors
from stac_fastapi.types import stac as stac_types


def bbox_from_geometry(geometry):
    from odc.geo import Geometry

    geom = Geometry(geometry)
    return geom.geom.bounds


@attrs.define
class Ifremer:
    session = attrs.field()

    prefix = "isi_cersat_naiad_"

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

    def temporal_query(self, range_):
        return []

    def spatial_query(self, bbox, intersects):
        return []

    def item_query(self, ids):
        return []

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

    def hit_to_item(self, hit):
        fname = hit.meta.id

        return pystac.Item(
            id=fname,
            geometry=hit.geometry.to_dict(),
            datetime=None,
            bbox=bbox_from_geometry(hit.geometry.to_dict()),
            properties={
                "start_datetime": hit.time_coverage_start,
                "end_datetime": hit.time_coverage_end,
            },
        )

    async def search(self, search_request, page):
        if search_request.collections:
            indexes = [self.prefix + name for name in search_request.collections]
        else:
            indexes = "_all"

        query = {
            "bool": {
                "filter": list(
                    itertools.chain(
                        self.item_query(search_request.ids),
                        self.temporal_query(search_request.datetime),
                        self.spatial_query(
                            search_request.bbox, search_request.intersects
                        ),
                    )
                ),
            }
        }
        if not query["bool"]["filter"]:
            # get all results
            query = None

        if search_request.limit:
            from_ = (page - 1) * search_request.limit
            size = search_request.limit
        else:
            from_ = None
            size = None

        result = await self.session.search(
            index=indexes,
            query=query,
            from_=from_,
            size=size,
            track_total_hits=True,
        )
        hits = result["hits"]
        n_total = hits["total"]["value"]

        return 0, []

        items = [self.hit_to_item(hit) for hit in result.hits]
        n_total = result.hits.total["value"]

        return n_total, items


dialects = {
    "ifremer": Ifremer,
}

from datetime import datetime

import attrs
import pystac
from elasticsearch_dsl import Search
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

    def collections(self) -> stac_types.Collections:
        """
        collections will be stored in index information in the future, but at the moment,
        there's only the names.

        As such, we will pull only the collection name from the database and fill in dummy
        values for everything else.
        """
        # collections are stored in indices
        indices = self.session.cat.indices(format="json")
        return [self.index_to_collection(index) for index in indices]

    def collection(self, name) -> stac_types.Collection:
        """get a specific collection by name

        Since there's no way to get just a the info of a single index, we can just
        delegate to `collections`.
        """
        collections = {col.id: col for col in self.collections()}
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

    def search(self, search_request, page):
        if search_request.collections:
            indexes = [self.prefix + name for name in search_request.collections]
        else:
            indexes = "_all"

        s = Search(index=indexes).using(self.session).extra(track_total_hits=True)

        # temporal extent
        if search_request.datetime:
            # Items have a date range, and the query can have these forms:
            # - a single datetime: in that case find any items that contain that datetime
            # - a interval: find any items that are entirely contained within that item
            def split_datetime(datetime):
                if "/" not in datetime:
                    # searching for exactly this datetime
                    return datetime, datetime

                return datetime.split("/")

            lower_bound, upper_bound = split_datetime(search_request.datetime)

            if lower_bound != "..":
                s = s.filter("range", time_coverage_start={"gte": lower_bound})

            if upper_bound != "..":
                s = s.filter("range", time_coverage_end={"lte": upper_bound})

        # spatial extent
        # if search_request.bbox:
        #     pass

        if search_request.limit:
            lower = (page - 1) * search_request.limit
            upper = page * search_request.limit

            s = s[lower:upper]

        result = s.execute()

        items = [self.hit_to_item(hit) for hit in result.hits]
        n_total = result.hits.total["value"]

        return n_total, items


dialects = {
    "ifremer": Ifremer,
}

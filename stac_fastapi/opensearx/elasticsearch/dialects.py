from datetime import datetime

import attrs
import pystac
from stac_fastapi.types import errors
from stac_fastapi.types import stac as stac_types


@attrs.define
class Ifremer:
    session = attrs.field()

    def clean_index_name(self, name):
        return name.removeprefix("isi_cersat_naiad_")

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

    def search(self, search_request, page, limit):
        pass


dialects = {
    "ifremer": Ifremer,
}

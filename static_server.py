from __future__ import annotations

from stac_fastapi.api.app import StacApi

from stac_fastapi.types.core import BaseCoreClient
from stac_fastapi.types.search import BaseSearchPostRequest
from stac_fastapi.types import stac as stac_types
from stac_fastapi.types import config

from stac_fastapi.extensions.core import PaginationExtension

import pystac
import attr


def pystac_to_collection(col):
    return stac_types.Collection({
        "type": col.catalog_type,
        "stac_version": pystac.version.get_stac_version(),
        "stac_extensions": col.stac_extensions,
        "id": col.id,
        "title": col.title,
        "description": col.description,
        "links": [link.to_dict() for link in col.links],
        "keywords": col.extra_fields["keywords"],
        "license": col.license,
        "providers": col.extra_fields["providers"],
        "extent": col.extent.to_dict(),
        "summaries": col.summaries.to_dict(),
        "assets": {name: asset.to_dict() for name, asset in col.assets.items()},
    })


@attr.s
class StaticCatalogClient(BaseCoreClient):
    """A client to search a static STAC catalog"""

    catalog: pystac.Catalog = attr.ib(default=None)

    def get_item(self, item_id: str, collection_id: str, **kwargs) -> stac_types.Item:
        pass

    def get_search(
        self,
        collections: Optional[List[str]] = None,
        ids: Optional[List[str]] = None,
        bbox: Optional[List[NumType]] = None,
        datetime: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = 10,
        query: Optional[str] = None,
        token: Optional[str] = None,
        fields: Optional[List[str]] = None,
        sortby: Optional[str] = None,
        **kwargs,
    ) -> stac_types.ItemCollection:
        pass

    def post_search(self, search_request: BaseSearchPostRequest, **kwargs) -> stac_types.ItemCollection:
        pass

    def all_collections(self, **kwargs) -> stac_types.Collections:
        # TODO: use request.query_params and request.base_url
        request = kwargs["request"]
        collections = [
            pystac_to_collection(col)
            for col in self.catalog.get_all_collections()
        ]
        return stac_types.Collections({
            "collections": list(collections),
            "links": [link.to_dict() for link in self.catalog.links],
        })

    def get_collection(self, collection_id: str, **kwargs) -> stac_types.Collection:
        print(kwargs)

    def item_collection(self, collection_id: str, limit: int = 10, token: str = None, **kwargs) -> stac_types.ItemCollection:
        pass

settings = config.ApiSettings(app_host="127.0.0.1", app_port=9588)

catalog = pystac.read_file("daymet/catalog.json")

client = StaticCatalogClient(catalog=catalog)

extensions = [
    PaginationExtension(),
]

api = StacApi(settings, client=client, extensions=extensions, pagination_extension=PaginationExtension)
app = api.app


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "static_server:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level="info",
        reload_dirs=["/app/stac_fastapi", "/app/conf"],
        reload=True,
    )

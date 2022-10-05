from datetime import datetime
from typing import List, Optional, Union

import attrs
from attrs import validators
from elasticsearch import AsyncElasticsearch
from stac_fastapi.types import stac as stac_types
from stac_fastapi.types.core import AsyncBaseCoreClient, NumType
from stac_fastapi.types.search import BaseSearchPostRequest

from . import pagination
from .dialects import dialects


# TODO: make this an async client once elasticsearch-dsl supports async
@attrs.define
class ElasticsearchClient(AsyncBaseCoreClient):
    credentials = attrs.field(default=None)
    timeout = attrs.field(
        default=20, validator=[validators.instance_of(int), validators.ge(0)]
    )
    dialect = attrs.field(default="ifremer", validator=validators.in_(dialects))
    dialect_config = attrs.field(factory=dict)
    use_socks_proxy = attrs.field(default=False)

    client = attrs.field(default=None, init=False)

    def __attrs_post_init__(self):
        if self.credentials is None:
            raise ValueError("need credentials to connect to the database")

        options = {
            "hosts": [self.credentials],
            "timeout": self.timeout,
        }
        if self.use_socks_proxy:
            from .connection import ProxyAIOHttpConnection

            options["connection_class"] = ProxyAIOHttpConnection

        self.session = AsyncElasticsearch(**options)

        dialect_class = dialects.get(self.dialect)
        self.client = dialect_class(self.session, **self.dialect_config)

    async def close(self):
        self.client = None

        await self.session.close()
        self.session = None

    async def all_collections(self, **kwargs) -> stac_types.Collections:
        collections = await self.client.collections()
        return stac_types.Collections(
            collections=[col.to_dict() for col in collections],
            links=[],
        )

    async def get_collection(
        self, collection_id: str, **kwargs
    ) -> stac_types.Collection:
        collection = await self.client.collection(collection_id)
        return collection.to_dict()

    async def get_item(
        self, item_id: str, collection_id: str, **kwargs
    ) -> stac_types.Item:
        pass

    async def item_collection(
        self, collection_id: str, limit: int = 10, token: str = None, **kwargs
    ) -> stac_types.ItemCollection:
        pass

    async def get_search(
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
        request = kwargs["request"]
        params = request.query_params

        token = params.get("token")

        options = {
            "collections": collections,
            "ids": ids,
            "bbox": bbox,
            "datetime": datetime,
            "limit": limit,
        }
        clean = {key: value for key, value in options.items() if value is not None}
        search_request = BaseSearchPostRequest(**clean)

        new_token, items = await self.client.search(search_request, token=token)

        links = pagination.generate_get_pagination_links(
            request.url,
            token=new_token,
        )

        return stac_types.ItemCollection(
            features=[item.to_dict() for item in items],
            links=links,
        )

    async def post_search(
        self, search_request: BaseSearchPostRequest, **kwargs
    ) -> stac_types.ItemCollection:
        request = kwargs["request"]

        params = await request.json()

        token = params.get("token")

        new_token, items = await self.client.search(search_request, token=token)

        links = pagination.generate_post_pagination_links(
            request.url,
            token=new_token,
        )

        return stac_types.ItemCollection(
            features=[item.to_dict() for item in items],
            links=links,
        )

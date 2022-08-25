from datetime import datetime
from typing import List, Optional, Union

import attrs
from attrs import validators
from elasticsearch import RequestsHttpConnection
from elasticsearch_dsl import connections
from stac_fastapi.types import stac as stac_types
from stac_fastapi.types.core import BaseCoreClient, NumType
from stac_fastapi.types.search import BaseSearchGetRequest, BaseSearchPostRequest

from .dialects import dialects


# TODO: make this an async client once elasticsearch-dsl supports async
@attrs.define
class ElasticsearchClient(BaseCoreClient):
    credentials = attrs.field(default=None)
    timeout = attrs.field(
        default=20, validator=[validators.instance_of(int), validators.ge(0)]
    )
    dialect = attrs.field(default="ifremer", validator=validators.in_(dialects))

    session = attrs.field(default=None, init=False)

    def __attrs_post_init__(self):
        if self.credentials is None:
            raise ValueError("need credentials to connect to the database")

        self.session = connections.create_connection(
            hosts=[self.credentials],
            timeout=self.timeout,
            connection_class=RequestsHttpConnection,
        )

    def close(self):
        self.session.close()
        self.session = None

    def all_collections(self, **kwargs) -> stac_types.Collections:
        return stac_types.Collections(collections=[], links=[])

    def get_collection(self, collection_id: str, **kwargs) -> stac_types.Collection:
        pass

    def get_item(self, item_id: str, collection_id: str, **kwargs) -> stac_types.Item:
        pass

    def item_collection(
        self, collection_id: str, limit: int = 10, token: str = None, **kwargs
    ) -> stac_types.ItemCollection:
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
        search_request = BaseSearchGetRequest(
            collections=collections,
            ids=ids,
            bbox=bbox,
            datetime=datetime,
        )
        search_request  # stub
        return None

    def post_search(
        self, search_request: BaseSearchPostRequest, **kwargs
    ) -> stac_types.ItemCollection:
        pass

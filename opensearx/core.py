from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import attrs
from stac_fastapi.types import stac as stac_types
from stac_fastapi.types.core import AsyncBaseCoreClient, NumType
from stac_fastapi.types.search import BaseSearchPostRequest, Union

from . import atom, json

format_parsers = {
    "json": json.parse,
    "atom": atom.parse,
}


@attrs.define
class OpensearxApiClient(AsyncBaseCoreClient):
    """A shim client for opensearx apis.

    Parameters
    ----------
    url : str
        The url of the opensearx json api
    """

    url = attrs.field(default="https://opensearch.ifremer.fr/granules.{format}")
    format = attrs.field(default="atom")

    @format.validator
    def _valid_format(self, attribute, value):
        if value not in format_parsers:
            raise ValueError(
                f"unknown format {value!r}, expected one of"
                f" {{{', '.join(repr(f) for f in format_parsers)}}}"
            )

    def __attrs_post_init__(self):
        self.url = self.url.format(format=self.format)
        self.parser = format_parsers.get(self.format)

    async def all_collections(self, **kwargs) -> stac_types.Collections:
        pass

    async def get_collection(
        self, collection_id: str, **kwargs
    ) -> stac_types.Collection:
        pass

    async def get_item(self, item_id: str, collection_id: str, **kwargs):
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
    ):
        pass

    async def post_search(self, search_request: BaseSearchPostRequest, **kwargs):
        pass

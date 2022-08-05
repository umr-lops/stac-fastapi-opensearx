from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import aiohttp
import attrs
import rich.console
from stac_fastapi.types import errors
from stac_fastapi.types import stac as stac_types
from stac_fastapi.types.core import AsyncBaseCoreClient, NumType
from stac_fastapi.types.search import BaseSearchPostRequest, Union

from . import atom, json, pagination, types

console = rich.console.Console()

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

    url = attrs.field(default="https://opensearch.ifremer.fr")
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
        self.session = aiohttp.ClientSession()
        self.parse = format_parsers.get(self.format)

    async def close(self):
        await self.session.close()

    async def query_api(self, path, params={}):
        url = f"{self.url}{path}"
        console.print("requesting from:", url)
        console.print("with params:", params)
        async with self.session.get(url, params=params) as r:
            return self.parse(await r.text())

    async def all_collections(self, **kwargs) -> stac_types.Collections:
        content = await self.query_api(f"/collections.{self.format}")
        entries = [types.Collection(**entry) for entry in content["entries"]]

        return types.Collections(entries=entries).to_stac()

    async def get_collection(
        self, collection_id: str, **kwargs
    ) -> stac_types.Collection:
        all_collections = await self.all_collections(**kwargs)
        for col in all_collections["collections"]:
            if col["id"] == collection_id:
                return col
        return stac_types.Collection({})

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
        request = kwargs["request"]
        request_params = await request.json()

        console.print("request body:", request_params)

        params = {}

        collections = search_request.collections
        if collections is None:
            raise errors.InvalidQueryParameter("Cannot search on all collections")
        elif len(collections) > 1:
            raise errors.InvalidQueryParameter("Cannot search more than one collection")
        elif len(collections) == 0:
            raise errors.InvalidQueryParameter("Need to search at least one collection")
        else:
            params["datasetId"] = collections[0]

        if search_request.bbox is not None:
            params["geoBox"] = ",".join(f"{v}" for v in search_request.bbox)

        if search_request.datetime is not None:
            parts = search_request.datetime.split("/")
            if len(parts) != 2:
                raise errors.InvalidQueryParameter(
                    f"invalid datetime format: {search_request.datetime}"
                )
            start, end = parts
            params["timeStart"] = start
            params["timeEnd"] = end
        else:
            params["timeStart"] = "1000-01-01T00:00:00Z"
            params["timeEnd"] = "2200-01-01T23:59:59Z"

        console.print(search_request)

        current_page = request_params.get("page", 1)

        params["startPage"] = current_page - 1

        if search_request.limit is not None:
            params["count"] = search_request.limit

        response = await self.query_api(f"/granules.{self.format}", params=params)

        feed = response.get("feed")
        if feed is None:
            raise errors.StacApiError("backend server returned invalid feed")

        entries = response.get("entries", [])
        items = [types.Item(**entry) for entry in entries]

        n_results = int(feed.get("opensearch_totalresults", "0"))
        links = pagination.generate_post_pagination_links(
            request,
            page=current_page,
            n_results=n_results,
            limit=search_request.limit,
        )
        return stac_types.ItemCollection(
            type="FeatureCollection",
            features=[item.to_stac() for item in items],
            links=links,
        )

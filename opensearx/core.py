from __future__ import annotations

from datetime import datetime
from typing import List, Optional

import aiohttp
import attrs
import rich.console
from stac_fastapi.types import stac as stac_types
from stac_fastapi.types.core import AsyncBaseCoreClient, NumType
from stac_fastapi.types.search import BaseSearchGetRequest, BaseSearchPostRequest, Union

from . import atom, json, pagination, types, webapi

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
    dialect = attrs.field(default="ifremer")
    format = attrs.field(default="atom")
    session = attrs.field(default=None)

    @format.validator
    def _valid_format(self, attribute, value):
        if value not in format_parsers:
            raise ValueError(
                f"unknown format {value!r}, expected one of"
                f" {{{', '.join(repr(f) for f in format_parsers)}}}"
            )

    def __attrs_post_init__(self):
        self.url = self.url.format(format=self.format)
        self.parse = format_parsers.get(self.format)

    async def close(self):
        if self.session is None:
            return

        await self.session.close()
        del self.session

    async def query_api(self, path, params={}):
        from urllib.parse import urlencode

        if self.session is None:
            self.session = aiohttp.ClientSession()
        url = f"{self.url}{path}"
        console.print("requesting from:", url)
        console.print("with params:", urlencode(params))
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
        request = kwargs["request"]
        request_params = request.query_params

        console.print("request params:", request_params)

        search_request = BaseSearchGetRequest(
            collections=collections,
            ids=ids,
            bbox=bbox,
            datetime=datetime,
            limit=limit,
        )

        console.print(search_request)

        current_page = int(request_params.get("page", 1))
        params = webapi.translate_request(
            search_request,
            additional={"page": current_page},
            opensearch_dialect=self.dialect,
        )

        response = await self.query_api(f"/granules.{self.format}", params=params)

        n_results, items = webapi.translate_response(response)

        links = pagination.generate_get_pagination_links(
            request,
            page=current_page,
            n_results=n_results,
            limit=search_request.limit,
        )

        item_ids = search_request.ids or []
        if item_ids:
            console.print("filtering:", items, "with:", item_ids)
            items = [item for item in items if item["id"] in item_ids]

        return stac_types.ItemCollection(
            type="FeatureCollection",
            features=items,
            links=links,
        )

    async def post_search(self, search_request: BaseSearchPostRequest, **kwargs):
        request = kwargs["request"]
        request_params = await request.json()

        console.print("request body:", request_params)

        console.print(search_request)

        current_page = request_params.get("page", 1)
        params = webapi.translate_request(
            search_request,
            additional={"page": current_page},
            opensearch_dialect=self.dialect,
        )

        response = await self.query_api(f"/granules.{self.format}", params=params)

        n_results, items = webapi.translate_response(response)

        links = pagination.generate_post_pagination_links(
            request,
            page=current_page,
            n_results=n_results,
            limit=search_request.limit,
        )

        item_ids = search_request.ids or []
        if item_ids:
            console.print("filtering:", items, "with:", item_ids)
            items = [item for item in items if item["id"] in item_ids]

        return stac_types.ItemCollection(
            type="FeatureCollection",
            features=items,
            links=links,
        )

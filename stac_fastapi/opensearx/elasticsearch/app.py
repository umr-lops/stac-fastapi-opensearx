from stac_fastapi.api.app import StacApi
from stac_fastapi.extensions.core import PaginationExtension
from stac_fastapi.types import config

from .core import ElasticsearchClient


def create_api(*, credentials, host="127.0.0.1", port=9588, dialect="ifremer"):
    settings = config.ApiSettings(app_host=host, app_port=port)

    client = ElasticsearchClient(credentials=credentials, dialect=dialect)
    extensions = [
        PaginationExtension(),
    ]
    api = StacApi(
        settings,
        client=client,
        extensions=extensions,
        pagination_extension=PaginationExtension,
    )

    @api.app.on_event("shutdown")
    async def app_shutdown():
        """shutdown the client to close the session

        If there's a way to have `StacApi` do that for us it would be better to put there.
        """
        await client.close()

    return api

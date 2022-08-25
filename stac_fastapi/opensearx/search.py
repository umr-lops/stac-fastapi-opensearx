import aiohttp


def construct_params(
    collection, page, count, datetime=None, geobox=None, protocol=None, source=None
):
    params = {
        "datasetId": collection,
        "startPage": page,
        "count": count,
    }
    if datetime is not None:
        if isinstance(datetime, (list, tuple)):
            time_start, time_end = datetime
        elif isinstance(datetime, str):
            time_start, time_end = datetime.split("/")
        else:
            raise ValueError("unknown datetime type: {repr(datetime)}")

        params["timeStart"] = time_start
        params["timeEnd"] = time_end

    if geobox is not None:
        params["geoBox"] = " ".join(f"{v}" for v in geobox)

    if source is not None:
        params["source"] = source

    if params["protocol"] is not None:
        params["protocol"] = protocol

    return params


async def search(
    url,
    collection,
    page=0,
    count=10,
    datetime=None,
    geobox=None,
    protocol=None,
    source=None,
):
    """query the opensearx api"""
    params = construct_params(
        collection, page, count, datetime, geobox, protocol, source
    )
    async with aiohttp.get(url, params=params) as r:
        return await r.json()

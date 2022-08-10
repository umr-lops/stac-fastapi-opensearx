from stac_fastapi.types import errors


def translate_request_ifremer(search_request, additional):
    default_start_time = "1000-01-01T00:00:00Z"
    default_end_time = "2200-01-01T23:59:59Z"

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

    if search_request.intersects is not None:
        raise errors.InvalidQueryParameter(
            "opensearch endpoints don't support intersect searches"
        )

    if search_request.bbox is not None:
        params["geoBox"] = ",".join(f"{v}" for v in search_request.bbox)

    if search_request.datetime is not None:
        parts = search_request.datetime.split("/")
        if len(parts) == 1:
            parts = [".."] + parts
        start, end = parts
        params["timeStart"] = start if start != ".." else default_start_time
        params["timeEnd"] = end if end != ".." else default_end_time
    else:
        params["timeStart"] = default_start_time
        params["timeEnd"] = default_end_time

    current_page = additional["page"]

    params["startPage"] = current_page - 1

    if search_request.limit is not None:
        params["count"] = search_request.limit

    return params


dialects = {
    "ifremer": translate_request_ifremer,
}


def translate_request(request, additional, opensearch_dialect):
    translate = dialects.get(opensearch_dialect)
    if translate is None:
        raise ValueError(f"unknown opensearch dialect: {opensearch_dialect}")

    return translate(request, additional)

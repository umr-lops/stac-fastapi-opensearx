import itertools
import math
from urllib.parse import urlunsplit

from starlette.datastructures import QueryParams

rels = ["prev", "self", "next"]


def concat_params(params, new_params):
    multi_items = params.multi_items()

    concatenated = dict(itertools.chain(multi_items, new_params.items()))
    return QueryParams(concatenated)


def get_link(rel, url, page, total_pages, limit):
    orig_params = QueryParams(url.query)
    if rel == "self":
        new_page = page
    elif rel == "next":
        new_page = page + 1
        if new_page > total_pages:
            return {}
    elif rel == "prev":
        new_page = page - 1
        if new_page < 1:
            return {}
    else:
        raise ValueError(f"unknown relation: {rel}")

    params = concat_params(orig_params, {"page": new_page})
    new_url = url.replace(query=str(params))

    return {
        "rel": rel,
        "href": str(new_url),
    }


def generate_get_pagination_links(request, *, page, n_results, limit):
    total_pages = math.ceil(n_results / limit)

    url = request.url

    links = [
        get_link(rel=rel, url=url, page=page, total_pages=total_pages, limit=limit)
        for rel in rels
    ]

    return [link for link in links if link]


def post_url(obj):
    return urlunsplit(
        [
            obj.scheme,
            obj.netloc,
            obj.path,
            None,
            None,
        ]
    )


def post_link(rel, url, page, total_pages, limit):
    if rel == "self":
        new_page = page
        return {
            "rel": "self",
            "href": url,
            "method": "POST",
            "body": {
                "page": new_page,
                "limit": limit,
            },
            "merge": True,
        }
    elif rel == "next":
        new_page = page + 1
        if new_page > total_pages:
            return {}

        return {
            "rel": "next",
            "href": url,
            "method": "POST",
            "body": {
                "page": new_page,
                "limit": limit,
            },
            "merge": True,
        }
    elif rel == "prev":
        new_page = page - 1
        if new_page < 1:
            return {}

        return {
            "rel": "prev",
            "href": url,
            "method": "POST",
            "body": {
                "page": new_page,
                "limit": limit,
            },
            "merge": True,
        }
    else:
        raise ValueError(f"unknown relation: {rel}")


def generate_post_pagination_links(request, *, page, n_results, limit):
    total_pages = math.ceil(n_results / limit)

    url = post_url(request.url)
    links = [
        post_link(rel=rel, url=url, page=page, total_pages=total_pages, limit=limit)
        for rel in rels
    ]
    return [link for link in links if link]

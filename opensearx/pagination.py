import math
from urllib.parse import urlunsplit


def generate_pagination_links_get(request, params):
    pass


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
        print(f"new page for {rel}:", new_page)
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
        print(f"new page for {rel}:", new_page)
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

    print("current page:", page)
    print("total pages:", total_pages)

    url = post_url(request.url)
    links = [
        post_link(rel=rel, url=url, page=page, total_pages=total_pages, limit=limit)
        for rel in ["prev", "self", "next"]
    ]
    print("links:", links)
    return [link for link in links if link]

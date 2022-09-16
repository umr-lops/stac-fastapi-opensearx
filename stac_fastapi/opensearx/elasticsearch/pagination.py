def generate_get_pagination_links(url, *, token):
    # to generate pagination links, we need:
    # - the url
    # - the request params
    # - the next token
    if token is None:
        return []

    new_url = url.replace_query_params(token=token)

    next_link = {
        "rel": "next",
        "href": str(new_url),
        "method": "GET",
    }

    return [next_link]


def generate_post_pagination_links(url, *, token):
    if token is None:
        return []

    next_link = {
        "rel": "next",
        "href": str(url),
        "method": "POST",
        "body": {
            "token": token,
        },
        "merge": True,
    }

    return [next_link]

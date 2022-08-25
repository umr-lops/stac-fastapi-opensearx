import re
from urllib.parse import urlencode

import pytest
from hypothesis import given, note
from hypothesis import strategies as st
from stac_fastapi.types import errors, search

from stac_fastapi.opensearx.webapi import dialects

methods = {
    "GET": search.BaseSearchGetRequest,
    "POST": search.BaseSearchPostRequest,
}
models = st.sampled_from(sorted(methods)).map(methods.get)

collections = st.lists(st.text()) | st.none()

ids = st.lists(st.text()) | st.none()


@st.composite
def bbox(draw):
    lat_values = st.floats(min_value=-90, max_value=90)
    lon_values = st.floats(min_value=-180, max_value=180)

    return draw(
        (
            st.tuples(lon_values, lat_values, lon_values, lat_values)
            .map(list)
            .filter(lambda b: b[0] < b[2] and b[1] < b[3])
        )
        | st.none()
    )


def format_datetime(d):
    if d == "..":
        return d
    return f"{d:%04Y-%m-%dT%H:%M:%SZ}"


datetime = (
    st.datetimes().map(format_datetime)
    | (
        st.tuples(st.just("..") | st.datetimes(), st.just("..") | st.datetimes())
        .filter(lambda t: not (t[0] == ".." and t[1] == ".."))
        .filter(lambda t: t[0] == ".." or t[1] == ".." or t[0] < t[1])
        .map(lambda t: "/".join(format_datetime(d) for d in t))
    )
    # | st.none()  # stac_fastapi.types.search.BasePostRequest seems to reject none datetimes
)

limit = st.integers(min_value=1, max_value=10000)


@st.composite
def search_request(draw):
    model = draw(models)
    collections_ = draw(collections)
    ids_ = draw(ids)
    bbox_ = draw(bbox())
    datetime_ = draw(datetime)
    limit_ = draw(limit)

    note(f"model: {model}")
    note(f"collections: {collections_}")
    note(f"ids: {ids_}")
    note(f"bbox: {bbox_}")
    note(f"datetime: {datetime_}")
    note(f"limit: {limit_}")

    if issubclass(model, search.BaseSearchGetRequest):
        collections_ = ",".join(collections_) if collections_ is not None else None
        ids_ = ",".join(ids_) if ids_ is not None else None
        bbox_ = ",".join(str(f) for f in bbox_) if bbox_ is not None else None

    return model(
        collections=collections_,
        ids=ids_,
        bbox=bbox_,
        datetime=datetime_,
        limit=limit_,
    )


@st.composite
def additional_information(draw):
    return {"page": draw(st.integers(min_value=1))}


def is_int(obj):
    return isinstance(obj, int) or (isinstance(obj, str) and obj.isdecimal())


number_re = r"-?\d+(?:\.\d+(?:[eE]-?\d+)?)?"
bbox_re = re.compile(rf"{number_re}(?:,{number_re}){{3}}")
time_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


@given(search_request(), additional_information())
def test_dialect_ifremer(r, a):
    if not r.collections or len(r.collections) > 1:
        with pytest.raises(errors.InvalidQueryParameter):
            dialects.translate_request_ifremer(r, a)
        return

    params = dialects.translate_request_ifremer(r, a)

    valid_keys = ["datasetId", "startPage", "count", "timeStart", "timeEnd", "geoBox"]

    assert isinstance(params, dict) and all([key in valid_keys for key in params])
    assert "datasetId" in params

    assert "startPage" in params and is_int(params["startPage"])
    assert "count" in params and is_int(params["count"])

    if "geoBox" in params:
        assert bbox_re.match(params["geoBox"])

    if "timeStart" in params:
        assert time_re.match(params["timeStart"])
    if "timeEnd" in params:
        assert time_re.match(params["timeEnd"])

    query = urlencode(params)
    assert query

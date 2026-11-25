from pydantic import HttpUrl, TypeAdapter, ValidationError

_http_url = TypeAdapter(HttpUrl)


def validate_link(value: str) -> str:
    """Accept only http(s) URLs, kept as plain strings"""
    try:
        return str(_http_url.validate_python(value))
    except ValidationError as e:
        raise ValueError("Link must be an http(s) URL") from e

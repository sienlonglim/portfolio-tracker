from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_SQL_DIR = Path(__file__).parent


def _sql_literal(value: str) -> str:
    """Render a Python string as a safely-escaped SQL string literal."""
    return "'" + value.replace("'", "''") + "'"

_JINJA_ENV = Environment(
    loader=FileSystemLoader(str(_SQL_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_JINJA_ENV.filters["sqllit"] = _sql_literal


def render_sql(template_name: str, **params) -> str:
    return _JINJA_ENV.get_template(template_name).render(**params)

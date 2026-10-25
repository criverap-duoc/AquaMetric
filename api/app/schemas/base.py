"""Base model for the public JSON contract."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """camelCase on the wire, snake_case in Python: one shared convention with TerraPlan."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class StrictCamelModel(CamelModel):
    """Input contract: unknown fields are rejected instead of silently dropped.

    A TerraPlan that starts sending `parameter` instead of `parameterCode` must get a 400,
    not a batch of rows with missing data.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        extra="forbid",
    )

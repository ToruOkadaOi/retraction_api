"""Request limits shared by HTTP routes and MCP tool schemas."""

from typing import Annotated

from pydantic import Field, StringConstraints

MAX_BATCH_IDENTIFIERS = 200
SearchText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
NameText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=300)]
FilterText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
DOIText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048)]
BatchDOI = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)]
BatchPMID = Annotated[int, Field(ge=-(2**63), le=2**63 - 1)]
BatchDOIs = Annotated[list[BatchDOI], Field(max_length=MAX_BATCH_IDENTIFIERS)]
BatchPMIDs = Annotated[list[BatchPMID], Field(max_length=MAX_BATCH_IDENTIFIERS)]

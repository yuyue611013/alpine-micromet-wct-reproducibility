"""Fixed-round production fitting; never used by the public default entrypoint."""

from __future__ import annotations

import math
from collections.abc import Iterable

from wce.contracts.scientific import ContractError


def production_rounds(outer_selected_rounds: Iterable[int]) -> int:
    values = sorted(int(value) for value in outer_selected_rounds)
    if len(values) != 5 or values[0] < 1:
        raise ContractError("FIVE_POSITIVE_OUTER_ROUNDS_REQUIRED")
    return values[2]


def production_contract() -> dict:
    return {
        "selection": "median_of_five_outer_selected_rounds",
        "validation_dataset": None,
        "early_stopping": False,
        "external_execution_in_public_repository": False,
        "full_grid_generation": False,
    }


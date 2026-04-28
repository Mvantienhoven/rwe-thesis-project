"""
Patch Calliope 0.6.x async prod/con set construction.

Calliope currently adds storage/transmission technologies to
`loc_techs_asynchronous_prod_con` when the key
`force_asynchronous_prod_con` exists, even if it is set to `false`.
That behavior creates unnecessary binary variables (`prod_con_switch`).

This patch keeps technologies in the async set only when the flag is
truthy.
"""

from __future__ import annotations

import calliope.preprocess.sets as calliope_sets


_ORIGINAL_GENERATE_LOC_TECH_SETS = calliope_sets.generate_loc_tech_sets


def _force_async_enabled(config) -> bool:
    constraints = getattr(config, "constraints", None)
    if constraints is None:
        return False
    return bool(constraints.get("force_asynchronous_prod_con", False))


def _patched_generate_loc_tech_sets(model_run, simple_sets):
    sets = _ORIGINAL_GENERATE_LOC_TECH_SETS(model_run, simple_sets)

    loc_techs_non_transmission_config = {
        loc_tech: model_run.get_key("locations.{}.techs.{}".format(*loc_tech.split("::")))
        for loc_tech in sets.loc_techs_non_transmission
    }
    loc_techs_transmission_config = {
        loc_tech: model_run.get_key(
            "locations.{loc_from}.links.{loc_to}.techs.{tech}".format(
                **calliope_sets.split_loc_techs_transmission(loc_tech)
            )
        )
        for loc_tech in sets.loc_techs_transmission
    }

    loc_techs_storage_async = {
        loc_tech
        for loc_tech in sets.loc_techs_store
        if _force_async_enabled(loc_techs_non_transmission_config[loc_tech])
    }
    loc_techs_transmission_async = {
        loc_tech
        for loc_tech in sets.loc_techs_transmission
        if _force_async_enabled(loc_techs_transmission_config[loc_tech])
    }

    sets.loc_techs_asynchronous_prod_con = (
        loc_techs_storage_async | loc_techs_transmission_async
    )
    return sets


def apply_async_binary_patch() -> bool:
    if calliope_sets.generate_loc_tech_sets is _patched_generate_loc_tech_sets:
        return False

    calliope_sets.generate_loc_tech_sets = _patched_generate_loc_tech_sets
    return True


"""Immutable configuration resources for MechWorld-PG."""

from .physics_profiles import (
    PhysicsProfile,
    PhysicsProfileError,
    ProfileMixingError,
    available_profile_ids,
    load_physics_profile,
)

__all__ = [
    "PhysicsProfile",
    "PhysicsProfileError",
    "ProfileMixingError",
    "available_profile_ids",
    "load_physics_profile",
]


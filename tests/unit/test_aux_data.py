"""Unit tests for pipeuhr.aux_data — physical constants and lookup tables.

AuxData backs the head-loss (Swamee-Jain) and cavitation (NPSH) formulas in
GlobalOptimization.evaluate(). Wrong lookup values would silently produce
wrong velocities/pressures throughout the solver without any test noticing,
since these are simple dict lookups with no other layer double-checking
them.
"""

from __future__ import annotations

import pytest

from pipeuhr.aux_data import AuxData

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
	"material, expected_epsilon",
	[("Aço", 0.0001), ("Concreto", 0.0003)],
)
def test_roughness_returns_expected_epsilon(material, expected_epsilon):
	"""roughness() must return the exact pipe-wall roughness (m) per
	material, since it directly scales the Swamee-Jain friction factor used
	for every head-loss calculation.
	"""
	# Arrange / Act
	value = AuxData.roughness(material)

	# Assert
	assert value == expected_epsilon


@pytest.mark.parametrize(
	"alias, canonical",
	[("aço", "Aço"), ("ACO", "Aço"), ("concreto", "Concreto"), ("CONCRETO", "Concreto")],
)
def test_normalize_material_accepts_common_aliases(alias, canonical):
	"""Material names typed into the web form (accents/case may vary) must
	normalize to the same canonical key as the enum value, otherwise a
	KeyError would surface deep inside the solver instead of at input time.
	"""
	# Arrange
	roughness_alias = AuxData.roughness(alias)

	# Act
	roughness_canonical = AuxData.roughness(canonical)

	# Assert
	assert roughness_alias == roughness_canonical


def test_equivalent_length_factor_returns_none_for_straight_segment():
	"""'Reto' (straight) segments carry their own explicit length, so the
	Le/Dh lookup must return None to signal 'use the straight length
	instead' to the head-loss calculation in GlobalOptimization.evaluate().
	"""
	# Arrange / Act / Assert
	assert AuxData.equivalent_length_factor("Reto") is None


def test_pump_phi_known_pump_type():
	"""pump_phi() must return the documented phi factor for a centrifugal
	pump, since it directly scales the NPSH-required (cavitation) formula.
	"""
	# Arrange / Act / Assert
	assert AuxData.pump_phi("Centrífuga") == 0.0011


def test_roughness_unknown_material_raises_keyerror():
	"""An unrecognized material must fail loudly (KeyError) rather than
	silently defaulting to an arbitrary roughness value that would corrupt
	downstream head-loss results.
	"""
	# Arrange / Act / Assert
	with pytest.raises(KeyError):
		AuxData.roughness("Titanium")

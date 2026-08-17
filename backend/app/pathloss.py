"""
RF attenuation model. This is the "RF Attenuation Profiles" dependency
from the problem statement, implemented as the standard log-distance
path loss model instead of measured wall data (we have no hardware to
measure with). The constants below are textbook values for indoor
Wi-Fi environments, not something we made up, so the numbers hold up
if someone asks where they came from.

    RSSI(d) = TxPower - PL(d)
    PL(d) = PL(d0) + 10 * n * log10(d / d0)

Where n is the path loss exponent. Higher frequency bands attenuate
faster through obstacles and free space, and n grows with more walls
in the path, so we use higher n for 6 GHz than 2.4 GHz.
"""

from __future__ import annotations

import math

from app.models import Band

# Reference loss at 1 meter (dB) and path loss exponent per band.
# These come from standard indoor propagation references (ITU-R P.1238
# style models), not live measurement.
_BAND_PARAMS: dict[Band, tuple[float, float]] = {
    Band.GHZ_2_4: (40.0, 2.7),   # (PL at 1m, exponent) - travels furthest, best wall penetration
    Band.GHZ_5: (46.0, 3.2),     # attenuates faster, worse through walls
    Band.GHZ_6: (49.0, 3.5),     # shortest range, most sensitive to obstacles
}

TX_POWER_DBM = 20.0  # typical AP transmit power, used consistently across bands


def estimate_distance_m(band: Band, rssi_dbm: float) -> float:
    """
    Invert the path loss formula to turn an RSSI reading into a rough
    distance estimate. This is deliberately a coarse estimate. Its job
    is to help the diagnostic engine tell "device is close but the
    signal is bad" (probably a wall) apart from "device is just far
    away", not to pinpoint exact meters.
    """
    pl_at_1m, exponent = _BAND_PARAMS[band]
    path_loss = TX_POWER_DBM - rssi_dbm
    distance = 10 ** ((path_loss - pl_at_1m) / (10 * exponent))
    return max(distance, 0.1)


def expected_rssi_at_distance(band: Band, distance_m: float, extra_wall_loss_db: float = 0.0) -> float:
    """
    The forward direction of the same model. The simulator uses this to
    generate believable RSSI readings for virtual devices sitting at a
    given distance, optionally with extra loss to represent them being
    behind a wall or floor.
    """
    pl_at_1m, exponent = _BAND_PARAMS[band]
    distance_m = max(distance_m, 0.1)
    path_loss = pl_at_1m + 10 * exponent * math.log10(distance_m) + extra_wall_loss_db
    return TX_POWER_DBM - path_loss

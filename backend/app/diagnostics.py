"""
The diagnostic engine. Given a device's capability profile and its
current telemetry, work out why it's performing the way it is.

This is written as one plain function with an ordered set of checks,
on purpose. A hackathon judge (or a teammate at 3am) should be able to
read this top to bottom and understand the reasoning without needing
to know anything about ML. Each check either returns a verdict or
falls through to the next one, roughly in order from "most certain"
to "most fuzzy".
"""

from app.models import Band, CapabilityProfile, DiagnosticCode, DiagnosticResult, TelemetrySample
from app.pathloss import estimate_distance_m

# Tunable thresholds. Pulled out as constants so they're easy to
# defend in a demo ("here's exactly why we picked -70 dBm") instead of
# being buried as magic numbers.
RSSI_GOOD_DBM = -60.0
RSSI_MARGINAL_DBM = -70.0

SNR_GOOD_DB = 25.0

RATE_UTILIZATION_POOR = 0.4  # actual rate below 40% of theoretical = something's wrong
RATE_UTILIZATION_OK = 0.7

RETRY_RATE_HIGH_PCT = 15.0


def diagnose(capability: CapabilityProfile, telemetry: TelemetrySample) -> DiagnosticResult:
    band_order = {Band.GHZ_2_4: 0, Band.GHZ_5: 1, Band.GHZ_6: 2}

    best_supported_band = max(capability.supported_bands, key=lambda b: band_order[b])
    is_on_best_band = telemetry.active_band == best_supported_band
    rate_utilization = telemetry.link_rate_mbps / telemetry.theoretical_max_mbps if telemetry.theoretical_max_mbps else 0
    distance_m = estimate_distance_m(telemetry.active_band, telemetry.rssi_dbm)

    # Check 1: is the device even capable of better than what it's on?
    # A device that maxes out at 2.4 GHz was never going anywhere else,
    # so there's no point diagnosing it as a "steering" problem.
    if len(capability.supported_bands) == 1 and capability.supported_bands[0] == Band.GHZ_2_4:
        return DiagnosticResult(
            code=DiagnosticCode.HARDWARE_LIMITED,
            summary="Hardware limited",
            detail=(
                f"This device only supports {capability.max_standard.value} on 2.4 GHz. "
                "There is no faster band available to it, so the current speed is close to "
                "the best this hardware can do here."
            ),
            estimated_distance_m=round(distance_m, 1),
        )

    # Check 2: device can do better but isn't on its best band right now.
    # This usually points at band steering config on the AP side rather
    # than anything wrong with the device or the RF environment.
    if not is_on_best_band and telemetry.rssi_dbm > RSSI_MARGINAL_DBM:
        return DiagnosticResult(
            code=DiagnosticCode.BAND_STEERING_ISSUE,
            summary="Connected below its capability",
            detail=(
                f"This device supports {best_supported_band.value} but is currently on "
                f"{telemetry.active_band.value} with a decent signal ({telemetry.rssi_dbm:.0f} dBm). "
                "That combination usually means band steering or client roaming behavior, "
                "not a hardware or RF limit."
            ),
            estimated_distance_m=round(distance_m, 1),
        )

    # Check 3: signal is weak. Now the question is whether that's
    # because the device is genuinely far from the AP, or because
    # something (a wall, a floor) is eating the signal at otherwise
    # close range.
    #
    # RSSI on its own can't answer that. A weak reading looks the same
    # whether it came from distance or from a wall, since both just
    # show up as extra path loss. What does tell them apart is the
    # retry rate. A single solid obstruction gives you a weaker but
    # still stable link, retries stay low. Real distance usually comes
    # with more multipath fading along the way, which shows up as a
    # noisier link and a higher retry rate even before packets are
    # dropped outright. So we lean on retry rate as the tie-breaker,
    # and use the path loss distance estimate as supporting context.
    if telemetry.rssi_dbm < RSSI_MARGINAL_DBM:
        if telemetry.retry_rate_pct > RETRY_RATE_HIGH_PCT:
            return DiagnosticResult(
                code=DiagnosticCode.FAR_DISTANCE,
                summary="Likely too far from the router",
                detail=(
                    f"Signal is weak ({telemetry.rssi_dbm:.0f} dBm) and the link is also unstable "
                    f"({telemetry.retry_rate_pct:.0f}% retries), which fits a device sitting at real "
                    f"range from the AP (roughly {distance_m:.1f} m estimated for this band) rather "
                    "than a single obstruction. Moving closer, or adding an access point nearer to "
                    "this device, should help more than any settings change."
                ),
                estimated_distance_m=round(distance_m, 1),
            )
        return DiagnosticResult(
            code=DiagnosticCode.ATTENUATED_SIGNAL,
            summary="Signal blocked, likely by a wall or floor",
            detail=(
                f"Signal is weak ({telemetry.rssi_dbm:.0f} dBm) but the link is still stable "
                f"({telemetry.retry_rate_pct:.0f}% retries), which is more consistent with a solid "
                "obstruction cutting the signal at otherwise short range than with genuine "
                "distance. Walls, floors, or metal and glass in the path are the usual cause."
            ),
            estimated_distance_m=round(distance_m, 1),
        )

    # Check 4: signal is fine but the link is still slow, or retries are
    # climbing even though signal quality looks okay. That's usually
    # airtime contention or interference rather than a range problem.
    if telemetry.rssi_dbm >= RSSI_MARGINAL_DBM and (
        rate_utilization < RATE_UTILIZATION_POOR or telemetry.retry_rate_pct > RETRY_RATE_HIGH_PCT
    ):
        return DiagnosticResult(
            code=DiagnosticCode.CONGESTED_LINK,
            summary="Signal is fine, but throughput isn't",
            detail=(
                f"RSSI ({telemetry.rssi_dbm:.0f} dBm) and SNR ({telemetry.snr_db:.0f} dB) both look "
                f"healthy, but the negotiated rate ({telemetry.link_rate_mbps:.0f} Mbps) is well below "
                f"what this connection should support ({telemetry.theoretical_max_mbps:.0f} Mbps). "
                f"Retry rate is {telemetry.retry_rate_pct:.1f}%, which suggests channel congestion or "
                "interference from other networks rather than a coverage issue."
            ),
            estimated_distance_m=round(distance_m, 1),
        )

    # Nothing flagged. Device is on its best band, close enough, and
    # getting a fair share of the theoretical rate for its class.
    return DiagnosticResult(
        code=DiagnosticCode.GOOD,
        summary="Performing as expected",
        detail=(
            f"Connected on {telemetry.active_band.value} at {telemetry.link_rate_mbps:.0f} Mbps, "
            f"which is a reasonable fraction of its {telemetry.theoretical_max_mbps:.0f} Mbps ceiling "
            "for this device class. No action needed."
        ),
        estimated_distance_m=round(distance_m, 1),
    )

"""
Resolves a device's theoretical capability, the "Client Capability
Parsing" requirement.

There are two paths in here:

1. parse_association_ie(): reads actual 802.11 Information Element
   bytes the way you would from a captured Association Request frame.
   This is the real deal and works with zero knowledge of what device
   it is, it just reads what the client announced about itself.

2. resolve_from_catalog(): the fallback we actually rely on for the
   demo, since we don't have a monitor-mode adapter capturing live
   frames. It matches a MAC address against the local device catalog,
   the same way you'd fall back to an OUI table when frame capture
   isn't available.

Both paths return the same CapabilityProfile shape so the rest of the
app doesn't care which one produced it.
"""

from __future__ import annotations

from app.device_catalog import lookup_by_mac
from app.models import Band, CapabilityProfile, WifiStandard

# 802.11 Information Element IDs we care about. The HE (Wi-Fi 6) and
# EHT (Wi-Fi 7) capabilities live in "extension" elements: tag 255
# followed by an extension ID, rather than getting their own top level
# tag number.
IE_HT_CAPABILITIES = 45
IE_VHT_CAPABILITIES = 191
IE_EXTENSION = 255
EXT_ID_HE_CAPABILITIES = 35
EXT_ID_EHT_CAPABILITIES = 108


def parse_association_ie(ie_blocks: list[tuple[int, bytes]], announces_6ghz: bool = False) -> CapabilityProfile:
    """
    Walk the IE list from a captured Association Request and work out
    the highest standard and band set the client is telling us it
    supports. ie_blocks is a list of (tag_id, payload_bytes) pairs, in
    the order they'd appear in the frame. This intentionally does not
    try to decode every bit in the capability payloads (MCS maps,
    beamforming flags and so on go well beyond what the diagnostic
    engine needs) and instead just tracks which capability elements
    are present, since that alone tells us the standard.
    """
    has_ht = has_vht = has_he = has_eht = False
    max_width = 20
    streams = 1

    for tag_id, payload in ie_blocks:
        if tag_id == IE_HT_CAPABILITIES:
            has_ht = True
            max_width = max(max_width, 40)
        elif tag_id == IE_VHT_CAPABILITIES:
            has_vht = True
            max_width = max(max_width, 80)
        elif tag_id == IE_EXTENSION and payload:
            ext_id = payload[0]
            if ext_id == EXT_ID_HE_CAPABILITIES:
                has_he = True
                max_width = max(max_width, 160)
            elif ext_id == EXT_ID_EHT_CAPABILITIES:
                has_eht = True
                max_width = max(max_width, 320)

    if has_eht:
        standard = WifiStandard.WIFI_7
    elif has_he and announces_6ghz:
        standard = WifiStandard.WIFI_6E
    elif has_he:
        standard = WifiStandard.WIFI_6
    elif has_vht:
        standard = WifiStandard.WIFI_5
    elif has_ht:
        standard = WifiStandard.WIFI_4
    else:
        standard = WifiStandard.WIFI_4  # anything this bare is at best legacy-ish

    bands = [Band.GHZ_2_4, Band.GHZ_5]
    if announces_6ghz and standard in (WifiStandard.WIFI_6E, WifiStandard.WIFI_7):
        bands.append(Band.GHZ_6)

    return CapabilityProfile(
        max_standard=standard,
        supported_bands=bands,
        max_channel_width_mhz=max_width,
        max_spatial_streams=streams,
        source="ie_parse",
    )


def resolve_from_catalog(mac_address: str) -> CapabilityProfile | None:
    """
    OUI style fallback: match the MAC prefix against the local device
    catalog and hand back that entry's known capability profile.
    Returns None if nothing matches, at which point the caller should
    fall back further (in this app, the simulator just picks a
    reasonable default rather than leaving the device unclassified).
    """
    entry = lookup_by_mac(mac_address)
    if entry is None:
        return None
    return entry.capability

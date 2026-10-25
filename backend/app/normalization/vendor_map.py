"""
Vendor detection heuristics — maps sanitizer VendorType values to
the parser strategies / TextFSM template keys used downstream.
"""
from app.ingestion.sanitizer import VendorType

# Maps VendorType → TextFSM template filename stem
VENDOR_TEMPLATE_MAP: dict[str, str] = {
    VendorType.CISCO_IOS: "cisco_ios_show_run",
    VendorType.CISCO_NXOS: "cisco_ios_show_run",   # NX-OS shares most IOS patterns
    VendorType.PALOALTO: "paloalto_show_config",
    VendorType.JUNOS: "junos_show_config",
    VendorType.SONIC: "sonic_config",
    VendorType.UNKNOWN: None,
}

# Maps VendorType → Genie platform identifier
VENDOR_GENIE_PLATFORM_MAP: dict[str, str] = {
    VendorType.CISCO_IOS: "ios",
    VendorType.CISCO_NXOS: "nxos",
    VendorType.PALOALTO: None,     # Not supported by Genie
    VendorType.JUNOS: "junos",
    VendorType.SONIC: None,        # Not supported by Genie
    VendorType.UNKNOWN: None,
}

# Maps VendorType → display label
VENDOR_DISPLAY_NAMES: dict[str, str] = {
    VendorType.CISCO_IOS: "Cisco IOS",
    VendorType.CISCO_NXOS: "Cisco NX-OS",
    VendorType.PALOALTO: "Palo Alto PAN-OS",
    VendorType.JUNOS: "Juniper JunOS",
    VendorType.SONIC: "SONiC",
    VendorType.UNKNOWN: "Unknown",
}


def get_template_key(vendor: str) -> str | None:
    return VENDOR_TEMPLATE_MAP.get(vendor)


def get_genie_platform(vendor: str) -> str | None:
    return VENDOR_GENIE_PLATFORM_MAP.get(vendor)

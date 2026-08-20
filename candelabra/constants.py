TYPE_MAP = {
    "QR Code Link": "QRCODE",
    "Item": "ITEM",
}

TYPE_MAP_REVERSE = {v: k for k, v in TYPE_MAP.items()}

def set_bootinfo(bootinfo):
    bootinfo.candelabra_type_map = TYPE_MAP
    bootinfo.candelabra_type_map_reverse = TYPE_MAP_REVERSE
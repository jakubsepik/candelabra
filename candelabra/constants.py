TYPE_MAP = {
    "Purchase Invoice": "INV",
    "Purchase Receipt": "REC",
    "Item": "ITEM",
}

TYPE_MAP_REVERSE = {v: k for k, v in TYPE_MAP.items()}

def set_bootinfo(bootinfo):
    bootinfo.candelabra_type_map = TYPE_MAP
    bootinfo.candelabra_type_map_reverse = TYPE_MAP_REVERSE
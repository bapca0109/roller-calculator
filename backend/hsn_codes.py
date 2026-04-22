"""HSN ↔ GST rate lookup table for the belt-conveyor manufacturing stock register.

Keyed by HSN prefix (4, 6 or 8 digits). On lookup we try the full code first, then
first 6 digits, then first 4 digits. Falls back to 18% (standard GST in India for
most industrial goods) if no match.

Rates below reflect the common post-GST 2.0 (Jan 2025) slabs for India. Update as
the council revises rates — central control via this single table.
"""

HSN_GST_MAP = {
    # Iron & steel
    "7214": 18.0,   # Bars & rods, hot-rolled (shafts)
    "7228": 18.0,   # Alloy steel bars (EN-8 etc.)
    "7304": 18.0,   # Seamless steel tubes
    "7305": 18.0,   # Large-dia welded steel tubes
    "7306": 18.0,   # ERW / welded steel tubes (pipes)
    "7307": 18.0,   # Pipe fittings
    "7308": 18.0,   # Structural steel (housings, brackets)
    "7318": 18.0,   # Fasteners (bolts, screws, nuts, washers, rivets)
    "7320": 18.0,   # Springs
    "7324": 18.0,   # Sanitary ware — not typical
    "7326": 18.0,   # Other articles of iron/steel (housings, misc)

    # Bearings & mechanical parts
    "8482": 18.0,   # Ball / roller bearings
    "8483": 18.0,   # Transmission shafts, couplings, pulleys
    "8484": 18.0,   # Gaskets, seals, mechanical sealing

    # Rubber / plastics / polymers
    "4016": 18.0,   # Vulcanised rubber articles (rubber rings, covers)
    "3916": 18.0,   # Plastic profiles / rods (MC-Nylon, HDPE)
    "3926": 18.0,   # Misc plastic articles (end plates, inserts)

    # Grease, paint, chemicals
    "2710": 18.0,   # Petroleum / lubricating oils
    "3403": 18.0,   # Lubricating preparations
    "3404": 18.0,   # Waxes / greases (EP-2 etc.)
    "3208": 18.0,   # Paints (synthetic / oil-based)
    "3209": 18.0,   # Paints (water-based)
    "3814": 18.0,   # Thinners / solvents

    # Electrical (uncommon but possible)
    "8544": 18.0,   # Wires & cables
    "8536": 18.0,   # Switches, connectors
}


def gst_for_hsn(hsn) -> float:
    """Return GST% for an HSN code. Tries the full code, then first 6, then first 4 digits.
    Falls back to 18.0 when unmatched.
    """
    if hsn is None:
        return 18.0
    h = str(hsn).strip().replace(" ", "")
    if not h:
        return 18.0
    if h in HSN_GST_MAP:
        return HSN_GST_MAP[h]
    if len(h) >= 6 and h[:6] in HSN_GST_MAP:
        return HSN_GST_MAP[h[:6]]
    if len(h) >= 4 and h[:4] in HSN_GST_MAP:
        return HSN_GST_MAP[h[:4]]
    return 18.0

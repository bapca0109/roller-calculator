# IS-9295:2024 - Standard Pipe Diameters (mm) - UPDATED
PIPE_DIAMETERS = [60.8, 76.1, 88.9, 114.3, 127.0, 139.7, 152.4, 159.0, 165.0]

# Pipe diameter display codes for product codes (actual OD -> display code)
# Based on industry standard notation
PIPE_DIAMETER_CODES = {
    60.8: 60,
    76.1: 76,
    88.9: 89,    # User requested 89 instead of 88
    114.3: 114,
    127.0: 127,
    139.7: 139,  # User requested 139 instead of 140
    152.4: 152,
    159.0: 159,
    165.0: 165
}

def get_pipe_code(pipe_dia):
    """Get display code for pipe diameter"""
    return PIPE_DIAMETER_CODES.get(pipe_dia, int(pipe_dia))

# Shaft End Type Extensions (mm)
# These define how much the shaft extends beyond the pipe
SHAFT_END_EXTENSIONS = {
    "A": 26,  # Type A: +26mm
    "B": 36,  # Type B: +36mm (default)
    "C": 56,  # Type C: +56mm
}

def get_shaft_length(pipe_length: float, shaft_end_type: str = "B", custom_shaft_length: int = None) -> float:
    """
    Calculate shaft length based on pipe length and shaft end type.
    
    Args:
        pipe_length: Length of the pipe in mm
        shaft_end_type: Type A (+26mm), B (+36mm), C (+56mm), or 'custom'
        custom_shaft_length: Total shaft length in mm (only used if shaft_end_type is 'custom')
    
    Returns:
        Total shaft length in mm
    """
    if shaft_end_type == "custom" and custom_shaft_length is not None:
        # User provides total shaft length directly
        return custom_shaft_length
    
    extension = SHAFT_END_EXTENSIONS.get(shaft_end_type.upper(), 36)  # Default to Type B
    return pipe_length + extension

# Shaft Diameters (mm)
SHAFT_DIAMETERS = [20, 25, 30, 35, 40, 45, 50]

# Bearing Selection based on Shaft Diameter - UPDATED with 420204 series
BEARING_OPTIONS = {
    20: ["6204", "6304", "420204"],
    25: ["6205", "6305", "420205"],
    30: ["6206", "6306", "420206"],
    35: ["6207", "6307"],
    40: ["6208", "6308"],
    45: ["6209", "6309"],
    50: ["6210", "6310"]
}

# Bearing Outside Diameters (mm) for housing selection - UPDATED
BEARING_OD = {
    "6204": 47, "6304": 52, "420204": 47,
    "6205": 52, "6305": 62, "420205": 52,
    "6206": 62, "6306": 72, "420206": 62,
    "6207": 72, "6307": 80,
    "6208": 80, "6308": 90,
    "6209": 85, "6309": 100,
    "6210": 90, "6310": 110
}

# Bearing Costs by Make (INR per piece) - ACTUAL PRICES
BEARING_COSTS = {
    # 20mm shaft bearings
    "6204": {"china": 20, "skf": 70, "fag": 70, "timken": 61},
    "6304": {"china": 30, "skf": 97, "fag": 89, "timken": 85},
    "420204": {"fag": 54},  # FAG only
    
    # 25mm shaft bearings
    "6205": {"china": 26, "skf": 84, "fag": 70, "timken": 70},  # Timken TBD, using FAG as placeholder
    "6305": {"skf": 178, "fag": 124, "timken": 124},  # China NA, Timken TBD
    "420205": {"fag": 60},  # FAG only
    
    # 30mm shaft bearings
    "6206": {"china": 40, "skf": 135, "fag": 105, "timken": 105},  # Timken TBD, using FAG as placeholder
    "6306": {"skf": 216, "fag": 177, "timken": 177},  # China NA, Timken TBD
    "420206": {"fag": 83},  # FAG only
    
    # 35mm shaft bearings
    "6207": {"skf": 205, "fag": 190, "timken": 190},  # China NA, Timken TBD
    "6307": {"skf": 342, "fag": 225, "timken": 216},
    
    # 40mm shaft bearings
    "6208": {"skf": 264, "fag": 210, "timken": 210},  # China NA, Timken TBD
    "6308": {"skf": 320, "fag": 275, "timken": 275},  # China NA, Timken TBD
    
    # 45mm shaft bearings
    "6209": {"skf": 320, "fag": 270, "timken": 270},  # China & Timken TBD
    "6309": {"skf": 520, "fag": 400, "timken": 400},  # China NA, FAG & Timken TBD
    
    # 50mm shaft bearings
    "6210": {"skf": 515, "fag": 400, "timken": 400},  # China, FAG & Timken TBD
    "6310": {"skf": 1046, "fag": 800, "timken": 800},  # China, FAG & Timken TBD
}

# Housing Selection: pipe_dia -> [(housing_dia, [bearing_bores])] - UPDATED
HOUSING_OPTIONS = {
    60.8: [(56, [47])],
    76.1: [(72, [47, 52])],
    88.9: [(84, [47, 52, 62])],
    114.3: [(108, [47, 52, 62, 72])],
    127.0: [(121, [47, 52, 62, 72, 80])],
    139.7: [(133, [52, 62, 72, 80, 90])],
    152.4: [(146, [52, 62, 72, 80, 90])],
    159.0: [(153, [62, 72, 80, 90, 100])],
    165.0: [(159, [52, 62, 72, 80, 90, 100])]
}

# Housing Costs (INR per piece) - ACTUAL PRICES
HOUSING_COSTS = {
    "56/47": 21,
    "72/47": 22, "72/52": 24,
    "84/47": 23, "84/52": 25, "84/62": 28,
    "108/47": 33, "108/52": 35, "108/62": 45, "108/72": 50,
    "121/47": 42, "121/52": 45, "121/62": 50, "121/72": 57, "121/80": 68,
    "133/52": 50, "133/62": 55, "133/72": 60, "133/80": 65, "133/90": 70,
    "146/52": 57, "146/62": 60, "146/72": 65, "146/80": 70, "146/90": 80,
    "153/62": 60, "153/72": 65, "153/80": 70, "153/90": 80, "153/100": 90,
    "159/52": 65, "159/62": 70, "159/72": 75, "159/80": 80, "159/90": 100, "159/100": 120
}

# IS-8598:2019 - Standard Roller/Pipe Lengths by Belt Width (mm)
# For 3-roll troughed carrying idlers
ROLLER_LENGTHS = {
    500: [200],
    650: [250],
    800: [315],
    1000: [380],
    1200: [465],
    1400: [530],
    1600: [600],
    1800: [670],
    2000: [750]
}

# IS-8598:2019 - Return Idler Lengths (single roll, flat)
# First value = single piece, second value = 2-piece per set (each roller length)
RETURN_ROLLER_LENGTHS = {
    500: [600, 250],     # Single: 600mm, 2-piece: 250mm each
    650: [750, 380],     # Single: 750mm, 2-piece: 380mm each
    800: [950, 465],     # Single: 950mm, 2-piece: 465mm each
    1000: [1150, 600],   # Single: 1150mm, 2-piece: 600mm each
    1200: [1400, 700],   # Single: 1400mm, 2-piece: 700mm each
    1400: [1600, 800],   # Single: 1600mm, 2-piece: 800mm each
    1600: [1800, 900],   # Single: 1800mm, 2-piece: 900mm each
    1800: [2000, 1000],  # Single: 2000mm, 2-piece: 1000mm each
    2000: [2200, 1100]   # Single: 2200mm, 2-piece: 1100mm each
}

# Pipe Weight per meter (kg/m) - IS-9295 Light/Medium/Heavy Classes
# Type A = Light, Type B = Medium, Type C = Heavy
# Pipe Weight per meter (kg/m) - Calculated using formula:
# Weight (kg/m) = π/4 × (OD² - ID²) × ρ / 1,000,000
# Where: ID = OD - (2 × Wall Thickness), ρ = 7.85 kg/dm³ (steel density)

PIPE_WEIGHT_PER_METER = {
    60.8: {  # 60mm OD per IS-9295
        "A": 4.14,   # Light: 2.90mm thickness
        "B": 5.14,   # Medium: 3.65mm thickness
        "C": 6.21    # Heavy: 4.47mm thickness
    },
    76.1: {  # 76mm OD per IS-9295
        "A": 5.84,   # Light: 3.25mm thickness
        "B": 6.52,   # Medium: 3.65mm thickness
        "C": 7.90    # Heavy: 4.47mm thickness
    },
    88.9: {  # 88mm OD per IS-9295
        "A": 6.86,   # Light: 3.25mm thickness
        "B": 8.47,   # Medium: 4.05mm thickness
        "C": 10.05   # Heavy: 4.85mm thickness
    },
    114.3: {  # 114mm OD per IS-9295
        "A": 9.96,   # Light: 3.65mm thickness
        "B": 12.11,  # Medium: 4.47mm thickness
        "C": 14.32   # Heavy: 5.33mm thickness
    },
    127.0: {  # 127mm OD
        "A": 12.13,  # Light: 4.00mm thickness
        "B": 14.61,  # Medium: 4.85mm thickness
        "C": 15.99   # Heavy: 5.33mm thickness
    },
    139.7: {  # 139mm OD
        "A": 13.39,  # Light: 4.00mm thickness
        "B": 16.13,  # Medium: 4.85mm thickness
        "C": 17.66   # Heavy: 5.33mm thickness
    },
    152.4: {  # 152mm OD
        "A": 14.64,  # Light: 4.00mm thickness
        "B": 17.65,  # Medium: 4.85mm thickness
        "C": 19.33   # Heavy: 5.33mm thickness
    },
    159.0: {  # 159mm OD
        "A": 15.29,  # Light: 4.00mm thickness
        "B": 18.44,  # Medium: 4.85mm thickness
        "C": 20.20   # Heavy: 5.33mm thickness
    },
    165.0: {  # 165mm OD
        "A": 15.88,  # Light: 4.00mm thickness
        "B": 19.16,  # Medium: 4.85mm thickness
        "C": 20.99   # Heavy: 5.33mm thickness
    }
}

# Shaft Weight per meter (kg/m) based on diameter
SHAFT_WEIGHT_PER_METER = {
    20: 2.47,
    25: 3.85,
    30: 5.55,
    35: 7.55,
    40: 9.87,
    45: 12.48,
    50: 15.41
}

# Raw Material Costs - ACTUAL PRICES
PIPE_COST_PER_KG = 67  # INR per kg - UNIFORM for all diameters
SHAFT_COST_PER_KG = 62  # INR per kg

# Seal Set Costs (INR per set) - BEARING-SPECIFIC - ACTUAL PRICES
SEAL_COSTS = {
    # 20mm shaft bearings
    "6204": 13,
    "6304": 18,
    "420204": 13,  # Same as 6204
    
    # 25mm shaft bearings
    "6205": 18,
    "6305": 25,
    "420205": 18,  # Same as 6205
    
    # 30mm shaft bearings
    "6206": 25,
    "6306": 40,
    "420206": 25,  # Same as 6206
    
    # 35mm shaft bearings
    "6207": 40,
    "6307": 50,
    
    # 40mm shaft bearings
    "6208": 50,
    "6308": 90,
    
    # 45mm shaft bearings
    "6209": 90,
    "6309": 120,
    
    # 50mm shaft bearings
    "6210": 120,
    "6310": 140
}

# Circlip Costs (INR per piece) - Based on Shaft Diameter - ACTUAL PRICES
# 4 pieces per roller
CIRCLIP_COSTS = {
    20: 1.0,
    25: 1.5,
    30: 2.0,
    35: 2.5,
    40: 3.0,
    45: 10.0,
    50: 12.0
}

# Impact Roller - Rubber Lagging Options
# Format: pipe_dia -> [rubber_dia_options]
RUBBER_LAGGING_OPTIONS = {
    60: [90, 114],
    76: [114, 127, 140],
    89: [127, 140, 152],
    114: [139, 152, 165, 190],
    127: [165, 190],
    139: [165, 190],
    152: [190]
}

# Rubber Ring Costs (INR per ring, 35mm thick) - ACTUAL PRICES
# Format: "pipe/rubber" -> cost_per_ring
RUBBER_RING_COSTS = {
    "60/90": 16,
    "60/114": 20,
    "76/114": 20,
    "76/127": 22,
    "76/140": 30,
    "89/127": 32,
    "89/140": 36,
    "89/152": 42,
    "114/139": 35,
    "114/152": 40,
    "114/165": 47,
    "114/190": 72,
    "127/165": 55,
    "127/190": 68,
    "139/165": 54,
    "139/190": 63,
    "152/190": 65
}

RUBBER_RING_THICKNESS = 35  # mm

# Locking Ring Costs (INR per roller) - For Impact Rollers
# Added to raw material before applying 2.112× formula
LOCKING_RING_COSTS = {
    60: 18,
    76: 20,
    89: 22,
    114: 26,
    127: 28,
    139: 30,
    152: 32,
    159: 34,
    165: 38
}

# GST Configuration
GST_RATE = 18.0  # 18% GST for conveyor rollers
CGST_RATE = 9.0  # Central GST (same state)
SGST_RATE = 9.0  # State GST (same state)
IGST_RATE = 18.0  # Integrated GST (different state)

# Company's state (Gujarat)
COMPANY_STATE_CODE = "24"  # Gujarat state code
COMPANY_PINCODE_PREFIX = "38"  # Gujarat pincodes start with 38

# Indian State Codes based on Pincode prefix (first 2 digits)
PINCODE_STATE_MAP = {
    "11": ("Delhi", "07"),
    "12": ("Haryana", "06"),
    "13": ("Haryana", "06"),
    "14": ("Punjab", "03"),
    "15": ("Punjab", "03"),
    "16": ("Punjab", "03"),
    "17": ("Himachal Pradesh", "02"),
    "18": ("Jammu & Kashmir", "01"),
    "19": ("Jammu & Kashmir", "01"),
    "20": ("Uttar Pradesh", "09"),
    "21": ("Uttar Pradesh", "09"),
    "22": ("Uttar Pradesh", "09"),
    "23": ("Uttar Pradesh", "09"),
    "24": ("Uttar Pradesh", "09"),
    "25": ("Uttar Pradesh", "09"),
    "26": ("Uttar Pradesh", "09"),
    "27": ("Uttar Pradesh", "09"),
    "28": ("Uttar Pradesh", "09"),
    "30": ("Rajasthan", "08"),
    "31": ("Rajasthan", "08"),
    "32": ("Rajasthan", "08"),
    "33": ("Rajasthan", "08"),
    "34": ("Rajasthan", "08"),
    "36": ("Gujarat", "24"),
    "37": ("Gujarat", "24"),
    "38": ("Gujarat", "24"),
    "39": ("Gujarat", "24"),
    "40": ("Maharashtra", "27"),
    "41": ("Maharashtra", "27"),
    "42": ("Maharashtra", "27"),
    "43": ("Maharashtra", "27"),
    "44": ("Maharashtra", "27"),
    "45": ("Madhya Pradesh", "23"),
    "46": ("Madhya Pradesh", "23"),
    "47": ("Madhya Pradesh", "23"),
    "48": ("Madhya Pradesh", "23"),
    "49": ("Chhattisgarh", "22"),
    "50": ("Telangana", "36"),
    "51": ("Telangana", "36"),
    "52": ("Andhra Pradesh", "37"),
    "53": ("Andhra Pradesh", "37"),
    "56": ("Karnataka", "29"),
    "57": ("Karnataka", "29"),
    "58": ("Karnataka", "29"),
    "59": ("Karnataka", "29"),
    "60": ("Tamil Nadu", "33"),
    "61": ("Tamil Nadu", "33"),
    "62": ("Tamil Nadu", "33"),
    "63": ("Tamil Nadu", "33"),
    "64": ("Tamil Nadu", "33"),
    "67": ("Kerala", "32"),
    "68": ("Kerala", "32"),
    "69": ("Kerala", "32"),
    "70": ("West Bengal", "19"),
    "71": ("West Bengal", "19"),
    "72": ("West Bengal", "19"),
    "73": ("West Bengal", "19"),
    "74": ("West Bengal", "19"),
    "75": ("Odisha", "21"),
    "76": ("Odisha", "21"),
    "77": ("Odisha", "21"),
    "78": ("Assam", "18"),
    "79": ("Northeast", "00"),
    "80": ("Bihar", "10"),
    "81": ("Bihar", "10"),
    "82": ("Bihar", "10"),
    "83": ("Bihar", "10"),
    "84": ("Bihar", "10"),
    "85": ("Bihar", "10"),
    "13": ("Chandigarh", "04"),
    "16": ("Chandigarh", "04"),
}

def get_state_from_pincode(pincode):
    """Get state name and code from pincode"""
    if not pincode or len(str(pincode)) < 2:
        return None, None
    prefix = str(pincode)[:2]
    state_info = PINCODE_STATE_MAP.get(prefix)
    if state_info:
        return state_info[0], state_info[1]
    return "Other", "00"

def calculate_gst(taxable_amount, destination_pincode=None):
    """
    Calculate GST based on destination state
    - Same state (Gujarat): CGST 9% + SGST 9%
    - Different state: IGST 18%
    """
    if not destination_pincode:
        # Default to IGST if no pincode provided
        igst = round(taxable_amount * (IGST_RATE / 100), 2)
        return {
            "taxable_amount": round(taxable_amount, 2),
            "gst_type": "IGST",
            "cgst_rate": 0,
            "cgst_amount": 0,
            "sgst_rate": 0,
            "sgst_amount": 0,
            "igst_rate": IGST_RATE,
            "igst_amount": igst,
            "total_gst": igst,
            "destination_state": "Unknown",
            "is_same_state": False
        }
    
    pincode_prefix = str(destination_pincode)[:2]
    state_name, state_code = get_state_from_pincode(destination_pincode)
    
    # Check if same state (Gujarat)
    is_same_state = pincode_prefix in ["36", "37", "38", "39"]
    
    if is_same_state:
        # Same state: CGST + SGST
        cgst = round(taxable_amount * (CGST_RATE / 100), 2)
        sgst = round(taxable_amount * (SGST_RATE / 100), 2)
        return {
            "taxable_amount": round(taxable_amount, 2),
            "gst_type": "CGST+SGST",
            "cgst_rate": CGST_RATE,
            "cgst_amount": cgst,
            "sgst_rate": SGST_RATE,
            "sgst_amount": sgst,
            "igst_rate": 0,
            "igst_amount": 0,
            "total_gst": round(cgst + sgst, 2),
            "destination_state": state_name,
            "is_same_state": True
        }
    else:
        # Different state: IGST
        igst = round(taxable_amount * (IGST_RATE / 100), 2)
        return {
            "taxable_amount": round(taxable_amount, 2),
            "gst_type": "IGST",
            "cgst_rate": 0,
            "cgst_amount": 0,
            "sgst_rate": 0,
            "sgst_amount": 0,
            "igst_rate": IGST_RATE,
            "igst_amount": igst,
            "total_gst": igst,
            "destination_state": state_name,
            "is_same_state": False
        }

# Product Code Mappings
ROLLER_TYPE_CODES = {
    "carrying": "CR",
    "return": "RR",
    "impact": "IR"
}

BEARING_MAKE_CODES = {
    "china": "C",
    "skf": "S",
    "fag": "F",
    "timken": "T"
}

BEARING_SERIES_MAP = {
    "6204": "62", "6205": "62", "6206": "62", "6207": "62", "6208": "62", "6209": "62", "6210": "62",
    "6304": "63", "6305": "63", "6306": "63", "6307": "63", "6308": "63", "6309": "63", "6310": "63",
    "420204": "42", "420205": "42", "420206": "42"
}

def generate_product_code(roller_type, shaft_dia, pipe_dia, pipe_length, pipe_type, bearing_number, bearing_make, rubber_dia=None):
    """
    Generate product code/SKU for conveyor rollers
    
    Format for Carrying Rollers: [TYPE][SHAFT] [PIPE] [LENGTH][THICKNESS] [SERIES][MAKE]
    Example: CR20 89 1000A 62S
    
    Format for Return Rollers: [TYPE][SHAFT] [PIPE] [LENGTH][THICKNESS] [SERIES][MAKE]
    Example: RR25 114 750B 62C
    
    Format for Impact Rollers: [TYPE][SHAFT] [PIPE/RUBBER] [LENGTH][THICKNESS] [SERIES][MAKE]
    Example: IR20 76/114 200B 62S
    """
    # Roller type
    type_code = ROLLER_TYPE_CODES.get(roller_type.lower(), "CR")
    
    # Shaft diameter
    shaft_code = str(int(shaft_dia))
    
    # Pipe diameter (with rubber for impact rollers)
    # Use custom mapping for display codes (88.9 -> 89, 139.7 -> 139)
    pipe_display = get_pipe_code(pipe_dia)
    if rubber_dia:
        pipe_code = f"{pipe_display}/{int(rubber_dia)}"
    else:
        pipe_code = str(pipe_display)
    
    # Length in mm
    length_code = str(int(pipe_length))
    
    # Pipe thickness type (uppercase)
    thickness_code = pipe_type.upper()
    
    # Bearing series
    series_code = BEARING_SERIES_MAP.get(bearing_number, "62")
    
    # Bearing make (uppercase)
    make_code = BEARING_MAKE_CODES.get(bearing_make.lower(), "C")
    
    # Combine all parts
    product_code = f"{type_code}{shaft_code} {pipe_code} {length_code}{thickness_code} {series_code}{make_code}"
    
    return product_code

# Cost Calculation Constants - AS PER YOUR FORMULA
LAYOUT_MARKUP = 0.32  # 32% layout/manufacturing cost
PROFIT_MARKUP = 0.60  # 60% profit margin
# Final multiplier: 1.32 × 1.60 = 2.112

# Packing Charges (Applied AFTER final product price calculation)
PACKING_CHARGES = {
    "none": 0.0,         # No packing
    "standard": 0.01,    # 1% for standard packing
    "pallet": 0.04,      # 4% for pallet packing
    "wooden_box": 0.08,  # 8% for wooden box packing
}

# Value-based Discount Slabs (in Lakhs)
# Applied on (Unit Price × Quantity) BEFORE packing and freight
DISCOUNT_SLABS = [
    (0, 200000, 5.0),           # 0 - 2 Lakh: 5%
    (200000, 500000, 7.5),      # 2 - 5 Lakh: 7.5%
    (500000, 750000, 10.0),     # 5 - 7.5 Lakh: 10%
    (750000, 1000000, 15.0),    # 7.5 - 10 Lakh: 15%
    (1000000, 1500000, 20.0),   # 10 - 15 Lakh: 20%
    (1500000, 3000000, 25.0),   # 15 - 30 Lakh: 25%
    (3000000, 5000000, 28.0),   # 30 - 50 Lakh: 28%
    (5000000, 10000000, 30.0),  # 50 Lakh - 1 Crore: 30%
    (10000000, float('inf'), 35.0),  # Above 1 Crore: 35%
]

def get_discount_percent(order_value):
    """Get discount percentage based on order value"""
    for min_val, max_val, discount in DISCOUNT_SLABS:
        if min_val <= order_value < max_val:
            return discount
    return 0.0

# Freight Charges Configuration
DISPATCH_PINCODE = "382433"  # Gujarat - Dispatch location

# Freight rates per kg based on distance from dispatch location
FREIGHT_RATES_PER_KG = {
    (0, 300): 2.0,       # 0-300 km: ₹2/kg
    (300, 600): 4.0,     # 300-600 km: ₹4/kg
    (600, 1000): 5.0,    # 600-1000 km: ₹5/kg
    (1000, 1500): 7.0,   # 1000-1500 km: ₹7/kg
    (1500, 9999): 9.0    # 1500+ km: ₹9/kg
}

def get_distance_from_pincode(destination_pincode):
    """
    Calculate distance from dispatch location (382433) to destination pincode.
    
    NOTE: This is a simplified implementation using pincode-based zones.
    For production, integrate with a pincode distance API like:
    - India Post Pincode API
    - Google Distance Matrix API
    - Delhivery/Other logistics APIs
    
    Returns distance in km.
    """
    # Simplified zone-based distance estimation
    # First 2 digits of pincode indicate region
    origin_zone = DISPATCH_PINCODE[:2]  # "38" = Gujarat
    dest_zone = destination_pincode[:2] if destination_pincode else "00"
    
    # Simplified distance mapping based on pincode zones
    # Gujarat (38) to various regions
    zone_distances = {
        "38": 150,    # Gujarat (local)
        "39": 250,    # Gujarat (other parts)
        "36": 350,    # Rajasthan
        "37": 400,    # Maharashtra (North)
        "40": 500,    # Maharashtra (Pune/Mumbai)
        "41": 550,    # Maharashtra (South)
        "42": 600,    # Madhya Pradesh
        "43": 650,    # Bihar
        "11": 900,    # Delhi
        "12": 950,    # Haryana
        "13": 1000,   # Punjab
        "14": 1100,   # Himachal
        "15": 1200,   # Jammu
        "16": 1150,   # Chandigarh
        "17": 1300,   # Uttarakhand
        "20": 800,    # Uttar Pradesh (West)
        "21": 850,    # Uttar Pradesh
        "22": 900,    # Uttar Pradesh (East)
        "24": 1400,   # West Bengal
        "60": 1600,   # Tamil Nadu
        "50": 1300,   # Karnataka (North)
        "56": 1400,   # Karnataka (South)
        "57": 1350,   # Andhra Pradesh
        "68": 1700,   # Kerala
        "70": 1800,   # Assam
        "78": 1900,   # North East
    }
    
    return zone_distances.get(dest_zone, 500)  # Default 500 km if zone unknown

def get_freight_rate_per_kg(distance_km):
    """Get freight rate per kg based on distance"""
    for (min_dist, max_dist), rate in FREIGHT_RATES_PER_KG.items():
        if min_dist <= distance_km < max_dist:
            return rate
    return 9.0  # Default to highest rate if distance exceeds all ranges


def get_belt_widths_for_length(roller_length, roller_type="carrying"):
    """
    Get belt width(s) that correspond to a roller length
    Returns list of belt widths (mm)
    """
    belt_widths = []
    
    if roller_type == "return":
        lengths_map = RETURN_ROLLER_LENGTHS
    else:
        lengths_map = ROLLER_LENGTHS
    
    for belt_width, lengths in lengths_map.items():
        if roller_length in lengths:
            belt_widths.append(belt_width)
    
    return belt_widths


def get_all_lengths_with_belt_widths(roller_type="carrying"):
    """
    Get all roller lengths with their corresponding belt widths
    Returns dict: {length: [belt_widths]}
    """
    result = {}
    
    if roller_type == "return":
        lengths_map = RETURN_ROLLER_LENGTHS
    else:
        lengths_map = ROLLER_LENGTHS
    
    for belt_width, lengths in lengths_map.items():
        for length in lengths:
            if length not in result:
                result[length] = []
            result[length].append(belt_width)
    
    return result


def calculate_roller_weight(pipe_dia, pipe_length_mm, shaft_dia, pipe_type, rubber_dia=None, shaft_end_type="B", custom_shaft_extension=None):
    """
    Calculate total roller weight in kg
    Includes: pipe + shaft + rubber (if impact roller)
    (Bearings, housing, seals, circlips weight is negligible)
    """
    # Pipe weight
    pipe_length_m = pipe_length_mm / 1000
    pipe_weight_per_m = PIPE_WEIGHT_PER_METER[pipe_dia].get(pipe_type, PIPE_WEIGHT_PER_METER[pipe_dia]["B"])
    pipe_weight = pipe_weight_per_m * pipe_length_m
    
    # Shaft weight (1 shaft per roller)
    shaft_length_mm = calculate_shaft_length(pipe_length_mm, shaft_end_type, custom_shaft_extension)
    shaft_length_m = shaft_length_mm / 1000
    shaft_weight = SHAFT_WEIGHT_PER_METER[shaft_dia] * shaft_length_m
    
    # Rubber weight (if impact roller)
    rubber_weight = 0
    if rubber_dia:
        # Simplified rubber weight calculation
        # Rubber ring weight ≈ volume × density
        # Approximation: add 30-50% to pipe weight for rubber lagging
        rubber_weight = pipe_weight * 0.4  # Approximate
    
    total_weight = pipe_weight + shaft_weight + rubber_weight
    return round(total_weight, 2)

def calculate_freight_charges(roller_weight_kg, destination_pincode):
    """
    Calculate freight charges based on roller weight and destination pincode
    
    Returns:
        - distance_km
        - freight_rate_per_kg
        - freight_charges (weight × rate)
    """
    distance_km = get_distance_from_pincode(destination_pincode)
    freight_rate = get_freight_rate_per_kg(distance_km)
    freight_charges = roller_weight_kg * freight_rate
    
    return {
        "distance_km": round(distance_km, 0),
        "freight_rate_per_kg": round(freight_rate, 2),
        "roller_weight_kg": round(roller_weight_kg, 2),
        "freight_charges": round(freight_charges, 2)
    }

def calculate_shaft_length(pipe_length_mm, shaft_end_type="B", custom_extension=None):
    """
    Calculate shaft length based on pipe length and shaft end type.
    
    Args:
        pipe_length_mm: Length of the pipe in mm
        shaft_end_type: Type A (+26mm), B (+36mm), C (+56mm), or 'custom'
        custom_shaft_length: Total shaft length in mm (only used if shaft_end_type is 'custom')
    
    Returns:
        Total shaft length in mm
    """
    return get_shaft_length(pipe_length_mm, shaft_end_type, custom_shaft_length)

def calculate_rubber_cost(pipe_dia, rubber_dia, pipe_length_mm):
    """
    Calculate rubber lagging cost for impact rollers.
    Number of rings = pipe_length / 35mm
    Total cost = number of rings × cost per ring
    """
    rubber_key = f"{int(pipe_dia)}/{int(rubber_dia)}"
    
    if rubber_key not in RUBBER_RING_COSTS:
        return 0  # No rubber for this combination
    
    number_of_rings = pipe_length_mm / RUBBER_RING_THICKNESS
    cost_per_ring = RUBBER_RING_COSTS[rubber_key]
    total_rubber_cost = number_of_rings * cost_per_ring
    
    return round(total_rubber_cost, 2)

def get_housing_for_pipe_and_bearing(pipe_dia, bearing_number):
    """Get compatible housing based on pipe diameter and bearing"""
    bearing_od = BEARING_OD.get(bearing_number)
    if not bearing_od:
        return None
    
    housing_options = HOUSING_OPTIONS.get(pipe_dia, [])
    for housing_dia, bearing_bores in housing_options:
        if bearing_od in bearing_bores:
            return f"{housing_dia}/{bearing_od}"
    return None

def get_bearing_cost(bearing_number, make="china"):
    """Get bearing cost by make. Defaults to cheapest available if make not available."""
    bearing_prices = BEARING_COSTS.get(bearing_number, {})
    
    # If requested make is available, return it
    if make.lower() in bearing_prices:
        return bearing_prices[make.lower()]
    
    # Otherwise return the cheapest available option
    if bearing_prices:
        return min(bearing_prices.values())
    
    return 0  # Shouldn't happen if bearing exists

def calculate_raw_material_cost(pipe_dia, pipe_length_mm, shaft_dia, bearing_number, bearing_make="china", rubber_dia=None, pipe_type="B", shaft_end_type="B", custom_shaft_length=None):
    """
    Calculate total raw material cost for a roller (optionally with rubber lagging for impact rollers)
    pipe_type: "A" (Light), "B" (Medium), "C" (Heavy) - defaults to "B" (Medium)
    shaft_end_type: "A" (+26mm), "B" (+36mm), "C" (+56mm), "custom" - defaults to "B"
    custom_shaft_length: Total shaft length in mm (only used if shaft_end_type is 'custom')
    """
    
    # Pipe cost - now depends on pipe type (A/B/C)
    pipe_length_m = pipe_length_mm / 1000
    pipe_weight_per_m = PIPE_WEIGHT_PER_METER[pipe_dia].get(pipe_type, PIPE_WEIGHT_PER_METER[pipe_dia]["B"])
    pipe_weight = pipe_weight_per_m * pipe_length_m
    pipe_cost = pipe_weight * PIPE_COST_PER_KG
    
    # Shaft cost (1 shaft per roller)
    shaft_length_mm = calculate_shaft_length(pipe_length_mm, shaft_end_type, custom_shaft_length)
    shaft_length_m = shaft_length_mm / 1000
    shaft_weight = SHAFT_WEIGHT_PER_METER[shaft_dia] * shaft_length_m
    shaft_cost = shaft_weight * SHAFT_COST_PER_KG
    
    # Bearing cost (2 bearings)
    bearing_unit_cost = get_bearing_cost(bearing_number, bearing_make)
    bearing_cost = bearing_unit_cost * 2
    
    # Housing cost (2 housings)
    housing = get_housing_for_pipe_and_bearing(pipe_dia, bearing_number)
    if housing and housing in HOUSING_COSTS:
        housing_cost = HOUSING_COSTS[housing] * 2
    else:
        housing_cost = 0  # Default if housing not found
    
    # Seal set cost (2 seal sets)
    seal_cost = SEAL_COSTS.get(bearing_number, 0) * 2
    
    # Circlip cost (4 circlips per roller)
    circlip_cost = CIRCLIP_COSTS[shaft_dia] * 4
    
    # Rubber lagging cost (optional, for impact rollers)
    rubber_cost = 0
    locking_ring_cost = 0
    if rubber_dia:
        rubber_cost = calculate_rubber_cost(pipe_dia, rubber_dia, pipe_length_mm)
        # Add locking ring cost for impact rollers
        locking_ring_cost = LOCKING_RING_COSTS.get(int(pipe_dia), 0)
    
    total_raw_material = pipe_cost + shaft_cost + bearing_cost + housing_cost + seal_cost + circlip_cost + rubber_cost + locking_ring_cost
    
    result = {
        "pipe_cost": round(pipe_cost, 2),
        "shaft_cost": round(shaft_cost, 2),
        "bearing_cost": round(bearing_cost, 2),
        "housing_cost": round(housing_cost, 2),
        "seal_cost": round(seal_cost, 2),
        "circlip_cost": round(circlip_cost, 2),
        "total_raw_material": round(total_raw_material, 2)
    }
    
    if rubber_dia:
        result["rubber_cost"] = round(rubber_cost, 2)
        result["locking_ring_cost"] = round(locking_ring_cost, 2)
        number_of_rings = pipe_length_mm / RUBBER_RING_THICKNESS
        result["rubber_rings"] = round(number_of_rings, 1)
    
    return result

def calculate_final_price(raw_material_cost, packing_type="none", quantity=1):
    """
    Calculate final price using your formula:
    Total = Raw Material × 1.32 × 1.60
    Then apply discount based on order value, then add packing charges
    
    Where:
    - 1.32 = Raw Material + 32% Layout cost
    - 1.60 = 60% Profit on (Raw Material + Layout)
    
    Flow:
    1. Calculate unit price (Raw Material × 2.112)
    2. Calculate order value (unit price × quantity)
    3. Apply discount based on order value
    4. Add packing charges on discounted price
    """
    layout_cost = raw_material_cost * LAYOUT_MARKUP
    subtotal_with_layout = raw_material_cost + layout_cost
    profit = subtotal_with_layout * PROFIT_MARKUP
    unit_price = subtotal_with_layout + profit  # Price per roller before discount
    
    # Calculate order value for discount calculation
    order_value = unit_price * quantity
    
    # Get discount based on order value
    discount_percent = get_discount_percent(order_value)
    discount_amount = order_value * (discount_percent / 100)
    price_after_discount = order_value - discount_amount
    
    # Calculate packing charges (on discounted total)
    packing_percent = PACKING_CHARGES.get(packing_type, 0.0)
    packing_charges = price_after_discount * packing_percent
    
    final_price = price_after_discount + packing_charges
    
    return {
        "raw_material_cost": round(raw_material_cost, 2),
        "layout_cost": round(layout_cost, 2),
        "subtotal_with_layout": round(subtotal_with_layout, 2),
        "profit": round(profit, 2),
        "unit_price": round(unit_price, 2),  # Per roller price before discount
        "quantity": quantity,
        "order_value": round(order_value, 2),  # Unit price × quantity
        "discount_percent": discount_percent,
        "discount_amount": round(discount_amount, 2),
        "price_after_discount": round(price_after_discount, 2),
        "packing_type": packing_type,
        "packing_percent": packing_percent * 100,
        "packing_charges": round(packing_charges, 2),
        "final_price": round(final_price, 2),  # After discount + packing (before freight)
        "multiplier": 2.112  # For reference (1.32 × 1.60)
    }

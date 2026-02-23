"""
Roller Drawing Generator - Engineering Style
Generates technical drawings matching the user's template
For Carrying and Return Rollers
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from io import BytesIO
from datetime import datetime


def generate_roller_drawing(
    product_code: str,
    roller_type: str,
    pipe_diameter: float,
    pipe_length: float,
    pipe_type: str,
    shaft_diameter: float,
    bearing: str,
    bearing_make: str,
    housing: str,
    weight_kg: float,
    unit_price: float = 0,
    rubber_diameter: float = None,
    belt_widths: list = None,
    quantity: int = 1,
    shaft_end_type: str = "B",
    custom_shaft_extension: int = None
) -> BytesIO:
    """
    Generate a technical drawing PDF for a roller in engineering style
    All sections stacked vertically
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Calculate shaft length
    shaft_extensions = {"A": 26, "B": 36, "C": 56}
    if shaft_end_type == "custom" and custom_shaft_extension is not None:
        shaft_length = custom_shaft_extension
    else:
        shaft_extension = shaft_extensions.get(shaft_end_type.upper(), 36)
        shaft_length = pipe_length + shaft_extension
    
    # Colors
    primary_color = colors.HexColor('#960018')
    black = colors.black
    blue = colors.HexColor('#0066CC')
    green = colors.HexColor('#228B22')
    red = colors.HexColor('#CC0000')
    gray = colors.HexColor('#666666')
    light_gray = colors.HexColor('#CCCCCC')
    
    # ============= HEADER =============
    c.setFillColor(primary_color)
    c.rect(0, height - 50, width, 50, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(15*mm, height - 30, "CONVERO SOLUTIONS")
    
    c.setFont("Helvetica", 9)
    c.drawString(15*mm, height - 42, "Belt Conveyor Components & Engineering")
    
    # Drawing number
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - 15*mm, height - 25, f"DWG: {product_code}")
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 15*mm, height - 36, f"Date: {datetime.now().strftime('%d-%m-%Y')}")
    
    # ============= TITLE =============
    y_pos = height - 70
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 14)
    
    roller_type_text = {
        'carrying': 'CARRYING ROLLER',
        'impact': 'IMPACT ROLLER', 
        'return': 'RETURN ROLLER'
    }.get(roller_type.lower(), 'CONVEYOR ROLLER')
    
    c.drawCentredString(width/2, y_pos, roller_type_text)
    
    # ============= DRAWING AREA (Side View + Front View on same center line) =============
    y_pos -= 15
    drawing_height = 160
    drawing_width = width - 30*mm
    
    # Drawing border
    c.setStrokeColor(light_gray)
    c.setLineWidth(0.5)
    c.rect(15*mm, y_pos - drawing_height, drawing_width, drawing_height, fill=0, stroke=1)
    
    # Common center line Y position for both views
    center_y = y_pos - drawing_height / 2
    
    # Side view (left 2/3 of drawing area)
    side_view_center_x = 15*mm + drawing_width * 0.4
    
    draw_engineering_schematic(
        c,
        center_x=side_view_center_x,
        center_y=center_y,
        pipe_diameter=pipe_diameter,
        pipe_length=pipe_length,
        shaft_diameter=shaft_diameter,
        shaft_length=shaft_length,
        rubber_diameter=rubber_diameter,
        roller_type=roller_type,
        scale_factor=0.32
    )
    
    # Front view / Cross-section (right 1/3 of drawing area) - SAME center_y
    front_view_center_x = 15*mm + drawing_width * 0.82
    draw_cross_section_detail(c, front_view_center_x, center_y, pipe_diameter, shaft_diameter, rubber_diameter, scale=1.2)
    
    # Labels for views
    c.setFillColor(gray)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(side_view_center_x, y_pos - drawing_height + 8, "SIDE VIEW")
    c.drawCentredString(front_view_center_x, y_pos - drawing_height + 8, "FRONT VIEW")
    
    # ============= DIMENSIONS TABLE (Full width, below drawing) =============
    y_pos = y_pos - drawing_height - 15
    
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y_pos, "DIMENSIONS")
    
    y_pos -= 8
    
    # Shaft end type display
    shaft_end_label = {
        "A": "Type A (+26mm)",
        "B": "Type B (+36mm)",
        "C": "Type C (+56mm)",
        "custom": f"Custom ({int(shaft_length)}mm)"
    }.get(shaft_end_type, f"Type {shaft_end_type}")
    
    dim_data = [
        ['Symbol', 'Parameter', 'Value', 'Unit'],
        ['D', 'Pipe Diameter', f'{pipe_diameter}', 'mm'],
        ['A', 'Pipe Length', f'{int(pipe_length)}', 'mm'],
        ['B', 'Shaft Length', f'{int(shaft_length)}', 'mm'],
        ['d', 'Shaft Diameter', f'{shaft_diameter}', 'mm'],
        ['-', 'Pipe Type', f'Type {pipe_type} ({"Light" if pipe_type == "A" else "Medium" if pipe_type == "B" else "Heavy"})', '-'],
        ['-', 'Shaft End', shaft_end_label, '-'],
        ['-', 'Weight', f'{weight_kg}', 'kg'],
    ]
    
    if rubber_diameter:
        dim_data.insert(2, ['RD', 'Rubber Diameter', f'{rubber_diameter}', 'mm'])
    
    # Full width table
    dim_table = Table(dim_data, colWidths=[20*mm, 55*mm, 55*mm, 20*mm])
    dim_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 1), (0, -1), blue),
        ('GRID', (0, 0), (-1, -1), 0.5, gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    
    dim_w, dim_h = dim_table.wrap(0, 0)
    dim_table.drawOn(c, 15*mm, y_pos - dim_h - 3)
    
    # ============= MATERIAL SPECIFICATIONS (Full width, below dimensions) =============
    y_pos = y_pos - dim_h - 18
    
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(15*mm, y_pos, "MATERIAL SPECIFICATIONS")
    
    y_pos -= 12
    c.setFillColor(black)
    
    specs = [
        ("Standard:", "IDLERS AS PER IS 8598"),
        ("Pipe:", "ERW AS PER IS:9295"),
        ("Shaft:", "EN 8"),
        ("Bearing:", f"{bearing_make.upper()} {bearing}"),
        ("Housing:", "CRCA DEEP DRAWN 3.15 MM (IS-513)"),
        ("Circlip:", "SPRING STEEL (IS-3075)"),
        ("Sealset:", "METAL CAP WITH NYLON SEALS FILLED WITH LITHIUM BASED EP-2 GREASE"),
    ]
    
    # Add rubber ring spec for impact rollers
    if rubber_diameter and roller_type.lower() == 'impact':
        specs.insert(4, ("Rubber Ring:", "SHORE HARDNESS 55-60"))
    
    for label, value in specs:
        c.setFont("Helvetica-Bold", 8)
        c.drawString(15*mm, y_pos, label)
        c.setFont("Helvetica", 8)
        c.drawString(15*mm + 18*mm, y_pos, value)
        y_pos -= 11
    
    # ============= FOOTER =============
    footer_y = 15
    c.setStrokeColor(light_gray)
    c.setLineWidth(0.5)
    c.line(15*mm, footer_y + 10, width - 15*mm, footer_y + 10)
    
    c.setFillColor(gray)
    c.setFont("Helvetica", 7)
    c.drawString(15*mm, footer_y, "CONVERO SOLUTIONS | Belt Conveyor Components")
    c.drawRightString(width - 15*mm, footer_y, f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(width/2, footer_y - 8, "ALL DIMENSIONS ARE IN MM. DRAWING NOT TO SCALE.")
    
    c.save()
    buffer.seek(0)
    return buffer


def draw_engineering_schematic(c, center_x, center_y, pipe_diameter, pipe_length, shaft_diameter, shaft_length, rubber_diameter=None, roller_type='carrying', scale_factor=0.4):
    """
    Draw engineering-style roller schematic with proper dimension notation
    """
    # Colors
    black = colors.black
    blue = colors.HexColor('#0066CC')
    green = colors.HexColor('#228B22')
    red = colors.HexColor('#CC0000')
    
    # Scale calculation
    max_width = 120 * mm
    max_height = 60 * mm
    
    scale = min(max_width / shaft_length, max_height / (rubber_diameter or pipe_diameter))
    scale = min(scale, scale_factor)
    
    # Scaled dimensions
    pipe_len_s = pipe_length * scale
    pipe_dia_s = pipe_diameter * scale
    shaft_len_s = shaft_length * scale
    shaft_dia_s = shaft_diameter * scale
    
    if rubber_diameter:
        outer_dia_s = rubber_diameter * scale
    else:
        outer_dia_s = pipe_dia_s
    
    # Calculate shaft extension on each side
    shaft_ext_s = (shaft_len_s - pipe_len_s) / 2
    
    # ============= DRAW CENTER LINE (Red, dash-dot-dot) =============
    c.setStrokeColor(red)
    c.setLineWidth(0.5)
    c.setDash([8, 3, 2, 3])
    c.line(center_x - shaft_len_s/2 - 15, center_y, center_x + shaft_len_s/2 + 15, center_y)
    c.setDash([])
    
    # ============= DRAW SHAFT (extends beyond pipe) =============
    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    c.setFillColor(colors.white)
    
    # Left shaft end
    c.rect(center_x - shaft_len_s/2, center_y - shaft_dia_s/2, shaft_ext_s, shaft_dia_s, fill=1, stroke=1)
    # Right shaft end
    c.rect(center_x + pipe_len_s/2, center_y - shaft_dia_s/2, shaft_ext_s, shaft_dia_s, fill=1, stroke=1)
    
    # ============= DRAW PIPE (main body) =============
    c.setFillColor(colors.HexColor('#E8E8E8'))
    c.rect(center_x - pipe_len_s/2, center_y - pipe_dia_s/2, pipe_len_s, pipe_dia_s, fill=1, stroke=1)
    
    # ============= DRAW RUBBER RINGS (if impact roller) =============
    if rubber_diameter and roller_type.lower() == 'impact':
        # Draw individual rubber rings pattern
        ring_width = 8 * scale  # Width of each rubber ring
        ring_gap = 3 * scale    # Gap between rings
        num_rings = int(pipe_len_s / (ring_width + ring_gap))
        start_x = center_x - pipe_len_s/2 + ring_gap
        
        c.setFillColor(colors.HexColor('#2D4A2D'))  # Dark green for rubber
        for i in range(num_rings):
            ring_x = start_x + i * (ring_width + ring_gap)
            if ring_x + ring_width <= center_x + pipe_len_s/2:
                # Draw rubber ring (rectangle extending above and below pipe)
                c.rect(ring_x, center_y - outer_dia_s/2, ring_width, outer_dia_s, fill=1, stroke=1)
    
    # ============= DIMENSION LINES =============
    c.setStrokeColor(blue)
    c.setFillColor(blue)
    c.setLineWidth(0.8)
    
    # --- Dimension A (Pipe Length) - below the roller ---
    dim_y_A = center_y - outer_dia_s/2 - 18
    c.line(center_x - pipe_len_s/2, center_y - outer_dia_s/2 - 3, center_x - pipe_len_s/2, dim_y_A - 3)
    c.line(center_x + pipe_len_s/2, center_y - outer_dia_s/2 - 3, center_x + pipe_len_s/2, dim_y_A - 3)
    c.line(center_x - pipe_len_s/2, dim_y_A, center_x + pipe_len_s/2, dim_y_A)
    draw_arrowhead(c, center_x - pipe_len_s/2, dim_y_A, 'right')
    draw_arrowhead(c, center_x + pipe_len_s/2, dim_y_A, 'left')
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(center_x, dim_y_A - 10, f"A = {int(pipe_length)}")
    
    # --- Dimension B (Shaft Length) - below A ---
    # Extension lines from shaft ends with proper EXEO (offset=2) and EXEE (extension=3)
    exeo = 2  # Extension line offset from object
    exee = 3  # Extension line extension beyond dimension line
    dim_y_B = dim_y_A - 22
    
    # Left extension line - from shaft bottom to below dimension line
    c.line(center_x - shaft_len_s/2, center_y - shaft_dia_s/2 - exeo, center_x - shaft_len_s/2, dim_y_B - exee)
    # Right extension line - from shaft bottom to below dimension line  
    c.line(center_x + shaft_len_s/2, center_y - shaft_dia_s/2 - exeo, center_x + shaft_len_s/2, dim_y_B - exee)
    
    # Dimension line
    c.line(center_x - shaft_len_s/2, dim_y_B, center_x + shaft_len_s/2, dim_y_B)
    draw_arrowhead(c, center_x - shaft_len_s/2, dim_y_B, 'right')
    draw_arrowhead(c, center_x + shaft_len_s/2, dim_y_B, 'left')
    c.drawCentredString(center_x, dim_y_B - 10, f"B = {int(shaft_length)}")
    
    # --- Dimension D (Pipe Diameter) - right side ---
    dim_x_D = center_x + pipe_len_s/2 + 22
    c.line(center_x + pipe_len_s/2 + 3, center_y - pipe_dia_s/2, dim_x_D + 3, center_y - pipe_dia_s/2)
    c.line(center_x + pipe_len_s/2 + 3, center_y + pipe_dia_s/2, dim_x_D + 3, center_y + pipe_dia_s/2)
    c.line(dim_x_D, center_y - pipe_dia_s/2, dim_x_D, center_y + pipe_dia_s/2)
    draw_arrowhead(c, dim_x_D, center_y - pipe_dia_s/2, 'down')
    draw_arrowhead(c, dim_x_D, center_y + pipe_dia_s/2, 'up')
    c.saveState()
    c.translate(dim_x_D + 10, center_y)
    c.rotate(90)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(0, 0, f"D = {int(pipe_diameter)}")
    c.restoreState()
    
    # --- Dimension RD (Rubber Diameter) - for impact rollers only, right side outer ---
    if rubber_diameter and roller_type.lower() == 'impact':
        dim_x_RD = dim_x_D + 25
        c.line(dim_x_D + 5, center_y - outer_dia_s/2, dim_x_RD + 3, center_y - outer_dia_s/2)
        c.line(dim_x_D + 5, center_y + outer_dia_s/2, dim_x_RD + 3, center_y + outer_dia_s/2)
        c.line(dim_x_RD, center_y - outer_dia_s/2, dim_x_RD, center_y + outer_dia_s/2)
        draw_arrowhead(c, dim_x_RD, center_y - outer_dia_s/2, 'down')
        draw_arrowhead(c, dim_x_RD, center_y + outer_dia_s/2, 'up')
        c.saveState()
        c.translate(dim_x_RD + 10, center_y)
        c.rotate(90)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(0, 0, f"RD = {int(rubber_diameter)}")
        c.restoreState()
    
    # --- Dimension d (Shaft Diameter) - left side ---
    dim_x_d = center_x - shaft_len_s/2 - 15
    c.line(center_x - shaft_len_s/2 - 3, center_y - shaft_dia_s/2, dim_x_d - 3, center_y - shaft_dia_s/2)
    c.line(center_x - shaft_len_s/2 - 3, center_y + shaft_dia_s/2, dim_x_d - 3, center_y + shaft_dia_s/2)
    c.line(dim_x_d, center_y - shaft_dia_s/2, dim_x_d, center_y + shaft_dia_s/2)
    draw_arrowhead(c, dim_x_d, center_y - shaft_dia_s/2, 'down')
    draw_arrowhead(c, dim_x_d, center_y + shaft_dia_s/2, 'up')
    c.saveState()
    c.translate(dim_x_d - 8, center_y)
    c.rotate(90)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(0, 0, f"d = {int(shaft_diameter)}")
    c.restoreState()


def draw_cross_section_detail(c, center_x, center_y, pipe_diameter, shaft_diameter, rubber_diameter=None, scale=1.0):
    """
    Draw a circular cross-section detail view (Front View)
    """
    blue = colors.HexColor('#0066CC')
    red = colors.HexColor('#CC0000')
    black = colors.black
    
    # Scale for detail view
    max_size = 35 * scale
    outer_dia = rubber_diameter if rubber_diameter else pipe_diameter
    detail_scale = max_size / outer_dia
    
    outer_r = (outer_dia * detail_scale) / 2
    pipe_r = (pipe_diameter * detail_scale) / 2
    shaft_r = (shaft_diameter * detail_scale) / 2
    
    # Draw outer circle (rubber or pipe)
    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    if rubber_diameter:
        c.setFillColor(colors.HexColor('#4A6741'))
        c.circle(center_x, center_y, outer_r, fill=1, stroke=1)
        c.setFillColor(colors.HexColor('#D0D0D0'))
        c.circle(center_x, center_y, pipe_r, fill=1, stroke=1)
    else:
        c.setFillColor(colors.HexColor('#E8E8E8'))
        c.circle(center_x, center_y, outer_r, fill=1, stroke=1)
    
    # Shaft hole (center)
    c.setFillColor(colors.white)
    c.circle(center_x, center_y, shaft_r, fill=1, stroke=1)
    
    # Center crosshairs (red)
    c.setStrokeColor(red)
    c.setLineWidth(0.5)
    c.setDash([4, 2, 1, 2])
    c.line(center_x - outer_r - 6, center_y, center_x + outer_r + 6, center_y)
    c.line(center_x, center_y - outer_r - 6, center_x, center_y + outer_r + 6)
    c.setDash([])
    
    # Dimension for outer diameter
    c.setStrokeColor(blue)
    c.setFillColor(blue)
    c.setLineWidth(0.8)
    c.setFont("Helvetica-Bold", 8)
    c.line(center_x, center_y, center_x + outer_r, center_y + outer_r * 0.7)
    c.drawString(center_x + outer_r + 3, center_y + outer_r * 0.7 - 2, f"D")


def draw_arrowhead(c, x, y, direction):
    """Draw a small arrowhead for dimension lines"""
    size = 3
    if direction == 'right':
        c.line(x, y, x + size, y - size/2)
        c.line(x, y, x + size, y + size/2)
    elif direction == 'left':
        c.line(x, y, x - size, y - size/2)
        c.line(x, y, x - size, y + size/2)
    elif direction == 'up':
        c.line(x, y, x - size/2, y - size)
        c.line(x, y, x + size/2, y - size)
    elif direction == 'down':
        c.line(x, y, x - size/2, y + size)
        c.line(x, y, x + size/2, y + size)

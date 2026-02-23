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
    c.rect(0, height - 60, width, 60, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(20*mm, height - 35, "CONVERO SOLUTIONS")
    
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, height - 48, "Belt Conveyor Components & Engineering")
    
    # Drawing number
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 20*mm, height - 30, f"DWG: {product_code}")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - 20*mm, height - 42, f"Date: {datetime.now().strftime('%d-%m-%Y')}")
    
    # ============= TITLE =============
    y_title = height - 85
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 16)
    
    roller_type_text = {
        'carrying': 'CARRYING ROLLER',
        'impact': 'IMPACT ROLLER', 
        'return': 'RETURN ROLLER'
    }.get(roller_type.lower(), 'CONVEYOR ROLLER')
    
    c.drawCentredString(width/2, y_title, roller_type_text)
    
    # ============= MAIN DRAWING AREA (LARGER) =============
    drawing_y = y_title - 30
    drawing_height = 280  # Increased from 200
    drawing_width = width - 40*mm
    
    # Drawing border
    c.setStrokeColor(light_gray)
    c.setLineWidth(0.5)
    c.rect(20*mm, drawing_y - drawing_height, drawing_width, drawing_height, fill=0, stroke=1)
    
    # Draw the roller schematic (centered and larger)
    center_x = width / 2 + 15*mm  # Shift right to leave room for cross-section
    center_y = drawing_y - drawing_height / 2 + 10
    
    draw_engineering_schematic(
        c,
        center_x=center_x,
        center_y=center_y,
        pipe_diameter=pipe_diameter,
        pipe_length=pipe_length,
        shaft_diameter=shaft_diameter,
        shaft_length=shaft_length,
        rubber_diameter=rubber_diameter,
        roller_type=roller_type,
        scale_factor=0.5  # Larger scale
    )
    
    # ============= CROSS-SECTION DETAIL (Left side) =============
    detail_x = 50*mm
    detail_y = center_y
    draw_cross_section_detail(c, detail_x, detail_y, pipe_diameter, shaft_diameter, rubber_diameter, scale=1.3)
    
    # ============= DIMENSION TABLE =============
    tables_y = drawing_y - drawing_height - 15
    
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20*mm, tables_y, "DIMENSIONS")
    
    tables_y_content = tables_y - 8
    
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
        dim_data.insert(2, ['E', 'Rubber Diameter', f'{rubber_diameter}', 'mm'])
    
    dim_table = Table(dim_data, colWidths=[18*mm, 45*mm, 45*mm, 15*mm])
    dim_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 1), (0, -1), blue),
        ('GRID', (0, 0), (-1, -1), 0.5, gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    dim_w, dim_h = dim_table.wrap(0, 0)
    dim_table.drawOn(c, 20*mm, tables_y_content - dim_h - 5)
    
    # ============= MATERIAL SPECS (Right side of dimensions) =============
    spec_x = 20*mm + dim_w + 15*mm
    spec_y = tables_y
    
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(spec_x, spec_y, "MATERIAL SPECIFICATIONS")
    
    spec_y -= 18
    c.setFillColor(black)
    
    specs = [
        ("Pipe:", "IS-9295 ERW Steel Tube"),
        ("Shaft:", "EN8/EN9 Steel, Ground Finish"),
        ("Bearing:", f"{bearing_make.upper()} Grade {bearing}"),
        ("Housing:", f"Cast Iron ({housing})"),
        ("Seals:", "Nitrile Rubber (NBR)"),
    ]
    
    if rubber_diameter:
        specs.append(("Rubber:", "Natural Rubber, 40±5 Shore A"))
    
    for label, value in specs:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(spec_x, spec_y, label)
        c.setFont("Helvetica", 9)
        c.drawString(spec_x + 18*mm, spec_y, value)
        spec_y -= 14
    
    # ============= LEGEND (Below specs) =============
    legend_y = spec_y - 10
    c.setFillColor(primary_color)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(spec_x, legend_y, "LEGEND")
    
    legend_y -= 14
    c.setFont("Helvetica", 8)
    
    # Blue dimension line
    c.setStrokeColor(blue)
    c.setLineWidth(1)
    c.line(spec_x, legend_y + 3, spec_x + 12*mm, legend_y + 3)
    c.setFillColor(black)
    c.drawString(spec_x + 14*mm, legend_y, "Dimension lines")
    
    legend_y -= 12
    # Green dashed line (hidden features)
    c.setStrokeColor(green)
    c.setDash([3, 2])
    c.line(spec_x, legend_y + 3, spec_x + 12*mm, legend_y + 3)
    c.setDash([])
    c.drawString(spec_x + 14*mm, legend_y, "Hidden features")
    
    legend_y -= 12
    # Red center line
    c.setStrokeColor(red)
    c.setDash([6, 2, 2, 2])
    c.line(spec_x, legend_y + 3, spec_x + 12*mm, legend_y + 3)
    c.setDash([])
    c.drawString(spec_x + 14*mm, legend_y, "Center line")
    
    # ============= FOOTER =============
    footer_y = 20
    c.setStrokeColor(light_gray)
    c.setLineWidth(0.5)
    c.line(15*mm, footer_y + 12, width - 15*mm, footer_y + 12)
    
    c.setFillColor(gray)
    c.setFont("Helvetica", 8)
    c.drawString(20*mm, footer_y, "CONVERO SOLUTIONS | Belt Conveyor Components")
    c.drawRightString(width - 20*mm, footer_y, f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(width/2, footer_y - 10, "All dimensions in mm. Drawing not to scale.")
    
    c.save()
    buffer.seek(0)
    return buffer


def draw_engineering_schematic(c, center_x, center_y, pipe_diameter, pipe_length, shaft_diameter, shaft_length, rubber_diameter=None, roller_type='carrying', scale_factor=0.4):
    """
    Draw engineering-style roller schematic with proper dimension notation
    Matching the user's template style
    """
    # Colors
    black = colors.black
    blue = colors.HexColor('#0066CC')
    green = colors.HexColor('#228B22')
    red = colors.HexColor('#CC0000')
    
    # Scale calculation
    max_width = 130 * mm
    max_height = 80 * mm
    
    scale = min(max_width / shaft_length, max_height / (rubber_diameter or pipe_diameter))
    scale = min(scale, scale_factor)  # Use provided scale factor
    
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
    c.line(center_x - shaft_len_s/2 - 20, center_y, center_x + shaft_len_s/2 + 20, center_y)
    c.setDash([])
    
    # ============= DRAW SHAFT (extends beyond pipe) =============
    c.setStrokeColor(black)
    c.setLineWidth(1.5)
    c.setFillColor(colors.white)
    
    # Shaft rectangles at ends
    # Left shaft end
    c.rect(center_x - shaft_len_s/2, center_y - shaft_dia_s/2, shaft_ext_s, shaft_dia_s, fill=1, stroke=1)
    # Right shaft end
    c.rect(center_x + pipe_len_s/2, center_y - shaft_dia_s/2, shaft_ext_s, shaft_dia_s, fill=1, stroke=1)
    
    # ============= DRAW PIPE (main body) =============
    c.setFillColor(colors.HexColor('#E8E8E8'))
    c.rect(center_x - pipe_len_s/2, center_y - pipe_dia_s/2, pipe_len_s, pipe_dia_s, fill=1, stroke=1)
    
    # ============= DRAW RUBBER (if impact roller) =============
    if rubber_diameter and roller_type.lower() == 'impact':
        c.setFillColor(colors.HexColor('#4A6741'))
        c.rect(center_x - pipe_len_s/2, center_y - outer_dia_s/2, pipe_len_s, outer_dia_s, fill=1, stroke=1)
        # Redraw pipe inside
        c.setFillColor(colors.HexColor('#D0D0D0'))
        c.rect(center_x - pipe_len_s/2 + 3, center_y - pipe_dia_s/2 + 3, pipe_len_s - 6, pipe_dia_s - 6, fill=1, stroke=0)
    
    # ============= DRAW HIDDEN LINES (internal bore - green dashed) =============
    c.setStrokeColor(green)
    c.setLineWidth(0.5)
    c.setDash([4, 3])
    
    # Inner bore of pipe (shaft passes through)
    bore_dia_s = shaft_dia_s + 5
    c.line(center_x - pipe_len_s/2, center_y - bore_dia_s/2, center_x + pipe_len_s/2, center_y - bore_dia_s/2)
    c.line(center_x - pipe_len_s/2, center_y + bore_dia_s/2, center_x + pipe_len_s/2, center_y + bore_dia_s/2)
    c.setDash([])
    
    # ============= DIMENSION LINES =============
    c.setStrokeColor(blue)
    c.setFillColor(blue)
    c.setLineWidth(0.8)
    
    # --- Dimension A (Pipe Length) - below the roller ---
    dim_y_A = center_y - outer_dia_s/2 - 25
    # Extension lines
    c.line(center_x - pipe_len_s/2, center_y - outer_dia_s/2 - 5, center_x - pipe_len_s/2, dim_y_A - 5)
    c.line(center_x + pipe_len_s/2, center_y - outer_dia_s/2 - 5, center_x + pipe_len_s/2, dim_y_A - 5)
    # Dimension line with arrows
    c.line(center_x - pipe_len_s/2, dim_y_A, center_x + pipe_len_s/2, dim_y_A)
    # Arrowheads
    draw_arrowhead(c, center_x - pipe_len_s/2, dim_y_A, 'right')
    draw_arrowhead(c, center_x + pipe_len_s/2, dim_y_A, 'left')
    # Label
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(center_x, dim_y_A - 15, f"A = {int(pipe_length)}")
    
    # --- Dimension B (Shaft Length) - below A ---
    dim_y_B = dim_y_A - 35
    # Extension lines
    c.line(center_x - shaft_len_s/2, dim_y_A - 8, center_x - shaft_len_s/2, dim_y_B - 5)
    c.line(center_x + shaft_len_s/2, dim_y_A - 8, center_x + shaft_len_s/2, dim_y_B - 5)
    # Dimension line
    c.line(center_x - shaft_len_s/2, dim_y_B, center_x + shaft_len_s/2, dim_y_B)
    # Arrowheads
    draw_arrowhead(c, center_x - shaft_len_s/2, dim_y_B, 'right')
    draw_arrowhead(c, center_x + shaft_len_s/2, dim_y_B, 'left')
    # Label
    c.drawCentredString(center_x, dim_y_B - 15, f"B = {int(shaft_length)}")
    
    # --- Dimension D (Pipe/Outer Diameter) - right side ---
    dim_x_D = center_x + pipe_len_s/2 + 30
    display_dia = rubber_diameter if rubber_diameter else pipe_diameter
    # Extension lines
    c.line(center_x + pipe_len_s/2 + 5, center_y - outer_dia_s/2, dim_x_D + 5, center_y - outer_dia_s/2)
    c.line(center_x + pipe_len_s/2 + 5, center_y + outer_dia_s/2, dim_x_D + 5, center_y + outer_dia_s/2)
    # Dimension line
    c.line(dim_x_D, center_y - outer_dia_s/2, dim_x_D, center_y + outer_dia_s/2)
    # Arrowheads
    draw_arrowhead(c, dim_x_D, center_y - outer_dia_s/2, 'down')
    draw_arrowhead(c, dim_x_D, center_y + outer_dia_s/2, 'up')
    # Label
    c.saveState()
    c.translate(dim_x_D + 15, center_y)
    c.rotate(90)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(0, 0, f"D = Ø{display_dia}")
    c.restoreState()
    
    # --- Dimension d (Shaft Diameter) - left side ---
    dim_x_d = center_x - shaft_len_s/2 - 20
    # Extension lines
    c.line(center_x - shaft_len_s/2 - 5, center_y - shaft_dia_s/2, dim_x_d - 5, center_y - shaft_dia_s/2)
    c.line(center_x - shaft_len_s/2 - 5, center_y + shaft_dia_s/2, dim_x_d - 5, center_y + shaft_dia_s/2)
    # Dimension line
    c.line(dim_x_d, center_y - shaft_dia_s/2, dim_x_d, center_y + shaft_dia_s/2)
    # Arrowheads
    draw_arrowhead(c, dim_x_d, center_y - shaft_dia_s/2, 'down')
    draw_arrowhead(c, dim_x_d, center_y + shaft_dia_s/2, 'up')
    # Label
    c.saveState()
    c.translate(dim_x_d - 12, center_y)
    c.rotate(90)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(0, 0, f"d = Ø{int(shaft_diameter)}")
    c.restoreState()


def draw_cross_section_detail(c, center_x, center_y, pipe_diameter, shaft_diameter, rubber_diameter=None, scale=1.0):
    """
    Draw a circular cross-section detail view
    """
    blue = colors.HexColor('#0066CC')
    green = colors.HexColor('#228B22')
    red = colors.HexColor('#CC0000')
    black = colors.black
    
    # Scale for detail view
    max_size = 40 * scale
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
        # Pipe circle
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
    c.line(center_x - outer_r - 8, center_y, center_x + outer_r + 8, center_y)
    c.line(center_x, center_y - outer_r - 8, center_x, center_y + outer_r + 8)
    c.setDash([])
    
    # Dimension for shaft diameter (d)
    c.setStrokeColor(blue)
    c.setFillColor(blue)
    c.setLineWidth(0.8)
    c.setFont("Helvetica-Bold", 9)
    c.line(center_x, center_y, center_x + shaft_r, center_y)
    c.drawString(center_x + shaft_r + 4, center_y - 3, f"Ød")
    
    # Label
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(center_x, center_y - outer_r - 15, "SECTION A-A")


def draw_arrowhead(c, x, y, direction):
    """Draw a small arrowhead for dimension lines"""
    size = 4
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

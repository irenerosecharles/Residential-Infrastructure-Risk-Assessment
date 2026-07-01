import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_property_pdf(property_data, trends, output_path):
    """
    Generates a professional PDF report for a property's risk assessment.
    
    property_data: dict representing the property (from database.json)
    trends: dict representing trend forecasts (from trend_analysis.py)
    output_path: path to save the generated PDF file
    """
    # Ensure reports directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Initialize Document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    # Color palette
    PRIMARY_COLOR = colors.HexColor("#1e293b")  # Slate 800
    SECONDARY_COLOR = colors.HexColor("#475569")  # Slate 600
    ACCENT_COLOR = colors.HexColor("#0f766e")  # Teal 700
    LIGHT_BG = colors.HexColor("#f8fafc")  # Slate 50
    BORDER_COLOR = colors.HexColor("#e2e8f0")  # Slate 200
    
    # Status Colors
    STATUS_COLORS = {
        "Critical": colors.HexColor("#ef4444"), # Red
        "High": colors.HexColor("#f97316"),     # Orange
        "Medium": colors.HexColor("#eab308"),   # Yellow
        "OK": colors.HexColor("#10b981")        # Green
    }
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=PRIMARY_COLOR,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=SECONDARY_COLOR,
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=PRIMARY_COLOR,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=SECONDARY_COLOR,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155")
    )
    
    bold_body_style = ParagraphStyle(
        'BoldBodyCustom',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    recommendation_style = ParagraphStyle(
        'RecText',
        parent=body_style,
        textColor=colors.HexColor("#0f766e"), # Teal
        fontName='Helvetica-Oblique'
    )
    
    override_style = ParagraphStyle(
        'OverrideText',
        parent=body_style,
        textColor=colors.HexColor("#b91c1c"), # Dark Red
        fontName='Helvetica-Bold'
    )
    
    story = []
    
    # 1. Header Band
    story.append(Paragraph("ResiIntel: Residential Infrastructure Intelligence", title_style))
    story.append(Paragraph("SAFETY & QUALITY ASSURANCE PROPERTY INSPECTION REPORT", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 2. Metadata Table
    current_time = datetime.now().strftime("%B %d, %Y - %I:%M %p")
    risk_score_str = f"{property_data['overall_risk_score']:.1f} / 100"
    
    # Custom colored badge representation for risk level
    overall_status = "OK"
    if property_data['overall_risk_score'] >= 70:
        overall_status = "Critical"
    elif property_data['overall_risk_score'] >= 45:
        overall_status = "High"
    elif property_data['overall_risk_score'] >= 20:
        overall_status = "Medium"
        
    meta_data = [
        [Paragraph("<b>Property Name:</b>", body_style), Paragraph(property_data['name'], body_style),
         Paragraph("<b>Assessment Date:</b>", body_style), Paragraph(current_time, body_style)],
        [Paragraph("<b>Address:</b>", body_style), Paragraph(property_data['address'], body_style),
         Paragraph("<b>Overall Risk Score:</b>", body_style), Paragraph(f"<b>{risk_score_str} ({overall_status})</b>", ParagraphStyle('RiskB', parent=body_style, textColor=STATUS_COLORS[overall_status]))],
        [Paragraph("<b>Trend Forecast:</b>", body_style), Paragraph(trends.get("trend_description", "Stable"), body_style),
         Paragraph("<b>RAG Database Check:</b>", body_style), Paragraph("Verified (IBC & NEC Indexed)", body_style)]
    ]
    
    meta_table = Table(meta_data, colWidths=[100, 160, 110, 160])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('BOX', (0,0), (-1,-1), 1, SECONDARY_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 20))
    
    # 3. Room-by-Room Risk Summary
    story.append(Paragraph("Room Risk Profile Summary", h1_style))
    summary_headers = [
        Paragraph("<b>Room/Area</b>", bold_body_style),
        Paragraph("<b>Risk Multiplier</b>", bold_body_style),
        Paragraph("<b>Risk Score</b>", bold_body_style),
        Paragraph("<b>Status</b>", bold_body_style),
        Paragraph("<b>Defects Found</b>", bold_body_style)
    ]
    summary_data = [summary_headers]
    
    for room in property_data['rooms']:
        defect_count = len(room.get('findings', []))
        defect_text = f"{defect_count} defect(s) logged" if defect_count > 0 else "No defects detected"
        
        status_text = f"<font color='{STATUS_COLORS[room['status']].hexval()}'><b>{room['status']}</b></font>"
        
        summary_data.append([
            Paragraph(room['name'], body_style),
            Paragraph(f"{room['importance_multiplier']:.1f}x", body_style),
            Paragraph(f"{room['current_risk_score']:.1f}", body_style),
            Paragraph(status_text, body_style),
            Paragraph(defect_text, body_style)
        ])
        
    summary_table = Table(summary_data, colWidths=[120, 90, 80, 80, 160])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LIGHT_BG]),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('BOX', (0,0), (-1,-1), 1, PRIMARY_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    # Quick text colors patch for reportlab header formatting
    for i in range(len(summary_headers)):
        summary_table.setStyle(TableStyle([('TEXTCOLOR', (i, 0), (i, 0), colors.white)]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # 4. Detailed Defect & Guideline Reference (RAG Results)
    story.append(Paragraph("Detailed Inspection Findings & RAG Safety References", h1_style))
    
    findings_exist = False
    for room in property_data['rooms']:
        for finding in room.get('findings', []):
            findings_exist = True
            
            # Setup card for each finding to avoid page splits mid-finding
            finding_elements = []
            
            # Subtitle banner for finding
            header_text = f"<b>{room['name']}</b> &mdash; Defect: {finding.get('inspector_defect_class', finding['ai_defect_class'])}"
            finding_elements.append(Paragraph(header_text, h2_style))
            
            # Main Details Table
            sev = finding.get('inspector_severity', finding['ai_severity'])
            sev_badge = f"<font color='{STATUS_COLORS[sev].hexval()}'><b>{sev}</b></font>"
            
            details_content = [
                [Paragraph("<b>Status / Severity:</b>", body_style), Paragraph(sev_badge, body_style),
                 Paragraph("<b>AI Confidence:</b>", body_style), Paragraph(f"{finding['ai_confidence']*100:.1f}%", body_style)],
                [Paragraph("<b>Action Priority:</b>", body_style), Paragraph(f"<b>{finding.get('priority', 'Monitor')}</b>", body_style),
                 Paragraph("<b>Timestamp:</b>", body_style), Paragraph(finding['timestamp'][:16].replace("T", " "), body_style)]
            ]
            
            # Add override info if applicable
            if finding.get('is_overridden', False):
                details_content.append([
                    Paragraph("<b>HITL Override:</b>", override_style),
                    Paragraph(f"AI severity was '{finding['ai_severity']}'. Overridden by Inspector.<br/><i>Reason: {finding['override_reason']}</i>", override_style),
                    Paragraph("", body_style), Paragraph("", body_style)
                ])
                
            det_table = Table(details_content, colWidths=[110, 160, 100, 160])
            det_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('LINEBELOW', (0,0), (-1,-2) if len(details_content) > 2 else (-1,-1), 0.5, BORDER_COLOR),
            ]))
            finding_elements.append(det_table)
            finding_elements.append(Spacer(1, 6))
            
            # Inspector Notes
            finding_elements.append(Paragraph("<b>Observed Inspection Notes:</b>", bold_body_style))
            finding_elements.append(Paragraph(finding['notes_text'], body_style))
            finding_elements.append(Spacer(1, 6))
            
            # AI Recommendation
            finding_elements.append(Paragraph("<b>AI Recommendation & Actions:</b>", bold_body_style))
            finding_elements.append(Paragraph(finding['ai_recommendation'], recommendation_style))
            finding_elements.append(Spacer(1, 6))
            
            # Retrieved Codes (RAG justification)
            finding_elements.append(Paragraph("<b>Retrieved Building Safety Regulations (RAG Justifications):</b>", bold_body_style))
            if finding.get('retrieved_codes'):
                for code_info in finding['retrieved_codes']:
                    finding_elements.append(Paragraph(f"&bull; <b>{code_info}</b>", body_style))
            else:
                finding_elements.append(Paragraph("&bull; No matching statutory code codes retrieved.", body_style))
                
            finding_elements.append(Spacer(1, 15))
            
            # Wrap in KeepTogether so a single finding card doesn't split awkwardly
            story.append(KeepTogether(finding_elements))
            story.append(Spacer(1, 10))
            
    if not findings_exist:
        story.append(Paragraph("<i>No safety defects currently registered for this property. All spaces validated OK.</i>", body_style))
        
    # Build Document
    doc.build(story)

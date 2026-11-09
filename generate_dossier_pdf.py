import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "CartMate — Strategic Product Dossier & Architectural Handoff")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 742, letter[0] - 54, 742)

        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 36, footer_text)
        self.drawString(54, 36, "CONFIDENTIAL — Prepared for Engineering & AI Handoff (Claude)")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 48, letter[0] - 54, 48)
        
        self.restoreState()

def build_pdf(filename="CartMate_Product_Dossier_and_Handoff.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom palette
    primary = colors.HexColor("#0f172a")     # Slate 900
    accent = colors.HexColor("#2563eb")      # Blue 600
    danger = colors.HexColor("#dc2626")      # Red 600
    warning = colors.HexColor("#d97706")     # Amber 600
    success = colors.HexColor("#16a34a")     # Green 600
    text_dark = colors.HexColor("#1e293b")   # Slate 800
    text_muted = colors.HexColor("#475569")  # Slate 600
    bg_light = colors.HexColor("#f8fafc")    # Slate 50
    border_color = colors.HexColor("#e2e8f0")# Slate 200

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary,
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=accent,
        spaceAfter=14
    )
    
    h1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary,
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=accent,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=text_dark,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=14,
        bulletIndent=4,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark
    )

    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=primary
    )

    story = []

    # Title block
    story.append(Paragraph("CARTMATE: PRODUCT DOSSIER & STRATEGIC AUDIT", title_style))
    story.append(Paragraph("Full Architecture, Critique of the Loneliness Problem, Codebase Audit & Claude Handoff", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent, spaceBefore=2, spaceAfter=12))

    # Metadata Card
    meta_data = [
        [
            Paragraph("<b>Project:</b> CartMate", body_style),
            Paragraph("<b>Target Market:</b> Katowice / GZM (Poland)", body_style),
            Paragraph("<b>Status:</b> Pre-Pilot Architecture", body_style)
        ],
        [
            Paragraph("<b>Author:</b> Abishek Venkateswari Ramesh", body_style),
            Paragraph("<b>Tech Stack:</b> FastAPI, SQLite, React 19, Capacitor", body_style),
            Paragraph("<b>Date:</b> November 2026", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[170, 180, 154])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # SECTION 1: EXECUTIVE SUMMARY
    story.append(Paragraph("1. Executive Summary & Core Mission", h1_style))
    story.append(Paragraph(
        "CartMate was conceived to combat the pervasive modern epidemic of loneliness and social isolation. "
        "Unlike dating applications (which induce romantic anxiety and swiping fatigue) or commercial gig platforms (focused on courier delivery and tasks), "
        "CartMate was designed to help adults find low-pressure companionship for ordinary life activities—such as outdoor walks, study sessions, workouts, casual meals, and everyday errands. "
        "Its philosophical foundation emphasizes high safety, mutual agreement, transparent spending terms, and blame-free cancellation.",
        body_style
    ))
    story.append(Paragraph(
        "While technically well-engineered with 240+ automated tests, this dossier identifies fundamental human-psychology bottlenecks in the current 1-on-1 model and establishes "
        "a concrete blueprint to pivot toward <b>3-to-5 person micro-pods</b> anchored in physical 'third places'.",
        body_style
    ))

    # SECTION 2: SYSTEM ARCHITECTURE
    story.append(Paragraph("2. Current System Architecture & Implementation", h1_style))
    
    arch_data = [
        [Paragraph("<b>Component</b>", body_style), Paragraph("<b>Technology Stack</b>", body_style), Paragraph("<b>Implementation Detail & Invariants</b>", body_style)],
        [
            Paragraph("<b>Frontend Client</b>", body_style),
            Paragraph("React 19, TypeScript, Vite 8, Tailwind CSS v4, MapLibre GL", body_style),
            Paragraph("Responsive web application with PWA capabilities. Serves map visualization, real-time WebSocket chat, trip coordination dialogs, and PIN handshakes.", body_style)
        ],
        [
            Paragraph("<b>Mobile Wrapper</b>", body_style),
            Paragraph("Capacitor 8 / Android", body_style),
            Paragraph("Android debug APK project wrapping the web bundle. Requires specific origin binding for production use.", body_style)
        ],
        [
            Paragraph("<b>Backend API</b>", body_style),
            Paragraph("FastAPI, Pydantic v2, Uvicorn, Python 3.12", body_style),
            Paragraph("Unified REST + WebSocket server. Enforces object-level authorization, rate limiting, and redacts one-use WS tickets from logs.", body_style)
        ],
        [
            Paragraph("<b>Persistence</b>", body_style),
            Paragraph("SQLite in WAL Mode", body_style),
            Paragraph("Single-writer atomic transactions, strict foreign keys, and ordered migrations (Migrations 1–10). Persistent named volume storage.", body_style)
        ],
        [
            Paragraph("<b>Safety & Moderation</b>", body_style),
            Paragraph("Deterministic Rules + Jev AI Classifier", body_style),
            Paragraph("Jev runs in advisory shadow mode (flags abuse for human operators). Immediate block/report severance. Direct emergency dialer (tel:112).", body_style)
        ]
    ]
    arch_table = Table(arch_data, colWidths=[100, 150, 254])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 10))

    # SECTION 3: THE CORE PROBLEM & CRITIQUE
    story.append(Paragraph("3. The Psychological & Strategic Dilemma: Why 1-on-1 Stranger Outings Struggle", h1_style))
    story.append(Paragraph(
        "Extensive analysis of the user journey reveals three structural tensions in the 1-on-1 stranger outing concept:",
        body_style
    ))
    
    critique_items = [
        ("The Burden of 1-on-1 Awkwardness:", 
         "Meeting an absolute stranger 1-on-1 for mundane tasks (e.g., buying groceries or taking a stroll) carries massive conversational burden. Dating apps survive this because romantic hope/attraction justifies the awkwardness. Hobby groups survive because shared passion (e.g., bouldering) fills conversational voids. A 1-on-1 errand has neither, creating acute social performance anxiety."),
        
        ("The Safety Priming Paradox:", 
         "CartMate's user interface is dominated by security mechanisms: PIN verification handshakes, SOS emergency dialers, explicit legal disclaimers, and rigorous check-ins. While designed to protect, this heavy emphasis psychologically primes users to perceive the encounter as inherently dangerous, elevating apprehension before they even leave home."),
        
        ("The Hyperlocal Liquidity Trap ('Empty Shelf'):", 
         "1-on-1 coordination requires immediate double coincidence of wants: matching two adults in the exact same neighborhood (within 1-2 km) at the exact same hour with identical activity intents. In early-stage pilots, liquidity is near zero, leading users to open the app, find no nearby partner, and uninstall immediately."),
        
        ("The Loneliness Paradox:", 
         "Sociological research shows individuals suffering from severe loneliness often experience elevated social anxiety. Forcing an anxious, lonely individual into a direct 1-on-1 encounter with an unvetted stranger asks for the highest possible emotional friction.")
    ]
    
    for title, desc in critique_items:
        story.append(Paragraph(f"• <b>{title}</b> {desc}", bullet_style))
    
    story.append(Spacer(1, 10))

    # SECTION 4: CURRENT TECHNICAL & OPERATIONAL BLOCKERS
    story.append(Paragraph("4. Concrete Technical & Operational Blockers (Audit Findings)", h1_style))
    
    blockers = [
        [Paragraph("<b>Domain</b>", body_style), Paragraph("<b>Specific Bottleneck</b>", body_style), Paragraph("<b>Severity & Impact</b>", body_style)],
        [
            Paragraph("<b>Identity & Age Gate</b>", body_style),
            Paragraph("Strict 18+ policy is enforced fail-closed, but carrier SMS only proves phone control. In staging, verification relies on in-person, operator-witnessed physical ID / mDowód inspection. No scalable, privacy-preserving automated age provider exists in production.", body_style),
            Paragraph("<font color='#dc2626'><b>CRITICAL (P0)</b></font><br/>Completely blocks open public onboarding.", body_style)
        ],
        [
            Paragraph("<b>Frontend UX & Bundle</b>", body_style),
            Paragraph("UI rated 6/10 in UX audit. Competes between 4 distinct discovery patterns (Feed, Deck, Map, Hotspot voting). Small font sizes (9-11px) and overlapping badge treatments. MapLibre (~1.06 MB) and main bundle (~547 KB) cause chunk warnings and sluggish mobile performance.", body_style),
            Paragraph("<font color='#d97706'><b>HIGH (P1)</b></font><br/>High drop-off and cognitive fatigue.", body_style)
        ],
        [
            Paragraph("<b>Backend Scaling</b>", body_style),
            Paragraph("FastAPI runs as a single process with in-memory WebSocket connection dictionaries and local SQLite WAL disk storage. It cannot horizontally scale across multiple instances without an external broker (Redis/PubSub) and centralized DB.", body_style),
            Paragraph("<font color='#d97706'><b>MEDIUM (P2)</b></font><br/>Fine for closed pilot (<=50 users); requires rewrite for growth.", body_style)
        ],
        [
            Paragraph("<b>Human Verification Gates</b>", body_style),
            Paragraph("Gates H-01 through H-06 (physical handset testing over live cellular HTTPS/WSS, real multi-party emergency drill, offsite S3 restore, 24/7 human moderation coverage) remain strictly NOT RUN.", body_style),
            Paragraph("<font color='#dc2626'><b>HIGH (P1)</b></font><br/>Legal and moral exposure during offline incidents.", body_style)
        ]
    ]
    b_table = Table(blockers, colWidths=[90, 270, 144])
    b_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(b_table)
    story.append(Spacer(1, 10))

    # SECTION 5: THE STRATEGIC PIVOT
    story.append(Paragraph("5. The Strategic Transformation: Micro-Pods & Third Places", h1_style))
    story.append(Paragraph(
        "To fulfill the founder's vision of genuinely defeating loneliness, CartMate should pivot from 1-on-1 ad-hoc errands to <b>3-to-5 Person Micro-Pods anchored in Third Places</b>:",
        body_style
    ))
    
    pivot_points = [
        ("Pivot to Micro-Pods (3 to 5 participants):", 
         "A small pod eliminates conversational strain. If one person is quiet or introverted, the group momentum sustains the social interaction naturally. Furthermore, groups create natural safety in public without requiring intimidating security rituals."),
        
        ("Anchor in Known 'Third Places':", 
         "Instead of negotiating vague GPS coordinates, outings should anchor to fixed, reliable community hubs (e.g., 'Central Library Study Floor', 'Silesia Park Fountain Loop', 'Main Square Café Table'). This eliminates meetup confusion and feels universally safe."),
        
        ("Structured Activity Intent (Contextual Crutches):", 
         "Replace arbitrary hangouts with structured activity formats that provide their own focal point: (1) <i>Co-working / Study Sprint</i> (45m focus + 15m coffee); (2) <i>Park Walk & Talk</i> (defined 45m loop); (3) <i>Casual Board Game / Cards</i>; (4) <i>Language Exchange Table</i>."),
        
        ("Closed-Community Pilot Rollout (Campus / Hubs):", 
         "Bypass the impossible cold-start problem by deploying CartMate as an invite-only tool for established cohorts—such as university students or local tech co-working spaces in Katowice. Pre-existing institutional trust solves the identity/age dilemma without invasive government ID checks.")
    ]
    for p_title, p_desc in pivot_points:
        story.append(Paragraph(f"• <b>{p_title}</b> {p_desc}", bullet_style))

    story.append(Spacer(1, 10))

    # SECTION 6: ACTIONABLE SPEC & PROMPT FOR CLAUDE
    story.append(Paragraph("6. Directive & Engineering Blueprint for Claude", h1_style))
    story.append(Paragraph(
        "When continuing work on this codebase with Claude, provide the following engineering priorities and directives:",
        body_style
    ))

    claude_prompt_box = [
        [
            Paragraph(
                "<b>INSTRUCTIONS FOR CLAUDE (SYSTEM & ARCHITECTURE PROMPT):</b><br/><br/>"
                "1. <b>Preserve the Single-Writer Integrity:</b> The repository is structured around SQLite WAL with strict migration numbering. Do not bypass migrations or corrupt <code>cartmate.db</code>.<br/>"
                "2. <b>Refactor Frontend Discovery into a Single Clean Feed:</b> Deprecate the splintered Deck, Map, and Hotspot tabs in <code>frontend/src/</code>. Build a unified mobile-first feed answering one question: <i>'What micro-pods are happening near me today?'</i>.<br/>"
                "3. <b>Promote Group Threshold Formation:</b> In <code>backend/main.py</code> and <code>backend/storage.py</code>, elevate existing Hotspot threshold logic into primary Outing entities with dynamic slot counters (e.g., <code>min_participants: 3, max_participants: 5</code>). Unlock group chat only when quorum (3) is reached.<br/>"
                "4. <b>Bundle Optimization:</b> Dynamic-import <code>maplibre-gl</code> so initial bundle load remains under 250 KB on mobile.<br/>"
                "5. <b>Structured Activity Templates:</b> Implement explicit backend schemas and frontend UI for the 4 core anchor templates (Walk, Study/Co-work, Board Game, Language Exchange).<br/>"
                "6. <b>Pragmatic Onboarding:</b> Transition the age/admission gate to support cohort/voucher tokens (e.g., university/organization partner codes) to allow smooth pilot onboarding without manual in-person inspection.",
                callout_style
            )
        ]
    ]
    c_table = Table(claude_prompt_box, colWidths=[504])
    c_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, accent),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(c_table)

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built at: {os.path.abspath(filename)}")

if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "CartMate_Product_Dossier_and_Handoff.pdf"
    build_pdf(output_path)

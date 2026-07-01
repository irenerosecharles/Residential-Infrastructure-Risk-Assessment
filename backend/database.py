import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "resiintel.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes the SQLite database tables and seeds them if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Properties Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            overall_risk_score REAL DEFAULT 0.0
        )
    """)
    
    # 2. Rooms Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            property_id TEXT NOT NULL,
            name TEXT NOT NULL,
            importance_multiplier REAL DEFAULT 1.0,
            current_risk_score REAL DEFAULT 0.0,
            status TEXT DEFAULT 'OK',
            FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE
        )
    """)
    
    # 3. Findings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS findings (
            id TEXT PRIMARY KEY,
            room_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            image_url TEXT,
            notes_text TEXT NOT NULL,
            ai_defect_class TEXT NOT NULL,
            ai_severity TEXT NOT NULL,
            ai_confidence REAL NOT NULL,
            inspector_defect_class TEXT,
            inspector_severity TEXT,
            is_overridden INTEGER DEFAULT 0,
            override_reason TEXT,
            override_by TEXT,
            retrieved_codes TEXT, -- Stored as comma-separated or JSON string
            ai_recommendation TEXT,
            priority TEXT DEFAULT 'Monitor',
            repeat_count INTEGER DEFAULT 1,
            FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE
        )
    """)
    
    # 4. Risk History Table (Auditing risk score progression)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            score REAL NOT NULL,
            FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE
        )
    """)
    
    # 5. Audit Timeline Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL, -- 'info', 'defect_detected', 'inspector_override', 'validation_failed'
            message TEXT NOT NULL,
            FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    
    # Seed data if empty
    cursor.execute("SELECT COUNT(*) FROM properties")
    if cursor.fetchone()[0] == 0:
        seed_database(conn)
        
    conn.close()

def seed_database(conn):
    cursor = conn.cursor()
    
    # Seed Properties
    properties = [
        ("prop-01", "Grandview Apartments - Unit 405", "405 Grandview Ave, Sector 4", 72.5),
        ("prop-02", "Oakwood Villa", "12 Pine Rd, Oakwood Hills", 38.4),
        ("prop-03", "Pinecrest Heights - Unit 12B", "77 Valley View Vista, Pinecrest", 0.0)
    ]
    cursor.executemany("INSERT INTO properties VALUES (?, ?, ?, ?)", properties)
    
    # Seed Rooms
    rooms = [
        # Grandview Unit 405
        ("room-01-kitchen", "prop-01", "Kitchen", 1.3, 93.6, "Critical"),
        ("room-01-bathroom", "prop-01", "Bathroom", 1.2, 64.8, "High"),
        ("room-01-living", "prop-01", "Living Room", 1.0, 38.0, "Medium"),
        ("room-01-bedroom", "prop-01", "Bedroom 1", 1.1, 0.0, "OK"),
        # Oakwood Villa
        ("room-02-kitchen", "prop-02", "Kitchen", 1.3, 0.0, "OK"),
        ("room-02-living", "prop-02", "Living Room", 1.0, 0.0, "OK"),
        ("room-02-garage", "prop-02", "Garage", 1.0, 80.0, "High"),
        ("room-02-bedroom", "prop-02", "Master Bedroom", 1.1, 0.0, "OK"),
        # Pinecrest Unit 12B
        ("room-03-living", "prop-03", "Living Area", 1.0, 0.0, "OK"),
        ("room-03-kitchen", "prop-03", "Kitchenette", 1.3, 0.0, "OK"),
        ("room-03-bedroom", "prop-03", "Sleeping Area", 1.1, 0.0, "OK")
    ]
    cursor.executemany("INSERT INTO rooms VALUES (?, ?, ?, ?, ?, ?)", rooms)
    
    # Seed Findings
    findings = [
        ("find-01-01", "room-01-kitchen", "2026-06-27T10:30:00Z", "/assets/exposed_wiring.jpg",
         "Observed bare cables hanging from the ceiling junction box above the stove. No cover plate or conduit installed.",
         "Exposed Wiring", "Critical", 0.96, "Exposed Wiring", "Critical", 0, "", "",
         json.dumps(["NEC-300.11"]), 
         "IMMEDIATE HAZARD: Exposed live wiring in active food preparation zone. Enclose wires in approved conduits and install cover plate immediately.",
         "Immediate Action", 1),
         
        ("find-01-02", "room-01-bathroom", "2026-06-24T14:15:00Z", "/assets/damp_wall.jpg",
         "Water stains on the drywall adjacent to the shower. The surface feels damp to the touch.",
         "Building Envelope Moisture Control", "High", 0.90, "Building Envelope Moisture Control", "High", 0, "", "",
         json.dumps(["IRC-R703"]),
         "Inspect tiling grout and shower seal. Use dehumidifier to dry area and prevent mold growth.",
         "Within 24 Hours", 1),
         
        ("find-01-03", "room-01-living", "2026-06-26T16:45:00Z", "/assets/loose_carpet.jpg",
         "Living room carpet is loose and buckling near the transition strip to the hallway.",
         "Uneven Stair Treads and Floor Finishes", "Medium", 0.85, "Uneven Stair Treads and Floor Finishes", "Low", 1,
         "Low traffic area, minor trip hazard only. Downgraded to Low severity.", "Inspector-01",
         json.dumps(["IRC-R311"]),
         "Stretch carpet and re-tack at transition strip to prevent minor trip hazard.",
         "Schedule Inspection", 1),
         
        ("find-02-01", "room-02-garage", "2026-06-27T11:00:00Z", "/assets/structural_crack.jpg",
         "Horizontal crack observed along the concrete support column, approximately 3.5mm wide.",
         "Structural Cracks and Foundation Settling", "Critical", 0.80, "Structural Cracks and Foundation Settling", "High", 1,
         "No signs of widening since last year, but needs tracking. Changed to High.", "Inspector-01",
         json.dumps(["IBC-1803.5"]),
         "Consult structural engineer to monitor column stability and evaluate foundation settling.",
         "Within 24 Hours", 1)
    ]
    cursor.executemany("""
        INSERT INTO findings (
            id, room_id, timestamp, image_url, notes_text, ai_defect_class, ai_severity, ai_confidence,
            inspector_defect_class, inspector_severity, is_overridden, override_reason, override_by,
            retrieved_codes, ai_recommendation, priority, repeat_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, findings)
    
    # Seed Risk History
    history = [
        ("prop-01", "2026-06-22T09:00:00Z", 10.0),
        ("prop-01", "2026-06-23T11:30:00Z", 10.0),
        ("prop-01", "2026-06-24T14:15:00Z", 38.5),
        ("prop-01", "2026-06-25T10:00:00Z", 38.5),
        ("prop-01", "2026-06-26T16:45:00Z", 45.0),
        ("prop-01", "2026-06-27T10:30:00Z", 72.5),
        
        ("prop-02", "2026-06-17T10:00:00Z", 5.0),
        ("prop-02", "2026-06-22T14:30:00Z", 5.0),
        ("prop-02", "2026-06-27T11:00:00Z", 38.4),
        
        ("prop-03", "2026-06-25T11:00:00Z", 0.0),
        ("prop-03", "2026-06-27T12:00:00Z", 0.0)
    ]
    cursor.executemany("INSERT INTO risk_history (property_id, timestamp, score) VALUES (?, ?, ?)", history)
    
    # Seed Timeline
    timeline = [
        ("prop-01", "2026-06-22T09:00:00Z", "info", "Property inspection started. Baseline risk score initialized."),
        ("prop-01", "2026-06-24T14:15:00Z", "defect_detected", "Damp wall detected in Bathroom. Risk score increased."),
        ("prop-01", "2026-06-26T16:45:00Z", "defect_detected", "Loose floor finishing detected in Living Room. AI flagged Medium severity."),
        ("prop-01", "2026-06-26T16:50:00Z", "inspector_override", "Inspector downgraded Living Room finish defect from Medium to Low."),
        ("prop-01", "2026-06-27T10:30:00Z", "defect_detected", "CRITICAL: Exposed wiring detected in Kitchen. Room status marked Critical."),
        
        ("prop-02", "2026-06-17T10:00:00Z", "info", "Property baseline registered. Structure appears intact."),
        ("prop-02", "2026-06-27T11:00:00Z", "defect_detected", "Structural crack detected in Garage. AI flagged Critical severity."),
        ("prop-02", "2026-06-27T11:05:00Z", "inspector_override", "Inspector modified Garage structural crack severity to High.")
    ]
    cursor.executemany("INSERT INTO timeline (property_id, timestamp, event_type, message) VALUES (?, ?, ?, ?)", timeline)
    
    conn.commit()

def calculate_room_risk_score(cursor, room_id):
    """
    Calculates Room Risk Score using the refined formula:
    Risk = Severity Weight * Confidence * Room Multiplier * Repeat Defect Multiplier
    Capped at 100.
    """
    cursor.execute("SELECT importance_multiplier FROM rooms WHERE id = ?", (room_id,))
    room = cursor.fetchone()
    if not room:
        return 0.0
    multiplier = room["importance_multiplier"]
    
    # Fetch all active findings for this room
    cursor.execute("""
        SELECT 
            COALESCE(inspector_severity, ai_severity) as severity,
            ai_confidence,
            COALESCE(inspector_defect_class, ai_defect_class) as defect_class
        FROM findings 
        WHERE room_id = ?
    """, (room_id,))
    
    findings = cursor.fetchall()
    if not findings:
        return 0.0
        
    severity_weights = {
        "Critical": 40.0,
        "High": 25.0,
        "Medium": 12.0,
        "Low": 5.0
    }
    
    # Calculate defect category repetition counts
    category_counts = {}
    total_raw_risk = 0.0
    
    for f in findings:
        cat = f["defect_class"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
        weight = severity_weights.get(f["severity"], 5.0)
        confidence = f["ai_confidence"]
        
        # Base defect risk
        defect_risk = weight * confidence
        total_raw_risk += defect_risk
        
    # Calculate Repeat Defect Multiplier: 1 + (N - 1) * 0.2
    # We find the max repeat count among the defect categories
    max_repeats = max(category_counts.values()) if category_counts else 1
    repeat_multiplier = 1.0 + (max_repeats - 1) * 0.2
    
    # Calculate final room risk
    room_risk = total_raw_risk * multiplier * repeat_multiplier
    return min(100.0, room_risk)

def get_room_status_by_score(score):
    if score >= 70.0:
        return "Critical"
    elif score >= 45.0:
        return "High"
    elif score >= 20.0:
        return "Medium"
    else:
        return "OK"

def update_property_and_room_scores(cursor, property_id):
    """
    Recalculates risk scores for all rooms in a property, updates them,
    recalculates the overall property risk score as a weighted average, and updates it.
    """
    # 1. Fetch all rooms
    cursor.execute("SELECT id, importance_multiplier FROM rooms WHERE property_id = ?", (property_id,))
    rooms = cursor.fetchall()
    
    sum_room_weights = 0.0
    sum_weighted_scores = 0.0
    
    for r in rooms:
        room_id = r["id"]
        room_mult = r["importance_multiplier"]
        
        room_score = calculate_room_risk_score(cursor, room_id)
        room_status = get_room_status_by_score(room_score)
        
        # Update Room
        cursor.execute("""
            UPDATE rooms 
            SET current_risk_score = ?, status = ?
            WHERE id = ?
        """, (room_score, room_status, room_id))
        
        sum_room_weights += room_mult
        sum_weighted_scores += (room_score * room_mult)
        
    # Calculate Property overall score
    overall_score = 0.0
    if sum_room_weights > 0:
        overall_score = sum_weighted_scores / sum_room_weights
    overall_score = min(100.0, overall_score)
    
    # Update Property
    cursor.execute("UPDATE properties SET overall_risk_score = ? WHERE id = ?", (overall_score, property_id))
    return overall_score

# API Data Fetching Helpers

def get_all_properties_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties")
    rows = cursor.fetchall()
    properties = []
    for r in rows:
        p_dict = dict(r)
        
        # Get count of high/critical rooms
        cursor.execute("""
            SELECT COUNT(*) FROM rooms 
            WHERE property_id = ? AND status IN ('High', 'Critical')
        """, (p_dict["id"],))
        p_dict["high_risk_rooms_count"] = cursor.fetchone()[0]
        
        properties.append(p_dict)
    conn.close()
    return properties

def get_property_details(property_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get Property
    cursor.execute("SELECT * FROM properties WHERE id = ?", (property_id,))
    p_row = cursor.fetchone()
    if not p_row:
        conn.close()
        return None
    property_data = dict(p_row)
    
    # Get Rooms
    cursor.execute("SELECT * FROM rooms WHERE property_id = ?", (property_id,))
    rooms = []
    for r_row in cursor.fetchall():
        r_dict = dict(r_row)
        
        # Get findings for this room
        cursor.execute("SELECT * FROM findings WHERE room_id = ?", (r_dict["id"],))
        findings = []
        for f_row in cursor.fetchall():
            f_dict = dict(f_row)
            # Parse JSON retrieved codes
            try:
                f_dict["retrieved_codes"] = json.loads(f_dict["retrieved_codes"])
            except Exception:
                f_dict["retrieved_codes"] = []
            findings.append(f_dict)
            
        r_dict["findings"] = findings
        rooms.append(r_dict)
        
    property_data["rooms"] = rooms
    
    # Get history
    cursor.execute("SELECT timestamp, score FROM risk_history WHERE property_id = ? ORDER BY timestamp ASC", (property_id,))
    property_data["risk_history"] = [dict(h) for h in cursor.fetchall()]
    
    # Get timeline
    cursor.execute("SELECT timestamp, event_type, message FROM timeline WHERE property_id = ? ORDER BY timestamp DESC", (property_id,))
    property_data["timeline"] = [dict(t) for t in cursor.fetchall()]
    
    conn.close()
    return property_data

def insert_new_finding(room_id, image_url, notes_text, ai_data, retrieved_codes, recommendations, priority):
    """
    Inserts a new finding into the database and recalculates metrics.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get property ID
    cursor.execute("SELECT property_id, name FROM rooms WHERE id = ?", (room_id,))
    room_info = cursor.fetchone()
    if not room_info:
        conn.close()
        return None
    property_id = room_info["property_id"]
    room_name = room_info["name"]
    
    finding_id = f"find-{datetime.now().strftime('%m%d%H%M%S')}"
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Count repeats of the same defect category in this room
    cursor.execute("""
        SELECT COUNT(*) FROM findings 
        WHERE room_id = ? AND COALESCE(inspector_defect_class, ai_defect_class) = ?
    """, (room_id, ai_data["defect_class"]))
    existing_count = cursor.fetchone()[0]
    repeat_count = existing_count + 1
    
    cursor.execute("""
        INSERT INTO findings (
            id, room_id, timestamp, image_url, notes_text, ai_defect_class, ai_severity, ai_confidence,
            retrieved_codes, ai_recommendation, priority, repeat_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        finding_id, room_id, timestamp, image_url, notes_text,
        ai_data["defect_class"], ai_data["severity"], ai_data["confidence"],
        json.dumps(retrieved_codes), recommendations, priority, repeat_count
    ))
    
    # Log timeline event
    msg = f"Defect '{ai_data['defect_class']}' ({ai_data['severity']}) detected in {room_name}."
    if repeat_count > 1:
        msg += f" (Repeat defect detected: count={repeat_count})"
        
    cursor.execute("""
        INSERT INTO timeline (property_id, timestamp, event_type, message)
        VALUES (?, ?, 'defect_detected', ?)
    """, (property_id, timestamp, msg))
    
    # Update scores
    new_overall_score = update_property_and_room_scores(cursor, property_id)
    
    # Write to risk history
    cursor.execute("""
        INSERT INTO risk_history (property_id, timestamp, score)
        VALUES (?, ?, ?)
    """, (property_id, timestamp, new_overall_score))
    
    conn.commit()
    conn.close()
    return finding_id

def save_inspector_override(finding_id, inspector_defect, inspector_severity, override_reason, override_by):
    """
    Saves inspector override parameters, updates scores and history.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find room and property info
    cursor.execute("""
        SELECT f.room_id, r.property_id, r.name as room_name, f.ai_severity, f.ai_defect_class
        FROM findings f
        JOIN rooms r ON f.room_id = r.id
        WHERE f.id = ?
    """, (finding_id,))
    finding_info = cursor.fetchone()
    if not finding_info:
        conn.close()
        return False
        
    room_id = finding_info["room_id"]
    property_id = finding_info["property_id"]
    room_name = finding_info["room_name"]
    ai_sev = finding_info["ai_severity"]
    ai_def = finding_info["ai_defect_class"]
    
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Update finding
    cursor.execute("""
        UPDATE findings
        SET inspector_defect_class = ?,
            inspector_severity = ?,
            is_overridden = 1,
            override_reason = ?,
            override_by = ?
        WHERE id = ?
    """, (inspector_defect, inspector_severity, override_reason, override_by, finding_id))
    
    # Log timeline event
    log_msg = f"Inspector {override_by} overridden finding in {room_name}. "
    if ai_sev != inspector_severity:
        log_msg += f"Severity changed: {ai_sev} ➔ {inspector_severity}. "
    if ai_def != inspector_defect:
        log_msg += f"Category changed: {ai_def} ➔ {inspector_defect}. "
    log_msg += f"Reason: {override_reason}"
    
    cursor.execute("""
        INSERT INTO timeline (property_id, timestamp, event_type, message)
        VALUES (?, ?, 'inspector_override', ?)
    """, (property_id, timestamp, log_msg))
    
    # Update scores
    new_overall_score = update_property_and_room_scores(cursor, property_id)
    
    # Write to risk history
    cursor.execute("""
        INSERT INTO risk_history (property_id, timestamp, score)
        VALUES (?, ?, ?)
    """, (property_id, timestamp, new_overall_score))
    
    conn.commit()
    conn.close()
    return True

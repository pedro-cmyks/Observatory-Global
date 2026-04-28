"""
CAMEO (Conflict and Mediation Event Observations) Event Codes mapping.
Translates GDELT EventCodes into human-readable actions.
"""

CAMEO_EVENT_CODES = {
    # 01: MAKE PUBLIC STATEMENT
    "010": "Make statement",
    "011": "Decline comment",
    "012": "Make pessimistic comment",
    "013": "Make optimistic comment",
    "014": "Consider policy option",
    "015": "Acknowledge or claim responsibility",
    "016": "Reject accusation",
    "017": "Engage in symbolic act",
    "018": "Make empathetic comment",
    "019": "Express accord",
    
    # 02: APPEAL
    "020": "Appeal, not specified below",
    "021": "Appeal for material cooperation",
    "0211": "Appeal for economic cooperation",
    "0212": "Appeal for military cooperation",
    "022": "Appeal for diplomatic cooperation",
    "023": "Appeal for aid",
    "024": "Appeal for political reform",
    "025": "Appeal to yield",
    "026": "Appeal to others to meet or negotiate",
    "027": "Appeal to others to settle dispute",
    "028": "Appeal to others to engage in or accept mediation",
    
    # 03: EXPRESS INTENT TO COOPERATE
    "030": "Express intent to cooperate",
    "031": "Express intent to engage in material cooperation",
    "0311": "Express intent to cooperate economically",
    "0312": "Express intent to cooperate militarily",
    "032": "Express intent to provide diplomatic cooperation",
    "033": "Express intent to provide material aid",
    "034": "Express intent to institute political reform",
    "035": "Express intent to yield",
    
    # 04: CONSULT
    "040": "Consult, not specified below",
    "041": "Discuss by telephone",
    "042": "Make a visit",
    "043": "Host a visit",
    "044": "Meet at a 'third' location",
    "045": "Mediate",
    "046": "Engage in negotiation",
    
    # 05: ENGAGE IN DIPLOMATIC COOPERATION
    "050": "Engage in diplomatic cooperation",
    "051": "Praise or endorse",
    "052": "Defend verbally",
    "053": "Rally support on behalf of",
    "054": "Grant asylum",
    "055": "Apologize",
    "056": "Forgive",
    "057": "Sign formal agreement",
    
    # 06: ENGAGE IN MATERIAL COOPERATION
    "060": "Engage in material cooperation",
    "061": "Cooperate economically",
    "062": "Cooperate militarily",
    "063": "Engage in judicial cooperation",
    "064": "Share intelligence or information",
    
    # 07: PROVIDE AID
    "070": "Provide aid, not specified below",
    "071": "Provide economic aid",
    "072": "Provide military aid",
    "073": "Provide humanitarian aid",
    "074": "Provide military protection or peacekeeping",
    "075": "Grant asylum",
    
    # 08: YIELD
    "080": "Yield, not specified below",
    "081": "Ease administrative sanctions",
    "082": "Ease political dissent",
    "083": "Accede to requests or demands",
    "084": "Return, release, not specified below",
    "085": "Surrender territory to",
    "086": "Allow international involvement",
    "087": "De-escalate military engagement",
    
    # 09: INVESTIGATE
    "090": "Investigate, not specified below",
    "091": "Investigate crime, corruption",
    "092": "Investigate human rights abuses",
    "093": "Investigate military action",
    "094": "Investigate war crimes",
    
    # 10: DEMAND
    "100": "Demand, not specified below",
    "101": "Demand material cooperation",
    "102": "Demand diplomatic cooperation",
    "103": "Demand aid",
    "104": "Demand political reform",
    "105": "Demand that target yields",
    
    # 11: DISAPPROVE
    "110": "Disapprove, not specified below",
    "111": "Criticize or denounce",
    "112": "Accuse",
    "113": "Rally opposition against",
    "114": "Complain officially",
    "115": "Bring lawsuit against",
    "116": "Find guilty or condemn",
    
    # 12: REJECT
    "120": "Reject, not specified below",
    "121": "Reject material cooperation",
    "122": "Reject request or demand for material aid",
    "123": "Reject request or demand for political reform",
    "124": "Refuse to yield",
    "125": "Reject proposal to meet, discuss, or negotiate",
    "126": "Reject mediation",
    "127": "Reject plan, agreement to settle dispute",
    "128": "Defy norms, law",
    "129": "Veto",
    
    # 13: THREATEN
    "130": "Threaten, not specified below",
    "131": "Threaten non-force",
    "132": "Threaten with administrative sanctions",
    "133": "Threaten with political dissent",
    "134": "Threaten to halt negotiations",
    "135": "Threaten to halt material or economic assistance",
    "136": "Threaten to suspend international relations",
    "137": "Threaten with repression",
    "138": "Threaten to use military force",
    "139": "Give ultimatum",
    
    # 14: PROTEST
    "140": "Engage in political dissent",
    "141": "Demonstrate or rally",
    "142": "Conduct strike or boycott",
    "143": "Conduct hunger strike",
    "144": "Obstruct passage, block",
    "145": "Protest violently, riot",
    
    # 15: EXHIBIT FORCE POSTURE
    "150": "Demonstrate military or police power",
    "151": "Increase police alert status",
    "152": "Increase military alert status",
    "153": "Mobilize or exacerbate police power",
    "154": "Mobilize or exacerbate armed forces",
    
    # 16: REDUCE RELATIONS
    "160": "Reduce relations, not specified below",
    "161": "Reduce or break diplomatic relations",
    "162": "Reduce or stop material aid",
    "163": "Impose embargo, boycott, or sanctions",
    "164": "Halt negotiations",
    "165": "Halt mediation",
    "166": "Expel or withdraw",
    
    # 17: COERCE
    "170": "Coerce, not specified below",
    "171": "Seize or damage property",
    "172": "Impose administrative sanctions",
    "173": "Arrest, detain, or charge with legal action",
    "174": "Expel or deport individuals",
    "175": "Use tactics of repression",
    
    # 18: ASSAULT
    "180": "Use unconventional violence",
    "181": "Abduct, hijack, or take hostage",
    "182": "Physically assault",
    "183": "Conduct suicide, car, or other non-military bombing",
    "184": "Use as human shield",
    "185": "Attempt to assassinate",
    "186": "Assassinate",
    
    # 19: FIGHT
    "190": "Use conventional military force",
    "191": "Impose blockade, restrict movement",
    "192": "Occupy territory",
    "193": "Fight with small arms and light weapons",
    "194": "Fight with artillery and tanks",
    "195": "Employ aerial weapons",
    "196": "Violate ceasefire",
    
    # 20: USE UNCONVENTIONAL MASS VIOLENCE
    "200": "Use unconventional mass violence",
    "201": "Engage in mass expulsion",
    "202": "Engage in mass killings",
    "203": "Engage in ethnic cleansing",
    "204": "Use weapons of mass destruction",
}

QUAD_CLASSES = {
    1: "Verbal Cooperation",
    2: "Material Cooperation",
    3: "Verbal Conflict",
    4: "Material Conflict"
}

def get_cameo_label(code: str) -> str:
    """Return a human-readable action label for a CAMEO code."""
    # Sometimes codes are parsed as ints and lack leading zeros
    code_str = str(code).zfill(3)
    return CAMEO_EVENT_CODES.get(code_str, f"Action {code_str}")

def get_quad_class_label(quad: int) -> str:
    """Return the label for a CAMEO quad class."""
    return QUAD_CLASSES.get(quad, "Unknown")

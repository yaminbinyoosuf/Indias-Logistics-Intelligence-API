
# --- Zone classification ---
# Metro: Both in major metros (hardcoded list)
# Local: Same district
# Regional: Same state
# National: Different state
# Special: NE, J&K, islands

METRO_PINCODES = set([
	# Example: Delhi, Mumbai, Bangalore, Chennai, Hyderabad, Kolkata
	"110001", "400001", "560001", "600001", "500001", "700001"
])
SPECIAL_STATES = {"Jammu & Kashmir", "Ladakh", "Andaman & Nicobar", "Lakshadweep", "Nagaland", "Manipur", "Mizoram", "Arunachal Pradesh", "Meghalaya", "Tripura", "Sikkim"}

def classify_zone(orig, dst, distance_km):
	if orig.pincode in METRO_PINCODES and dst.pincode in METRO_PINCODES:
		return "Metro"
	if orig.district == dst.district:
		return "Local"
	if orig.state == dst.state:
		return "Regional"
	if orig.state in SPECIAL_STATES or dst.state in SPECIAL_STATES:
		return "Special"
	return "National"

def score_risk(orig, dst, distance_km, zone):
	# Conservative: high risk for rural, long distance, or special zones
	if not orig.serviceable or not dst.serviceable:
		return "high"
	if zone == "Special":
		return "high"
	if zone == "National" and distance_km > 1500:
		return "high"
	if orig.tier == "Rural" or dst.tier == "Rural":
		return "high"
	if zone == "Regional" and distance_km > 500:
		return "medium"
	return "low"

def estimate_eta(zone):
	# Deterministic, conservative
	if zone == "Local":
		return 1
	if zone == "Metro":
		return 2
	if zone == "Regional":
		return 3
	if zone == "National":
		return 4
	if zone == "Special":
		return 7
	return 5

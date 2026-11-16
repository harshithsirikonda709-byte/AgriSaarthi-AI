import json
import re

telugu_re = re.compile(r'[\u0C00-\u0C7F]')
hindi_re = re.compile(r'[\u0900-\u097F]')

from agrisaarthi.chat_protocol import (
    format_acp_recommendation,
    format_acp_recommendation_telugu,
    format_acp_recommendation_hindi,
)
from agrisaarthi.engine import AgriSaarthiEngine
from agrisaarthi.models import FarmerProfileRequest

req = FarmerProfileRequest(
    farmer_id="test_farmer",
    state="Telangana",
    district="Warangal",
    land_size_acres=3.0,
    soil_type="black",
    water_availability="moderate",
    season="kharif",
    budget_inr=90000,
    risk_tolerance="moderate"
)
resp = AgriSaarthiEngine.execute(req)

# English recommendation check
en_text = format_acp_recommendation(resp, req)
print(f"English ACP Output sample:\n{en_text[:300]}\n---")
assert not telugu_re.search(en_text), "English ACP contains Telugu!"
assert not hindi_re.search(en_text), "English ACP contains Hindi!"
print("PASS: English ACP recommendation has ZERO Telugu and ZERO Hindi characters.")

# Telugu recommendation check
te_text = format_acp_recommendation_telugu(resp, req)
print(f"Telugu ACP Output sample:\n{te_text[:300]}\n---")
assert not hindi_re.search(te_text), "Telugu ACP contains Hindi!"
# Verify no English crop names in parentheses e.g. (Maize) or (Cotton)
assert not re.search(r'\((Cotton|Paddy|Rice|Chilli|Wheat|Maize|Groundnut|Soybean|Chickpea)\)', te_text, re.IGNORECASE), "Telugu ACP contains English crop in parentheses!"
print("PASS: Telugu ACP recommendation has ZERO Hindi and ZERO English crop names in parentheses.")

# Hindi recommendation check
hi_text = format_acp_recommendation_hindi(resp, req)
print(f"Hindi ACP Output sample:\n{hi_text[:300]}\n---")
assert not telugu_re.search(hi_text), "Hindi ACP contains Telugu!"
assert not re.search(r'\((Cotton|Paddy|Rice|Chilli|Wheat|Maize|Groundnut|Soybean|Chickpea)\)', hi_text, re.IGNORECASE), "Hindi ACP contains English crop in parentheses!"
print("PASS: Hindi ACP recommendation has ZERO Telugu and ZERO English crop names in parentheses.")

print("\nALL BACKEND CHAT PROTOCOL TRILINGUAL ENFORCEMENT CHECKS PASSED!")

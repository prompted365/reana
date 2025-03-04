import os
import requests
import json
import datetime

# API Endpoint Configuration
BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
ENDPOINT = "/optimize"
FULL_URL = f"{BASE_URL}{ENDPOINT}"

def to_utc_z_string(dt: datetime.datetime) -> str:
    return dt.replace(tzinfo=datetime.timezone.utc).isoformat().replace("+00:00", "Z")

# Define test execution date and time
test_date = datetime.date(2025, 3, 3)
tour_start = to_utc_z_string(datetime.datetime.combine(test_date, datetime.time(9, 0)))   # 9:00 AM UTC
tour_end = to_utc_z_string(datetime.datetime.combine(test_date, datetime.time(17, 0)))    # 5:00 PM UTC

# Define agent home as an address (for the FastAPI input)
AGENT_HOME = "10 Columbus Circle, New York, NY 10019"

# Define agent preference (can be "optimize", "furthest", or "closest")
AGENT_PREFERENCE = "optimize"  # Change this to test different preferences

# Define properties as a list of addresses and related info
PROPERTIES = [
    {
        "address": "350 5th Ave, New York, NY 10118",  # Empire State Building
        "available_from": "09:30",
        "available_to": "11:00",
        "square_footage": 1800,
        "video_url": "https://example.com/videos/empire-state.mp4",
        "sellside_agent_name": "Agent A",
        "contact_method_preferred": "sms",
        "confirmation_status": "confirmed",
        "constraint_indicator": "flexible"
    },
    {
        "address": "405 Lexington Ave, New York, NY 10174",  # Chrysler Building
        "available_from": "10:00",
        "available_to": "12:00",
        "square_footage": 1500,
        "video_url": "https://example.com/videos/chrysler.mp4",
        "sellside_agent_name": "Agent B",
        "contact_method_preferred": "call",
        "confirmation_status": "pending",
        "constraint_indicator": "strict"
    },
    {
        "address": "20 W 34th St, New York, NY 10001",  # Macy's Herald Square
        "available_from": "11:00",
        "available_to": "13:00",
        "square_footage": 2200,
        "video_url": "https://example.com/videos/macys.mp4",
        "sellside_agent_name": "Agent C",
        "contact_method_preferred": "showingsTime",
        "confirmation_status": "confirmed",
        "constraint_indicator": "moderate"
    },
    {
        "address": "30 Rockefeller Plaza, New York, NY 10112",  # 30 Rock
        "available_from": "12:00",
        "available_to": "14:00",
        "square_footage": 1700,
        "video_url": "https://example.com/videos/30rock.mp4",
        "sellside_agent_name": "Agent D",
        "contact_method_preferred": "go-direct",
        "confirmation_status": "confirmed",
        "constraint_indicator": "flexible"
    },
    {
        "address": "1 World Trade Center, New York, NY 10007",  # One World Trade
        "available_from": "13:00",
        "available_to": "15:00",
        "square_footage": 2000,
        "video_url": "https://example.com/videos/one-world-trade.mp4",
        "sellside_agent_name": "Agent E",
        "contact_method_preferred": "sms",
        "confirmation_status": "pending",
        "constraint_indicator": "strict"
    },
    {
        "address": "11 Wall St, New York, NY 10005",  # NYSE
        "available_from": "14:00",
        "available_to": "16:00",
        "square_footage": 1600,
        "video_url": "https://example.com/videos/nyse.mp4",
        "sellside_agent_name": "Agent F",
        "contact_method_preferred": "call",
        "confirmation_status": "confirmed",
        "constraint_indicator": "moderate"
    },
    {
        "address": "768 5th Ave, New York, NY 10019",  # The Plaza Hotel
        "available_from": "15:00",
        "available_to": "17:00",
        "square_footage": 1900,
        "video_url": "https://example.com/videos/plaza-hotel.mp4",
        "sellside_agent_name": "Agent G",
        "contact_method_preferred": "showingTime",
        "confirmation_status": "confirmed",
        "constraint_indicator": "flexible"
    }
]

# Build JSON Payload (matching the OptimizeRequest model)
payload = {
    "agent_home": AGENT_HOME,
    "tour_start_time": tour_start,
    "tour_end_time": tour_end,
    "properties": PROPERTIES,
    "start_preference": AGENT_PREFERENCE
}

print("📦 Request Payload Sent to FastAPI:")
print(json.dumps(payload, indent=2))

def generate_html_form(data):
    with open("showings_plan.html", "r") as template_file:
        template_content = template_file.read()

    # Populate the template with data
    try:
        populated_content = template_content.replace(
            "{total_properties}", str(len(data['schedule']))
        ).replace(
            "{total_drive_time}", str(data['total_drive_time_minutes'])
        ).replace(
            "{total_drive_distance}", str(data['total_drive_distance_km'])
        ).replace(
            "{schedule}", "\n".join([
                f"<li>Stop {i+1}: {appointment['property_address']} - Arrival: {appointment['arrival_time']}, Duration: {appointment['visit_duration_minutes']} minutes</li>"
                for i, appointment in enumerate(data['schedule'])
            ])
        )
    except KeyError as e:
        print(f"❌ Template formatting error: Missing key {e}")
        return

    # Generate a unique filename using the first property address and current timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"tour_schedule_{data['schedule'][0]['property_address'].replace(' ', '_')}_{timestamp}.html"

    with open(f"tours/{unique_filename}", "w") as file:
        file.write(populated_content)
    print(f"✅ HTML form generated and saved as '{unique_filename}'")

try:
    print(f"📡 Sending request to {FULL_URL}...")
    response = requests.post(FULL_URL, json=payload, timeout=60)  # Increased timeout for more properties
    response.raise_for_status()
    
    data = response.json()
    print("✅ API Response:")
    
    # Print summary information
    print(f"\n📊 Tour Summary:")
    print(f"Total properties: {len(data['schedule'])}")
    print(f"Total drive time: {data['total_drive_time_minutes']} minutes")
    print(f"Total drive distance: {data['total_drive_distance_km']} km")
    
    # Print detailed schedule
    print("\n📅 Optimized Schedule:")
    for i, appointment in enumerate(data['schedule']):
        print(f"\n🏠 Stop {i+1}: {appointment['property_address']}")
        print(f"  Arrival: {appointment['arrival_time']}")
        print(f"  Visit duration: {appointment['visit_duration_minutes']} minutes")
        
        if appointment['drive_time_minutes'] is not None:
            print(f"  Drive time from previous stop: {appointment['drive_time_minutes']} minutes")
            print(f"  Drive distance from previous stop: {appointment['drive_distance_km']} km")
        
        if appointment['video_url']:
            print(f"  Video: {appointment['video_url']}")
    
    # Generate HTML form with the response data
    generate_html_form(data)
    
except requests.exceptions.HTTPError as http_err:
    print(f"❌ HTTP error: {http_err}\nResponse: {response.text}")
except requests.exceptions.RequestException as req_err:
    print(f"❌ Request failed: {req_err}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

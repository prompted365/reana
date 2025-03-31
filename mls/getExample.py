import requests
import json

def fetch_and_parse_mls_data():
    """
    Fetch MLS data from the API and parse it into a structured dictionary with essential fields.
    
    Returns:
        list: A list of dictionaries, each containing the essential fields for a property.
    """
    # Define the API endpoint and access token
    api_url = "https://api.bridgedataoutput.com/api/v2/OData/test/Property"
    access_token = "6baca547742c6f96a6ff71b138424f21"
    full_url = f"{api_url}?access_token={access_token}"
    
    try:
        # Make the GET request
        response = requests.get(full_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the JSON response
        mls_data = response.json()
        
        # Get the array of properties from the 'value' key, default to empty list if not found
        properties = mls_data.get("value", [])
        parsed_data = []
        
        for property in properties:
            # Extract ListingKey or ListingId
            listing_key = property.get("ListingKey") or property.get("ListingId")
            
            # Extract Address
            unparsed_address = property.get("UnparsedAddress")
            if unparsed_address:
                address = unparsed_address
            else:
                street_number = property.get("StreetNumber", "")
                street_name = property.get("StreetName", "")
                city = property.get("City", "")
                state = property.get("StateOrProvince", "")
                postal_code = property.get("PostalCode", "")
                address = f"{street_number} {street_name}, {city}, {state} {postal_code}".strip()
            
            # Extract other essential fields
            showing_instructions = property.get("ShowingInstructions", "")
            mls_status = property.get("MlsStatus", "")
            lockbox_location = property.get("LockBoxLocation", "")
            access_code = property.get("AccessCode", "")
            occupant_type = property.get("OccupantType", "")
            private_remarks = property.get("PrivateRemarks", "")
            
            # Extract contact information into a dictionary
            contact_info = {
                "ListAgentFullName": property.get("ListAgentFullName", ""),
                "ListAgentOfficePhone": property.get("ListAgentOfficePhone", ""),
                "ListAgentMobilePhone": property.get("ListAgentMobilePhone", ""),
                "ShowingContactName": property.get("ShowingContactName", ""),
                "ShowingContactPhone": property.get("ShowingContactPhone", ""),
                "ShowingContactType": property.get("ShowingContactType", [])
            }
            
            # Extract coordinates (latitude and longitude)
            coordinates = property.get("Coordinates", [None, None])
            latitude, longitude = coordinates if len(coordinates) == 2 else (None, None)
            
            # Create a dictionary for the property with all essential fields
            property_data = {
                "ListingKey": listing_key,
                "Address": address,
                "ShowingInstructions": showing_instructions,
                "MlsStatus": mls_status,
                "LockBoxLocation": lockbox_location,
                "AccessCode": access_code,
                "OccupantType": occupant_type,
                "PrivateRemarks": private_remarks,
                "ContactInfo": contact_info,
                "Latitude": latitude,
                "Longitude": longitude
            }
            
            # Add the property data to the result list
            parsed_data.append(property_data)
        
        return parsed_data
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

# Fetch and parse the data
parsed_properties = fetch_and_parse_mls_data()

# Optionally, print the first property to verify
if parsed_properties:
    print(json.dumps(parsed_properties[0], indent=2))
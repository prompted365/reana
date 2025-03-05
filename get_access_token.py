import requests

def get_access_token(client_id, client_secret, refresh_token):
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Failed to obtain access token: {response.text}")

if __name__ == "__main__":
    client_id = "764086051850-6qr4p6gpi6hn506pt8ejuq83di341hur.apps.googleusercontent.com"
    client_secret = "d-FL95Q19q7MQmFpd7hHD0Ty"
    refresh_token = "1//04QUTisUajMD5CgYIARAAGAQSNwF-L9Ir5t-WLMUWqAhyyruR-LPjj50EHvo17AuqzCs1HFXJveuSBvtuHGgW5PqQnF8Lxo4UqdQ"
    
    try:
        access_token = get_access_token(client_id, client_secret, refresh_token)
        print(f"Access Token: {access_token}")
    except Exception as e:
        print(e)

import os
import requests
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# Configuration
USERNAME = "Navachess"
API_URL = f"https://lichess.org/api/user/{USERNAME}"
STATE_FILE = "state.json"

def get_lichess_data():
    response = requests.get(API_URL)
    response.raise_for_status()
    return response.json()

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {"last_seen": 0, "total_playtime": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def send_email(total_playtime, seen_at):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    receiver = os.getenv("RECEIVER_EMAIL")
    
    if not all([user, password, receiver]):
        print("Email environment variables missing. Skipping email.")
        return

    dt_object = datetime.fromtimestamp(seen_at / 1000.0)
    subject = f"Lichess Alert: {USERNAME} has played!"
    body = (f"{USERNAME} has been playing on Lichess.\n"
            f"New total play time: {total_playtime} seconds.\n"
            f"Last seen at: {dt_object.strftime('%Y-%m-%d %H:%M:%S')}.")
    
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = receiver

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, receiver, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    try:
        data = get_lichess_data()
        seen_at = data.get("seenAt", 0)
        current_playtime = data.get("playTime", {}).get("total", 0)
        
        state = load_state()
        last_playtime = state.get("total_playtime", 0)
        
        if current_playtime > last_playtime:
            print(f"Play time incremented for {USERNAME} ({last_playtime} -> {current_playtime}). Sending alert.")
            send_email(current_playtime, seen_at)
            state["total_playtime"] = current_playtime
            state["last_seen"] = seen_at
            save_state(state)
        elif seen_at > state.get("last_seen", 0):
            print(f"Activity detected for {USERNAME}, but play time did not increase. Updating state without email.")
            state["last_seen"] = seen_at
            save_state(state)
        else:
            print(f"No new activity for {USERNAME}.")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()

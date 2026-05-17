import os
import requests
import json
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

USERNAME = "Navachess"
API_URL = f"https://lichess.org/api/user/{USERNAME}"
STATE_FILE = "state.json"

def get_lichess_data():
    response = requests.get(API_URL)
    response.raise_for_status()
    return response.json()

def extract_current(data):
    perfs = data.get("perfs", {})
    return {
        "last_seen": data.get("seenAt", 0),
        "total_playtime": data.get("playTime", {}).get("total", 0),
        "puzzle_games": perfs.get("puzzle", {}).get("games", 0),
        "blitz_games": perfs.get("blitz", {}).get("games", 0),
        "rapid_games": perfs.get("rapid", {}).get("games", 0),
    }

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return None

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def send_email(changes, seen_at):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    receiver = os.getenv("RECEIVER_EMAIL")

    if not all([user, password, receiver]):
        print("Email environment variables missing. Skipping email.")
        return

    dt_object = datetime.fromtimestamp(seen_at / 1000.0)
    subject = f"Lichess Alert: {USERNAME} has played!"
    changes_text = "\n".join(f"  - {c}" for c in changes)
    body = (f"{USERNAME} has been active on Lichess.\n\n"
            f"Changes detected:\n{changes_text}\n\n"
            f"Last seen at: {dt_object.strftime('%Y-%m-%d %H:%M:%S')} UTC.")

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
        current = extract_current(data)

        state = load_state()

        if state is None:
            print(f"No state file found. Saving baseline for {USERNAME} (no email sent).")
            save_state(current)
            return

        changes = []
        if current["total_playtime"] > state.get("total_playtime", 0):
            changes.append(
                f"Play time: {state.get('total_playtime', 0)}s → {current['total_playtime']}s"
            )
        if current["puzzle_games"] > state.get("puzzle_games", 0):
            changes.append(
                f"Puzzles: {state.get('puzzle_games', 0)} → {current['puzzle_games']}"
            )
        if current["blitz_games"] > state.get("blitz_games", 0):
            changes.append(
                f"Blitz games: {state.get('blitz_games', 0)} → {current['blitz_games']}"
            )
        if current["rapid_games"] > state.get("rapid_games", 0):
            changes.append(
                f"Rapid games: {state.get('rapid_games', 0)} → {current['rapid_games']}"
            )

        if changes:
            print(f"Activity detected for {USERNAME}: {', '.join(changes)}. Sending alert.")
            send_email(changes, current["last_seen"])
            save_state(current)
        else:
            print(f"No new activity for {USERNAME}.")

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()

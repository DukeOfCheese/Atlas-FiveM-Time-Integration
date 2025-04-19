import datetime
from flask import Flask, request, jsonify, Response
import requests
import sqlite3

conn = sqlite3.connect("time.db")
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS
          (user_id INTEGER, type TEXT)''')
conn.commit()

def format_discord_timestamp(datetime_str):
    try:
        dt_object = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        unix_timestamp = int(dt_object.timestamp())
        return f"<t:{unix_timestamp}:R>"
    except ValueError as e:
        return f"Invalid datetime string: {e}"

app = Flask(__name__)

@app.route('/', methods=['GET'])
def api_test():
    return {"check": "pass"}

@app.route('/api/time/start', methods=['POST'])
def time_start():
    data = request.get_json()

    required_fields = ['discordId', 'type']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400
    
    discordId = data.get('discordId')
    type = data.get('type')
    webhook_url = data.get('webhookUrl')

    if webhook_url:
        data = {
            "username": "Atlas Time Integration",
            "embeds": [
            {
                "title": "Clock-In Alert",
                "description": "A user has clocked in.",
                "color": 0x00ff00,
                "fields": [
                    {"name": "Start", "value": format_discord_timestamp(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')), "inline": True},
                    {"name": "User", "value": f"<@{discordId}>", "inline": True},
                    {"name": "Type", "value": type, "inline": False},
                ],
                "footer": {"text": "Atlas Time Integration"},
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
        ]
        }
        requests.post(webhook_url, json=data)
    
    now = datetime.datetime.now()
    
    conn = sqlite3.connect('time.db')
    c = conn.cursor()

    c.execute("SELECT * FROM clockin WHERE user_id = ? AND type = ?", (discordId, type,))
    row = c.fetchone()
    if row:
        return ({"error": "User is clocked in to this type already"}), 417
    else:
        c.execute("INSERT INTO clockin VALUES (?, ?, ?)", (discordId, type, now,))
        conn.commit()
        
        conn.close()
        return ({"success": "User is now clocked in"}), 200

@app.route('/api/time/end', methods=['POST'])
def time_end():
    data = request.get_json()

    required_fields = ['discordId', 'type']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400
    
    discordId = data.get('discordId')
    type = data.get('type')
    webhook_url = data.get('webhookUrl')
    
    conn = sqlite3.connect('time.db')
    c = conn.cursor()

    c.execute("SELECT * FROM clockin WHERE user_id = ? AND type = ?", (discordId, type,))
    row = c.fetchone()
    if not row:
        return ({"error": "User is not clocked"})
    else:
        now = datetime.datetime.now()
        row_datetime = datetime.datetime.fromisoformat(row[2])
        formatted_start = row_datetime.strftime('%Y-%m-%d %H:%M:%S')
        formatted_end = now.strftime('%Y-%m-%d %H:%M:%S')
        time_taken = now - row_datetime
        seconds = time_taken.total_seconds()
        total_time = seconds_converter(seconds)
        c.execute("DELETE FROM clockin WHERE user_id = ? AND type = ?", (discordId, type,))
        c.execute("INSERT INTO logs VALUES (?, ?, ?, ?)", (discordId, type, now, seconds))
        conn.commit()
        conn.close()

        if webhook_url:
            data = {
                "username": "Atlas Time Integration",
                "embeds": [
                {
                    "title": "Clock-Out Alert",
                    "description": "A user has clocked out.",
                    "color": 0xFF0000,
                    "fields": [
                        {"name": "Start", "value": format_discord_timestamp(formatted_start), "inline": True},
                        {"name": "End", "value": format_discord_timestamp(formatted_end), "inline": True},
                        {"name": "User", "value": f"<@{discordId}>", "inline": True},
                        {"name": "Type", "value": type, "inline": True},
                        {"name": "Total Time", "value": total_time, "inline": True}
                    ],
                    "footer": {"text": "Atlas Time Integration"},
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
                }
            ]
            }
        requests.post(webhook_url, json=data)
        return jsonify({"success": "DM logged"}), 200
    
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
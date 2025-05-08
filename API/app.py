from flask import Flask, request, jsonify, Response
import sqlite3
import datetime
from datetime import timedelta
import requests

database_path = 'atlastime.db'
apiPasskey = 'changeMe' # same as in server.lua

def format_discord_timestamp():
    dt_object = datetime.datetime.now()
    unix_timestamp = int(dt_object.timestamp())
    return f"<t:{unix_timestamp}:R>"

conn = sqlite3.connect(database_path)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS time
          (number INTEGER, user_id INTEGER, clockin TIMESTAMP, clockout TIMESTAMP, notification INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS setup
          (number INTEGER, name TEXT, webhook TEXT, image TEXT, dms INTEGER)''')
conn.commit()
conn.close()

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'message': 'API is online'}), 200

@app.route('/time/start', methods=['POST'])
def time_start():
    data = request.get_json()

    required_fields = ['userId', 'number']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 417
    
    passkey = data.get('passkey')
    user_id = data.get('userId')
    number = data.get('number')
    
    if passkey == apiPasskey:    
        conn = sqlite3.connect(database_path)
        c = conn.cursor()

        c.execute("INSERT INTO time (number, user_id, clockin, clockout, notification) VALUES (?, ?, ?, ?, ?)", (number, user_id, datetime.datetime.now(), 0 , 0))
        conn.commit()

        c.execute("SELECT * FROM setup WHERE number = ?", (int(number),))
        row = c.fetchone()
        if row:
            if row[2]:
                now = datetime.datetime.utcnow().isoformat() + "Z"
                webhook_data = {
                    "embeds": [
                        {
                            "title": f"{row[1]} Clock-In",
                            "color": 3066993,
                            "fields": [
                                {"name": "Start Time", "value": format_discord_timestamp(), "inline": True},
                                {"name": "User", "value": f"<@{user_id}>"}
                            ],
                            "footer": {
                                "text": "Atlas Time Integration"
                            },
                            "timestamp": now
                        }
                    ]
                }
                conn.close()
                response = requests.post(row[2], json=webhook_data)
                if response.status_code == 204:
                    return jsonify({'message': 'success'}), 200
                else:
                    return jsonify({'error': response.status_code}), 400

        else:
            conn.close()
            return jsonify({'error': 'No row'}), 400
        
    else:
        conn.close()
        return jsonify({'error': 'passkey'}), 401

@app.route('/time/end', methods=['POST'])
def time_end():
    data = request.get_json()

    required_fields = ['userId', 'number']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 417
    
    passkey = data.get('passkey')
    user_id = data.get('userId')
    number = data.get('number')
    
    if passkey == apiPasskey:    
        conn = sqlite3.connect(database_path)
        c = conn.cursor()

        c.execute("UPDATE time SET clockout = ? WHERE number = ? AND user_id = ? AND clockout = ?", (datetime.datetime.now(), number, user_id, 0,))
        conn.commit()
        conn.close()

        return jsonify({'message': 'success'}), 200
    else:
        return jsonify({'error': 'Passkey'}), 401

@app.route('/time/notifications', methods=['GET'])
def time_notis():
    conn = sqlite3.connect(database_path)
    c = conn.cursor()

    c.execute("SELECT * FROM time WHERE notification = ?", (0,))
    notis = c.fetchall()
    if notis:
        c.execute("UPDATE time SET notification = ? WHERE notification = ?", (1, 0,))
        conn.commit()
        conn.close()
        return jsonify({'notis': notis}), 200
    else:
        conn.close()
        return jsonify({'error': 'No notifications'}), 402
    
@app.route('/time/setup/name', methods=['POST'])
def time_setup():
    data = request.get_json()

    passkey = data.get('passkey')
    name = data.get('name')

    if passkey == apiPasskey:
        conn = sqlite3.connect(database_path)
        c = conn.cursor()

        c.execute("SELECT * FROM setup")
        rows = c.fetchall()
        if rows:
            count = len(rows) + 1
        else:
            count = 1

        c.execute("INSERT INTO setup (number, name) VALUES (?, ?)", (count, name,))
        conn.commit()

        return jsonify({'message': 'success'}), 200
    else:
        return jsonify({'error': 'passkey'}), 401
    
@app.route('/time/setup/webhook', methods=['POST'])
def webhook_setup():
    data = request.get_json()

    passkey = data.get('passkey')
    number = data.get('number')
    webhook = data.get('webhook')

    if passkey == apiPasskey:
        conn = sqlite3.connect(database_path)
        c = conn.cursor()

        c.execute("UPDATE setup SET webhook = ? WHERE number = ?", (webhook, number,))
        conn.commit()

        return jsonify({'message': 'success'}), 200
    else:
        return jsonify({'error': 'passkey'}), 401   

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=32388, debug=True)
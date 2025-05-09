from flask import Flask, request, jsonify, Response
import sqlite3
import datetime
from datetime import timedelta
import requests
from calendar import monthrange
import math

database_path = 'atlastime.db'
apiPasskey = 'changeMe' # same as in server.lua

def format_discord_timestamp(timestamp):
    dt_object = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
    unix_timestamp = int(dt_object.timestamp())
    return f"<t:{unix_timestamp}:R>"

def format_seconds(seconds):
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    parts = []
    if days > 0:
        days_r = math.floor(days)
        parts.append(f"{days_r} {'day' if days_r == 1 else 'days'}")
    if hours > 0 or days > 0:
        hours_r = math.floor(hours)
        parts.append(f"{hours_r} {'hour' if hours_r == 1 else 'hours'}")
    if minutes > 0 or hours > 0 or days > 0:
        minutes_r = math.floor(minutes)
        parts.append(f"{minutes_r} {'minute' if minutes_r == 1 else 'minutes'}")
    seconds_r = math.floor(seconds)
    parts.append(f"{seconds_r} {'second' if seconds_r == 1 else 'seconds'}")

    return ' '.join(parts)

conn = sqlite3.connect(database_path)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS time
          (number INTEGER, user_id INTEGER, clockin TIMESTAMP, clockout TIMESTAMP, seconds INTEGER, notification INTEGER)''')
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

        c.execute("SELECT clockin FROM time WHERE number = ? AND user_id = ? ORDER BY clockin DESC LIMIT 1", (number, user_id,))
        result = c.fetchone()

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
                                {"name": "User", "value": f"<@{user_id}>"},
                                {"name": "Start Time", "value": format_discord_timestamp(result[0]), "inline": True},
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
            return jsonify({'message': 'success'}), 200
        
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

        c.execute("SELECT clockin FROM time WHERE number = ? AND user_id = ? ORDER BY clockin DESC LIMIT 1", (number, user_id))
        result = c.fetchone()

        if result:
            now = datetime.datetime.now()
            seconds = (now - datetime.datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S.%f")).total_seconds()

            c.execute("UPDATE time SET clockout = ?, seconds = ? WHERE number = ? AND user_id = ? AND clockout = ?", (now, seconds, number, user_id, 0,))
            conn.commit()

            c.execute("SELECT * FROM setup WHERE number = ?", (int(number),))
            row = c.fetchone()
            if row:
                if row[2]:
                    webhook_data = {
                        "embeds": [
                            {
                                "title": f"{row[1]} Clock-Out",
                                "color": 16711680,
                                "fields": [
                                    {"name": "User", "value": f"<@{user_id}>"},
                                    {"name": "Start Time", "value": format_discord_timestamp(result[0]), "inline": True},
                                    {"name": "End Time", "value": format_discord_timestamp(now.strftime('%Y-%m-%d %H:%M:%S.%f')), "inline": True},
                                    {"name": "Total Time", "value": format_seconds(seconds), "inline": True},
                                ],
                                "footer": {
                                    "text": "Atlas Time Integration"
                                },
                                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
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
            return jsonify({'message': 'success'}), 200
    else:
        return jsonify({'error': 'passkey'}), 401

@app.route('/time/notifications', methods=['POST'])
def time_notis():
    data = request.get_json()

    passkey = data.get('passkey')

    if passkey == apiPasskey:
        conn = sqlite3.connect(database_path)
        c = conn.cursor()

        c.execute("SELECT * FROM time WHERE notification = ? AND clockout != ?", (0, 0,))
        notis = c.fetchall()
        if notis:
            for noti in notis:
                c.execute("UPDATE time SET notification = ? WHERE notification = ? AND clockin = ?", (1, 0, noti[2],))
            conn.commit()
            conn.close()
            return jsonify({'notis': notis}), 200
        else:
            conn.close()
            return jsonify({'notis': None}), 200
    else:
        return jsonify({'error': 'passkey'}), 401
    
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
    
@app.route('/stats/name')
def stats_name():
    data = request.get_json()

    passkey = data.get('passkey')
    number = data.get('number')

    if passkey == apiPasskey:
        c.execute("SELECT name FROM setup WHERE number = ?", (number,))
        row = c.fetchone()
        return jsonify({'name': row[0]}), 200
    else:
        return jsonify({'error': 'passkey'}), 401
    
@app.route('/stats/user')
def stats_user():
    data = request.get_json()

    passkey = data.get('passkey')
    user_id = data.get('userId')
    time_frame = data.get('timeFrame')
    number = data.get('number')

    if passkey == apiPasskey:
        if time_frame != "All Time":
            today = datetime.datetime.today()
            days_to_subtract = today.weekday() + 1
            last_sunday = today - timedelta(days=days_to_subtract)
            current_sunday = last_sunday
            if time_frame == "This Month":
                start = today.replace(day=1, hour=0, minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S')
                end = today.strftime('%Y-%m-%d %H:%M:%S')
            elif time_frame == "Last Month":
                first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                last_day_last_month = first_day_last_month.replace(day=monthrange(first_day_last_month.year, first_day_last_month.month)[1])
                start = first_day_last_month.strftime('%Y-%m-%d %H:%M:%S')
                end = last_day_last_month.strftime('%Y-%m-%d %H:%M:%S')
            elif time_frame == "This Week":
                start = current_sunday.strftime('%Y-%m-%d %H:%M:%S')
                end = today.strftime('%Y-%m-%d %H:%M:%S')
            elif time_frame == "Last Week":
                start = (current_sunday - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
                end = (current_sunday - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            if number:
                c.execute("SELECT number, SUM(seconds) as total_seconds FROM time WHERE clockout BETWEEN ? AND ? AND user_id = ? AND number = ? ORDER BY total_seconds DESC", (start, end, user_id, number,))
            else:
                c.execute("SELECT number, SUM(seconds) as total_seconds FROM time WHERE clockout BETWEEN ? AND ? AND user_id = ? ORDER BY total_seconds DESC", (start, end, user_id,))
        else:
            if number:
                c.execute("SELECT number, SUM(seconds) as total_seconds FROM time WHERE user_id = ? AND number = ? ORDER BY total_seconds DESC", (user_id, number,))
            else:
                c.execute("SELECT number, SUM(seconds) as total_seconds FROM time WHERE user_id = ? ORDER BY total_seconds DESC", (user_id,))
        rows = c.fetchall()
        return jsonify({'rows': rows}), 200
    else:
        return jsonify({'error': 'passkey'}), 401

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=32388, debug=True)
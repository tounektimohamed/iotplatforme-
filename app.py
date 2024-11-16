import os
import ssl
import requests
from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask_socketio import SocketIO, emit
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key')

# Firebase Admin SDK Initialization
cred = credentials.Certificate('credentials.json')  # Make sure your credentials.json file is correct
firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

# Secure session cookies
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# List to hold received messages
messages = []

# Initialize SocketIO
socketio = SocketIO(app)
@app.route('/api/receive_message', methods=['POST'])
def receive_message():
    try:
        data = request.get_json()
        message = data.get('message')
        topic = data.get('topic')

        if message and topic:
            # Add current timestamp
            timestamp = datetime.utcnow()

            # Check topic and store data in respective collection
            if topic == "spo2":
                # Store Spo2 data in 'spo2' collection
                db.collection("spo2").add({
                    "message": message,
                    "timestamp": timestamp
                })
            elif topic == "heart_rate":
                # Store heart rate data in 'heart_rate' collection
                db.collection("heart_rate").add({
                    "message": message,
                    "timestamp": timestamp
                })
            else:
                # You can handle other topics or default action here
                db.collection("mqtt_data").add({
                    "message": message,
                    "topic": topic,
                    "timestamp": timestamp
                })

            # Emit data for real-time update (message length and topic)
            socketio.emit('new_message', {'topic': topic, 'message': message})

            return jsonify({"status": "success", "message": "Message received successfully!"}), 200
        else:
            return jsonify({"status": "error", "message": "Invalid message or topic"}), 400
    except Exception as e:
        print(f"Error receiving message: {e}")
        return jsonify({"status": "error", "message": "An error occurred"}), 500
    
# Home route to render the page
@app.route('/')
def home():
    if 'user' in session:
        return render_template('home.html', user=session['user'], messages=messages)
    return render_template('index.html')
@app.route('/spo2_plot')
def spo2_plot():
    return render_template('spo2_plot.html')

# Login route
@app.route('/login')
def login():
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri=http://localhost:5000/callback&"  # Update this for production
        f"response_type=code&"
        f"scope=openid email profile"
    )
    return redirect(google_auth_url)

# OAuth2 Callback route
@app.route('/callback')
def callback():
    code = request.args.get("code")
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": "http://localhost:5000/callback",
        "grant_type": "authorization_code",
    }
    
    try:
        # Get access token
        token_response = requests.post(token_url, data=data)
        token_response_json = token_response.json()
        access_token = token_response_json.get("access_token")
        
        if not access_token:
            flash("Could not retrieve access token.")
            return redirect(url_for("home"))

        # Get user info
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        # Log user info
        print(f"User info: {user_info}")

        # Save user info in session
        session["user"] = {
            "id": user_info.get("id"),
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "picture": user_info.get("picture")
        }

        # Check if user exists in Firestore; if not, create them
        user_ref = db.collection('users').document(user_info['id'])
        if not user_ref.get().exists:
            user_ref.set({
                "email": user_info["email"],
                "name": user_info["name"],
                "picture": user_info["picture"]
            })

        return redirect(url_for("home"))
    except Exception as e:
        print(f"Error in callback: {e}")
        flash("An error occurred during authentication.")
        return redirect(url_for("home"))
# Route to fetch data from Firestore and return as JSON
@app.route('/api/fetch_data', methods=['GET'])
def fetch_data():
    try:
        # Initialize data structure for the response
        chart_data = {'timestamps': [], 'heart_rates': [], 'spo2_values': []}

        # Query Firestore to get all messages from heart_rate and spo2 collections
        heart_rate_ref = db.collection('heart_rate').stream()
        spo2_ref = db.collection('spo2').stream()

        # Collect heart rate data
        for msg in heart_rate_ref:
            message = msg.to_dict()
            timestamp = message.get('timestamp').strftime('%Y-%m-%d %H:%M:%S')
            chart_data['timestamps'].append(timestamp)
            chart_data['heart_rates'].append(message.get('message'))  # Assuming message is the heart rate value

        # Collect spo2 data
        for msg in spo2_ref:
            message = msg.to_dict()
            timestamp = message.get('timestamp').strftime('%Y-%m-%d %H:%M:%S')
            chart_data['timestamps'].append(timestamp)
            chart_data['spo2_values'].append(message.get('message'))  # Assuming message is the spo2 value

        # Return data as JSON
        return jsonify({"status": "success", "data": chart_data}), 200
    except Exception as e:
        print(f"Error fetching data: {e}")
        return jsonify({"status": "error", "message": "An error occurred"}), 500


@app.route('/filter.html')
def filter_page():
    return render_template('filter.html')


@app.route('/api/filter_data', methods=['GET'])
def filter_data():
    try:
        # Get the start and end date from query params
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')

        if not start_date or not end_date:
            return jsonify({"status": "error", "message": "Please provide both start and end dates"}), 400

        # Convert to datetime objects
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
        end_datetime = end_datetime.replace(hour=23, minute=59, second=59)  # Set to end of the day

        # Query Firestore for heart_rate and spo2 data in the given date range
        heart_rate_ref = db.collection('heart_rate').where('timestamp', '>=', start_datetime).where('timestamp', '<=', end_datetime).stream()
        spo2_ref = db.collection('spo2').where('timestamp', '>=', start_datetime).where('timestamp', '<=', end_datetime).stream()

        filtered_data = []

        # Process heart rate data
        for message in heart_rate_ref:
            message_data = message.to_dict()
            filtered_data.append({
                'message': message_data.get('message'),
                'topic': 'heart_rate',
                'timestamp': message_data.get('timestamp').strftime('%Y-%m-%d %H:%M:%S')  # Format the timestamp
            })

        # Process spo2 data
        for message in spo2_ref:
            message_data = message.to_dict()
            filtered_data.append({
                'message': message_data.get('message'),
                'topic': 'spo2',
                'timestamp': message_data.get('timestamp').strftime('%Y-%m-%d %H:%M:%S')  # Format the timestamp
            })

        return jsonify({"status": "success", "data": filtered_data}), 200
    except Exception as e:
        print(f"Error filtering data: {e}")
        return jsonify({"status": "error", "message": "An error occurred during filtering"}), 500

# Logout route
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    # Start SocketIO server
    socketio.run(app, debug=True)

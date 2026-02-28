from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sock import Sock 
import database_helper
import re
import json

app = Flask(__name__)
CORS(app)
sock = Sock(app)

# Use global dictionary to save the connect of active WebSocket
active_sockets = {}

@app.route('/')
def root():
    return app.send_static_file('client.html')

@sock.route('/ws')
def websocket_handler(ws):
    #Receive first information from client after connecting
    token = ws.receive()
    if not token:
        return

    user_data = database_helper.get_user_data_by_token(token)

    if user_data:
        email = user_data['email']
        #Renew global dictionary to current connect object
        active_sockets[email] = ws

        #Keep the connection monitored until the user disconnects
        try:
            while True:
                data = ws.receive()
                if data is None: 
                    break
        except Exception as e:
            print(f"WebSocket Connection ended for {email}")
        finally:
            if email in active_sockets and active_sockets[email] == ws:
                del active_sockets[email]

def is_valid_email(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

@app.route('/sign_up', methods=['POST'])
def sign_up():
    data = request.get_json()
    required_fields = ['email', 'password', 'firstname', 'familyname', 'gender', 'city', 'country']
    for field in required_fields:
        if field not in data or not str(data[field]).strip():
            return jsonify({"success": False, "message": f"Field '{field}' cannot be empty."}), 400
    if not is_valid_email(data['email']):
        return jsonify({"success": False, "message": "Invalid email format."}), 400
    if len(data['password']) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters long."}), 400
    if database_helper.get_user_by_email(data['email']):
        return jsonify({"success": False, "message": "User already exists."}), 409
    result = database_helper.insert_user(
        data['email'], data['password'], data['firstname'], 
        data['familyname'], data['gender'], data['city'], data['country']
    )
    if result:
        return jsonify({"success": True, "message": "Successfully signed up."}), 201
    return jsonify({"success": False, "message": "Signup failed."}), 500

@app.route('/sign_in', methods=['POST'])
def sign_in():
    data = request.get_json()
    email = data.get('email') or data.get('username')
    password = data.get('password')
    
    if database_helper.verify_user(email, password):
        # The backend automatically logs out and disconnects
        if email in active_sockets:
            try:
                print(f">>> 後端偵測到重複登入，主動關閉舊連線: {email}")
                active_sockets[email].send("sign_out")
                active_sockets[email].close() 
            except Exception as e:
                print(f"Error kicking old user: {e}")

        database_helper.remove_all_sessions_by_email(email) 
        token = database_helper.create_session(email)
        if token:
            return jsonify({"success": True, "message": "Successfully signed in.", "data": token}), 200
    return jsonify({"success": False, "message": "Wrong username or password."}), 401

@app.route('/sign_out', methods=['DELETE'])
def sign_out():
    token = request.headers.get('Authorization')
    if token and database_helper.remove_session(token):
        return jsonify({"success": True, "message": "Successfully signed out."}), 200
    return jsonify({"success": False, "message": "Incorrect token."}), 401

@app.route('/change_password', methods=['PUT'])
def change_password():
    token = request.headers.get('Authorization')
    data = request.get_json()
    old_p = data.get('old_password')
    new_p = data.get('new_password')
    user_data = database_helper.get_user_data_by_token(token)
    if not user_data:
        return jsonify({"success": False, "message": "You are not signed in."}), 401
    if database_helper.verify_user(user_data['email'], old_p):
        if len(new_p) >= 6 and database_helper.change_password(user_data['email'], new_p):
            return jsonify({"success": True, "message": "Password changed."}), 200
    return jsonify({"success": False, "message": "Failed to change password."}), 400

@app.route('/get_user_data_by_token', methods=['GET'])
def get_user_data_by_token():
    token = request.headers.get('Authorization')
    user_data = database_helper.get_user_data_by_token(token)
    if user_data:
        if 'password' in user_data: del user_data['password']
        return jsonify({"success": True, "message": "User data retrieved.", "data": user_data}), 200
    return jsonify({"success": False, "message": "You are not signed in."}), 401

@app.route('/get_user_data_by_email/<email>', methods=['GET'])
def get_user_data_by_email(email):
    token = request.headers.get('Authorization')
    if database_helper.get_user_data_by_token(token):
        user_data = database_helper.get_user_by_email(email)
        if user_data:
            if 'password' in user_data: del user_data['password']
            return jsonify({"success": True, "message": "User data retrieved.", "data": user_data}), 200
        return jsonify({"success": False, "message": "No such user."}), 404
    return jsonify({"success": False, "message": "You are not signed in."}), 401

@app.route('/post_message', methods=['POST'])
def post_message():
    token = request.headers.get('Authorization')
    data = request.get_json()
    recipient_email = data.get('recipient')
    message_content = data.get('message')
    user_data = database_helper.get_user_data_by_token(token)
    if not user_data:
        return jsonify({"success": False, "message": "You are not signed in."}), 401
    if not message_content or not message_content.strip():
        return jsonify({"success": False, "message": "Empty message."}), 400
    if recipient_email is None:
        recipient_email = user_data['email']
    recipient = database_helper.get_user_by_email(recipient_email)
    if not recipient:
        return jsonify({"success": False, "message": "Recipient email not found."}), 404
    if database_helper.post_message(user_data['email'], recipient_email, message_content):
        return jsonify({"success": True, "message": "Message posted!"}), 201
    return jsonify({"success": False, "message": "Failed to post message."}), 500

@app.route('/get_user_messages_by_token', methods=['GET'])
def get_user_messages_by_token():
    token = request.headers.get('Authorization')
    if token:
        messages = database_helper.get_user_messages_by_token(token)
        if messages is not None:
            return jsonify({"success": True, "message": "User messages retrieved.", "data": messages}), 200
    return jsonify({"success": False, "message": "You are not signed in."}), 401

@app.route('/get_user_messages_by_email/<email>', methods=['GET'])
def get_user_messages_by_email(email):
    token = request.headers.get('Authorization')
    if database_helper.get_user_data_by_token(token):
        messages = database_helper.get_user_messages_by_email(email)
        return jsonify({"success": True, "message": "User messages retrieved.", "data": messages}), 200
    return jsonify({"success": False, "message": "You are not signed in."}), 401

if __name__ == '__main__':
    app.run(port=5000, debug=True)
    
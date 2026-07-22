from flask import Flask, request, jsonify
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import aiohttp
import requests
import json
import base64
import like_pb2
import uid_generator_pb2
import visit_count_pb2
from collections import OrderedDict

app = Flask(__name__)

VALID_API_KEYS = {"DARK"}
used_count = 0

# 🔥 यह लिस्ट टेलीग्राम से अपलोड किए गए सभी टोकन्स को 1 सेकंड में सेव कर लेगी 🔥
ACTIVE_TOKENS = []

def load_tokens(region):
    if ACTIVE_TOKENS:
        return ACTIVE_TOKENS
    try:
        with open("token_ind.json", "r") as f: return json.load(f)
    except Exception: return None

def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        return binascii.hexlify(cipher.encrypt(padded_message)).decode('utf-8')
    except Exception: return None

def create_protobuf_message(user_id, region):
    try:
        message = like_pb2.like()
        message.uid = int(user_id)
        message.region = region
        return message.SerializeToString()
    except Exception: return None

async def send_request(encrypted_uid, token, url):
    try:
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=edata, headers=headers) as response:
                return await response.text()
    except Exception: return None

async def send_multiple_requests(uid, region, url):
    try:
        protobuf_message = create_protobuf_message(uid, region)
        encrypted_uid = encrypt_message(protobuf_message)
        tokens = load_tokens(region)
        if not tokens or not encrypted_uid: return None
        
        tasks = []
        # 20 Requests distributed across ALL available tokens in your JSON!
        for i in range(20):
            token = tokens[i % len(tokens)]["token"]
            tasks.append(send_request(encrypted_uid, token, url))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    except Exception: return None

def create_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.saturn_ = int(uid)
        message.garena = 1
        return message.SerializeToString()
    except Exception: return None

def enc(uid):
    protobuf_data = create_protobuf(uid)
    return encrypt_message(protobuf_data) if protobuf_data else None

def make_request(encrypt, region, token):
    try:
        url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        edata = bytes.fromhex(encrypt)
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "ReleaseVersion": "OB54"
        }
        response = requests.post(url, data=edata, headers=headers, verify=False)
        decoded = visit_count_pb2.Info()
        decoded.ParseFromString(response.content)
        return decoded
    except Exception: return None

def decode_jwt_uid(token):
    try:
        parts = token.split('.')
        if len(parts) >= 2:
            padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
            payload = json.loads(base64.b64decode(padded).decode('utf-8'))
            return str(payload.get('account_id', ''))
    except: pass
    return None

# ==========================================
# API ENDPOINTS
# ==========================================
@app.route('/', methods=['GET'])
def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>DARK LIKES BOT - API</title>
        <style>
            body { background-color: #0d0d0d; color: #00ffcc; font-family: 'Courier New', Courier, monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; overflow: hidden; }
            .terminal { border: 2px solid #00ffcc; padding: 40px; box-shadow: 0 0 15px #00ffcc; text-align: center; background: rgba(0, 0, 0, 0.8); border-radius: 10px; }
            h1 { font-size: 2.5em; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 2px; }
            .status { color: #39ff14; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="terminal">
            <h1>⚡ DARK LIKES BOT ⚡</h1>
            <p>API SYSTEM <span class="status">ONLINE</span></p>
            <p>MULTI-TOKEN UPLOAD: <span class="status">ENABLED</span></p>
        </div>
    </body>
    </html>
    """
    return html_content

@app.route('/upload_tokens', methods=['POST'])
def upload_tokens():
    global ACTIVE_TOKENS
    api_key = request.headers.get("key")
    if api_key not in VALID_API_KEYS: return jsonify({"error": "Access Denied"}), 401
    
    data = request.json
    if isinstance(data, list) and len(data) > 0 and 'token' in data[0]:
        ACTIVE_TOKENS = data
        return jsonify({"status": "Success", "message": f"{len(data)} Tokens Loaded Instantly!"})
    return jsonify({"error": "Invalid JSON format. Must be a list of tokens."}), 400

@app.route('/status', methods=['GET'])
def check_status():
    api_key = request.args.get("key")
    if api_key not in VALID_API_KEYS: return jsonify({"error": "Access Denied"}), 401
    
    region = request.args.get("region", "IND").upper()
    tokens = load_tokens(region)
    if not tokens: return jsonify({"error": "No tokens found."})
    
    results = []
    for i, t_data in enumerate(tokens[:10]): # Can check up to 10 bots now
        token = t_data.get("token", "")
        uid = decode_jwt_uid(token)
        
        if not uid:
            results.append({"bot": i+1, "status": "❌ Invalid Token", "level": 0})
            continue
            
        encrypted_uid = enc(uid)
        info = make_request(encrypted_uid, region, token)
        
        if info and info.AccountInfo and info.AccountInfo.UID:
            results.append({
                "bot": i+1, "name": info.AccountInfo.PlayerNickname, 
                "uid": uid, "status": "✅ Active", "level": info.AccountInfo.Levels
            })
        else:
            results.append({"bot": i+1, "uid": uid, "status": "⚠️ Expired/Blocked", "level": 0})
            
    return jsonify({"total_tokens": len(tokens), "data": results})

@app.route('/visit', methods=['GET'])
def handle_visit():
    api_key = request.args.get("key")
    if api_key not in VALID_API_KEYS: return jsonify({"error": "Access Denied"}), 401

    uid = request.args.get("uid")
    region = request.args.get("region", "").upper()
    if not uid or not region: return jsonify({"error": "UID required"}), 400

    try:
        tokens = load_tokens(region)
        if not tokens: raise Exception("JSON Error: Token not found.")
        
        # Loop through tokens until one works
        info = None
        for t_data in tokens:
            encrypted_uid = enc(uid)
            info = make_request(encrypted_uid, region, t_data['token'])
            if info and info.AccountInfo.UID: break
            
        if info is None: raise Exception("API Error: All Tokens Expired or Blocked.")
        
        result = OrderedDict([
            ("PlayerNickname", info.AccountInfo.PlayerNickname),
            ("PlayerLevel", info.AccountInfo.Levels),
            ("Likes", info.AccountInfo.Likes),
            ("UID", info.AccountInfo.UID)
        ])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/like', methods=['GET'])
def handle_requests():
    global used_count
    api_key = request.args.get("key")
    if api_key not in VALID_API_KEYS: return jsonify({"error": "Access Denied", "status": 3}), 401

    uid = request.args.get("uid")
    region = request.args.get("region", "").upper()
    if not uid or not region: return jsonify({"error": "UID required"}), 400

    try:
        tokens = load_tokens(region)
        if not tokens: raise Exception("JSON Error: Token not found.")
        
        # Find a working token for 'before' request
        before = None
        working_token = None
        for t_data in tokens:
            encrypted_uid = enc(uid)
            before = make_request(encrypted_uid, region, t_data['token'])
            if before and before.AccountInfo.UID:
                working_token = t_data['token']
                break
                
        if before is None: raise Exception("API Error: All Tokens Expired or Blocked.")
        before_like = before.AccountInfo.Likes

        url = "https://client.ind.freefiremobile.com/LikeProfile"
        asyncio.run(send_multiple_requests(uid, region, url))

        after = make_request(encrypted_uid, region, working_token)
        if after is None: raise Exception("API Error: Failed to fetch data after liking.")
        after_like = after.AccountInfo.Likes
        
        like_given = after_like - before_like
        status = 1 if like_given > 0 else 2
        if status == 1: used_count += 1

        result = OrderedDict([
            ("LikesGivenByAPI", like_given),
            ("LikesafterCommand", after_like),
            ("LikesbeforeCommand", before_like),
            ("PlayerNickname", after.AccountInfo.PlayerNickname),
            ("PlayerLevel", after.AccountInfo.Levels),
            ("UID", after.AccountInfo.UID),
            ("status", status)
        ])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
        

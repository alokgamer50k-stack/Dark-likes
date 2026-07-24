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

async def send_multiple_requests(uid, region, url, token):
    try:
        protobuf_message = create_protobuf_message(uid, region)
        encrypted_uid = encrypt_message(protobuf_message)
        if not token or not encrypted_uid: return None
        
        # 🔥 THE ZEXXY TRICK (30 Requests instantly) 🔥
        tasks = []
        for _ in range(30): 
            tasks.append(send_request(encrypted_uid, token, url))
            
        return await asyncio.gather(*tasks, return_exceptions=True)
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

def make_request(encrypt, token):
    try:
        url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "ReleaseVersion": "OB54"
        }
        response = requests.post(url, data=bytes.fromhex(encrypt), headers=headers, verify=False)
        decoded = visit_count_pb2.Info()
        decoded.ParseFromString(response.content)
        return decoded
    except Exception: return None

def decode_jwt_uid(token):
    try:
        parts = token.split('.')
        padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
        return str(json.loads(base64.b64decode(padded).decode('utf-8')).get('account_id', ''))
    except: return None

@app.route('/', methods=['GET'])
def home():
    return "<h1>⚡ DARK MASTER API ONLINE (AUTO-TOKEN MODE) ⚡</h1>"

@app.route('/status', methods=['GET'])
def check_status():
    api_key = request.args.get("key")
    token = request.args.get("token")
    if api_key not in VALID_API_KEYS: return jsonify({"error": "Access Denied"}), 401
    if not token: return jsonify({"error": "No token provided by Wispbyte."})
    
    uid = decode_jwt_uid(token)
    if not uid: return jsonify({"data": [{"bot": 1, "status": "❌ Invalid Token", "level": 0}]})
        
    encrypted_uid = enc(uid)
    info = make_request(encrypted_uid, token)
    
    if info and info.AccountInfo and info.AccountInfo.UID:
        return jsonify({"data": [{"bot": 1, "name": info.AccountInfo.PlayerNickname, "uid": uid, "status": "✅ Active (Race Ready)", "level": info.AccountInfo.Levels}]})
    else:
        return jsonify({"data": [{"bot": 1, "uid": uid, "status": "⚠️ Expired/Blocked", "level": 0}]})

@app.route('/visit', methods=['GET'])
def handle_visit():
    api_key = request.args.get("key")
    token = request.args.get("token")
    if api_key not in VALID_API_KEYS: return jsonify({"error": "Access Denied"}), 401
    if not token: return jsonify({"error": "No token provided."})
    
    uid = request.args.get("uid")
    try:
        encrypted_uid = enc(uid)
        info = make_request(encrypted_uid, token)
        if info is None or not info.AccountInfo.UID: raise Exception("Token Expired or Blocked.")
        
        result = OrderedDict([("PlayerNickname", info.AccountInfo.PlayerNickname), ("PlayerLevel", info.AccountInfo.Levels), ("Likes", info.AccountInfo.Likes), ("UID", info.AccountInfo.UID)])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/like', methods=['GET'])
def handle_requests():
    api_key = request.args.get("key")
    token = request.args.get("token")
    if api_key not in VALID_API_KEYS: return jsonify({"error": "Access Denied"}), 401
    if not token: return jsonify({"error": "No token provided."})
    
    uid = request.args.get("uid")
    region = request.args.get("region", "IND").upper()

    try:
        encrypted_uid = enc(uid)
        before = make_request(encrypted_uid, token)
        
        if before is None or not before.AccountInfo.UID: raise Exception("Token Expired or Invalid.")
        before_like = before.AccountInfo.Likes

        # रेस कंडीशन फायर (एक साथ 30 लाइक्स)
        url = "https://client.ind.freefiremobile.com/LikeProfile"
        asyncio.run(send_multiple_requests(uid, region, url, token))

        after = make_request(encrypted_uid, token)
        after_like = after.AccountInfo.Likes
        
        like_given = after_like - before_like
        status = 1 if like_given > 0 else 2
        msg = "SUCCESS" if status == 1 else "⚠️ *DAILY LIMIT REACHED!* कल सुबह 4:00 AM बजे नया लाइक जाएगा।"

        result = OrderedDict([
            ("LikesGivenByAPI", like_given),
            ("LikesafterCommand", after_like),
            ("LikesbeforeCommand", before_like),
            ("PlayerNickname", after.AccountInfo.PlayerNickname),
            ("UID", after.AccountInfo.UID),
            ("status", status),
            ("message", msg)
        ])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    

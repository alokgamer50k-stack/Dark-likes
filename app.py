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

def load_tokens(region):
    try:
        with open("token_ind.json", "r") as f: 
            return json.load(f)
    except Exception: return None

# ... [encrypt_message, create_protobuf_message, send_request, create_protobuf, enc, make_request, decode_jwt_uid] ...
# (नोट: बाकी के सभी फंक्शन पिछली फाइल की तरह सेम रहेंगे, बस /like वाला राऊट अपडेट कर लें)

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
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
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
        for t_data in tokens:
            tasks.append(send_request(encrypted_uid, t_data["token"], url))
            
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

def make_request(encrypt, region, token):
    try:
        url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/x-www-form-urlencoded", "X-Unity-Version": "2018.4.11f1", "ReleaseVersion": "OB54"}
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

@app.route('/like', methods=['GET'])
def handle_requests():
    global used_count
    api_key = request.args.get("key")
    if api_key not in VALID_API_KEYS: return jsonify({"error": "Access Denied"}), 401
    uid = request.args.get("uid")
    region = request.args.get("region", "").upper()
    
    tokens = load_tokens(region)
    if not tokens: return jsonify({"error": "No tokens found."}), 400
    total_bots = len(tokens)

    try:
        before = None
        working_token = None
        for t_data in tokens:
            encrypted_uid = enc(uid)
            before = make_request(encrypted_uid, region, t_data['token'])
            if before and before.AccountInfo.UID:
                working_token = t_data['token']
                break
                
        if before is None: raise Exception("API Error: All Tokens Expired.")
        before_like = before.AccountInfo.Likes

        url = "https://client.ind.freefiremobile.com/LikeProfile"
        asyncio.run(send_multiple_requests(uid, region, url))

        after = make_request(encrypted_uid, region, working_token)
        after_like = after.AccountInfo.Likes
        
        like_given = after_like - before_like
        
        if like_given > 0:
            status = 1
            msg = "SUCCESS"
        else:
            status = 2
            msg = "⚠️ *DAILY LIMIT REACHED!* आपके सभी बॉट्स ने लाइक कर दिया है। कल सुबह 4:00 AM बजे टोकन रिसेट होंगे।"

        result = OrderedDict([
            ("LikesGivenByAPI", like_given),
            ("TotalBotsLoaded", total_bots),
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

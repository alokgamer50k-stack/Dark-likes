from flask import Flask, request, jsonify, render_template_string
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import aiohttp
import requests
import json
import like_pb2
import uid_generator_pb2
import visit_count_pb2
from collections import OrderedDict

app = Flask(__name__)

# API Key for DARK Brand
VALID_API_KEYS = {"DARK"}
daily_limit = 20
used_count = 0

# ==========================================
# 1. LIKE API LOGIC (Background System)
# ==========================================
def load_tokens(region):
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
        for i in range(100):
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

@app.route('/like', methods=['GET'])
def handle_requests():
    global used_count
    api_key = request.args.get("key")
    if api_key not in VALID_API_KEYS:
        return jsonify({"error": "Access Denied", "status": 3}), 401

    uid = request.args.get("uid")
    region = request.args.get("region", "").upper()
    if not uid or not region: return jsonify({"error": "UID required"}), 400

    try:
        tokens = load_tokens(region)
        if not tokens: raise Exception("Failed to load tokens.")
        
        token = tokens[0]['token']
        encrypted_uid = enc(uid)
        
        before = make_request(encrypted_uid, region, token)
        if before is None: raise Exception("Failed to get info.")
        before_like = before.AccountInfo.Likes

        url = "https://client.ind.freefiremobile.com/LikeProfile"
        asyncio.run(send_multiple_requests(uid, region, url))

        after = make_request(encrypted_uid, region, token)
        if after is None: raise Exception("Failed to get info.")
        after_like = after.AccountInfo.Likes
        
        like_given = after_like - before_like
        status = 1 if like_given > 0 else 2
        if status == 1: used_count += 1

        result = OrderedDict([
            ("LikesGivenByAPI", like_given),
            ("LikesafterCommand", after_like),
            ("LikesbeforeCommand", before_like),
            ("PlayerNickname", after.AccountInfo.PlayerNickname),
            ("UID", after.AccountInfo.UID),
            ("status", status)
        ])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# 2. JWT GENERATOR WEBSITE (File Upload UI)
# ==========================================
@app.route('/', methods=['GET'])
def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DARK LIKES BOT - Token Gen</title>
        <style>
            * { box-sizing: border-box; }
            body { 
                background-color: #0d0d0d; 
                color: #00ffcc; 
                font-family: 'Courier New', Courier, monospace; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                height: 100vh; 
                margin: 0; 
                overflow: hidden; 
            }
            .container { 
                border: 2px solid #00ffcc; 
                padding: 40px; 
                box-shadow: 0 0 15px #00ffcc; 
                text-align: center; 
                background: rgba(0, 0, 0, 0.9); 
                border-radius: 10px; 
                width: 380px; 
            }
            h1 { font-size: 1.8em; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 1px;}
            label { display: block; text-align: left; margin: 15px 0 5px 0; color: #39ff14; font-weight: bold; }
            input[type="file"] {
                width: 100%;
                padding: 10px;
                background: #1a1a1a;
                color: #00ffcc;
                border: 1px dashed #00ffcc;
                border-radius: 5px;
                cursor: pointer;
            }
            select { 
                width: 100%; 
                padding: 12px; 
                margin: 10px 0; 
                background: #1a1a1a; 
                color: #00ffcc; 
                border: 1px solid #00ffcc; 
                border-radius: 5px; 
                font-family: 'Courier New', Courier, monospace;
            }
            input:focus, select:focus { outline: none; border-color: #39ff14; }
            button { 
                width: 100%; 
                padding: 12px; 
                background: #00ffcc; 
                color: #0d0d0d; 
                border: none; 
                font-weight: bold; 
                font-size: 1.1em;
                cursor: pointer; 
                border-radius: 5px; 
                margin-top: 20px; 
                transition: 0.3s;
            }
            button:hover { background: #39ff14; box-shadow: 0 0 10px #39ff14;}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚡ DARK TOKEN GEN ⚡</h1>
            <!-- enctype="multipart/form-data" file upload ke liye zaroori hai -->
            <form action="/generate" method="POST" enctype="multipart/form-data">
                <label>Upload Guest File:</label>
                <input type="file" name="guest_file" required>
                
                <label>Select Region:</label>
                <select name="region">
                    <option value="IND">India (IND)</option>
                    <option value="BD">Bangladesh (BD)</option>
                    <option value="SG">Singapore (SG)</option>
                </select>
                
                <button type="submit">GENERATE JWT</button>
            </form>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_content)

@app.route('/generate', methods=['POST'])
def generate_token():
    # File check karna
    if 'guest_file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['guest_file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    region = request.form.get('region', 'IND')
    
    try:
        # File ke andar ka text (Device ID) read karna
        file_content = file.read()
        device_id = file_content.decode('utf-8').strip()
        
        # यहाँ पर Garena सर्वर से कनेक्ट करने वाला मेन जनरेटर लॉजिक आएगा
        # अभी यह चेक करने के लिए है कि फाइल सही से रीड हो रही है या नहीं
        return jsonify({
            "status": "Success",
            "message": "File uploaded and read successfully.",
            "extracted_device_id": device_id,
            "region": region,
            "note": "Garena Auth backend logic will be added here next."
        })
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
        

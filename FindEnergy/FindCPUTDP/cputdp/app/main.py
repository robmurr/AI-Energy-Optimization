from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

client = MongoClient("mongodb://mongo:27017/")
db = client["cputdp"]
collection = db["tdps"]

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def fetch_tdp(cpu_name):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "I will give you CPU information and I need you to do research and find the CPU's Thermal Design Power. ONLY return the number of the TDP and NOTHING else. If you cannot find their CPU TDP, give an estimate based on what is most likely, given the manufacturer and the family of chips it is in, etc."},
                {"role": "user", "content": cpu_name}
            ]
        )
        output = response.choices[0].message.content.strip()
        print(output)
        # Try to extract the first int in the response
        for token in output.split():
            if token.isdigit():
                return int(token)

        return -1  # fallback if no number found
    except:
        return -1

@app.route("/get-tdp", methods=["POST"])
def get_tdp():
    data = request.get_json()
    cpu_name = data.get("cpu_name", "")

    existing = collection.find_one({"cpu_name": cpu_name})
    if existing:
        return jsonify({"tdp": existing["tdp"]}), 200

    tdp = fetch_tdp(cpu_name)
    if tdp == -1:
        return jsonify({"error": "TDP not found"}), 404

    collection.insert_one({"cpu_name": cpu_name, "tdp": tdp})
    return jsonify({"tdp": tdp}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


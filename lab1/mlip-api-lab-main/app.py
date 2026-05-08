from flask import Flask, request, jsonify, render_template
from analyze import get_itinerary
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/api/v1/itinerary")
def itinerary():
    destination = request.args.get("destination", "").strip()

    # Basic request validation
    if not destination:
        return jsonify({"error": "Missing required query parameter: destination"}), 400
    if len(destination) > 120:
        return jsonify({"error": "destination is too long (max 120 chars)"}), 400

    try:
        result = get_itinerary(destination)
        return jsonify(result), 200
    except ValueError as e:
        # Client-side input errors
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # Upstream/model errors
        return jsonify({"error": f"Failed to generate itinerary: {e}"}), 502




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)

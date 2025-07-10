from flask import Flask, request, jsonify
from kairos_scraper import login_kairos, get_notes, get_planning, get_absences, parse_notes_html, format_planning

app = Flask(__name__)
@app.route("/")
def home():
    return "<h1>Bienvenue sur mon API Kairos BEM</h1>"

@app.route("/notes", methods=["POST"])
def notes():
    data = request.json
    session = login_kairos(data["j_username"], data["j_password"])
    if not session:
        return jsonify({"error": "Identifiants invalides"}), 401
    notes_html = get_notes(session)
    notes_data = parse_notes_html(notes_html)
    return jsonify({"notes": notes_data})


@app.route("/planning", methods=["POST"])
def planning():
    data = request.json
    session = login_kairos(data["j_username"], data["j_password"])
    if not session:
        return jsonify({"error": "Identifiants invalides"}), 401
    start = data.get("start")
    end = data.get("end")
    classe_id = data.get("classeId")
    planning_data = get_planning(session, start, end, classe_id)
    formatted = format_planning(planning_data)
    return jsonify(formatted)

@app.route("/absences", methods=["POST"])
def absences():
    data = request.json
    session = login_kairos(data["j_username"], data["j_password"])
    if not session:
        return jsonify({"error": "Identifiants invalides"}), 401
    absences_data = get_absences(session)
    return jsonify({"absences": absences_data})

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)


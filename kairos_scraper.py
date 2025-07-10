import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime


BASE_URL = "https://bem.kairossuite.com/kairos_bem/"

def login_kairos(username, password):
    session = requests.Session()
    login_url = BASE_URL + "j_spring_security_check"  # nom exact du handler Kairos

    payload = {
        "j_username": username,
        "j_password": password
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0",
        "Referer": BASE_URL + "login"
    }

    response = session.post(login_url, data=payload, headers=headers)

    # Vérifie si le login a réussi en testant la redirection vers /portailEtudiant
    if "portailEtudiant" in response.text or response.url.endswith("portailEtudiant"):
        return session

    print("[DEBUG] Échec de la connexion : ", response.url)
    return None


def get_notes(session):
    url = BASE_URL + "portailEtudiant/ajaxGetNoteAnnee"
    headers = {
        "x-requested-with": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": BASE_URL + "portailEtudiant/note",
        "Origin": "https://bem.kairossuite.com",
        "User-Agent": "Mozilla/5.0"
    }
    payload = {
        "anneeScolaireId": "104"
    }
    response = session.post(url, headers=headers, data=payload)
    return response.text



def parse_notes_html(html):
    soup = BeautifulSoup(html, "html.parser")
    notes = []

    rows = soup.find_all("tr")
    for row in rows:
        try:
            td = row.find("td")
            if not td:
                continue

            # Matière
            subject_div = td.find("div", style=lambda v: v and "font-size" in v)
            subject = subject_div.get_text(strip=True) if subject_div else None

            # Type et Date
            small_tags = td.find_all("small")
            type_, date, semestre = None, None, None
            for tag in small_tags:
                text = tag.get_text(strip=True)
                if "Semestre" in text:
                    # Extrait "Semestre X"
                    for part in text.split("|"):
                        part = part.strip()
                        if part.startswith("Semestre"):
                            semestre = part
                if "Examen" in text or "Devoir" in text or "Devoirs" in text:
                    parts = text.split("du")
                    if len(parts) == 2:
                        type_ = parts[0].strip()
                        date = parts[1].strip()

            # Enseignant
            enseignant_tag = td.find("i", class_="fa fa-user")
            enseignant = enseignant_tag.next_sibling.strip() if enseignant_tag else None

            # Note
            badge = td.find("span", class_="badge")
            note_text = badge.text.strip() if badge else None
            if note_text and note_text == "portailParent.note.notFound":
                note = None
            else:
                try:
                    note = float(note_text.replace(',', '.')) if note_text else None
                except:
                    note = None

            if subject and enseignant:
                notes.append({
                    "matiere": subject,
                    "type": type_,
                    "date": date,
                    "enseignant": enseignant,
                    "semestre": semestre,
                    "note": note
                })
        except Exception as e:
            print(f"Erreur de parsing: {e}")
            continue

    return notes



def get_planning(session, start, end, classe_id):
    url = f"https://bem.kairossuite.com/kairos_bem/portailEtudiant/getEmploisDuTemps?start={start}&end={end}&classeId={classe_id}"
    
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://bem.kairossuite.com/kairos_bem/portailEtudiant/emploiDuTemps",
        "X-Requested-With": "XMLHttpRequest"
    }

    response = session.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()  # liste des événements
    else:
        return {"error": "Erreur récupération planning"}
    

def format_planning(data):
    formatted = []
    for event in data:
        objet = event.get("objet", "")
        match = re.match(
            r"(.+?)\s*-\s*(Semestre\s\d+)\s*\[professeur\s*:\s*[^-]+-\s*(.+?)\s*,\s*salle\s*:\s*(.+?)\s*\]",
            objet
        )
        if match:
            matiere, semestre, professeur, salle = match.groups()
        else:
            matiere = professeur = salle = semestre = "Inconnu"
        formatted.append({
            "couleur": event.get("couleur"),
            "matiere": matiere,
            "professeur": professeur,
            "salle": salle,
            "semestre": semestre,
            "debut": datetime.strptime(event["heureDebut"].split(".")[0], "%Y-%m-%d %H:%M:%S").isoformat(),
            "fin": datetime.strptime(event["heureFin"].split(".")[0], "%Y-%m-%d %H:%M:%S").isoformat()
        })
    return formatted


def get_absences(session):
    url = "https://bem.kairossuite.com/kairos_bem/portailEtudiant/assiduite"
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://bem.kairossuite.com/kairos_bem/portailEtudiant/emploiDuTemps"
    }

    response = session.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    with open("debug_absences.html", "w", encoding="utf-8") as f:
        f.write(response.text)

    return parse_absences_html(response.text)


def parse_absences_html(html):
    soup = BeautifulSoup(html, "html.parser")
    absences = []

    for row in soup.find_all("tr", class_=["odd", "even"]):
        professeur = row.find("i", class_="fa fa-user")
        professeur_nom = professeur.find_next(text=True).strip() if professeur else ""

        matiere_div = row.find("div", style=lambda x: x and "font-size: 18px" in x)
        matiere = matiere_div.get_text(strip=True) if matiere_div else ""

        date_tag = row.find("i", class_="fa fa- fa-calendar")
        date = date_tag.find_parent("b").find_next_sibling(text=True).strip() if date_tag else ""

        statut_badge = row.find("span", class_="badge badge-thunderbird")
        statut = statut_badge.get_text(strip=True) if statut_badge else ""

        absences.append({
            "matiere": matiere,
            "date": date,
            "statut": statut,
            "professeur": professeur_nom
        })

    return absences

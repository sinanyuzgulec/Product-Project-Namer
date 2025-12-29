import os
import json
import random
import whois
import threading
import csv
from flask import Flask, render_template, jsonify, request, send_file

app = Flask(__name__)

DB_FILE = "saved_names.json" 

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except:
            return {}
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_name', methods=['POST'])
def generate_name():
    config = request.json
    length = int(config.get('length', 6))
    structure = config.get('structure', 'CVCV')
    
    consonants = "bcdfghjklmnpqrstvwxyz"
    vowels = "aeiou"
    
    name = ""
    for i in range(length):
        if i % 2 == 0:
            name += random.choice(consonants)
        else:
            name += random.choice(vowels)
            
    if structure == 'CVCVC' and length >= 5:
        list_name = list(name)
        list_name[2] = random.choice(consonants)
        name = "".join(list_name)

    return jsonify({"name": name.capitalize()})

@app.route('/check_availability', methods=['POST'])
def check_availability():
    data = request.json
    name = data.get('name')
    extensions = data.get('extensions', [".com", ".net", ".org", ".io"])
    
    db = load_db()
    results = {}
    name_lower = name.lower()
    threads = []

    def check_single(ext):
        try:
            w = whois.whois(name_lower + ext)
            results[ext] = False if (w.domain_name or w.status) else True
        except:
            results[ext] = True

    for ext in extensions:
        t = threading.Thread(target=check_single, args=(ext,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=5)
    
    db[name] = results
    save_db(db)
    return jsonify(results)

@app.route('/save_name', methods=['POST'])
def save_name():
    db = load_db()
    name = request.json.get('name')
    if name and name not in db:
        db[name] = None 
        save_db(db)
    return jsonify({"status": "success"})

@app.route('/delete_name', methods=['POST'])
def delete_name():
    db = load_db()
    name = request.json.get('name')
    if name in db:
        del db[name]
        save_db(db)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

@app.route('/list_saved')
def list_saved():
    return jsonify({"saved": load_db()})

@app.route('/export')
def export_csv():
    db = load_db()
    if not db: return "Liste boş", 400
    
    all_exts = set()
    for val in db.values():
        if isinstance(val, dict):
            all_exts.update(val.keys())
    ext_list = sorted(list(all_exts))
    
    csv_file = "proje_isim_listesi.csv"
    with open(csv_file, "w", encoding="utf-8-sig", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Proje/Ürün İsmi"] + ext_list)
        for name, domains in db.items():
            row = [name]
            for ext in ext_list:
                status = "Müsait" if isinstance(domains, dict) and domains.get(ext) else "Dolu"
                row.append(status)
            writer.writerow(row)
    return send_file(csv_file, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
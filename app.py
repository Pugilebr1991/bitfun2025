from flask import Flask, render_template, request, redirect, url_for, session, jsonify 
import mysql.connector
import requests
import json
from config import (
    DB_CONFIG, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, BITCOIN_ADDRESS, SECRET_KEY,
    PAYMENT_ENABLED, COINBASE_API_KEY, COINBASE_WEBHOOK_SECRET, SITE_URL,
    SUBSCRIPTION_PRICE_BTC, REFERRAL_COMMISSION_BTC, COINBASE_WALLET_API_KEY, COINBASE_WALLET_API_SECRET
)
from flask_bcrypt import Bcrypt
from coinbase_commerce.client import Client
from coinbase_commerce.error import SignatureVerificationError
from coinbase_commerce.webhook import Webhook
from datetime import datetime, timedelta

# ========================
# Flask setup
# ========================
app = Flask(__name__)
app.secret_key = SECRET_KEY
bcrypt = Bcrypt(app)

# Connessione al database
db = mysql.connector.connect(**DB_CONFIG)

# Coinbase Commerce client
coinbase_client = Client(api_key=COINBASE_API_KEY)

# ========================
# Rotte principali
# ========================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/referral")
def referral_info():
    return render_template("referral.html")

@app.route("/obiettivi")
def obiettivi():
    return render_template("obiettivi.html")

@app.route("/graduatoria")
def graduatoria():
    return render_template("graduatoria.html")

@app.route("/graduatoriainfo")
def graduatoriainfo():
    if "users_id" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, nome, cognome, wallet, graduatoria_pos FROM users ORDER BY graduatoria_pos ASC")
    graduatoria = cursor.fetchall()
    return render_template("graduatoriainfo.html", graduatoria=graduatoria)

# ========================
# Registrazione e login
# ========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form["nome"]
        cognome = request.form["cognome"]
        email = request.form["email"]
        password = request.form["password"]
        wallet = request.form["wallet"]
        referral = request.form.get("referral", None)

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO users (nome, cognome, email, password, wallet, referral, graduatoria_pos) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (nome, cognome, email, hashed_pw, wallet, referral, 0)
        )
        db.commit()
        user_id = cursor.lastrowid
        session["user_id"] = user_id

        if PAYMENT_ENABLED:
            return redirect(url_for("pagamento_bitcoin"))
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        if user and bcrypt.check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        else:
            return "Email o password non corretti!"
    return render_template("login.html")

# ========================
# Dashboard
# ========================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    cursor = db.cursor(dictionary=True)

    # Recupera utente
    cursor.execute("SELECT id, nome, cognome, email, wallet, graduatoria_pos, abbonamento_attivo, referral, data_abbonamento FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    # Recupera invitati
    cursor.execute("SELECT * FROM users WHERE referral=%s", (user["id"],))
    invitati = cursor.fetchall()

    bitcoin_inviati = 0
    bitcoin_ricevuti = 0

    crypto_price = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur,usd"
    ).json()

    prezzo_eur = crypto_price["bitcoin"]["eur"]
    prezzo_usd = crypto_price["bitcoin"]["usd"]
    prezzo_fisso_btc = SUBSCRIPTION_PRICE_BTC

    # ✅ Passiamo la data come stringa ISO (leggibile da JS per countdown)
    data_abbonamento_iso = user["data_abbonamento"].strftime("%Y-%m-%dT%H:%M:%S") if user["data_abbonamento"] else None

    return render_template(
        "dashboard.html",
        user=user,
        invitati=invitati,
        btc_inviati=bitcoin_inviati,
        btc_ricevuti=bitcoin_ricevuti,
        prezzo_eur=prezzo_eur,
        prezzo_usd=prezzo_usd,
        prezzo_fisso_btc=prezzo_fisso_btc,
        data_abbonamento_iso=data_abbonamento_iso
    )

# ========================
# Pagamento automatico Coinbase Commerce (BTC-only)
# ========================
@app.route("/pagamento_bitcoin")
def pagamento_bitcoin():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    try:
        btc_amount_str = f"{SUBSCRIPTION_PRICE_BTC:.8f}"

        charge_data = {
            "name": "Abbonamento BitFun Mensile",
            "description": f"Pagamento mensile in Bitcoin utente ID {user_id}",
            "pricing_type": "fixed_price",
            "local_price": {"amount": btc_amount_str, "currency": "BTC"},
            "metadata": {"user_id": user_id},
            "redirect_url": f"{SITE_URL}/dashboard",
            "cancel_url": f"{SITE_URL}/dashboard"
        }

        try:
            charge_data["payment_currencies"] = ["BTC"]
            charge = coinbase_client.charge.create(**charge_data)
        except Exception:
            charge_data.pop("payment_currencies", None)
            charge = coinbase_client.charge.create(**charge_data)

        checkout_url = charge.hosted_url
    except Exception as e:
        return f"Errore durante la creazione del pagamento Bitcoin: {e}"

    return redirect(checkout_url)

# ========================
# Funzione per inviare BTC tramite Coinbase Wallet API
# ========================
def invia_btc_wallet(to_address, amount_btc, note="Pagamento referral"):
    url = "https://api.coinbase.com/v2/accounts/primary/transactions"
    headers = {
        "Content-Type": "application/json",
        "CB-VERSION": "2025-08-18",
        "Authorization": f"Bearer {COINBASE_WALLET_API_KEY}"
    }
    payload = {
        "type": "send",
        "to": to_address,
        "amount": f"{amount_btc:.8f}",
        "currency": "BTC",
        "description": note
    }
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code in [200, 201]:
        return response.json()
    else:
        raise Exception(f"Errore invio BTC: {response.text}")

# ========================
# Helper: aggiorna graduatoria
# ========================
def aggiorna_graduatoria(user_id, referral_id=None):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, graduatoria_pos FROM users ORDER BY graduatoria_pos ASC")
    utenti = cursor.fetchall()

    if referral_id:
        cursor.execute("UPDATE users SET referral=%s WHERE id=%s", (referral_id, user_id))
        db.commit()
        max_pos = max([u["graduatoria_pos"] for u in utenti], default=0)
        cursor.execute("UPDATE users SET graduatoria_pos=%s WHERE id=%s", (max_pos + 1, user_id))
        db.commit()
    else:
        if utenti:
            for u in utenti:
                cursor.execute("UPDATE users SET graduatoria_pos=graduatoria_pos+1 WHERE id=%s", (u["id"],))
            db.commit()
        cursor.execute("UPDATE users SET graduatoria_pos=1 WHERE id=%s", (user_id,))
        db.commit()

# ========================
# Webhook Coinbase Commerce con referral automatico
# ========================
@app.route("/coinbase_webhook", methods=["POST"])
def coinbase_webhook():
    payload = request.data
    signature = request.headers.get("X-CC-Webhook-Signature", "")

    try:
        event = Webhook.construct_event(payload, signature, COINBASE_WEBHOOK_SECRET)

        if event["type"] in ["charge:confirmed", "checkout:completed"]:
            data = event.get("data", {}) or {}
            metadata = data.get("metadata", {}) or {}
            user_id = metadata.get("user_id")
            if user_id:
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                user = cursor.fetchone()

                referral_id = user.get("referral")

                # Aggiorna graduatoria
                if not referral_id:
                    aggiorna_graduatoria(user_id)
                else:
                    aggiorna_graduatoria(user_id, referral_id)

                # ✅ Aggiorna data abbonamento
                cursor.execute("UPDATE users SET abbonamento_attivo=1, data_abbonamento=%s WHERE id=%s", (datetime.utcnow(), user_id))
                db.commit()

                messaggio = f"💰 Pagamento confermato per {user['nome']} {user['cognome']}."

                if referral_id:
                    cursor.execute("SELECT * FROM users WHERE id=%s", (referral_id,))
                    ref_user = cursor.fetchone()
                    messaggio += f" 💵 Commissione da inviare a {ref_user['nome']} {ref_user['cognome']}."

                    try:
                        invia_btc_wallet(ref_user["wallet"], REFERRAL_COMMISSION_BTC, note=f"Referral da {user['nome']}")
                        messaggio += " ✅ Referral pagato con successo."
                    except Exception as e:
                        messaggio += f" ⚠️ Errore pagamento referral: {e}"

                invia_telegram(messaggio)

        return jsonify({"status": "success"})
    except SignatureVerificationError:
        return jsonify({"status": "invalid signature"}), 400

# ========================
# Avvisi Telegram
# ========================
def invia_telegram(messaggio):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": messaggio})

# ========================
# Wallets disponibili
# ========================
@app.route("/wallets")
def wallets():
    wallets_data = {
        "Mobile": [
            {"nome": "Trust Wallet", "logo": "trustwalletlogo.png"},
            {"nome": "Coinbase Wallet", "logo": "coinbasewalletlogo.png"},
            {"nome": "MetaMask", "logo": "metamasklogo.png"}
        ],
        "Desktop": [
            {"nome": "Exodus", "logo": "exoduslogo.png"},
            {"nome": "Electrum", "logo": "electrumlogo.png"},
            {"nome": "Coinbase Desktop", "logo": "coinbasewalletlogo.png"}
        ],
        "Web": [
            {"nome": "Coinbase", "logo": "coinbaselogo.png"},
            {"nome": "Binance", "logo": "binancelogo.png"},
            {"nome": "Kraken", "logo": "krakenlogo.png"}
        ]
    }
    return render_template("wallets.html", wallets=wallets_data)

# ========================
# Avvio Flask
# ========================
if __name__ == "__main__":
    app.run(debug=True)

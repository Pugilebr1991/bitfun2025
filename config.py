# ============================
# Configurazioni progetto BitFun.com
# ============================

# Database MySQL
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Bitfun2025.",
    "database": "bitfun"
}

# Telegram Bot
TELEGRAM_TOKEN = "8252612586:AAGMoHSu5Jk7MxoXAZdQXGDxwvWd3Bk91yU"
TELEGRAM_CHAT_ID = "2072924638"

# Wallet Bitcoin (Coinbase)
BITCOIN_ADDRESS = "3LrxMcZ5BWYPcPwmMkViQCgZrNh94ELeiB"

# Sicurezza Flask
SECRET_KEY = "bitfun_secret_key"

# ============================
# Impostazioni pagamento
# ============================
PAYMENT_ENABLED = True  # Abilita/disabilita la pagina pagamento
CURRENCY = "BTC"        # Solo Bitcoin come valuta principale

# Prezzi fissi in Bitcoin
SUBSCRIPTION_PRICE_BTC = 0.002   # Prezzo abbonamento mensile
REFERRAL_COMMISSION_BTC = 0.001  # Commissione referral (50%)

# ============================
# Coinbase Commerce
# ============================
COINBASE_API_KEY = "dd698e9d-75a4-4ee4-8e8c-e88075feb742"
COINBASE_WEBHOOK_SECRET = "d62c81a0-ecba-4085-af14-a349a2b04864"

# ============================
# Coinbase Wallet API (per invio commissioni BTC)
# ============================
COINBASE_WALLET_API_KEY = "organizations/bb4c2b0b-93e4-4bd7-ab8f-5fd3ab9f942f/apiKeys/5ecc3f40-5e90-428e-b4cd-a1448a10e0d2"
COINBASE_WALLET_API_SECRET = "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEEIFzQ6HyllCiZZYOemJHzE0WVAc4IiXa0zRqdP6/BE6QQoAoGCCqGSM49\nAwEHoUQDQgAEl9KGglhHT37k1/Wob7IkLcOKz8aB5kCqLgPL/UIV1UrU92iULcqD\nc+zSfblHvtoNAQ/AnhcB/lEqVqtFuQZrtg==\n-----END EC PRIVATE KEY-----\n"

# URL base del sito, utile per redirect dopo pagamento
SITE_URL = "https://bitfun.com"

# ============================
# Funzioni extra opzionali
# ============================
# Timeout pagamento (in secondi)
PAYMENT_TIMEOUT = 3600  # 1 ora

# Email di notifica admin per errori pagamento
ADMIN_EMAIL = "admin@bitfun.com"

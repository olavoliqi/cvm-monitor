"""
Script de configuração única para obter o refresh token do Gmail OAuth2.

Uso:
  1. Crie um projeto no Google Cloud Console
  2. Ative a Gmail API
  3. Crie credenciais OAuth2 (tipo "App para computador")
  4. Baixe o JSON e coloque neste diretório como 'credentials.json'
  5. Execute: python setup_oauth.py
  6. O refresh token será exibido no terminal
"""

import json
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
REDIRECT_URI = "http://localhost:8090"

auth_code = None


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        auth_code = params.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Autorizado! Pode fechar esta aba.</h1>")

    def log_message(self, format, *args):
        pass  # silencia logs do servidor


def main():
    try:
        with open("credentials.json") as f:
            creds = json.load(f)
    except FileNotFoundError:
        print("Erro: 'credentials.json' não encontrado neste diretório.")
        print("Baixe as credenciais OAuth2 do Google Cloud Console.")
        sys.exit(1)

    # O JSON pode ter a chave "installed" ou "web"
    info = creds.get("installed") or creds.get("web")
    if not info:
        print("Erro: formato de credentials.json inválido.")
        sys.exit(1)

    client_id = info["client_id"]
    client_secret = info["client_secret"]
    auth_uri = info.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")
    token_uri = info.get("token_uri", "https://oauth2.googleapis.com/token")

    # Montar URL de autorização
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    })
    auth_url = f"{auth_uri}?{params}"

    print(f"Abrindo navegador para autorização...")
    print(f"Se não abrir automaticamente, acesse:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Servidor local para receber o callback
    server = HTTPServer(("localhost", 8090), OAuthHandler)
    print("Aguardando autorização no navegador...")
    server.handle_request()

    if not auth_code:
        print("Erro: não foi possível obter o código de autorização.")
        sys.exit(1)

    # Trocar código por tokens
    import requests
    resp = requests.post(token_uri, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    })
    resp.raise_for_status()
    tokens = resp.json()

    print("\n" + "=" * 60)
    print("CONFIGURAÇÃO CONCLUÍDA!")
    print("=" * 60)
    print(f"\nDefina estes secrets no GitHub Actions:\n")
    print(f"  GMAIL_CLIENT_ID     = {client_id}")
    print(f"  GMAIL_CLIENT_SECRET = {client_secret}")
    print(f"  GMAIL_REFRESH_TOKEN = {tokens['refresh_token']}")
    print(f"  GMAIL_ADDRESS       = olavo@liqi.com.br")
    print(f"\n{'=' * 60}")


if __name__ == "__main__":
    main()

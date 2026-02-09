"""
Monitor diário de ofertas públicas CVM (Resolução 160 + ICVM 400/476).
Baixa o CSV da CVM, filtra ofertas registradas no dia útil anterior,
e envia resumo por e-mail via Gmail API (OAuth2).
"""

import base64
import io
import os
import zipfile
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import requests

CVM_URL = "https://dados.cvm.gov.br/dados/OFERTA/DISTRIB/DADOS/oferta_distribuicao.zip"
CSV_ENCODING = "latin-1"
CSV_SEP = ";"

# Feriados nacionais brasileiros fixos + móveis conhecidos para 2025-2026.
# Atualize esta lista anualmente ou use uma lib como workalendar.
FERIADOS_BR = {
    # 2025
    date(2025, 1, 1),   # Confraternização
    date(2025, 3, 3),   # Carnaval
    date(2025, 3, 4),   # Carnaval
    date(2025, 4, 18),  # Sexta-feira Santa
    date(2025, 4, 21),  # Tiradentes
    date(2025, 5, 1),   # Dia do Trabalho
    date(2025, 6, 19),  # Corpus Christi
    date(2025, 9, 7),   # Independência
    date(2025, 10, 12), # N.S. Aparecida
    date(2025, 11, 2),  # Finados
    date(2025, 11, 15), # Proclamação da República
    date(2025, 11, 20), # Consciência Negra
    date(2025, 12, 25), # Natal
    # 2026
    date(2026, 1, 1),
    date(2026, 2, 16),  # Carnaval
    date(2026, 2, 17),  # Carnaval
    date(2026, 4, 3),   # Sexta-feira Santa
    date(2026, 4, 21),  # Tiradentes
    date(2026, 5, 1),   # Dia do Trabalho
    date(2026, 6, 4),   # Corpus Christi
    date(2026, 9, 7),   # Independência
    date(2026, 10, 12), # N.S. Aparecida
    date(2026, 11, 2),  # Finados
    date(2026, 11, 15), # Proclamação da República
    date(2026, 11, 20), # Consciência Negra
    date(2026, 12, 25), # Natal
}


def dia_util_anterior(ref: date = None) -> date:
    """Retorna o dia útil anterior à data de referência."""
    if ref is None:
        ref = date.today()
    d = ref - timedelta(days=1)
    while d.weekday() >= 5 or d in FERIADOS_BR:  # 5=sáb, 6=dom
        d -= timedelta(days=1)
    return d


def baixar_csvs() -> dict[str, pd.DataFrame]:
    """Baixa o ZIP da CVM e retorna dict com DataFrames dos CSVs."""
    print(f"Baixando {CVM_URL} ...")
    resp = requests.get(CVM_URL, timeout=60)
    resp.raise_for_status()

    dfs = {}
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        for name in z.namelist():
            if name.endswith(".csv"):
                with z.open(name) as f:
                    df = pd.read_csv(f, sep=CSV_SEP, encoding=CSV_ENCODING, low_memory=False)
                    dfs[name] = df
                    print(f"  {name}: {len(df)} registros")
    return dfs


def filtrar_ofertas_distribuicao(df: pd.DataFrame, data_alvo: date) -> pd.DataFrame:
    """Filtra oferta_distribuicao.csv por Data_Registro_Oferta == data_alvo."""
    col = "Data_Registro_Oferta"
    if col not in df.columns:
        return pd.DataFrame()
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df[df[col] == data_alvo].copy()


def filtrar_ofertas_res160(df: pd.DataFrame, data_alvo: date) -> pd.DataFrame:
    """Filtra oferta_resolucao_160.csv por Data_Registro == data_alvo."""
    col = "Data_Registro"
    if col not in df.columns:
        return pd.DataFrame()
    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
    return df[df[col] == data_alvo].copy()


def formatar_valor(valor) -> str:
    """Formata valor numérico como moeda BRL."""
    try:
        v = float(valor)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(valor) if pd.notna(valor) else "—"


def gerar_tabela_html(df: pd.DataFrame, colunas: list[tuple[str, str]]) -> str:
    """Gera tabela HTML a partir do DataFrame com as colunas especificadas."""
    header = "".join(f"<th style='padding:8px;border:1px solid #ddd;background:#f4f4f4;text-align:left'>{label}</th>" for _, label in colunas)
    rows = ""
    for _, row in df.iterrows():
        cells = ""
        for col, _ in colunas:
            val = row.get(col, "—")
            if "valor" in col.lower() or "total" in col.lower():
                val = formatar_valor(val)
            else:
                val = str(val) if pd.notna(val) else "—"
            cells += f"<td style='padding:8px;border:1px solid #ddd'>{val}</td>"
        rows += f"<tr>{cells}</tr>"
    return f"<table style='border-collapse:collapse;width:100%;font-size:14px'><tr>{header}</tr>{rows}</table>"


def gerar_email_html(data_alvo: date, dist: pd.DataFrame, res160: pd.DataFrame) -> str:
    """Gera o corpo HTML do e-mail."""
    data_fmt = data_alvo.strftime("%d/%m/%Y")
    html = f"""
    <html><body style='font-family:Arial,sans-serif;color:#333'>
    <h2>Ofertas Públicas CVM — {data_fmt}</h2>
    """

    if len(res160) > 0:
        html += f"<h3>Resolução 160 ({len(res160)} ofertas)</h3>"
        html += gerar_tabela_html(res160, [
            ("Nome_Emissor", "Emissor"),
            ("Valor_Mobiliario", "Valor Mobiliário"),
            ("Valor_Total_Registrado", "Valor Total"),
            ("Tipo_Oferta", "Tipo"),
            ("Nome_Lider", "Coordenador Líder"),
            ("Status_Requerimento", "Status"),
            ("Publico_alvo", "Público-Alvo"),
        ])
    else:
        html += "<p>Nenhuma oferta da Resolução 160 registrada nesta data.</p>"

    if len(dist) > 0:
        html += f"<h3>Demais Ofertas — ICVM 400 / ICVM 476 ({len(dist)} ofertas)</h3>"
        html += gerar_tabela_html(dist, [
            ("Nome_Emissor", "Emissor"),
            ("Tipo_Ativo", "Tipo de Ativo"),
            ("Valor_Total", "Valor Total"),
            ("Rito_Oferta", "Rito"),
            ("Nome_Lider", "Coordenador Líder"),
            ("Modalidade_Oferta", "Modalidade"),
        ])
    else:
        html += "<p>Nenhuma outra oferta (ICVM 400/476) registrada nesta data.</p>"

    html += """
    <br><p style='font-size:12px;color:#888'>
    Fonte: <a href='https://dados.cvm.gov.br/dataset/oferta-distribuicao'>dados.cvm.gov.br</a>
    — Gerado automaticamente pelo CVM Monitor.
    </p></body></html>
    """
    return html


def obter_access_token() -> str:
    """Obtém access token do Gmail usando refresh token via OAuth2."""
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")

    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def enviar_email(assunto: str, html: str):
    """Envia e-mail via Gmail API (OAuth2)."""
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    gmail_addr = os.environ.get("GMAIL_ADDRESS", "olavo@liqi.com.br")

    if not all([client_id, client_secret, refresh_token]):
        print("Credenciais OAuth2 não configuradas. E-mail não enviado.")
        print("--- Preview do e-mail ---")
        print(f"Assunto: {assunto}")
        print("(HTML omitido no preview)")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = gmail_addr
    msg["To"] = "olavo@liqi.com.br"
    msg.attach(MIMEText(html, "html"))

    raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    access_token = obter_access_token()
    resp = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"raw": raw_msg},
    )
    resp.raise_for_status()
    print("E-mail enviado com sucesso via Gmail API.")


def main():
    data_alvo = dia_util_anterior()
    print(f"Data alvo (dia útil anterior): {data_alvo}")

    dfs = baixar_csvs()

    # Filtrar ofertas
    df_dist = dfs.get("oferta_distribuicao.csv", pd.DataFrame())
    df_res160 = dfs.get("oferta_resolucao_160.csv", pd.DataFrame())

    novas_dist = filtrar_ofertas_distribuicao(df_dist, data_alvo)
    novas_res160 = filtrar_ofertas_res160(df_res160, data_alvo)

    total = len(novas_dist) + len(novas_res160)
    print(f"Ofertas encontradas: {total} (Res.160: {len(novas_res160)}, Outras: {len(novas_dist)})")

    if total == 0:
        print("Nenhuma oferta nova. E-mail não será enviado.")
        return

    assunto = f"CVM Monitor — {total} nova(s) oferta(s) em {data_alvo.strftime('%d/%m/%Y')}"
    html = gerar_email_html(data_alvo, novas_dist, novas_res160)
    enviar_email(assunto, html)


if __name__ == "__main__":
    main()

"""
Monitor diário de ofertas públicas CVM (Resolução 160 + ICVM 400/476).
Baixa o CSV da CVM, filtra ofertas registradas no dia útil anterior,
e envia resumo por e-mail via Gmail API (OAuth2).
"""

import base64
import html as html_lib
import io
import os
import re
import socket
import zipfile
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import requests
import urllib3.util.connection as urllib3_cn

# O servidor da CVM é dual-stack e responde com um IPv6 brasileiro (bloco 2804::)
# que os runners do GitHub Actions não conseguem rotear ("[Errno 101] Network is
# unreachable"). Forçamos IPv4 para que o download funcione em qualquer ambiente.
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

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
    headers = {"User-Agent": "Mozilla/5.0 (compatible; cvm-monitor/1.0)"}
    ultimo_erro = None
    for tentativa in range(1, 4):
        try:
            resp = requests.get(CVM_URL, timeout=60, headers=headers)
            resp.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            ultimo_erro = e
            print(f"  tentativa {tentativa}/3 falhou: {e}")
    else:
        raise ultimo_erro

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


#: Campos de texto livre (devedores, lastro, destinação, garantias). A CVM
#: preenche esses campos com parágrafos inteiros (chegam a 3.000+ caracteres),
#: então são truncados antes de entrar no e-mail.
CAMPOS_LONGOS = {
    "Identificacao_devedores_coobrigados",
    "Descricao_lastro",
    "Destinacao_recursos",
    "Descricao_garantias",
    "Ativos_alvo",
}

#: Limite de caracteres por célula nos campos longos. Não aumentar muito: o
#: Gmail corta ("mensagem truncada") mensagens acima de ~102 KB.
MAX_CHARS_CAMPO_LONGO = 400

#: Colunas com valor monetário que passam por formatar_valor().
CAMPOS_VALOR = {
    "Valor_Total_Registrado",
    "Valor_Total",
    "Preco_Unitario",
}

#: Colunas booleanas S/N da CVM, traduzidas para Sim/Não.
MAPA_SN = {"S": "Sim", "N": "Não"}

#: Colunas de data, que saem no formato dd/mm/aaaa.
CAMPOS_DATA = {
    "Data_Emissao",
    "Data_Vencimento",
    "Data_Registro",
    "Data_Registro_Oferta",
    "Data_Inicio_Oferta",
    "Data_Encerramento_Oferta",
    "Data_deliberacao_aprovou_oferta",
}

#: Colunas de contagem/quantidade. O pandas as lê como float; sem isso
#: sairiam no e-mail como "99.0" em vez de "99".
CAMPOS_INTEIROS = {
    "Emissao",
    "Serie",
    "Quantidade_Total",
    "Qtde_Total_Registrada",
    "Quantidade_Sem_Lote_Suplementar",
    "Quantidade_No_Lote_Suplementar",
}


def limpar_texto(valor, max_chars: int = MAX_CHARS_CAMPO_LONGO) -> str:
    """Normaliza espaços/quebras de linha e trunca texto livre da CVM."""
    if pd.isna(valor):
        return "—"
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    if not texto or texto.lower() in {"nan", "none"}:
        return "—"
    if len(texto) > max_chars:
        texto = texto[:max_chars].rstrip() + "…"
    return texto


def formatar_celula(col: str, valor) -> str:
    """Aplica a formatação adequada ao valor de acordo com a coluna."""
    if col in CAMPOS_LONGOS:
        return limpar_texto(valor)
    if pd.isna(valor):
        return "—"
    if col in CAMPOS_VALOR:
        return formatar_valor(valor)
    if col in CAMPOS_DATA:
        d = pd.to_datetime(valor, errors="coerce")
        if pd.notna(d):
            return d.strftime("%d/%m/%Y")
    if col in CAMPOS_INTEIROS:
        try:
            return f"{int(float(valor)):,}".replace(",", ".")
        except (ValueError, TypeError, OverflowError):
            pass
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    # Rede de segurança para as demais colunas numéricas: o pandas lê
    # inteiros como float, então "99.0" volta a ser "99".
    if re.fullmatch(r"-?\d+\.0", texto):
        texto = texto[:-2]
    if not texto or texto.lower() in {"nan", "none"}:
        return "—"
    if texto.upper() in MAPA_SN and len(texto) == 1:
        return MAPA_SN[texto.upper()]
    return texto


# Estilos reaproveitados pelas tabelas do e-mail. Tudo inline: clientes de
# e-mail ignoram <style> em boa parte dos casos.
_TH = (
    "padding:7px 9px;border:1px solid #d8dce3;background:#212121;color:#ffffff;"
    "text-align:left;vertical-align:top;font-weight:600;font-size:11px;"
    "text-transform:uppercase"
)
_TD = "padding:7px 9px;border:1px solid #d8dce3;vertical-align:top;word-break:break-word"
_TD_DET = (
    "padding:9px 10px;border:1px solid #d8dce3;border-top:0;background:#f7f8fa;"
    "vertical-align:top;word-break:break-word;font-size:11.5px;line-height:1.5"
)


def gerar_tabela_html(
    df: pd.DataFrame,
    colunas: list,
    detalhes: list = None,
) -> str:
    """Gera a tabela HTML do e-mail.

    ``colunas`` são os campos curtos, que viram colunas de verdade.
    ``detalhes`` são os campos descritivos (texto livre da CVM e prestadores):
    cada oferta ganha uma segunda linha, em colspan, com esses campos
    rotulados. Sem isso a tabela ficaria com mais de 20 colunas e estouraria a
    largura em qualquer cliente de e-mail.
    """
    detalhes = detalhes or []
    header = "".join(
        "<th style='%s'>%s</th>" % (_TH, html_lib.escape(label, quote=False))
        for _, label in colunas
    )

    linhas = ""
    for i, (_, row) in enumerate(df.iterrows()):
        fundo = "#ffffff" if i % 2 == 0 else "#fbfbfc"
        cells = "".join(
            "<td style='%s;background:%s'>%s</td>"
            % (_TD, fundo, html_lib.escape(formatar_celula(col, row.get(col)), quote=False))
            for col, _ in colunas
        )
        linhas += "<tr>%s</tr>" % cells

        if detalhes:
            partes = []
            for col, label in detalhes:
                if col not in df.columns:
                    continue
                val = formatar_celula(col, row.get(col))
                if val == "—":
                    continue
                partes.append(
                    "<span style='color:#0247fe;font-weight:600'>%s:</span> %s"
                    % (html_lib.escape(label, quote=False), html_lib.escape(val, quote=False))
                )
            corpo = "<br>".join(partes) if partes else (
                "<span style='color:#999999'>Sem informações adicionais na "
                "base da CVM.</span>"
            )
            linhas += "<tr><td colspan='%d' style='%s'>%s</td></tr>" % (
                len(colunas), _TD_DET, corpo
            )

    return (
        "<table role='presentation' cellpadding='0' cellspacing='0' "
        "style='border-collapse:collapse;width:100%;font-size:12px;line-height:1.45;"
        "font-family:Arial,Helvetica,sans-serif;color:#212121'>"
        "<tr>" + header + "</tr>" + linhas + "</table>"
    )


#: Colunas curtas da tabela de ofertas da Resolução 160.
COLS_RES160 = [
    ("Nome_Emissor", "Emissor"),
    ("Valor_Mobiliario", "Valor Mobiliário"),
    ("Tipo_Oferta", "Tipo de Oferta"),
    ("Valor_Total_Registrado", "Valor Total"),
    ("Publico_alvo", "Público-Alvo"),
    ("Rito_Requerimento", "Rito"),
    ("Regime_distribuicao", "Regime de Distribuição"),
    ("Status_Requerimento", "Status"),
]

#: Campos que vão na linha de detalhe de cada oferta da Resolução 160.
DET_RES160 = [
    ("Nome_Lider", "Coordenador líder"),
    ("Regime_fiduciario", "Regime fiduciário"),
    ("Tipo_lastro", "Tipo de lastro"),
    ("Identificacao_devedores_coobrigados", "Devedores/coobrigados"),
    ("Descricao_lastro", "Lastro"),
    ("Ativos_alvo", "Ativos-alvo"),
    ("Destinacao_recursos", "Destinação dos recursos"),
    ("Descricao_garantias", "Garantias"),
    ("Possibilidade_revolvencia", "Revolvência"),
    ("Titulo_incentivado", "Título incentivado"),
    ("Titulo_classificado_como_sustentavel", "Título sustentável"),
    ("Mercado_negociacao", "Mercado de negociação"),
    ("Agente_fiduciario", "Agente fiduciário"),
    ("Administrador", "Administrador"),
    ("Gestor", "Gestor"),
    ("Escriturador", "Escriturador"),
    ("Custodiante", "Custodiante"),
    ("Avaliador_Risco", "Agência de rating"),
]

#: Colunas curtas da tabela de ofertas ICVM 400/476.
COLS_DIST = [
    ("Nome_Emissor", "Emissor"),
    ("Tipo_Ativo", "Tipo de Ativo"),
    ("Valor_Total", "Valor Total"),
    ("Rito_Oferta", "Rito"),
    ("Modalidade_Oferta", "Modalidade"),
    ("Oferta_Regime_Fiduciario", "Regime Fiduciário"),
]

#: Campos que vão na linha de detalhe de cada oferta ICVM 400/476.
DET_DIST = [
    ("Nome_Lider", "Coordenador líder"),
    ("Nome_Ofertante", "Ofertante"),
    ("Classe_Ativo", "Classe do ativo"),
    ("Especie_Ativo", "Espécie"),
    ("Forma_Ativo", "Forma"),
    ("Emissao", "Emissão"),
    ("Serie", "Série"),
    ("Quantidade_Total", "Quantidade total"),
    ("Preco_Unitario", "Preço unitário"),
    ("Data_Emissao", "Data de emissão"),
    ("Data_Vencimento", "Vencimento"),
    ("Atualizacao_Monetaria", "Atualização monetária"),
    ("Juros", "Juros"),
    ("Oferta_Incentivo_Fiscal", "Incentivo fiscal"),
    ("Tipo_Fundo_Investimento", "Tipo de fundo"),
    ("Modalidade_Registro", "Modalidade de registro"),
    ("Modalidade_Dispensa_Registro", "Dispensa de registro"),
]


def gerar_email_html(data_alvo: date, dist: pd.DataFrame, res160: pd.DataFrame) -> str:
    """Gera o corpo HTML do e-mail."""
    data_fmt = data_alvo.strftime("%d/%m/%Y")
    total = len(dist) + len(res160)
    html = (
        "<html><body style='margin:0;padding:0;background:#f2f3f5'>"
        "<div style='max-width:1100px;margin:0 auto;padding:22px 18px;"
        "font-family:Arial,Helvetica,sans-serif;color:#212121'>"
        "<div style='background:#212121;border-radius:8px 8px 0 0;padding:16px 18px'>"
        "<div style='height:3px;width:64px;background:#0247fe;"
        "background-image:linear-gradient(45deg,#0247fe,#f556e9);margin-bottom:10px;"
        "font-size:0;line-height:0'>&nbsp;</div>"
        "<div style='color:#ffffff;font-size:18px;font-weight:700'>CVM Monitor</div>"
        "<div style='color:#b9bec7;font-size:12.5px;margin-top:3px'>"
        "Ofertas públicas registradas em " + data_fmt + " · "
        + str(total) + " oferta(s)</div>"
        "</div>"
        "<div style='background:#ffffff;border:1px solid #e2e5ea;border-top:0;"
        "border-radius:0 0 8px 8px;padding:18px'>"
    )

    if len(res160) > 0:
        html += (
            "<h3 style='margin:0 0 4px;font-size:14px'>Resolução CVM 160 ("
            + str(len(res160)) + " oferta(s))</h3>"
            "<p style='margin:0 0 10px;font-size:11.5px;color:#666666'>"
            "A faixa cinza abaixo de cada oferta traz os campos descritivos: devedores/"
            "coobrigados, lastro, destinação de recursos, garantias e "
            "prestadores de serviço.</p>"
        )
        html += gerar_tabela_html(res160, COLS_RES160, DET_RES160)
        html += (
            "<p style='font-size:11px;color:#888888;margin:8px 0 22px'>"
            "Devedores/coobrigados, lastro, destinação de recursos e garantias "
            "são texto livre preenchido pelo emissor e vêm truncados em "
            + str(MAX_CHARS_CAMPO_LONGO) + " caracteres. Campos vazios na base da CVM "
            "são omitidos. Texto integral no dashboard.</p>"
        )
    else:
        html += (
            "<p style='font-size:13px'>Nenhuma oferta da Resolução 160 "
            "registrada nesta data.</p>"
        )

    if len(dist) > 0:
        html += (
            "<h3 style='margin:0 0 8px;font-size:14px'>Demais ofertas — ICVM 400 / "
            "ICVM 476 (" + str(len(dist)) + " oferta(s))</h3>"
        )
        html += gerar_tabela_html(dist, COLS_DIST, DET_DIST)
        # O dataset oferta_distribuicao.csv não traz público-alvo, regime de
        # distribuição, devedores/coobrigados, lastro, destinação de recursos nem
        # garantias: esses campos só existem no oferta_resolucao_160.csv.
        html += (
            "<p style='font-size:11px;color:#888888;margin:8px 0 0'>"
            "Público-alvo, regime de distribuição, devedores/coobrigados, "
            "lastro, destinação de recursos e garantias não são "
            "divulgados pela CVM para ofertas ICVM 400/476: esses campos existem apenas "
            "na base da Resolução 160.</p>"
        )
    else:
        html += (
            "<p style='font-size:13px'>Nenhuma outra oferta (ICVM 400/476) registrada "
            "nesta data.</p>"
        )

    html += (
        "<p style='font-size:11px;color:#888888;margin:22px 0 0;"
        "border-top:1px solid #e2e5ea;padding-top:12px'>Fonte: "
        "<a href='https://dados.cvm.gov.br/dataset/oferta-distribuicao' "
        "style='color:#0247fe'>dados.cvm.gov.br</a> · Gerado automaticamente pelo "
        "CVM Monitor.</p>"
        "</div></div></body></html>"
    )
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
    msg["To"] = "olavo@liqi.com.br, flavio.altimari@liqi.com.br"
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

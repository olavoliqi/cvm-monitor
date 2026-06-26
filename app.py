"""
Dashboard Streamlit — Ofertas CVM Resolução 160
Permite consulta do histórico completo com filtros por período e outros campos.
"""

import io
import re
import zipfile

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

CVM_URL = "https://dados.cvm.gov.br/dados/OFERTA/DISTRIB/DADOS/oferta_distribuicao.zip"
CSV_NAME = "oferta_resolucao_160.csv"
CSV_ENCODING = "latin-1"
CSV_SEP = ";"

# ── Identidade visual Liqi ──────────────────────────────────────────────

# Logo oficial Liqi (versão escura, fill #212121) — usar inline, nunca placeholder
LIQI_LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="75 170 1780 745" height="34" role="img" aria-label="Liqi Digital Assets">
  <defs><style>.liqi{fill:#212121;}</style></defs>
  <path class="liqi" d="M86.72,279.97c-3.33,2.71-5.31,6.74-5.39,11.03l1.46,267.51c.28,67.37,54.97,121.84,122.34,121.84h1.3c25.89.02,46.91-20.92,46.98-46.81h0c0-25.83-20.86-46.8-46.69-46.94h0c-12.98,0-23.51-10.51-23.53-23.49l-.54-203.1c0-46.48-50.16-84.1-80.29-84.1-6.52.04-10.7,0-15.63,4.05Z"/>
  <path class="liqi" d="M344.71,679.81h0c-27.54,0-49.86-22.33-49.86-49.86h0v-230.89c0-12.14,9.84-21.99,21.99-21.99h0c42.96,0,77.79,34.83,77.79,77.79,0,.07,0,.14,0,.21v175.09c-.12,27.47-22.43,49.68-49.91,49.66Z"/>
  <path class="liqi" d="M862.75,679.81h0c-27.54,0-49.87-22.33-49.87-49.86h0v-230.89c0-12.14,9.84-21.99,21.99-21.99h0c42.96.05,77.75,34.91,77.7,77.87,0,.04,0,.08,0,.13v175.09c-.11,27.44-22.38,49.63-49.82,49.66Z"/>
  <path class="liqi" d="M760.74,522.86l-.13-2.17c0-85.65-69.42-155.09-155.07-155.11h-1.8c-86.62-1.79-158.28,66.98-160.07,153.59-1.75,84.66,64.02,155.43,148.58,159.89,15.25.19,30.47-1.5,45.31-5.06,8.68-1.87,18.66-4.94,23.11-6.37v42.27h0c0,4.02.53,7.9,1.42,11.64,5.85,37.13,37.88,65.56,76.66,65.61,12.14,0,21.99-9.84,21.99-21.99v-104.24c0-1.76-.1-3.5-.27-5.21.18-59.38.27-132.86.27-132.86ZM603.84,584.63h-.09c-34.3,0-62.11-27.81-62.11-62.11s27.81-62.11,62.11-62.11,62.06,27.76,62.11,62.03c.05,34.3-27.73,62.15-62.03,62.2Z"/>
  <path class="liqi" d="M1399.58,181.15l-253.81,146.53c-23.62,13.64-38.17,38.83-38.17,66.1v293.07c0,27.27,14.55,52.47,38.17,66.1l253.81,146.53c23.62,13.64,52.71,13.63,76.33,0l127.21-73.49c11.01-6.36,17.79-18.1,17.79-30.81v-109.65c0-15.97,8.52-30.74,22.36-38.72l106.83-61.63c11.01-6.36,17.79-18.1,17.79-30.81v-160.59c0-27.27-14.55-52.47-38.17-66.1l-253.8-146.53c-23.62-13.64-52.71-13.64-76.33,0ZM1436.77,570.06v186.83c0,22.23-24.06,36.12-43.31,25.01l-161.81-93.42c-16.09-9.29-26-26.45-26-45.03v-206.83c0-18.57,9.91-35.74,26-45.03l179.13-103.42c16.09-9.29,35.9-9.29,51.99,0l161.8,93.42c19.25,11.11,19.25,38.9,0,50.02l-161.8,93.42c-16.09,9.29-25.99,26.45-25.99,45.02Z"/>
  <path class="liqi" d="M1685.14,827.63v-108.58c0-17.11,9.13-32.92,23.95-41.48l98.21-56.7c14.28-8.24,32.13,2.06,32.13,18.55v113.41c0,17.11-9.13,32.92-23.95,41.48l-94.04,54.29c-16.14,9.32-36.3-2.33-36.3-20.96Z"/>
</svg>
"""

# CSS com a identidade visual da Liqi (fundo claro, gradiente azul→rosa, Poppins/Inter)
LIQI_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

:root {
    --liqi-preto: #212121;
    --liqi-azul: #0247fe;
    --liqi-rosa: #f556e9;
    --liqi-grad: linear-gradient(45deg, #0247fe 0%, #f556e9 100%);
    --liqi-borda: #e8eaed;
}

html, body, .stApp, [data-testid="stAppViewContainer"], [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: var(--liqi-preto);
}

.stApp { background-color: #ffffff; }

h1, h2, h3, h4 { font-family: 'Poppins', sans-serif !important; color: var(--liqi-preto); }

/* ── Cabeçalho de marca ───────────────────────────────────────────── */
.liqi-header {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    padding-bottom: 0.6rem;
    margin-bottom: 0.4rem;
}
.liqi-header .liqi-divider {
    width: 1px; height: 34px; background: var(--liqi-borda);
}
.liqi-header .liqi-titulo {
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
    font-size: 1.45rem;
    line-height: 1.1;
    color: var(--liqi-preto);
}
.liqi-header .liqi-sub {
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    color: #606d7f;
    margin-top: 1px;
}
.liqi-gradbar {
    height: 4px;
    border-radius: 4px;
    background: var(--liqi-grad);
    margin-bottom: 1rem;
}

/* ── Botões com gradiente da marca ────────────────────────────────── */
.stButton > button {
    background: var(--liqi-grad);
    color: #ffffff !important;
    border: none;
    border-radius: 10px;
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
    transition: filter .15s ease, transform .15s ease;
}
.stButton > button:hover { filter: brightness(1.07); transform: translateY(-1px); }
.stButton > button:active, .stButton > button:focus { color: #ffffff !important; }

.stDownloadButton > button {
    background: #ffffff;
    color: var(--liqi-azul) !important;
    border: 1.5px solid var(--liqi-azul);
    border-radius: 10px;
    font-family: 'Poppins', sans-serif;
    font-weight: 600;
}
.stDownloadButton > button:hover {
    background: var(--liqi-azul);
    color: #ffffff !important;
}

/* ── Métricas como cards ──────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid var(--liqi-borda);
    border-radius: 14px;
    padding: 0.8rem 1.1rem !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Poppins', sans-serif;
    color: var(--liqi-azul);
}
[data-testid="stMetricLabel"] { color: #606d7f; }

/* ── Abas ─────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--liqi-borda); }
.stTabs [data-baseweb="tab"] {
    font-family: 'Poppins', sans-serif;
    font-weight: 500;
    color: #606d7f;
}
.stTabs [aria-selected="true"] { color: var(--liqi-azul) !important; }
.stTabs [data-baseweb="tab-highlight"] { background: var(--liqi-grad) !important; height: 3px; }

/* ── Sidebar ──────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #f4f6f9;
    border-right: 1px solid var(--liqi-borda);
}

/* ── Subtítulos com leve barra de marca ───────────────────────────── */
[data-testid="stMainBlockContainer"] h3 {
    border-left: 3px solid;
    border-image: var(--liqi-grad) 1;
    padding-left: 0.55rem;
}

a { color: var(--liqi-azul); }
hr { border-color: var(--liqi-borda); }

/* ── Compactação (mantida do layout anterior) ─────────────────────── */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div { gap: 0.1rem; }
[data-testid="stSidebar"] label { margin-bottom: -0.3rem; font-size: 0.85rem; }
[data-testid="stSidebar"] .stMultiSelect,
[data-testid="stSidebar"] .stTextInput,
[data-testid="stSidebar"] .stDateInput { margin-bottom: -0.5rem; }
header[data-testid="stHeader"] { height: 2rem; }
[data-testid="stMainBlockContainer"] { padding-top: 2.5rem; }
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div { gap: 0.25rem; }
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3 { font-size: 1.15rem; margin-bottom: -0.3rem; }
[data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] { font-size: 1.35rem; }
[data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] { font-size: 0.8rem; }
[data-testid="stMainBlockContainer"] .stDataFrame { font-size: 0.8rem; }
[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] label { font-size: 0.85rem; }
[data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] { margin-bottom: -0.5rem; }
</style>
"""


@st.cache_data(ttl=3600, show_spinner="Baixando dados da CVM...")
def carregar_dados() -> pd.DataFrame:
    """Baixa o ZIP da CVM e retorna o DataFrame da Resolução 160."""
    resp = requests.get(CVM_URL, timeout=60)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        with z.open(CSV_NAME) as f:
            df = pd.read_csv(f, sep=CSV_SEP, encoding=CSV_ENCODING, low_memory=False)

    # Converter colunas de data
    for col in ["Data_Registro", "Data_requerimento", "Data_Encerramento"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Converter valor numérico
    if "Valor_Total_Registrado" in df.columns:
        df["Valor_Total_Registrado"] = pd.to_numeric(
            df["Valor_Total_Registrado"], errors="coerce"
        )

    return df


ABREV_INSTRUMENTOS = {
    "Cotas de FIDC": "FIDC",
    "Cotas de FII": "FII",
    "Cotas de FIP": "FIP",
    "Cotas de FIF": "FIF",
    "Cotas de Fundos de Infra": "F-Infra",
    "Cotas de Funcine": "Funcine",
    "Cotas de FIAGRO - FIDC": "FIAGRO-FIDC",
    "Cotas de FIAGRO - FII": "FIAGRO-FII",
    "Cotas de FIAGRO - FIP": "FIAGRO-FIP",
    "Cotas de FIAGRO": "FIAGRO",
    "Certificados de Recebíveis Imobiliários": "CRI",
    "Certificados de Recebíveis do Agronegócio": "CRA",
    "Certificados de Recebíveis": "CR",
    "Certificado de Direitos Creditórios do Agronegócio": "CDCA",
    "Certificado de depósito de ações (Unit)": "Unit",
    "Cédula de Produto Rural Financeira": "CPR-F",
    "Debêntures Conversíveis": "Debêntures Conv.",
    "Outros títulos de securitização": "Outros Securit.",
}


def abreviar_instrumento(nome: str) -> str:
    """Abrevia nomes longos de instrumentos financeiros."""
    if pd.isna(nome):
        return "—"
    for longo, curto in ABREV_INSTRUMENTOS.items():
        if longo.lower() == nome.strip().lower():
            return curto
    return nome


def formatar_brl(valor) -> str:
    """Formata valor numérico como moeda BRL."""
    try:
        v = float(valor)
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "—"


def abreviar_securitizadora(nome: str) -> str:
    """Abrevia nome da securitizadora: 'Opea Securitizadora S.A.' → 'Opea'."""
    if pd.isna(nome):
        return "—"
    n = str(nome).strip()
    # Caso abreviado: "ECO. SEC. DTOS. CREDIT. AGRONEGÓCIOS S/A" → pegar primeira palavra
    if re.match(r"(?i)^[\w]+\.\s+SEC\.", n):
        return re.match(r"^([\w]+)\.", n).group(1).upper()
    # "COMPANHIA SECURITIZADORA KANASTRA" → "KANASTRA" (nome após securitizadora)
    m = re.match(
        r"(?i)^(?:cia|companhia)\s+securitizadora\s+(.+?)"
        r"(?:\s*(?:s[./]?\s*a\.?|s/a|sa))?\.?\s*$", n)
    if m:
        return m.group(1).strip()
    n = re.sub(
        r"(?i)\s*(?:\b(?:cia|companhia)\s+(?:de\s+)?securitiza[çc][ãa]o|"
        r"\b(?:cia|companhia)\s+securitizadora|"
        r"securitizadora\s+(?:(?:de\s+)?(?:e\s+)?[\w\s]*)?|"
        r"securitizadora)"
        r"[\s,]*(?:s[./]?\s*a\.?|s/a|sa)?\.?\s*$",
        "",
        n,
    )
    # Remover prefixo "CIA" residual
    n = re.sub(r"(?i)^CIA\s+", "", n)
    # Remover "DE SECURITIZAÇÃO" residual (usar \S para cobrir variações de encoding)
    n = re.sub(r"(?i)\s*(?:de\s+)?securitiza\S+o\s*$", "", n)
    # Remover sufixos residuais
    n = re.sub(r"(?i)\s*(?:s[./]?\s*a\.?|s/a|ltda\.?)\s*$", "", n)
    n = n.strip().strip(".").strip(",").strip()
    return n if n else nome.strip()


# ── Parsing de devedores ────────────────────────────────────────────────

_PULVERIZADO_PATTERNS = [
    r"(?i)pulverizad",
    r"(?i)^significa[mn]?\s",
    r"(?i)^s[ãa]o\s+os\s+cedentes",
    r"(?i)^todos\s+os\s+devedor",
    r"(?i)lastro\s+.*pulverizad",
    r"(?i)^os\s+compradores\s+e/ou\s+devedor",
    r"(?i)^os\s+devedores\s+(?:dos|s[ãa]o|principais|pessoas|e\s+coobrigad)",
    r"(?i)^os\s+clientes\s+contratantes",
    r"(?i)^os\s+locat[áa]rios\s+dos",
    r"(?i)^os\s+compradores\s+pessoas",
    r"(?i)^os\s+respectivos\s+emitentes",
    r"(?i)^os\s+adquir[ie]ntes?\s+d",
    r"(?i)^as\s+pessoas\s+f[ií]sicas",
    r"(?i)^pessoas\s+f[ií]sicas",
    r"(?i)^s[ãa]o\s+os\s+(?:clientes|devedores)",
    r"(?i)^clientes\s+d[ao]",
    r"(?i)^os\s+direitos\s+credit[óo]rios\s+(?:do\s+agroneg|que\s+comp|s[ãa]o)",
    r"(?i)^os\s+cra\s+s(?:er[ãa]o|ão)\s+lastread",
    r"(?i)^os\s+cr[eé]ditos\s+imobili[áa]rios",
    r"(?i)^conforme\s+(?:anexo|previsto|descrit|as\s+datas)",
    r"(?i)^descritos?\s+no\s+anexo",
    r"(?i)^n[ãa]o\s+haver[áa]\s+coobriga",
    r"(?i)^a\s+serem?\s+identificad",
    r"(?i)^devedores?\s+(?:dos|principais|e\s+coobrigad)",
    r"(?i)^cedentes?\s+dos\s+cr[eé]ditos",
    r"(?i)^pagamento\s+[àa]\s+",
    r"(?i)^das\s+(?:duplicat|cpr)",
    r"(?i)^clientes\s+contratantes",
    r"(?i)^as\s+pessoas\s+f[ií]sicas\s+devedoras",
]

# Padrões de ruído pós-extração — fragmentos jurídicos que não são nomes
_NOISE_PATTERNS = [
    r"(?i)^sociedade\s+(?:limitada|por\s*a[çc][õo]es|an[ôo]nima|simples|beneficente|pora)",
    r"(?i)^sociedade$",
    r"(?i)^cnpj",
    r"(?i)^cpf[:/\s]",
    r"(?i)^com\s+re(?:gistro|sponsabilidade)",
    r"(?i)^com\s+endere[çc]o",
    r"(?i)^com\s+aval\s+d",
    r"(?i)^com\s+filial",
    r"(?i)^institui[çc][ãa]o\s+financeira",
    r"(?i)^pessoa\s+jur[ií]dica",
    r"(?i)^os\s+devedores",
    r"(?i)^os\s+direitos",
    r"(?i)^os\s+cr[eé]ditos",
    r"(?i)^garantidor[ae]?\s*[:,]?\s+(?:por\s+meio|de\s+forma)",
    r"(?i)^em\s+fase\s+operacional",
    r"(?i)^n[ãa]o\s+h[aá]",
    r"(?i)^cedente\s*[:/]?\s*$",
    r"(?i)^cedente\s*/$",
    r"(?i)^representad[oa]\s+p",
    r"(?i)^direitos?\s+credit[óo]rios",
    r"(?i)^que\s+",
    r"(?i)^sendo\s+",
    r"(?i)^nos?\s+termos",
    r"(?i)^significam?\s+",
    r"(?i)^(?:das|dos)\s+(?:duplicat|cpr|notas)",
    r"(?i)^sob\s+(?:o\s+)?n[°º.]",
    r"(?i)^sob\s+n[°º.]",
]


def _normalizar_devedor(nome: str) -> str:
    """Normaliza nome do devedor para agrupamento."""
    n = nome.strip().upper()
    n = re.sub(r"\s+", " ", n)
    n = re.sub(r"\s*[–—]\s*", " - ", n)
    # Remover artigo inicial "A " / "O " (ex: "A KLABIN S.A." → "KLABIN S.A.")
    n = re.sub(r'^[AO]\s+(?=[A-Z]{2})', '', n)
    # Remover prefixos numéricos (ex: "1. COMPANY LTDA." → "COMPANY LTDA.")
    n = re.sub(r'^\d+[\.\)\-]\s*', '', n)
    # Remover prefixos com percentual (ex: "100% - SLC AGRÍCOLA S.A.")
    n = re.sub(r'^\d+%\s*[-–]\s*', '', n)
    # Remover labels entre aspas no início (ex: ("DEVEDORA")FIBRA...)
    n = re.sub(r'^[("\s]*(?:DEVEDORA?|CEDENTE|AVALISTA|GARANTIDORA?\s*\d*|EMISSORA|FIADORA?\s*\d*)["\s)]*\s*', '', n)
    # Remover label "CEDENTE:" / "CEDENTE " no início
    n = re.sub(r'^CEDENTE\s*[\d]*\s*[:\-]?\s*', '', n)
    n = re.sub(r'^GARANTIDORA?\s*[:\-]\s*', '', n)
    # Normalizar sufixos empresariais
    n = re.sub(r"\bS\.?\s*A\.?\s*$", "S.A.", n)
    n = re.sub(r"\bS/A\s*$", "S.A.", n)
    n = re.sub(r"\bLTDA\.?\s*$", "LTDA.", n)
    n = n.strip(".").strip(",").strip()
    if n.endswith("S.A"):
        n += "."
    if n.endswith("LTDA"):
        n += "."
    return n


def _is_noise(nome: str) -> bool:
    """Verifica se um nome extraído é ruído (descrição jurídica, não um devedor real)."""
    if len(nome) < 5:
        return True
    for pat in _NOISE_PATTERNS:
        if re.search(pat, nome):
            return True
    # Texto muito longo sem sufixo empresarial provavelmente é descrição
    if len(nome) > 120 and not re.search(r"(?i)\b(?:S\.?A\.?|LTDA\.?|S/A|SPE)\b", nome):
        return True
    return False


def extrair_devedores(texto: str) -> list[str]:
    """Extrai nomes individuais de devedores/coobrigados do campo texto livre."""
    if pd.isna(texto) or not str(texto).strip():
        return []

    t = str(texto).strip()

    # Detectar lastro pulverizado / texto descritivo sem nomes
    for pat in _PULVERIZADO_PATTERNS:
        if re.search(pat, t):
            return ["PULVERIZADO"]

    # Remover CNPJ e CPF
    t = re.sub(
        r"\(?\s*CNPJ[/:\s]*(?:(?:ME|MF)\s+)?(?:n[°º.]?\s*)?(?:\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})?\s*\)?",
        "",
        t,
    )
    t = re.sub(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "", t)
    t = re.sub(
        r"\(?\s*CPF[/:\s]*(?:(?:ME|MF)\s+)?(?:n[°º.]?\s*)?\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}\s*\)?",
        "",
        t,
    )
    t = re.sub(r"\d{3}\.\d{3}\.\d{3}-\d{2}", "", t)

    # Remover preâmbulos descritivos
    t = re.sub(
        r"(?i)^os\s+direitos\s+credit[óo]rios.*?concentrad[oa]s?\s+(?:na|no|em)\s+",
        "",
        t,
    )
    t = re.sub(
        r"(?i)^os\s+direitos\s+credit[óo]rios.*?devid[oa]s?\s+(?:pela|pelo)\s+",
        "",
        t,
    )
    t = re.sub(
        r"(?i)^(?:a\s+)?identificação.*?(?:é|são|:)\s*",
        "",
        t,
    )

    # Remover labels entre parênteses (ex: "(Devedora)", "(devedor único)")
    t = re.sub(
        r'\(\s*"?(?i:devedor(?:a)?|avalistas?|fiadores?\s*\d*|coobrigad[oa]s?|'
        r'devedor\s+[úu]nico|cedentes?\s*\d*|garantidor[ae]?\s*\d*|emissora)"?\s*\)',
        "",
        t,
    )

    # Remover labels entre aspas no início de segmentos (ex: "CEDENTE 1" A ...)
    t = re.sub(r'"[^"]{0,30}"\s*', '', t)

    # Remover ruído final
    t = re.sub(r"(?i)Acionistas?:.*$", "", t)
    t = re.sub(r"(?i),?\s*das?\s+quais?\s+decorrem.*$", "", t)
    t = re.sub(r"(?i),?\s*(?:brasileiro|brasileira),?\s*(?:solteiro|casado|maior).*$", "", t)

    # Substituir labels por delimitador
    t = re.sub(
        r"(?i)(?:Devedor(?:a|es)?|Coobrigad[oa]s?|Fiador(?:es|a)?\s*\d*|"
        r"Avalistas?\s*\d*|Cedentes?\s*\d*|Garantidor(?:es|a)?\s*\d*)\s*[:\-]",
        "\n",
        t,
    )

    # Pipe e barra como delimitador
    t = t.replace("|", "\n")

    # Marcadores com numerais romanos
    t = re.sub(
        r"\((?:i{1,4}|iv|vi{0,3}|ix|x{1,3})\)\s*", "\n", t, flags=re.IGNORECASE
    )

    # Marcadores numéricos (1., 2-, 3), etc.)
    t = re.sub(r"(?:^|\n)\s*\d+[\.\)\-]\s*", "\n", t)

    # Quebrar após sufixo de empresa seguido de outra empresa (maiúsculas)
    # (?<=\s) evita match dentro de palavras como "PISANI" (SA falso positivo)
    t = re.sub(r"(?<=\s)(S\.A\.|S\.A|LTDA\.?|S/A)\s*(?=[A-Z][A-Z])", r"\1\n", t)

    # Quebrar após sufixo + " e " + maiúscula (conector entre empresas)
    t = re.sub(r"(?<=\s)(S\.A\.|S\.A|LTDA\.?|S/A)\s+e\s+(?=[A-Z])", r"\1\n", t)

    # Quebrar após sufixo + vírgula
    t = re.sub(r"(?<=\s)(S\.A\.|S\.A|LTDA\.?|S/A)\s*,\s*", r"\1\n", t)

    partes = re.split(r"\n+", t)

    devedores = []
    for p in partes:
        p = p.strip().strip(",").strip(".").strip()
        if not p:
            continue

        # Remover descrições residuais
        p = re.sub(r"(?i),?\s*(?:com sede|sediada|situada|inscrit[oa]).*$", "", p)
        p = re.sub(r"(?i),?\s*(?:neste ato|sociedade empres[áa]ria).*$", "", p)
        p = re.sub(
            r"(?i),?\s*fundo de investimento.*?(?:inscrit|constitu[ií]).*$", "", p
        )
        p = re.sub(r"(?i),?\s*(?:na qualidade de|representad[oa]\s+p).*$", "", p)
        p = re.sub(r"(?i),?\s*(?:associa[çc][ãa]o\s+constitu[ií]da).*$", "", p)
        p = re.sub(r"(?i),?\s*(?:sociedade\s+constitu[ií]da).*$", "", p)
        p = p.strip().strip(",").strip(".").strip("-").strip()

        if len(p) < 4:
            continue
        if re.match(
            r"^(?:e|ou|das?|dos?|na|no|em|sob|o|a|de|para|que|com|por|os|as)$",
            p,
            re.IGNORECASE,
        ):
            continue

        nome = _normalizar_devedor(p)

        # Filtro pós-extração: descartar fragmentos jurídicos
        if _is_noise(nome):
            continue

        if nome:
            devedores.append(nome)

    return devedores if devedores else ["PULVERIZADO"]


@st.cache_data(ttl=3600, show_spinner="Processando devedores CRI/CRA...")
def montar_tabela_devedores(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra CRI/CRA e explode coluna de devedores em linhas individuais."""
    mask = df["Valor_Mobiliario"].str.contains(
        "Certificados de Recebíveis", case=False, na=False
    )
    df_cri_cra = df[mask].copy()

    rows = []
    for _, row in df_cri_cra.iterrows():
        devs = extrair_devedores(row.get("Identificacao_devedores_coobrigados"))
        instrumento = abreviar_instrumento(row["Valor_Mobiliario"])
        ano = (
            int(row["Data_Registro"].year)
            if pd.notna(row.get("Data_Registro"))
            else None
        )
        for dev in devs:
            rows.append(
                {
                    "Devedor": dev,
                    "Instrumento": instrumento,
                    "Ano": ano,
                    "Emissor": row.get("Nome_Emissor", ""),
                    "Valor": row.get("Valor_Total_Registrado"),
                    "Coord_Lider": row.get("Nome_Lider", ""),
                    "Data_Registro": row.get("Data_Registro"),
                    "Numero_Requerimento": row.get("Numero_Requerimento"),
                }
            )

    return pd.DataFrame(rows)


def tabela_recorrencia(
    df_in: pd.DataFrame,
    entity_col: str,
    ano_col: str = "Ano",
    valor_col: str = "Valor",
) -> pd.DataFrame:
    """Monta tabela entidade × ano (contagem) + Total + Volume.

    Usada na aba de Coordenadores para cruzar securitizadoras/devedores
    com o coordenador líder ao longo dos anos.
    """
    total = df_in.groupby(entity_col).size().rename("Total")
    volume = df_in.groupby(entity_col)[valor_col].sum().rename("Volume")

    base = df_in.dropna(subset=[ano_col]).copy()
    if len(base) > 0:
        base[ano_col] = base[ano_col].astype(int)
        cont_ano = base.groupby([entity_col, ano_col]).size().unstack(fill_value=0)
        cont_ano = cont_ano[sorted(cont_ano.columns)]
    else:
        cont_ano = pd.DataFrame(index=total.index)

    res = total.to_frame().join(cont_ano).fillna(0).join(volume)
    year_cols = [c for c in res.columns if c not in ("Total", "Volume")]
    res = res[year_cols + ["Total", "Volume"]]
    for c in year_cols + ["Total"]:
        res[c] = res[c].astype(int)
    res = res.sort_values("Total", ascending=False)
    res.index.name = entity_col
    return res


def formatar_recorrencia(res: pd.DataFrame) -> pd.DataFrame:
    """Prepara a tabela de recorrência para exibição (volume em BRL, anos como texto)."""
    exib = res.reset_index().copy()
    if "Volume" in exib.columns:
        exib["Volume (R$)"] = exib["Volume"].apply(formatar_brl)
        exib = exib.drop(columns=["Volume"])
    rename = {c: str(int(c)) for c in exib.columns if isinstance(c, (int, float))}
    return exib.rename(columns=rename)


# ── Interface ───────────────────────────────────────────────────────────


def main():
    st.set_page_config(
        page_title="Monitor CVM — Liqi",
        page_icon="📊",
        layout="wide",
    )

    # Identidade visual Liqi
    st.markdown(LIQI_CSS, unsafe_allow_html=True)

    # Cabeçalho de marca (logo + título + barra de gradiente)
    # IMPORTANTE: sem indentação no HTML — 4+ espaços viram bloco de código no Markdown
    header_html = (
        '<div class="liqi-header">'
        + LIQI_LOGO_SVG
        + '<div class="liqi-divider"></div>'
        + '<div>'
        + '<div class="liqi-titulo">Monitor CVM — Resolução 160</div>'
        + '<div class="liqi-sub">Fonte: dados.cvm.gov.br · Atualizado a cada 1 hora</div>'
        + '</div></div>'
        + '<div class="liqi-gradbar"></div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    df = carregar_dados()

    # ── Sidebar ─────────────────────────────────────────────────────────
    if st.sidebar.button("Ir para Ranking Securitizadoras", use_container_width=True):
        st.session_state._switch_tab = "Ofertas"
        st.session_state._scroll_to = "ranking-securitizadoras"
    if st.sidebar.button("Ir para Devedores CRI/CRA", use_container_width=True):
        st.session_state._switch_tab = "Devedores CRI/CRA"
    if st.sidebar.button("Ir para Coordenadores", use_container_width=True):
        st.session_state._switch_tab = "Coordenadores"

    st.sidebar.caption("**Filtros — Ofertas:**")

    datas_validas = df["Data_Registro"].dropna()
    if len(datas_validas) > 0:
        data_min = datas_validas.min().date()
        data_max = datas_validas.max().date()
    else:
        from datetime import date

        data_min = date(2020, 1, 1)
        data_max = date.today()

    col_de, col_ate = st.sidebar.columns(2)
    data_de = col_de.date_input(
        "De", value=data_max, min_value=data_min, max_value=data_max, format="DD/MM/YYYY"
    )
    data_ate = col_ate.date_input(
        "Até", value=data_max, min_value=data_min, max_value=data_max, format="DD/MM/YYYY"
    )

    tipos_vm = sorted(df["Valor_Mobiliario"].dropna().unique())
    sel_tipo_vm = st.sidebar.multiselect("Tipo de Valor Mobiliário", tipos_vm)

    busca_emissor = st.sidebar.text_input("Emissor (busca por nome)")

    lideres = sorted(df["Nome_Lider"].dropna().unique())
    sel_lideres = st.sidebar.multiselect("Coordenador Líder", lideres)

    statuses = sorted(df["Status_Requerimento"].dropna().unique())
    sel_status = st.sidebar.multiselect("Status", statuses)

    # ── Tabs ────────────────────────────────────────────────────────────
    tab_ofertas, tab_devedores, tab_coord = st.tabs(
        ["Ofertas", "Devedores CRI/CRA", "Coordenadores"]
    )

    # Trocar aba e/ou scroll via JavaScript quando botão da sidebar é clicado
    _target_tab = st.session_state.pop("_switch_tab", None)
    _scroll_anchor = st.session_state.pop("_scroll_to", None)
    if _target_tab or _scroll_anchor:
        js_parts = []
        if _target_tab:
            js_parts.append(f"""
                var tabs = window.parent.document.querySelectorAll('button[data-baseweb="tab"]');
                tabs.forEach(function(tab) {{
                    if (tab.textContent.trim() === '{_target_tab}') {{ tab.click(); }}
                }});
            """)
        if _scroll_anchor:
            js_parts.append(f"""
                setTimeout(function() {{
                    var el = window.parent.document.getElementById('{_scroll_anchor}');
                    if (el) {{ el.scrollIntoView({{ behavior: 'smooth' }}); }}
                }}, 300);
            """)
        components.html(f"<script>{''.join(js_parts)}</script>", height=0)

    # ═══════════════════════════════════════════════════════════════════
    # TAB 1 — Ofertas (funcionalidade existente)
    # ═══════════════════════════════════════════════════════════════════
    with tab_ofertas:
        # Aplicar filtros
        mask = pd.Series(True, index=df.index)
        mask &= df["Data_Registro"].dt.date.ge(data_de) & df[
            "Data_Registro"
        ].dt.date.le(data_ate)

        if sel_tipo_vm:
            mask &= df["Valor_Mobiliario"].isin(sel_tipo_vm)
        if busca_emissor:
            mask &= df["Nome_Emissor"].str.contains(
                busca_emissor, case=False, na=False
            )
        if sel_lideres:
            mask &= df["Nome_Lider"].isin(sel_lideres)
        if sel_status:
            mask &= df["Status_Requerimento"].isin(sel_status)

        filtrado = df[mask].copy()

        ORDEM_INSTRUMENTO = {
            "Debêntures": 0,
            "CR": 1,
            "CRA": 2,
            "CRI": 3,
        }
        filtrado["_ordem_instr"] = filtrado["Valor_Mobiliario"].apply(
            lambda x: ORDEM_INSTRUMENTO.get(abreviar_instrumento(x), 99)
        )
        filtrado["_abrev"] = filtrado["Valor_Mobiliario"].apply(abreviar_instrumento)
        filtrado = filtrado.sort_values(
            ["Data_Registro", "_ordem_instr", "_abrev"],
            ascending=[False, True, True],
        ).drop(columns=["_ordem_instr", "_abrev"])

        # Métricas
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de ofertas", f"{len(filtrado):,}".replace(",", "."))
        volume = filtrado["Valor_Total_Registrado"].sum()
        col2.metric("Volume total", formatar_brl(volume))
        emissores_unicos = filtrado["Nome_Emissor"].nunique()
        col3.metric("Emissores únicos", f"{emissores_unicos:,}".replace(",", "."))

        # Tabela de ofertas
        st.subheader("Ofertas")

        colunas_exibir = [
            "Nome_Emissor",
            "Data_requerimento",
            "Data_Registro",
            "Valor_Mobiliario",
            "Valor_Total_Registrado",
            "Tipo_Oferta",
            "Nome_Lider",
            "Status_Requerimento",
            "Publico_alvo",
            "Regime_distribuicao",
            "Identificacao_devedores_coobrigados",
            "Descricao_lastro",
            "Destinacao_recursos",
            "Descricao_garantias",
            "Data_Encerramento",
        ]
        colunas_presentes = [c for c in colunas_exibir if c in filtrado.columns]

        exibicao = filtrado[colunas_presentes].copy()

        if "Valor_Mobiliario" in exibicao.columns:
            exibicao["Valor_Mobiliario"] = exibicao["Valor_Mobiliario"].apply(
                abreviar_instrumento
            )

        for col in ["Data_Registro", "Data_requerimento", "Data_Encerramento"]:
            if col in exibicao.columns:
                exibicao[col] = exibicao[col].dt.strftime("%d/%m/%Y").fillna("—")

        if "Valor_Total_Registrado" in exibicao.columns:
            exibicao["Valor_Total_Registrado"] = exibicao[
                "Valor_Total_Registrado"
            ].apply(formatar_brl)

        renomear = {
            "Nome_Emissor": "Emissor",
            "Valor_Mobiliario": "Instrumento",
            "Valor_Total_Registrado": "Valor (R$)",
            "Tipo_Oferta": "Tipo",
            "Nome_Lider": "Coord. Líder",
            "Status_Requerimento": "Status",
            "Publico_alvo": "Público",
            "Regime_distribuicao": "Regime",
            "Identificacao_devedores_coobrigados": "Devedores/Coobrigados",
            "Descricao_lastro": "Lastro",
            "Destinacao_recursos": "Destinação Recursos",
            "Descricao_garantias": "Garantias",
            "Data_Registro": "Registro",
            "Data_requerimento": "Requerimento",
            "Data_Encerramento": "Encerramento",
        }
        exibicao = exibicao.rename(columns=renomear)

        if len(exibicao) > 0:
            col_config = {
                "Emissor": st.column_config.TextColumn(width="medium"),
                "Instrumento": st.column_config.TextColumn(width="small"),
                "Valor (R$)": st.column_config.TextColumn(width="small"),
                "Tipo": st.column_config.TextColumn(width="small"),
                "Coord. Líder": st.column_config.TextColumn(width="medium"),
                "Status": st.column_config.TextColumn(width="small"),
                "Público": st.column_config.TextColumn(width="small"),
                "Regime": st.column_config.TextColumn(width="small"),
                "Devedores/Coobrigados": st.column_config.TextColumn(width="medium"),
                "Lastro": st.column_config.TextColumn(width="medium"),
                "Destinação Recursos": st.column_config.TextColumn(width="medium"),
                "Garantias": st.column_config.TextColumn(width="medium"),
                "Registro": st.column_config.TextColumn(width="small"),
                "Requerimento": st.column_config.TextColumn(width="small"),
                "Encerramento": st.column_config.TextColumn(width="small"),
            }
            st.dataframe(
                exibicao,
                use_container_width=True,
                hide_index=True,
                column_config=col_config,
            )
        else:
            st.info("Nenhuma oferta encontrada para os filtros selecionados.")

        # Download CSV
        csv_bytes = exibicao.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            label="Baixar CSV filtrado",
            data=csv_bytes,
            file_name="ofertas_res160_filtrado.csv",
            mime="text/csv",
        )

        # Ofertas por tipo de instrumento
        st.subheader("Ofertas por tipo de instrumento")
        if len(filtrado) > 0:
            por_tipo = (
                filtrado.groupby("Valor_Mobiliario", dropna=True)
                .agg(
                    Quantidade=("Valor_Mobiliario", "size"),
                    Volume=("Valor_Total_Registrado", "sum"),
                )
                .sort_values("Quantidade", ascending=False)
                .reset_index()
                .rename(columns={"Valor_Mobiliario": "Tipo de Instrumento"})
            )
            st.bar_chart(
                por_tipo.set_index("Tipo de Instrumento")["Quantidade"],
                horizontal=True,
            )

        # Ranking de Securitizadoras
        st.divider()
        st.subheader(
            "Ranking de Securitizadoras — Ofertas Resolução 160",
            anchor="ranking-securitizadoras",
        )

        mask_sec = (
            df["Nome_Emissor"].str.contains("securitiz", case=False, na=False)
            & ~df["Nome_Emissor"].str.contains("fidc", case=False, na=False)
            & ~df["Nome_Emissor"].str.contains("fundo de investimento", case=False, na=False)
        )
        df_sec = df[mask_sec].copy()
        df_sec = df_sec[
            df_sec["Data_Registro"].notna()
            & (df_sec["Valor_Total_Registrado"] > 0)
        ]

        if len(df_sec) > 0:
            df_sec["Ano"] = df_sec["Data_Registro"].dt.year
            df_sec["_abrev_instr"] = df_sec["Valor_Mobiliario"].apply(
                abreviar_instrumento
            )

            col_ano, col_instr, col_rank = st.columns(3)

            anos_disponiveis = sorted(
                df_sec["Ano"].dropna().unique(), reverse=True
            )
            anos_disponiveis = [int(a) for a in anos_disponiveis]
            ano_sel = col_ano.selectbox("Ano", anos_disponiveis, index=0)

            instrumentos = sorted(df_sec["_abrev_instr"].dropna().unique())
            opcoes_instr = ["Todos"] + instrumentos
            instr_sel = col_instr.selectbox("Instrumento", opcoes_instr, index=0)

            criterio = col_rank.radio(
                "Ordenar por",
                ["Quantidade de Operações", "Volume"],
                horizontal=False,
            )

            df_ano = df_sec[df_sec["Ano"] == ano_sel]
            if instr_sel != "Todos":
                df_ano = df_ano[df_ano["_abrev_instr"] == instr_sel]

            sort_col = "Ofertas" if criterio == "Quantidade de Operações" else "Volume"

            ranking = (
                df_ano.groupby("Nome_Emissor", dropna=True)
                .agg(
                    Ofertas=("Nome_Emissor", "size"),
                    Volume=("Valor_Total_Registrado", "sum"),
                )
                .sort_values(sort_col, ascending=False)
                .reset_index()
            )
            ranking.index = range(1, len(ranking) + 1)
            ranking.index.name = "#"
            ranking = ranking.rename(columns={"Nome_Emissor": "Securitizadora"})

            ranking["Volume (R$)"] = ranking["Volume"].apply(formatar_brl)

            st.dataframe(
                ranking[["Securitizadora", "Ofertas", "Volume (R$)"]],
                use_container_width=True,
            )

            if sort_col == "Ofertas":
                st.bar_chart(ranking.set_index("Securitizadora")["Ofertas"], horizontal=True)
            else:
                st.bar_chart(ranking.set_index("Securitizadora")["Volume"], horizontal=True)
        else:
            st.info("Nenhuma securitizadora encontrada nos dados.")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 2 — Devedores CRI/CRA
    # ═══════════════════════════════════════════════════════════════════
    with tab_devedores:
        st.subheader("Recorrência de Devedores — CRI / CRA / CR", anchor="devedores-cri-cra")

        df_dev = montar_tabela_devedores(df)

        # Período dos dados
        datas_dev = pd.to_datetime(df_dev["Data_Registro"], errors="coerce").dropna()
        if len(datas_dev) > 0:
            dt_ini = datas_dev.min().strftime("%d/%m/%Y")
            dt_fim = datas_dev.max().strftime("%d/%m/%Y")
        else:
            dt_ini = dt_fim = "—"
        st.caption(
            f"Período dos dados: **{dt_ini}** a **{dt_fim}** · "
            "Extração automática dos devedores e coobrigados a partir do campo "
            "livre das ofertas Resolução 160."
        )

        if len(df_dev) == 0:
            st.info("Nenhum dado de devedor encontrado.")
        else:
            # ── Filtros inline ──────────────────────────────────────────
            col_f1, col_f2, col_f3 = st.columns([1, 1, 2])

            instrumentos_disp = sorted(df_dev["Instrumento"].dropna().unique())
            sel_instr = col_f1.multiselect(
                "Instrumento",
                instrumentos_disp,
                default=instrumentos_disp,
                key="dev_instr",
            )

            opcoes_pulv = ["Incluir", "Excluir", "Somente pulverizado"]
            sel_pulv = col_f2.selectbox("Lastro pulverizado", opcoes_pulv, index=1)

            busca_dev = col_f3.text_input(
                "Buscar devedor", key="dev_busca"
            )

            # Aplicar filtros
            mask_dev = df_dev["Instrumento"].isin(sel_instr)

            if sel_pulv == "Excluir":
                mask_dev &= df_dev["Devedor"] != "PULVERIZADO"
            elif sel_pulv == "Somente pulverizado":
                mask_dev &= df_dev["Devedor"] == "PULVERIZADO"

            if busca_dev:
                mask_dev &= df_dev["Devedor"].str.contains(
                    busca_dev, case=False, na=False
                )

            df_filt = df_dev[mask_dev].copy()

            # ── Tabela de recorrência ───────────────────────────────────
            if len(df_filt) == 0:
                st.info("Nenhum resultado para os filtros aplicados.")
            else:
                # Contagem por instrumento
                contagem_instr = (
                    df_filt.groupby(["Devedor", "Instrumento"])
                    .size()
                    .unstack(fill_value=0)
                )

                # Contagem por ano
                df_com_ano = df_filt.dropna(subset=["Ano"])
                if len(df_com_ano) > 0:
                    df_com_ano["Ano"] = df_com_ano["Ano"].astype(int)
                    contagem_ano = (
                        df_com_ano.groupby(["Devedor", "Ano"])
                        .size()
                        .unstack(fill_value=0)
                    )
                    # Ordenar colunas de ano
                    contagem_ano = contagem_ano[sorted(contagem_ano.columns)]
                else:
                    contagem_ano = pd.DataFrame(index=contagem_instr.index)

                # Total
                total = df_filt.groupby("Devedor").size().rename("Total")

                # Volume total
                vol_total = (
                    df_filt.groupby("Devedor")["Valor"]
                    .sum()
                    .rename("Volume Total")
                )

                # Securitizadoras por devedor
                securitizadoras = (
                    df_filt.groupby("Devedor")["Emissor"]
                    .apply(lambda x: ", ".join(
                        sorted(set(abreviar_securitizadora(e) for e in x.dropna().unique()))
                    ))
                    .rename("Securitizadoras")
                )

                # Juntar tudo
                resultado = (
                    contagem_instr
                    .join(securitizadoras)
                    .join(contagem_ano)
                    .join(total)
                    .join(vol_total)
                )
                resultado = resultado.sort_values("Total", ascending=False)
                resultado.index.name = "Devedor"

                # Métricas
                m1, m2, m3, m4 = st.columns(4)
                n_devedores = len(resultado)
                n_operacoes = int(resultado["Total"].sum())
                top_devedor = resultado.index[0] if n_devedores > 0 else "—"
                top_count = int(resultado["Total"].iloc[0]) if n_devedores > 0 else 0
                vol_sum = resultado["Volume Total"].sum()

                m1.metric("Devedores únicos", f"{n_devedores:,}".replace(",", "."))
                m2.metric("Participações em operações", f"{n_operacoes:,}".replace(",", "."))
                m3.metric("Mais recorrente", f"{top_devedor[:35]}... ({top_count}x)" if len(top_devedor) > 35 else f"{top_devedor} ({top_count}x)")
                m4.metric("Volume total", formatar_brl(vol_sum))

                # Preparar exibição
                exib = resultado.reset_index().copy()

                # Formatar volume
                exib["Volume Total"] = exib["Volume Total"].apply(formatar_brl)

                # Renomear colunas de ano para string
                col_rename = {}
                for c in exib.columns:
                    if isinstance(c, (int, float)):
                        col_rename[c] = str(int(c))
                exib = exib.rename(columns=col_rename)

                st.dataframe(
                    exib,
                    use_container_width=True,
                    hide_index=True,
                    height=600,
                )

                # Download CSV
                csv_dev = exib.to_csv(index=False, sep=";").encode("utf-8-sig")
                st.download_button(
                    label="Baixar CSV devedores",
                    data=csv_dev,
                    file_name="devedores_cri_cra_recorrencia.csv",
                    mime="text/csv",
                    key="download_dev",
                )

                # ── Top 20 mais recorrentes (gráfico) ──────────────────
                st.subheader("Top 20 — Devedores mais recorrentes")
                top20 = resultado.head(20)["Total"]
                st.bar_chart(top20, horizontal=True)

                # ── Detalhe por devedor ─────────────────────────────────
                st.subheader("Detalhe por devedor")
                opcoes_dev = resultado.index.tolist()
                if opcoes_dev:
                    dev_selecionado = st.selectbox(
                        "Selecione um devedor",
                        opcoes_dev,
                        key="dev_detalhe",
                    )
                    detalhe = df_filt[df_filt["Devedor"] == dev_selecionado][
                        ["Data_Registro", "Instrumento", "Emissor", "Coord_Lider", "Valor"]
                    ].copy()
                    detalhe = detalhe.sort_values("Data_Registro", ascending=False)
                    if "Data_Registro" in detalhe.columns:
                        detalhe["Data_Registro"] = pd.to_datetime(
                            detalhe["Data_Registro"], errors="coerce"
                        ).dt.strftime("%d/%m/%Y")
                    detalhe["Valor"] = detalhe["Valor"].apply(formatar_brl)
                    detalhe = detalhe.rename(
                        columns={
                            "Data_Registro": "Registro",
                            "Coord_Lider": "Coord. Líder",
                            "Valor": "Valor (R$)",
                        }
                    )
                    st.dataframe(
                        detalhe,
                        use_container_width=True,
                        hide_index=True,
                    )

    # ═══════════════════════════════════════════════════════════════════
    # TAB 3 — Coordenadores Líderes
    # ═══════════════════════════════════════════════════════════════════
    with tab_coord:
        st.subheader("Análise por Coordenador Líder", anchor="coordenadores")
        st.caption(
            "Relaciona as securitizadoras e os devedores que trabalharam com "
            "cada coordenador líder, por ano. Os devedores são extraídos "
            "automaticamente apenas de ofertas de CRI / CRA / CR."
        )

        lideres_disp = df["Nome_Lider"].dropna()
        if len(lideres_disp) == 0:
            st.info("Nenhum coordenador líder encontrado nos dados.")
        else:
            # Coordenadores ordenados por nº de ofertas (mais ativos primeiro)
            ordem_lideres = df["Nome_Lider"].value_counts().index.tolist()

            col_c1, col_c2 = st.columns([2, 1])
            lider_sel = col_c1.selectbox(
                "Coordenador Líder", ordem_lideres, key="coord_lider"
            )

            df_lider = df[df["Nome_Lider"] == lider_sel].copy()
            df_lider["Ano"] = df_lider["Data_Registro"].dt.year

            anos_l = sorted(
                df_lider["Ano"].dropna().astype(int).unique(), reverse=True
            )
            anos_sel = col_c2.multiselect(
                "Ano", anos_l, default=anos_l, key="coord_anos"
            )
            if anos_sel:
                df_lider = df_lider[df_lider["Ano"].isin(anos_sel)]

            incluir_pulv = st.checkbox(
                "Incluir lastro pulverizado na lista de devedores",
                value=False,
                key="coord_pulv",
            )

            # ── Securitizadoras parceiras ───────────────────────────────
            mask_sec_l = (
                df_lider["Nome_Emissor"].str.contains("securitiz", case=False, na=False)
                & ~df_lider["Nome_Emissor"].str.contains("fidc", case=False, na=False)
                & ~df_lider["Nome_Emissor"].str.contains(
                    "fundo de investimento", case=False, na=False
                )
            )
            df_sec_l = df_lider[mask_sec_l].copy()
            df_sec_l["Securitizadora"] = df_sec_l["Nome_Emissor"].apply(
                abreviar_securitizadora
            )
            df_sec_l = df_sec_l.rename(columns={"Valor_Total_Registrado": "Valor"})

            # ── Devedores associados ────────────────────────────────────
            df_dev_all = montar_tabela_devedores(df)
            df_dev_l = df_dev_all[df_dev_all["Coord_Lider"] == lider_sel].copy()
            if anos_sel:
                df_dev_l = df_dev_l[df_dev_l["Ano"].isin(anos_sel)]
            if not incluir_pulv:
                df_dev_l = df_dev_l[df_dev_l["Devedor"] != "PULVERIZADO"]

            # ── Métricas ────────────────────────────────────────────────
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Ofertas", f"{len(df_lider):,}".replace(",", "."))
            m2.metric(
                "Volume total",
                formatar_brl(df_lider["Valor_Total_Registrado"].sum()),
            )
            m3.metric(
                "Securitizadoras",
                f"{df_sec_l['Securitizadora'].nunique():,}".replace(",", "."),
            )
            m4.metric(
                "Devedores identificados",
                f"{df_dev_l['Devedor'].nunique():,}".replace(",", "."),
            )

            nome_arquivo = re.sub(r"[^\w]+", "_", str(lider_sel))[:30].strip("_")

            # ── Securitizadoras por ano ─────────────────────────────────
            st.subheader("Securitizadoras parceiras")
            if len(df_sec_l) > 0:
                rec_sec = tabela_recorrencia(df_sec_l, "Securitizadora")
                exib_sec = formatar_recorrencia(rec_sec)
                st.dataframe(exib_sec, use_container_width=True, hide_index=True)
                st.download_button(
                    "Baixar CSV securitizadoras",
                    data=exib_sec.to_csv(index=False, sep=";").encode("utf-8-sig"),
                    file_name=f"securitizadoras_{nome_arquivo}.csv",
                    mime="text/csv",
                    key="dl_coord_sec",
                )
                st.bar_chart(rec_sec.head(15)["Total"], horizontal=True)
            else:
                st.info(
                    "Nenhuma securitizadora associada a este coordenador no período."
                )

            # ── Devedores por ano ───────────────────────────────────────
            st.subheader("Devedores (CRI / CRA / CR)")
            if len(df_dev_l) > 0:
                rec_dev = tabela_recorrencia(df_dev_l, "Devedor")
                exib_dev = formatar_recorrencia(rec_dev)
                st.dataframe(
                    exib_dev, use_container_width=True, hide_index=True, height=500
                )
                st.download_button(
                    "Baixar CSV devedores",
                    data=exib_dev.to_csv(index=False, sep=";").encode("utf-8-sig"),
                    file_name=f"devedores_{nome_arquivo}.csv",
                    mime="text/csv",
                    key="dl_coord_dev",
                )
                st.bar_chart(rec_dev.head(20)["Total"], horizontal=True)
            else:
                st.info(
                    "Nenhum devedor identificado para este coordenador no período."
                )


if __name__ == "__main__":
    main()

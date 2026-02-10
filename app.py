"""
Dashboard Streamlit — Ofertas CVM Resolução 160
Permite consulta do histórico completo com filtros por período e outros campos.
"""

import io
import zipfile

import pandas as pd
import requests
import streamlit as st

CVM_URL = "https://dados.cvm.gov.br/dados/OFERTA/DISTRIB/DADOS/oferta_distribuicao.zip"
CSV_NAME = "oferta_resolucao_160.csv"
CSV_ENCODING = "latin-1"
CSV_SEP = ";"


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


def main():
    st.set_page_config(
        page_title="CVM Resolução 160 — Liqi",
        page_icon="📊",
        layout="wide",
    )

    st.title("Ofertas CVM — Resolução 160")
    st.caption("Fonte: dados.cvm.gov.br · Atualizado a cada 1 hora")

    df = carregar_dados()

    # ── Sidebar: filtros ──────────────────────────────────────────────
    st.sidebar.header("Filtros")

    # Período — dois campos separados (De / Até)
    datas_validas = df["Data_Registro"].dropna()
    if len(datas_validas) > 0:
        data_min = datas_validas.min().date()
        data_max = datas_validas.max().date()
    else:
        from datetime import date

        data_min = date(2020, 1, 1)
        data_max = date.today()

    st.sidebar.subheader("Período (Data Registro)")
    data_de = st.sidebar.date_input("De", value=data_max, min_value=data_min, max_value=data_max, format="DD/MM/YYYY")
    data_ate = st.sidebar.date_input("Até", value=data_max, min_value=data_min, max_value=data_max, format="DD/MM/YYYY")

    st.sidebar.divider()

    # Tipo de valor mobiliário
    tipos_vm = sorted(df["Valor_Mobiliario"].dropna().unique())
    sel_tipo_vm = st.sidebar.multiselect("Tipo de Valor Mobiliário", tipos_vm)

    st.sidebar.divider()

    # Emissor (busca textual)
    busca_emissor = st.sidebar.text_input("Emissor (busca por nome)")

    # Coordenador líder
    lideres = sorted(df["Nome_Lider"].dropna().unique())
    sel_lideres = st.sidebar.multiselect("Coordenador Líder", lideres)

    # Status
    statuses = sorted(df["Status_Requerimento"].dropna().unique())
    sel_status = st.sidebar.multiselect("Status", statuses)

    # ── Aplicar filtros ───────────────────────────────────────────────
    mask = pd.Series(True, index=df.index)

    mask &= df["Data_Registro"].dt.date.ge(data_de) & df["Data_Registro"].dt.date.le(data_ate)

    if sel_tipo_vm:
        mask &= df["Valor_Mobiliario"].isin(sel_tipo_vm)

    if busca_emissor:
        mask &= df["Nome_Emissor"].str.contains(busca_emissor, case=False, na=False)

    if sel_lideres:
        mask &= df["Nome_Lider"].isin(sel_lideres)

    if sel_status:
        mask &= df["Status_Requerimento"].isin(sel_status)

    filtrado = df[mask].copy()

    # Ordenar: por data (desc), depois por tipo de instrumento na ordem definida
    ORDEM_INSTRUMENTO = {
        "Debêntures": 0,
        "CR": 1,
        "CRA": 2,
        "CRI": 3,
    }
    filtrado["_ordem_instr"] = (
        filtrado["Valor_Mobiliario"]
        .apply(lambda x: ORDEM_INSTRUMENTO.get(abreviar_instrumento(x), 99))
    )
    filtrado["_abrev"] = filtrado["Valor_Mobiliario"].apply(abreviar_instrumento)
    filtrado = filtrado.sort_values(
        ["Data_Registro", "_ordem_instr", "_abrev"],
        ascending=[False, True, True],
    ).drop(columns=["_ordem_instr", "_abrev"])

    # ── Métricas ──────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de ofertas", f"{len(filtrado):,}".replace(",", "."))
    volume = filtrado["Valor_Total_Registrado"].sum()
    col2.metric("Volume total", formatar_brl(volume))
    emissores_unicos = filtrado["Nome_Emissor"].nunique()
    col3.metric("Emissores únicos", f"{emissores_unicos:,}".replace(",", "."))

    # ── Tabela de ofertas ─────────────────────────────────────────────
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

    # Abreviar nomes de instrumentos
    if "Valor_Mobiliario" in exibicao.columns:
        exibicao["Valor_Mobiliario"] = exibicao["Valor_Mobiliario"].apply(abreviar_instrumento)

    # Formatar datas para dd/mm/yyyy
    for col in ["Data_Registro", "Data_requerimento", "Data_Encerramento"]:
        if col in exibicao.columns:
            exibicao[col] = exibicao[col].dt.strftime("%d/%m/%Y").fillna("—")

    # Formatar valor como BRL
    if "Valor_Total_Registrado" in exibicao.columns:
        exibicao["Valor_Total_Registrado"] = exibicao["Valor_Total_Registrado"].apply(
            formatar_brl
        )

    # Renomear colunas para exibição (nomes curtos para caber sem scroll)
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

    # ── Download CSV ──────────────────────────────────────────────────
    csv_bytes = exibicao.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        label="Baixar CSV filtrado",
        data=csv_bytes,
        file_name="ofertas_res160_filtrado.csv",
        mime="text/csv",
    )

    # ── Ofertas por tipo de instrumento ──────────────────────────────
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

    # ── Ranking de Securitizadoras ────────────────────────────────────
    st.divider()
    st.subheader("Ranking de Securitizadoras — Ofertas Resolução 160")

    # Filtrar apenas securitizadoras (usa df completo, sem filtros da sidebar)
    mask_sec = df["Nome_Emissor"].str.contains(
        "securitizadora", case=False, na=False
    )
    df_sec = df[mask_sec].copy()

    if len(df_sec) > 0:
        df_sec["Ano"] = df_sec["Data_Registro"].dt.year
        df_sec["_abrev_instr"] = df_sec["Valor_Mobiliario"].apply(abreviar_instrumento)

        col_ano, col_instr = st.columns(2)

        anos_disponiveis = sorted(df_sec["Ano"].dropna().unique(), reverse=True)
        anos_disponiveis = [int(a) for a in anos_disponiveis]
        ano_sel = col_ano.selectbox("Ano", anos_disponiveis, index=0)

        instrumentos = sorted(df_sec["_abrev_instr"].dropna().unique())
        opcoes_instr = ["Todos"] + instrumentos
        instr_sel = col_instr.selectbox("Instrumento", opcoes_instr, index=0)

        df_ano = df_sec[df_sec["Ano"] == ano_sel]
        if instr_sel != "Todos":
            df_ano = df_ano[df_ano["_abrev_instr"] == instr_sel]

        ranking = (
            df_ano.groupby("Nome_Emissor", dropna=True)
            .agg(
                Ofertas=("Nome_Emissor", "size"),
                Volume=("Valor_Total_Registrado", "sum"),
            )
            .sort_values("Ofertas", ascending=False)
            .reset_index()
        )
        ranking.index = range(1, len(ranking) + 1)
        ranking.index.name = "#"
        ranking = ranking.rename(columns={
            "Nome_Emissor": "Securitizadora",
            "Volume": "Volume (R$)",
        })
        ranking["Volume (R$)"] = ranking["Volume (R$)"].apply(formatar_brl)

        st.dataframe(ranking, use_container_width=True)

        st.bar_chart(
            ranking.set_index("Securitizadora")["Ofertas"],
            horizontal=True,
        )
    else:
        st.info("Nenhuma securitizadora encontrada nos dados.")


if __name__ == "__main__":
    main()

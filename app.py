import html as _html
import json
import re
import random as _bgrandom

import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

from config.estados import ESTADOS, CORTE_PADRAO, detectar_estado, detectar_tipo
from src.etl import ler_excel, montar_snapshot
from src import metricas
from src.formato import fmt_num, fmt_pct, formatar_tabela

st.set_page_config(page_title="Liberados x Montados", layout="wide")

# =============================================================================
# TEMA (fundo futurista) — planeta estilizado com destaque na Amazônia,
# gradientes azuis, iluminação sutil, partículas discretas, atmosfera, nuvens
# e anel orbital. Mesma estrutura do exemplo de referência (Delly's),
# adaptada pra esse app.
#
# Técnica: conteúdo transparente + cor de texto forçada pra clara de forma
# ampla (mais confiável entre versões do Streamlit do que tentar sobrepor
# um "cartão branco" no .block-container).
# =============================================================================
_bgrandom.seed(42)


def _gen_star_shadows(n, min_op, max_op):
    """Gera posições fixas (x,y em vw/vh) de partículas/estrelas para um
    campo discreto via CSS puro (box-shadow), sem precisar de imagem."""
    parts = []
    for _ in range(n):
        x = round(_bgrandom.uniform(0, 100), 2)
        y = round(_bgrandom.uniform(0, 100), 2)
        op = round(_bgrandom.uniform(min_op, max_op), 2)
        parts.append(f"{x}vw {y}vh 0 rgba(148,197,255,{op})")
    return ",\n    ".join(parts)


_STARS_FAR = _gen_star_shadows(70, 0.10, 0.28)
_STARS_NEAR = _gen_star_shadows(30, 0.20, 0.42)

CSS_TEMA = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
  font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif !important;
  color: #E7F3EC !important;
}}

.stApp {{
  background: linear-gradient(150deg, #030712 0%, #071a34 45%, #0a2a52 100%) !important;
  background-attachment: fixed;
  background-size: cover;
}}

/* Campo de partículas — estrelas distantes (estáticas, bem discretas) */
.bg-stars-far {{
  position: fixed; inset: 0;
  width: 1px; height: 1px;
  background: transparent;
  box-shadow: {_STARS_FAR};
  z-index: -6;
  pointer-events: none;
  animation: bgTwinkleFar 9s ease-in-out infinite alternate;
}}
/* Campo de partículas — mais próximas, leve brilho e cintilação */
.bg-stars-near {{
  position: fixed; inset: 0;
  width: 2px; height: 2px;
  background: transparent;
  box-shadow: {_STARS_NEAR};
  border-radius: 50%;
  z-index: -6;
  pointer-events: none;
  animation: bgTwinkleNear 6s ease-in-out infinite alternate;
}}
@keyframes bgTwinkleFar {{
  0%   {{ opacity: 0.5; }}
  100% {{ opacity: 1; }}
}}
@keyframes bgTwinkleNear {{
  0%   {{ opacity: 0.6; transform: translateY(0); }}
  100% {{ opacity: 1; transform: translateY(-3px); }}
}}

/* Planeta Terra — esfera 100% CSS, com oceano azul, continente
   (América do Sul) e um brilho verde-esmeralda sutil sobre a região
   Amazônica, além de nuvens, terminador e anel tecnológico orbital. */
.bg-earth-wrap {{
  position: fixed;
  right: -14vw; bottom: -20vw;
  width: min(52vw, 720px); height: min(52vw, 720px);
  z-index: -5;
  pointer-events: none;
  animation: bgEarthFloat 14s ease-in-out infinite;
}}
@keyframes bgEarthFloat {{
  0%, 100% {{ transform: translateY(0); }}
  50%      {{ transform: translateY(-14px); }}
}}
.bg-earth-atmo {{
  position: absolute; inset: -6%;
  border-radius: 50%;
  background: radial-gradient(circle at 38% 32%, rgba(96,165,250,0.35), transparent 62%);
  filter: blur(18px);
  opacity: 0.8;
}}
.bg-earth-globe {{
  position: absolute; inset: 0;
  border-radius: 50%;
  overflow: hidden;
  background:
    radial-gradient(circle at 30% 26%, rgba(191,219,254,0.55) 0%, transparent 12%),
    radial-gradient(circle at 34% 30%, #1d4ed8 0%, #1e3a8a 42%, #0b1533 78%, #050a17 100%);
  box-shadow:
    inset -60px -50px 110px rgba(0,0,0,0.65),
    inset 22px 18px 60px rgba(147,197,253,0.18),
    0 0 90px 20px rgba(59,130,246,0.20);
}}
.bg-earth-continent {{
  position: absolute; width: 46%; height: 58%; left: 27%; top: 18%;
  background:
    radial-gradient(ellipse 60% 70% at 45% 30%, rgba(34,197,94,0.55) 0%, rgba(21,128,61,0.42) 45%, transparent 72%),
    radial-gradient(ellipse 50% 40% at 55% 62%, rgba(101,163,13,0.35) 0%, transparent 70%);
  border-radius: 46% 54% 50% 50% / 55% 50% 55% 45%;
  filter: blur(1.5px);
  opacity: 0.92;
  transform: rotate(-8deg);
}}
.bg-earth-amazon-glow {{
  position: absolute; width: 26%; height: 20%; left: 38%; top: 34%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(74,222,128,0.85) 0%, rgba(34,197,94,0.35) 45%, transparent 75%);
  filter: blur(4px);
  mix-blend-mode: screen;
  animation: bgAmazonPulse 4.5s ease-in-out infinite;
}}
@keyframes bgAmazonPulse {{
  0%, 100% {{ opacity: 0.55; transform: scale(1); }}
  50%      {{ opacity: 0.95; transform: scale(1.12); }}
}}
.bg-earth-clouds {{
  position: absolute; inset: 0;
  border-radius: 50%;
  background:
    radial-gradient(ellipse 70% 30% at 60% 15%, rgba(248,250,252,0.10) 0%, transparent 60%),
    radial-gradient(ellipse 50% 20% at 30% 70%, rgba(248,250,252,0.06) 0%, transparent 65%);
  mix-blend-mode: screen;
}}
.bg-earth-terminator {{
  position: absolute; inset: 0; border-radius: 50%;
  background: radial-gradient(circle at 72% 68%, transparent 30%, rgba(2,6,18,0.82) 68%);
}}
.bg-earth-ring {{
  position: absolute; inset: -9%;
  border-radius: 50%;
  border: 1px dashed rgba(96,165,250,0.28);
  animation: bgRingSpin 60s linear infinite;
}}
.bg-earth-ring::before {{
  content: '';
  position: absolute; top: -4px; left: 50%;
  width: 8px; height: 8px; margin-left: -4px;
  border-radius: 50%;
  background: #60a5fa;
  box-shadow: 0 0 10px 3px rgba(96,165,250,0.8);
}}
@keyframes bgRingSpin {{
  from {{ transform: rotate(0deg); }}
  to   {{ transform: rotate(360deg); }}
}}

/* véu leve pra manter contraste do conteúdo por cima do fundo */
.bg-scrim {{
  position: fixed; inset: 0;
  background:
    linear-gradient(180deg, rgba(6,11,22,0.55) 0%, rgba(6,11,22,0.25) 22%, rgba(6,11,22,0.38) 100%),
    radial-gradient(ellipse 65% 45% at 50% 0%, rgba(6,11,22,0.30) 0%, transparent 60%);
  z-index: -4;
  pointer-events: none;
}}

/* inputs, selects e áreas de upload: fundo escuro translúcido pra combinar com o tema */
[data-testid="stTextInput"] input,
[data-testid="stFileUploaderDropzone"],
[data-baseweb="select"] > div,
textarea {{
  background-color: rgba(255,255,255,0.06) !important;
  border-color: rgba(255,255,255,0.18) !important;
  color: #E7F3EC !important;
}}
[data-testid="stFileUploaderDropzone"] * {{ color: #E7F3EC !important; }}

/* botões: acento verde, combinando com o restante do app */
.stButton > button {{
  background: linear-gradient(135deg, #1c7a45, #2f9e5c) !important;
  color: #ffffff !important;
  border: none !important;
}}

section[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, #08213f 0%, #0a2a52 100%) !important;
}}
</style>

<div class="bg-stars-far"></div>
<div class="bg-stars-near"></div>
<div class="bg-earth-wrap">
  <div class="bg-earth-atmo"></div>
  <div class="bg-earth-globe">
    <div class="bg-earth-continent"></div>
    <div class="bg-earth-amazon-glow"></div>
    <div class="bg-earth-clouds"></div>
    <div class="bg-earth-terminator"></div>
  </div>
  <div class="bg-earth-ring"></div>
</div>
<div class="bg-scrim"></div>
"""

st.markdown(CSS_TEMA, unsafe_allow_html=True)

# =============================================================================
# DATAGRID (tabela estilo profissional) — antes em src/datagrid.py, agora
# direto aqui pelo mesmo motivo.
# =============================================================================
_ROTULOS_GRID = {
    "categoria": "Categoria", "pedidos": "Pedidos", "peso": "Peso", "valor": "Valor",
    "estado": "Estado", "numero_pedido": "Nº Pedido", "cliente": "Cliente", "cidade": "Cidade",
    "data_hora_liberacao": "Liberado em", "idade_horas": "Idade (h)", "faixa_aging": "Faixa",
    "status_corte": "Status", "timestamp": "Data / Hora", "pedidos_pendentes": "Pedidos pendentes",
    "peso_pendente": "Peso pendente", "valor_pendente": "Valor pendente",
    "pedidos_montados": "Pedidos montados", "peso_montado": "Peso montado",
    "valor_montado": "Valor montado", "pct_montado": "% Montado",
}

_CSS_GRID = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
#{uid} {{ font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif; }}
#{uid} .dg-title {{ font-weight: 700; font-size: 15px; color: #0b3d24; padding: 2px 2px 8px 2px; letter-spacing: .01em; }}
#{uid} .dg-shell {{ border-radius: 12px; overflow: hidden; border: 1px solid #d7ede1; box-shadow: 0 4px 18px rgba(15, 81, 50, 0.08); background: #ffffff; }}
#{uid} .dg-scroll {{ max-height: {altura}px; overflow: auto; }}
#{uid} table {{ width: 100%; border-collapse: separate; border-spacing: 0; }}
#{uid} thead th {{
  position: sticky; top: 0; z-index: 3;
  background: linear-gradient(135deg, #1c7a45, #2f9e5c 55%, #3cb873);
  color: #ffffff; padding: 13px 16px; font-size: 12.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .05em; text-align: center;
  white-space: nowrap; border-bottom: 2px solid #17693b;
}}
#{uid} tbody td {{ padding: 11px 16px; font-size: 13.5px; color: #16382a; text-align: center; white-space: nowrap; border-bottom: 1px solid #eef6f1; }}
#{uid} tbody tr {{ transition: background-color .12s ease-in-out; }}
#{uid} tbody tr:nth-child(even) {{ background-color: #f5fbf8; }}
#{uid} tbody tr:hover td {{ background-color: #dcf3e6 !important; }}
#{uid} tbody tr.dg-total td {{ background-color: #bfead0 !important; color: #0b3d24; font-weight: 800; }}
#{uid} tbody tr.dg-montados td {{ background-color: #e4f8ec; }}
#{uid} tbody tr.dg-liberados td {{ background-color: #f4fcf7; }}
#{uid} .dg-pager {{ display: flex; align-items: center; justify-content: center; gap: 14px; padding: 10px 12px; background: #f8fdfa; border-top: 1px solid #e4f2ea; font-size: 12.5px; color: #2f6b46; }}
#{uid} .dg-pager button {{ border: none; background: #2f9e5c; color: white; padding: 6px 14px; border-radius: 999px; cursor: pointer; font-weight: 700; font-size: 12.5px; font-family: inherit; transition: transform .1s ease, background .15s ease; }}
#{uid} .dg-pager button:hover:not(:disabled) {{ background: #237a48; transform: translateY(-1px); }}
#{uid} .dg-pager button:disabled {{ opacity: .35; cursor: default; }}
#{uid} .dg-empty {{ padding: 22px; text-align: center; color: #6b8f7c; font-size: 13px; }}
"""

_JS_GRID = """
(function() {{
  const rowsPerPage = {linhas_por_pagina};
  const dados = {dados_json};
  const classes = {classes_json};
  const tbody = document.getElementById('{uid}_body');
  const info = document.getElementById('{uid}_info');
  const prevBtn = document.getElementById('{uid}_prev');
  const nextBtn = document.getElementById('{uid}_next');
  let page = 0;
  const totalPages = Math.max(1, Math.ceil(dados.length / rowsPerPage));

  function render() {{
    tbody.innerHTML = '';
    const inicio = page * rowsPerPage;
    const fim = Math.min(inicio + rowsPerPage, dados.length);
    if (dados.length === 0) {{
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.className = 'dg-empty'; td.colSpan = 99; td.textContent = 'Sem dados neste snapshot.';
      tr.appendChild(td); tbody.appendChild(tr);
    }}
    for (let i = inicio; i < fim; i++) {{
      const tr = document.createElement('tr');
      if (classes[i]) tr.className = classes[i];
      dados[i].forEach(valor => {{
        const td = document.createElement('td');
        td.textContent = valor;
        tr.appendChild(td);
      }});
      tbody.appendChild(tr);
    }}
    info.textContent = 'Página ' + (page + 1) + ' de ' + totalPages + ' · ' + dados.length + ' registros';
    prevBtn.disabled = page === 0;
    nextBtn.disabled = page >= totalPages - 1;
  }}
  prevBtn.onclick = () => {{ if (page > 0) {{ page--; render(); }} }};
  nextBtn.onclick = () => {{ if (page < totalPages - 1) {{ page++; render(); }} }};
  render();
}})();
"""


def _rotulo_grid(col):
    return _ROTULOS_GRID.get(col, col.replace("_", " ").title())


def _slug_grid(texto):
    s = re.sub(r"[^a-zA-Z0-9]+", "_", str(texto)).strip("_").lower()
    return s or "grid"


def _val_grid(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v)


def _classe_categoria_grid(cat):
    if cat == "TOTAL":
        return "dg-total"
    if cat == "Montados":
        return "dg-montados"
    if cat.startswith("Liberados"):
        return "dg-liberados"
    return ""


def render_datagrid(df, key, titulo=None, altura_max=360, linhas_por_pagina=8, colorir_categoria=False):
    """DataGrid HTML/CSS/JS: cabeçalho fixo, hover, zebra, paginação real (só a página atual entra no DOM)."""
    uid = f"dg_{_slug_grid(key)}"
    n_linhas = 0 if df.empty else len(df)

    dados, classes = [], []
    if not df.empty:
        for _, row in df.iterrows():
            dados.append([_val_grid(v) for v in row])
            classes.append(
                _classe_categoria_grid(str(row["categoria"]))
                if colorir_categoria and "categoria" in df.columns else ""
            )

    headers = "".join(f"<th>{_html.escape(_rotulo_grid(c))}</th>" for c in df.columns)
    titulo_html = f"<div class='dg-title'>{_html.escape(titulo)}</div>" if titulo else ""
    css = _CSS_GRID.format(uid=uid, altura=altura_max)
    js = _JS_GRID.format(
        uid=uid, linhas_por_pagina=linhas_por_pagina,
        dados_json=json.dumps(dados, ensure_ascii=False),
        classes_json=json.dumps(classes, ensure_ascii=False),
    )

    grid_html = f"""
    <div id="{uid}">
      <style>{css}</style>
      {titulo_html}
      <div class="dg-shell">
        <div class="dg-scroll">
          <table>
            <thead><tr>{headers}</tr></thead>
            <tbody id="{uid}_body"></tbody>
          </table>
        </div>
        <div class="dg-pager">
          <button id="{uid}_prev">‹ Anterior</button>
          <span id="{uid}_info"></span>
          <button id="{uid}_next">Próxima ›</button>
        </div>
      </div>
      <script>{js}</script>
    </div>
    """
    linhas_visiveis = min(n_linhas, linhas_por_pagina) if n_linhas else 1
    altura_estimada = min(altura_max, 46 + 40 * linhas_visiveis) + (34 if titulo else 0) + 56
    return grid_html, altura_estimada


# =============================================================================
# App
# =============================================================================
GSHEETS_OK = "gcp_service_account" in st.secrets and "gsheets" in st.secrets
if GSHEETS_OK:
    from src import gsheets

st.title("📦 Liberados x Montados")
st.caption("Comparação de pedidos liberados (aguardando montagem) x pedidos montados, por estado.")

if not GSHEETS_OK:
    st.warning(
        "Google Sheets não está configurado em `st.secrets` — o histórico intradiário "
        "não será salvo nesta sessão. Veja o README para configurar.",
        icon="⚠️",
    )

# ---------------------------------------------------------------------------
# Configuração de corte (sidebar)
# ---------------------------------------------------------------------------
if "corte_config" not in st.session_state:
    if GSHEETS_OK:
        st.session_state.corte_config = gsheets.carregar_config_corte(CORTE_PADRAO)
    else:
        st.session_state.corte_config = dict(CORTE_PADRAO)

with st.sidebar:
    st.header("⚙️ Configuração de corte")
    st.caption("Ajuste por estado. Estados 'sem corte' nunca entram como atrasado.")
    novo_config = {}
    for estado, nome in ESTADOS.items():
        cfg = st.session_state.corte_config.get(estado, {"tem_corte": False, "hora_corte": None})
        tem_corte = st.checkbox(f"{nome} tem corte", value=cfg["tem_corte"], key=f"chk_{estado}")
        hora_corte = None
        if tem_corte:
            hora_default = cfg.get("hora_corte") or "14:00"
            hora_corte = st.text_input(
                f"Horário de corte ({nome})", value=hora_default, key=f"hora_{estado}",
                help="Formato HH:MM"
            )
        novo_config[estado] = {"tem_corte": tem_corte, "hora_corte": hora_corte}

    if st.button("💾 Salvar configuração de corte"):
        st.session_state.corte_config = novo_config
        if GSHEETS_OK:
            gsheets.salvar_config_corte(novo_config)
        st.success("Configuração salva.")

# ---------------------------------------------------------------------------
# Upload dos arquivos
# ---------------------------------------------------------------------------
st.subheader("1. Upload dos arquivos deste snapshot")
uploads = st.file_uploader(
    "Envie os arquivos LIBERADOS_*.xls e MONTADOS_*.xlsx de uma vez (pode selecionar vários)",
    type=["xls", "xlsx"],
    accept_multiple_files=True,
)

arquivos_liberados = {}
arquivos_montados = {}

if uploads:
    st.write("Confirme o estado e o tipo detectados para cada arquivo:")
    for f in uploads:
        col1, col2, col3 = st.columns([3, 2, 2])
        estado_sugerido = detectar_estado(f.name) or list(ESTADOS.keys())[0]
        tipo_sugerido = detectar_tipo(f.name) or "liberado"
        with col1:
            st.text(f.name)
        with col2:
            estado_escolhido = st.selectbox(
                "Estado", list(ESTADOS.keys()),
                index=list(ESTADOS.keys()).index(estado_sugerido),
                key=f"estado_{f.name}",
                format_func=lambda e: ESTADOS[e],
            )
        with col3:
            tipo_escolhido = st.selectbox(
                "Tipo", ["liberado", "montado"],
                index=0 if tipo_sugerido == "liberado" else 1,
                key=f"tipo_{f.name}",
            )
        try:
            df = ler_excel(f)
        except Exception as e:
            st.error(f"Não consegui ler {f.name}: {e}")
            continue
        if tipo_escolhido == "liberado":
            arquivos_liberados[estado_escolhido] = df
        else:
            arquivos_montados[estado_escolhido] = df

# ---------------------------------------------------------------------------
# Processamento
# ---------------------------------------------------------------------------
if arquivos_liberados or arquivos_montados:
    try:
        df_lib, df_mont, avisos = montar_snapshot(arquivos_liberados, arquivos_montados)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    for aviso in avisos:
        st.warning(f"⚠️ {aviso}", icon="⚠️")

    agora = pd.Timestamp.now()
    df_pendentes = metricas.pedidos_nao_montados(df_lib, df_mont)
    df_lib_aging = metricas.calcular_aging(df_pendentes, agora)
    df_lib_corte = metricas.status_corte(df_lib_aging, st.session_state.corte_config, agora)
    comparativo = metricas.comparativo_por_estado(df_pendentes, df_mont)
    tabela_estado = metricas.tabela_detalhada_por_estado(df_pendentes, df_mont)

    st.subheader("2. Panorama deste snapshot")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pedidos pendentes", fmt_num(comparativo["pedidos_pendentes"].sum()))
    c2.metric("Pedidos montados", fmt_num(comparativo["pedidos_montados"].sum()))
    atrasados = (df_lib_corte["status_corte"] == "atrasado").sum() if not df_lib_corte.empty else 0
    c3.metric("Liberados atrasados (passou do corte)", fmt_num(atrasados))
    pct_geral = (
        comparativo["pedidos_montados"].sum()
        / max(comparativo["pedidos_montados"].sum() + comparativo["pedidos_pendentes"].sum(), 1)
        * 100
    )
    c4.metric("% já montado (geral)", fmt_pct(pct_geral))

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Comparativo por estado", "Aging dos pendentes", "Status de corte", "Histórico do dia"]
    )

    # -----------------------------------------------------------------------
    with tab1:
        st.markdown("#### 📊 Montados x Liberados x Total, por estado")
        st.markdown(
            "<div style='display:flex; gap:18px; margin:4px 0 16px 0; font-size:13px; color:#2f6b46;'>"
            "<span>🟩 <b>Montados</b></span>"
            "<span>🟢 <b>Liberados</b> (pendentes)</span>"
            "<span>🟦 <b>TOTAL</b></span>"
            "</div>",
            unsafe_allow_html=True,
        )

        estados_lista = list(tabela_estado["estado"].unique())
        for i in range(0, len(estados_lista), 2):
            par = estados_lista[i:i + 2]
            colunas_grid = st.columns(len(par))
            for col, estado in zip(colunas_grid, par):
                with col:
                    bloco = tabela_estado[tabela_estado["estado"] == estado].drop(columns="estado")
                    bloco_fmt = formatar_tabela(
                        bloco, colunas_moeda=["valor"], colunas_peso=["peso"], colunas_num=["pedidos"],
                    )
                    grid_html, altura = render_datagrid(
                        bloco_fmt, key=f"estado_{estado}", titulo=ESTADOS.get(estado, estado),
                        altura_max=160, linhas_por_pagina=3, colorir_categoria=True,
                    )
                    components.html(grid_html, height=altura, scrolling=False)

        st.markdown("<br>", unsafe_allow_html=True)
        fig = px.bar(
            comparativo.melt(
                id_vars="estado",
                value_vars=["pedidos_pendentes", "pedidos_montados"],
                var_name="tipo", value_name="pedidos",
            ),
            x="estado", y="pedidos", color="tipo", barmode="group",
            title="Pedidos pendentes x montados por estado",
        )
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------------------------
    with tab2:
        if df_lib_aging.empty:
            st.info("Sem pedidos liberados neste snapshot.")
        else:
            resumo_aging = metricas.resumo_aging_por_estado(df_lib_aging)
            fig2 = px.bar(
                resumo_aging, x="estado", y="pedidos", color="faixa_aging",
                title="Idade dos pedidos liberados pendentes",
                category_orders={"faixa_aging": ["0-2h", "2-6h", "6-12h", "12-24h", "24h+", "sem data"]},
            )
            st.plotly_chart(fig2, use_container_width=True)
            tabela_aging = df_lib_aging[[
                "numero_pedido", "estado", "cliente", "cidade", "data_hora_liberacao",
                "idade_horas", "faixa_aging", "peso", "valor",
            ]].sort_values("idade_horas", ascending=False)
            tabela_aging = formatar_tabela(tabela_aging, colunas_moeda=["valor"], colunas_peso=["peso"])
            tabela_aging["idade_horas"] = tabela_aging["idade_horas"].round(1)
            grid_html, altura = render_datagrid(
                tabela_aging, key="aging", altura_max=420, linhas_por_pagina=10,
            )
            components.html(grid_html, height=altura, scrolling=False)

    # -----------------------------------------------------------------------
    with tab3:
        if df_lib_corte.empty:
            st.info("Sem pedidos liberados neste snapshot.")
        else:
            fig3 = px.histogram(
                df_lib_corte, x="estado", color="status_corte", barmode="group",
                title="Status de corte por estado",
            )
            st.plotly_chart(fig3, use_container_width=True)
            tabela_atrasados = df_lib_corte[df_lib_corte["status_corte"] == "atrasado"][[
                "numero_pedido", "estado", "cliente", "cidade", "data_hora_liberacao",
                "idade_horas", "peso", "valor",
            ]]
            tabela_atrasados = formatar_tabela(tabela_atrasados, colunas_moeda=["valor"], colunas_peso=["peso"])
            tabela_atrasados["idade_horas"] = tabela_atrasados["idade_horas"].round(1)
            grid_html, altura = render_datagrid(
                tabela_atrasados, key="atrasados", altura_max=420, linhas_por_pagina=10,
            )
            components.html(grid_html, height=altura, scrolling=False)

    # -----------------------------------------------------------------------
    with tab4:
        if GSHEETS_OK:
            if st.button("💾 Salvar este snapshot no histórico"):
                gsheets.salvar_snapshot(comparativo, agora)
                st.cache_data.clear()
                st.success("Snapshot salvo no histórico.")
            historico = gsheets.carregar_historico()
            if historico.empty:
                st.info("Ainda não há snapshots salvos no histórico.")
            else:
                fig4 = px.line(
                    historico.sort_values("timestamp"),
                    x="timestamp", y="pedidos_pendentes", color="estado",
                    title="Evolução dos pedidos pendentes ao longo do tempo",
                    markers=True,
                )
                st.plotly_chart(fig4, use_container_width=True)
                historico_fmt = formatar_tabela(
                    historico.sort_values("timestamp", ascending=False),
                    colunas_moeda=["valor_pendente", "valor_montado"],
                    colunas_peso=["peso_pendente", "peso_montado"],
                    colunas_num=["pedidos_pendentes", "pedidos_montados"],
                    colunas_pct=["pct_montado"],
                )
                grid_html, altura = render_datagrid(
                    historico_fmt, key="historico", altura_max=420, linhas_por_pagina=10,
                )
                components.html(grid_html, height=altura, scrolling=False)
        else:
            st.info("Configure o Google Sheets (veja o README) para habilitar o histórico intradiário.")
else:
    st.info("Envie os arquivos de Liberados e/ou Montados acima para começar.")

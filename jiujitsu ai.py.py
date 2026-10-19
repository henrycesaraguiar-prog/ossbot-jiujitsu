import os
import io
import json
import uuid
import hashlib
import tempfile
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components
from groq import Groq

# Tenta carregar a biblioteca de voz gTTS
try:
    from gTTS import gTTS
    tem_gtts = True
except ImportError:
    tem_gtts = False

def gerar_audio(texto):
    if not tem_gtts:
        return b""
    limpo = (
        texto.replace("*", "")
        .replace("#", "")
        .replace("|", " ")
        .replace("_", " ")
    )
    buffer = io.BytesIO()
    gTTS(text=limpo, lang="pt", slow=False).write_to_fp(buffer)
    return buffer.getvalue()

# ---------------------------------------------------------------------------
# Gerenciamento de dados por Usuário
# ---------------------------------------------------------------------------
PASTA_DADOS = os.path.dirname(os.path.abspath(__file__))

def obter_caminho_usuario(nome_usuario):
    nome_limpo = "".join(c if c.isalnum() else "_" for c in nome_usuario.lower()).strip("_")
    return os.path.join(PASTA_DADOS, f"usuario_{nome_limpo}.json")

def carregar_dados_usuario(nome_usuario):
    caminho = obter_caminho_usuario(nome_usuario)
    try:
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if "historico_lutas" not in dados:
                    dados["historico_lutas"] = []
                return dados
    except Exception:
        pass
    return {"conversas": {}, "historico_lutas": []}

def salvar_dados_usuario(nome_usuario, dados):
    caminho = obter_caminho_usuario(nome_usuario)
    try:
        tmp = caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(tmp, caminho)
    except Exception as e:
        st.warning(f"Não consegui salvar os dados: {e}")

SAUDACAO_PADRAO = (
    "Olá, OSS! 🥋 Como posso te ajudar hoje? Posso criar um cronograma de aula, "
    "montar uma dinâmica para a turma kids, tirar uma dúvida técnica ou preparar uma "
    "estratégia para campeonato."
)

def iniciar_nova_conversa():
    st.session_state.historico = [{"role": "assistant", "content": SAUDACAO_PADRAO}]
    st.session_state.conversa_id = uuid.uuid4().hex
    st.session_state.titulo = ""
    st.session_state.titulo_ia = False

def salvar_conversa_atual():
    if not any(m["role"] == "user" for m in st.session_state.historico):
        return
    st.session_state.conversas[st.session_state.conversa_id] = {
        "titulo": st.session_state.titulo or "Nova conversa",
        "titulo_ia": st.session_state.titulo_ia,
        "atualizada": datetime.now().isoformat(timespec="seconds"),
        "mensagens": st.session_state.historico,
    }
    salvar_dados_usuario(st.session_state.usuario_atual, {
        "conversas": st.session_state.conversas,
        "historico_lutas": st.session_state.historico_lutas
    })

def abrir_conversa(cid):
    conv = st.session_state.conversas.get(cid)
    if conv:
        st.session_state.historico = conv["mensagens"]
        st.session_state.conversa_id = cid
        st.session_state.titulo = conv["titulo"]
        st.session_state.titulo_ia = conv.get("titulo_ia", True)

def apagar_conversa(cid):
    if cid in st.session_state.conversas:
        del st.session_state.conversas[cid]
        salvar_dados_usuario(st.session_state.usuario_atual, {
            "conversas": st.session_state.conversas,
            "historico_lutas": st.session_state.historico_lutas
        })
    if cid == st.session_state.conversa_id:
        iniciar_nova_conversa()

def gerar_atalhos_inteligentes(conversas):
    palavras_chave = {}
    termos_comuns = {"como", "para", "qual", "uma", "com", "que", "dos", "das", "por", "sobre", "mais", "isso", "ele", "ela"}
    
    for cid, conv in conversas.items():
        for m in conv.get("mensagens", []):
            if m["role"] == "user":
                texto = m["content"].lower()
                for palavra in texto.split():
                    p_limpa = "".join(c for c in palavra if c.isalnum())
                    if len(p_limpa) > 3 and p_limpa not in termos_comuns:
                        palavras_chave[p_limpa] = palavras_chave.get(p_limpa, 0) + 1
                        
    ordenados = sorted(palavras_chave.items(), key=lambda x: x[1], reverse=True)
    top_temos = [item[0].capitalize() for item in ordenados[:4]]
    
    if not top_temos:
        return ["Guarda", "Raspagem", "Campeonato", "Kids"]
    return top_temos

# Configuração da página
st.set_page_config(
    page_title="OssBot - Assistente de Jiu-Jitsu",
    page_icon="🥋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Mode
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    .main { background-color: #121212; }
    h1, h2, h3, h4, h5, h6, span, label { color: #ffffff !important; }
    p { color: #ff4d4d !important; }
    div[data-testid="stChatInput"] { background-color: #f0f0f0 !important; border-radius: 10px; border: 2px solid #ff4d4d !important; }
    div[data-testid="stChatInput"] textarea { color: #000000 !important; background-color: #f0f0f0 !important; font-weight: bold !important; }
    .stButton button { border-radius: 10px; font-weight: bold; background-color: #333333; color: #ff4d4d; border: 1px solid #ff4d4d; }
    .stButton button:hover { background-color: #555555; color: #ffffff; }
    .placar-box { background-color: #1e1e1e; border: 2px solid #ff4d4d; border-radius: 15px; padding: 20px; text-align: center; margin-bottom: 20px; }
    .placar-numero { font-size: 50px; font-weight: bold; color: #00ffcc; }
    </style>
""", unsafe_allow_html=True)

# Barra Lateral - Identificação
with st.sidebar:
    st.markdown("## 🥋 Identificação")
    usuario_input = st.text_input(
        "Digite seu Nome e Sobrenome:",
        value=st.session_state.get("usuario_atual", ""),
        placeholder="Ex: Henry Cesar",
        key="input_usuario"
    ).strip()

    if not usuario_input:
        st.warning("⚠️ Por favor, digite seu nome e sobrenome para começar.")
        st.stop()

    if "usuario_atual" not in st.session_state or st.session_state.usuario_atual != usuario_input:
        st.session_state.usuario_atual = usuario_input
        dados_carregados = carregar_dados_usuario(usuario_input)
        st.session_state.conversas = dados_carregados.get("conversas", {})
        st.session_state.historico_lutas = dados_carregados.get("historico_lutas", [])
        
        if not st.session_state.conversas:
            iniciar_nova_conversa()
            salvar_conversa_atual()
        else:
            ultimo_id = max(st.session_state.conversas, key=lambda c: st.session_state.conversas[c].get("atualizada", ""))
            abrir_conversa(ultimo_id)

    st.divider()
    st.markdown("## 🥋 Minhas conversas")
    if st.button("➕ Nova conversa", on_click=iniciar_nova_conversa, key="btn_nova_conversa"):
        salvar_conversa_atual()

    conversas = st.session_state.conversas
    ids = sorted(conversas, key=lambda c: conversas[c].get("atualizada", ""), reverse=True)

    for cid in ids:
        conv = conversas[cid]
        atual = cid == st.session_state.conversa_id
        col_a, col_b = st.columns([5, 1])
        with col_a:
            st.button(("▶ " if atual else "") + conv["titulo"], key=f"abrir_{cid}", on_click=abrir_conversa, args=(cid,))
        with col_b:
            st.button("🗑️", key=f"apagar_{cid}", on_click=apagar_conversa, args=(cid,))

# Inicializações do Modo Luta
if "pts_a" not in st.session_state: st.session_state.pts_a = 0
if "vant_a" not in st.session_state: st.session_state.vant_a = 0
if "pun_a" not in st.session_state: st.session_state.pun_a = 0
if "pts_b" not in st.session_state: st.session_state.pts_b = 0
if "vant_b" not in st.session_state: st.session_state.vant_b = 0
if "pun_b" not in st.session_state: st.session_state.pun_b = 0
if "tempo_segundos" not in st.session_state: st.session_state.tempo_segundos = 300
if "cronometro_rodando" not in st.session_state: st.session_state.cronometro_rodando = False
if "historico_lutas" not in st.session_state: st.session_state.historico_lutas = []

groq_api_key = "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"
client = None
try:
    client = Groq(api_key=groq_api_key)
except Exception as e:
    st.error(f"Erro na chave Groq: {e}")

MODELO = "openai/gpt-oss-120b"

st.markdown("<h1 style='text-align: center; color: #ff4d4d !important;'>🥋 OssBot</h1>", unsafe_allow_html=True)
st.markdown(f"<h4 style='text-align: center; color: #00ffcc;'>Usuário: {st.session_state.usuario_atual}</h4>", unsafe_allow_html=True)

st.divider()

aba_chat, aba_modo_luta, aba_historico_lutas = st.tabs(["💬 Chat com IA", "🤼 MODO LUTA", "📜 Histórico de Lutas"])

# ===========================================================================
# ABA MODO LUTA
# ===========================================================================
with aba_modo_luta:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>⏱️ PLACAR E CRONÔMETRO DE LUTA</h2>", unsafe_allow_html=True)
    
    col_l1, col_l2 = st.columns(2)
    with col_l1: nome_a = st.text_input("🔵 Atleta 1 (Azul/Preto):", value="Atleta Azul", key="nome_a")
    with col_l2: nome_b = st.text_input("⚪ Atleta 2 (Branco):", value="Atleta Branco", key="nome_b")
        
    mins = st.session_state.tempo_segundos // 60
    segs = st.session_state.tempo_segundos % 60
    st.markdown(f"<h1 style='text-align: center; font-size: 60px; color: #ff4d4d;'>{mins:02d}:{segs:02d}</h1>", unsafe_allow_html=True)
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown(f"<div class='placar-box'><h2 style='color: #4da6ff;'>🔵 {nome_a}</h2><div class='placar-numero'>{st.session_state.pts_a} Pts</div><p>Vantagens: {st.session_state.vant_a} | Punições: {st.session_state.pun_a}</p></div>", unsafe_allow_html=True)
        if st.button("+2 Pts (Azul)", key="a_2"): st.session_state.pts_a += 2
        if st.button("+3 Pts (Azul)", key="a_3"): st.session_state.pts_a += 3
        if st.button("+4 Pts (Azul)", key="a_4"): st.session_state.pts_a += 4
        if st.button("+ Vantagem (Azul)", key="a_v"): st.session_state.vant_a += 1

    with col_p2:
        st.markdown(f"<div class='placar-box'><h2 style='color: #ffffff;'>⚪ {nome_b}</h2><div class='placar-numero'>{st.session_state.pts_b} Pts</div><p>Vantagens: {st.session_state.vant_b} | Punições: {st.session_state.pun_b}</p></div>", unsafe_allow_html=True)
        if st.button("+2 Pts (Branco)", key="b_2"): st.session_state.pts_b += 2
        if st.button("+3 Pts (Branco)", key="b_3"): st.session_state.pts_b += 3
        if st.button("+4 Pts (Branco)", key="b_4"): st.session_state.pts_b += 4
        if st.button("+ Vantagem (Branco)", key="b_v"): st.session_state.vant_b += 1

    st.divider()
    if st.button("💾 SALVAR RESULTADO DA LUTA NO HISTÓRICO", use_container_width=True):
        nova_luta = {
            "data": datetime.now().strftime("%d/%m/%Y - %H:%M"),
            "atleta_a": nome_a,
            "pts_a": st.session_state.pts_a,
            "vant_a": st.session_state.vant_a,
            "pun_a": st.session_state.pun_a,
            "atleta_b": nome_b,
            "pts_b": st.session_state.pts_b,
            "vant_b": st.session_state.vant_b,
            "pun_b": st.session_state.pun_b,
        }
        st.session_state.historico_lutas.append(nova_luta)
        salvar_dados_usuario(st.session_state.usuario_atual, {
            "conversas": st.session_state.conversas,
            "historico_lutas": st.session_state.historico_lutas
        })
        st.success("✅ Luta salva com sucesso no histórico!")

# ===========================================================================
# ABA HISTÓRICO DE LUTAS
# ===========================================================================
with aba_historico_lutas:
    st.markdown("### 📜 Lutas Registradas")
    if not st.session_state.historico_lutas:
        st.info("Nenhuma luta registrada ainda. Use o botão no Modo Luta para guardar seus placares!")
    else:
        for idx, luta in enumerate(reversed(st.session_state.historico_lutas)):
            with st.expander(f"🥋 Luta em {luta['data']} - {luta['atleta_a']} vs {luta['atleta_b']}"):
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    st.write(f"🔵 **{luta['atleta_a']}**: {luta['pts_a']} Pts | {luta['vant_a']} Vant | {luta['pun_a']} Pun")
                with col_h2:
                    st.write(f"⚪ **{luta['atleta_b']}**: {luta['pts_b']} Pts | {luta['vant_b']} Vant | {luta['pun_b']} Pun")

# ===========================================================================
# ABA CHAT COM IA
# ===========================================================================
with aba_chat:
    st.markdown("### 💬 Converse com o OssBot")
    for i, mensagem in enumerate(st.session_state.historico):
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])

    pergunta = st.chat_input("Digite sua dúvida sobre Jiu-Jitsu...")
    if pergunta:
        st.session_state.historico.append({"role": "user", "content": pergunta})
        salvar_conversa_atual()
        st.rerun()

import os
import io
import json
import uuid
import hashlib
import tempfile
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# Tenta carregar biblioteca de áudio sem travar a execução
try:
    from gTTS import gTTS
    tem_gtts_lib = True
except Exception:
    tem_gtts_lib = False

def gerar_audio_local(texto):
    if not tem_gtts_lib:
        return b""
    limpo = texto.replace("*", "").replace("#", "").replace("|", " ").replace("_", " ")
    buffer = io.BytesIO()
    try:
        gTTS(text=limpo, lang="pt", slow=False).write_to_fp(buffer)
        return buffer.getvalue()
    except Exception:
        return b""

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
                if "dinamic_kids_custom" not in dados:
                    dados["dinamic_kids_custom"] = []
                if "flashcards_pressao" not in dados:
                    dados["flashcards_pressao"] = []
                if "alunos_graduacao" not in dados:
                    dados["alunos_graduacao"] = []
                if "cards_vitoria" not in dados:
                    dados["cards_vitoria"] = []
                if "cursos_interativos" not in dados:
                    dados["cursos_interativos"] = []
                return dados
    except Exception:
        pass
    return {
        "conversas": {}, 
        "historico_lutas": [], 
        "dinamic_kids_custom": [],
        "flashcards_pressao": [],
        "alunos_graduacao": [],
        "cards_vitoria": [],
        "cursos_interativos": []
    }

def salvar_dados_usuario(nome_usuario, dados):
    caminho = obter_caminho_usuario(nome_usuario)
    try:
        tmp = caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(tmp, caminho)
    except Exception:
        pass

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
        "historico_lutas": st.session_state.historico_lutas,
        "dinamic_kids_custom": st.session_state.dinamic_kids_custom,
        "flashcards_pressao": st.session_state.flashcards_pressao,
        "alunos_graduacao": st.session_state.alunos_graduacao,
        "cards_vitoria": st.session_state.cards_vitoria,
        "cursos_interativos": st.session_state.cursos_interativos
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
            "historico_lutas": st.session_state.historico_lutas,
            "dinamic_kids_custom": st.session_state.dinamic_kids_custom,
            "flashcards_pressao": st.session_state.flashcards_pressao,
            "alunos_graduacao": st.session_state.alunos_graduacao,
            "cards_vitoria": st.session_state.cards_vitoria,
            "cursos_interativos": st.session_state.cursos_interativos
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

# Estilização CSS Avançada (Corrigindo contraste de inputs, caixas e uploaders)
st.markdown("""
<head>
    <link rel="manifest" href="data:application/manifest+json;utf8,{\"name\":\"OssBot Jiu-Jitsu App\",\"short_name\":\"OssBot\",\"start_url\":\"/\",\"display\":\"standalone\",\"background_color\":\"#121212\",\"theme_color\":\"#ff4d4d\",\"icons\":[{\"src\":\"https://em-content.zobj.net/source/apple/354/martial-arts-uniform_1f94b.png\",\"sizes\":\"192x192\",\"type\":\"image/png\"}]}">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#ff4d4d">
</head>
<style>
.stApp { background-color: #121212; color: #ffffff; }
.main { background-color: #121212; }
h1, h2, h3, h4, h5, h6, span, label, div, p { color: #ffffff !important; }

/* Correção rigorosa de contraste para caixas de texto, inputs e uploaders (fundo claro com letras pretas nítidas) */
input, textarea, select {
    background-color: #f8fafc !important;
    color: #0f172a !important;
    font-weight: bold !important;
    border: 2px solid #ff4d4d !important;
    border-radius: 8px !important;
}

div[data-testid="stTextInput"] input, 
div[data-testid="stTextArea"] textarea, 
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background-color: #f8fafc !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
}

/* Uploaders com fundo legível e letras escuras */
div[data-testid="stFileUploader"] {
    background-color: #f8fafc !important;
    border-radius: 10px !important;
    padding: 15px !important;
    border: 2px dashed #ff4d4d !important;
}
div[data-testid="stFileUploader"] * {
    color: #0f172a !important;
}

div[data-testid="stAudioInput"], div[data-testid="stCameraInput"] {
    background-color: #1e1e1e !important;
    border-radius: 10px !important;
    padding: 15px;
    border: 1px solid #444444;
}

div[data-testid="stChatInput"] {
    background-color: #f0f0f0 !important;
    border-radius: 10px !important;
    border: 2px solid #ff4d4d !important;
}
div[data-testid="stChatInput"] textarea {
    color: #000000 !important;
    background-color: #f0f0f0 !important;
    font-weight: bold !important;
    font-size: 16px !important;
}

.stButton button {
    border-radius: 10px;
    font-weight: bold;
    background-color: #333333;
    color: #ff4d4d;
    border: 1px solid #ff4d4d;
}
.stButton button:hover { background-color: #555555; color: #ffffff; }

.placar-box { background-color: #1e1e1e; border: 2px solid #ff4d4d; border-radius: 15px; padding: 20px; text-align: center; margin-bottom: 20px; }
.placar-numero { font-size: 50px; font-weight: bold; color: #00ffcc; }
.nutri-box { background-color: #1e293b; border: 2px solid #00ffcc; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
.camp-box { background-color: #1e1b4b; border: 2px solid #ff4d4d; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
.curso-box { background-color: #0f172a; border: 2px solid #38bdf8; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
.kids-box { background-color: #451a03; border: 2px solid #fbbf24; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
.extra-box { background-color: #064e3b; border: 2px solid #34d399; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# Botões flutuantes para subir e descer a página
components.html("""
<script>
const doc = window.parent.document;
const janela = window.parent;

['botoes-rolagem', 'estilo-botoes-rolagem'].forEach(function(id) {
  const antigo = doc.getElementById(id);
  if (antigo) antigo.remove();
});

const estilo = doc.createElement('style');
estilo.id = 'estilo-botoes-rolagem';
estilo.innerHTML = `
  #botoes-rolagem {
    position: fixed; right: 20px; bottom: 110px; display: flex; flex-direction: column; gap: 12px; z-index: 999999;
  }
  #botoes-rolagem button {
    width: 64px; height: 64px; font-size: 28px; font-weight: bold; color: #ffffff; background-color: #e60000; border: 2px solid #ffffff; border-radius: 50%; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.6);
  }
  #botoes-rolagem button:hover { background-color: #ff4d4d; }
`;
doc.head.appendChild(estilo);

function rolar(direcao) {
  doc.querySelectorAll('*').forEach(function(el) {
    if (el.closest('[data-testid="stSidebar"]')) return;
    const e = janela.getComputedStyle(el);
    const rola = (e.overflowY === 'auto' || e.overflowY === 'scroll');
    if (rola && el.scrollHeight > el.clientHeight + 20) {
      el.scrollTop = (direcao === 'cima') ? 0 : el.scrollHeight;
    }
  });
  doc.documentElement.scrollTop = (direcao === 'cima') ? 0 : doc.documentElement.scrollHeight;
  doc.body.scrollTop = (direcao === 'cima') ? 0 : doc.body.scrollTop;
}

const caixa = doc.createElement('div');
caixa.id = 'botoes-rolagem';

const subir = doc.createElement('button');
subir.type = 'button'; subir.title = 'Subir'; subir.textContent = '▲';
subir.addEventListener('click', function() { rolar('cima'); });

const descer = doc.createElement('button');
descer.type = 'button'; descer.title = 'Descer'; descer.textContent = '▼';
descer.addEventListener('click', function() { rolar('baixo'); });

caixa.appendChild(subir);
caixa.appendChild(descer);
doc.body.appendChild(caixa);
</script>
""", height=0)

# Barra Lateral - Identificação
with st.sidebar:
    st.markdown("## 🥋 Identificação")
    usuario_input = st.text_input(
        "Digite seu Nome e Sobrenome:",
        value=st.session_state.get("usuario_atual", "Henry Cesar"),
        placeholder="Ex: Henry Cesar",
        key="input_usuario"
    ).strip()

    if "usuario_atual" not in st.session_state or st.session_state.usuario_atual != usuario_input:
        st.session_state.usuario_atual = usuario_input
        dados_carregados = carregar_dados_usuario(usuario_input)
        st.session_state.conversas = dados_carregados.get("conversas", {})
        st.session_state.historico_lutas = dados_carregados.get("historico_lutas", [])
        st.session_state.dinamic_kids_custom = dados_carregados.get("dinamic_kids_custom", [])
        st.session_state.flashcards_pressao = dados_carregados.get("flashcards_pressao", [])
        st.session_state.alunos_graduacao = dados_carregados.get("alunos_graduacao", [])
        st.session_state.cards_vitoria = dados_carregados.get("cards_vitoria", [])
        st.session_state.cursos_interativos = dados_carregados.get("cursos_interativos", [])
        
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

    busca = st.text_input("🔍 Pesquisar", placeholder="Ex.: guarda", key="busca_conversas").strip().lower()
    st.divider()

    conversas = st.session_state.conversas
    ids = sorted(conversas, key=lambda c: conversas[c].get("atualizada", ""), reverse=True)

    mostradas = 0
    for cid in ids:
        conv = conversas[cid]
        if busca:
            texto_total = conv["titulo"].lower() + " " + " ".join(m["content"].lower() for m in conv["mensagens"])
            if busca not in texto_total: continue

        mostradas += 1
        atual = cid == st.session_state.conversa_id
        col_a, col_b = st.columns([5, 1])
        with col_a:
            st.button(("▶ " if atual else "") + conv["titulo"], key=f"abrir_{cid}", on_click=abrir_conversa, args=(cid,))
        with col_b:
            st.button("🗑️", key=f"apagar_{cid}", on_click=apagar_conversa, args=(cid,), help="Apagar esta conversa")

    if mostradas == 0:
        st.caption("Nenhuma conversa encontrada." if busca else "Suas conversas vão aparecer aqui. 🥋")

# Inicialização de estados auxiliares
if "audio_key" not in st.session_state: st.session_state.audio_key = 0
if "ultimo_audio" not in st.session_state: st.session_state.ultimo_audio = None
if "ultima_imagem" not in st.session_state: st.session_state.ultima_imagem = None
if "atalho_clicado" not in st.session_state: st.session_state.atalho_clicado = None

# Estados do Modo Luta
if "pts_a" not in st.session_state: st.session_state.pts_a = 0
if "vant_a" not in st.session_state: st.session_state.vant_a = 0
if "pun_a" not in st.session_state: st.session_state.pun_a = 0
if "pts_b" not in st.session_state: st.session_state.pts_b = 0
if "vant_b" not in st.session_state: st.session_state.vant_b = 0
if "pun_b" not in st.session_state: st.session_state.pun_b = 0
if "tempo_segundos" not in st.session_state: st.session_state.tempo_segundos = 300
if "cronometro_rodando" not in st.session_state: st.session_state.cronometro_rodando = False
if "historico_lutas" not in st.session_state: st.session_state.historico_lutas = []
if "lista_alunos_academia" not in st.session_state: st.session_state.lista_alunos_academia = []
if "dinamic_kids_custom" not in st.session_state: st.session_state.dinamic_kids_custom = []
if "flashcards_pressao" not in st.session_state: st.session_state.flashcards_pressao = []
if "alunos_graduacao" not in st.session_state: st.session_state.alunos_graduacao = []
if "cards_vitoria" not in st.session_state: st.session_state.cards_vitoria = []
if "cursos_interativos" not in st.session_state: st.session_state.cursos_interativos = []

MODELO = "openai/gpt-oss-120b"

# Cabeçalho com Fotos
col_esq, col_centro, col_dir = st.columns([1.2, 2.6, 1.2])
with col_esq:
    st.image("https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=600&auto=format&fit=crop", caption="Técnica e Combate", use_container_width=True)
with col_centro:
    st.markdown("<h1 style='text-align: center; color: #ff4d4d !important;'>🥋 OssBot App</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center; color: #00ffcc;'>Usuário: {st.session_state.usuario_atual}</h4>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #aaaaaa;'>O seu Assistente de Jiu-Jitsu (PWA)</h3>", unsafe_allow_html=True)

with col_dir:
    st.image("https://images.unsplash.com/photo-1555597673-b21d5c935865?q=80&w=600&auto=format&fit=crop", caption="Faixa Preta — Tradição", use_container_width=True)

st.divider()

# Abas Principais (14 Abas - "Testão" do PWA removido para limpar a tela)
aba_chat, aba_modo_luta, aba_historico_lutas, aba_nutricao, aba_camp, aba_cursos, aba_kids, aba_drills, aba_pressao, aba_grad, aba_kimono, aba_card, aba_caderneta, aba_chaves = st.tabs([
    "💬 Chat IA", 
    "🤼 Luta", 
    "📜 Histórico",
    "🥗 Nutrição",
    "🏆 Camp",
    "📚 Cursos",
    "👶 Kids",
    "⏱️ Drills",
    "🧠 Pressão",
    "🥇 Graduação",
    "🥋 Kimono",
    "📸 Card",
    "📇 Alunos",
    "⏱️ Chaves"
])

# ===========================================================================
# ABA 1: CHAT COM IA
# ===========================================================================
with aba_chat:
    st.markdown("### ⚙️ Escolha o Modo de Atendimento")
    modo_selecionado

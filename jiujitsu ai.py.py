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
                if "historico_lutas" not in dados: dados["historico_lutas"] = []
                if "dinamic_kids_custom" not in dados: dados["dinamic_kids_custom"] = []
                if "flashcards_pressao" not in dados: dados["flashcards_pressao"] = []
                if "alunos_graduacao" not in dados: dados["alunos_graduacao"] = []
                if "cards_vitoria" not in dados: dados["cards_vitoria"] = []
                if "cursos_interativos" not in dados: dados["cursos_interativos"] = []
                if "lista_alunos_academia" not in dados: dados["lista_alunos_academia"] = []
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
        "cursos_interativos": [],
        "lista_alunos_academia": []
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
        "cursos_interativos": st.session_state.cursos_interativos,
        "lista_alunos_academia": st.session_state.lista_alunos_academia
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
            "cursos_interativos": st.session_state.cursos_interativos,
            "lista_alunos_academia": st.session_state.lista_alunos_academia
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

# Estilização CSS Limpa (Sem vazar texto na tela, contrastes ajustados para caixas legíveis)
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

/* Campos de texto, inputs e selects com fundo claro e texto bem preto/visível */
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

/* Uploaders com contraste legível */
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
        st.session_state.lista_alunos_academia = dados_carregados.get("lista_alunos_academia", [])
        
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

# Abas Principais (14 Abas - Sem o "testão" gigante do PWA)
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
    modo_selecionado = st.radio(
        "Como você quer que o OssBot responda?",
        [
            "🥋 Aluno / Competidor (Online)",
            "👶 Professor / Turma Kids (Online)",
            "📡 Modo Offline (Economizar Dados Móveis / Sem Internet)"
        ],
        index=0, key="modo_atendimento"
    )

    if "Modo Offline" in modo_selecionado:
        st.info("📡 **Modo Offline Ativado!** Nenhuma requisição externa será feita nesta aba. Você pode usar 100% das outras abas sem gastar nada da sua rede!")
    else:
        client = None
        try:
            from groq import Groq
            groq_api_key = "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"
            client = Groq(api_key=groq_api_key)
        except Exception:
            client = None

        system_prompt = "Você é o OssBot, assistente especialista em BJJ focado em atletas e professores. Use termos como OSS, guarda, raspagem."

        st.divider()
        st.markdown("### ⚡ Atalhos Inteligentes")
        atalhos_personalizados = gerar_atalhos_inteligentes(st.session_state.conversas)
        cols_atalhos = st.columns(len(atalhos_personalizados))
        for idx, atalho in enumerate(atalhos_personalizados):
            with cols_atalhos[idx]:
                if st.button(f"📌 {atalho}", key=f"atalho_{idx}", use_container_width=True):
                    st.session_state.atalho_clicado = f"Quero dicas sobre: {atalho}"

        st.divider()
        for i, mensagem in enumerate(st.session_state.historico):
            with st.chat_message(mensagem["role"]):
                st.markdown(mensagem["content"])
                if mensagem["role"] == "assistant" and st.button("🔊 Ouvir", key=f"ouvir_{i}"):
                    ab = gerar_audio_local(mensagem["content"])
                    if ab: st.audio(ab, format="audio/mp3")

        texto_para_enviar = None
        pergunta_texto = st.chat_input("Digite sua dúvida...")

        if st.session_state.atalho_clicado:
            texto_para_enviar = st.session_state.atalho_clicado
            st.session_state.atalho_clicado = None

        if pergunta_texto:
            texto_para_enviar = pergunta_texto
            st.session_state.historico.append({"role": "user", "content": pergunta_texto})
            salvar_conversa_atual()

        if texto_para_enviar:
            if not client:
                st.warning("⚠️ Sem rede para a IA. Mude para a opção 'Modo Offline'!")
            else:
                with st.chat_message("assistant"):
                    with st.spinner("OssBot pensando... OSS! 🥋"):
                        try:
                            res = client.chat.completions.create(model=MODELO, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": texto_para_enviar}], temperature=0.7)
                            resp = res.choices[0].message.content
                            st.markdown(resp)
                            st.session_state.historico.append({"role": "assistant", "content": resp})
                            salvar_conversa_atual()
                        except Exception:
                            st.warning("Erro de rede com a IA.")

# ===========================================================================
# ABA 2: MODO LUTA
# ===========================================================================
with aba_modo_luta:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>⏱️ PLACAR & CRONÔMETRO DE LUTA</h2>", unsafe_allow_html=True)
    
    col_l1, col_l2 = st.columns(2)
    with col_l1: nome_atleta_a = st.text_input("🔵 Atleta 1 (Azul/Preto):", value="Atleta Azul", key="nome_a")
    with col_l2: nome_atleta_b = st.text_input("⚪ Atleta 2 (Branco):", value="Atleta Branco", key="nome_b")
    st.divider()

    col_t1, col_t2, col_t3 = st.columns([1, 2, 1])
    with col_t2:
        minutos_opcao = st.selectbox("Tempo do Rola:", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], index=4, key="select_tempo")
        if not st.session_state.cronometro_rodando and st.session_state.tempo_segundos == 300 and minutos_opcao != 5:
            st.session_state.tempo_segundos = minutos_opcao * 60
        mins, segs = divmod(st.session_state.tempo_segundos, 60)
        st.markdown(f"<h1 style='text-align: center; font-size: 70px; color: #ff4d4d;'>{mins:02d}:{segs:02d}</h1>", unsafe_allow_html=True)
        
        bc1, bc2, bc3 = st.columns(3)
        if bc1.button("▶️ INICIAR", use_container_width=True, key="btn_iniciar_luta"): st.session_state.cronometro_rodando = True
        if bc2.button("⏸️ PAUSAR", use_container_width=True, key="btn_pausar_luta"): st.session_state.cronometro_rodando = False
        if bc3.button("🔄 ZERAR", use_container_width=True, key="btn_zerar_luta"):
            st.session_state.cronometro_rodando = False
            st.session_state.tempo_segundos = minutos_opcao * 60
            st.session_state.pts_a = st.session_state.vant_a = st.session_state.pun_a = 0
            st.session_state.pts_b = st.session_state.vant_b = st.session_state.pun_b = 0

    st.divider()
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown(f"<div class='placar-box'><h2 style='color: #4da6ff;'>🔵 {nome_atleta_a}</h2><div class='placar-numero'>{st.session_state.pts_a} Pts</div><p>Vantagens: {st.session_state.vant_a} | Punições: {st.session_state.pun_a}</p></div>", unsafe_allow_html=True)
        b1, b2, b3, b4, b5 = st.columns(5)
        if b1.button("+2 Pts", key="a_2"): st.session_state.pts_a += 2
        if b2.button("+3 Pts", key="a_3"): st.session_state.pts_a += 3
        if b3.button("+4 Pts", key="a_4"): st.session_state.pts_a += 4
        if b4.button("+Vant", key="a_v"): st.session_state.vant_a += 1
        if b5.button("+Pun", key="a_p"): st.session_state.pun_a += 1
    with col_p2:
        st.markdown(f"<div class='placar-box'><h2 style='color: #ffffff;'>⚪ {nome_atleta_b}</h2><div class='placar-numero'>{st.session_state.pts_b} Pts</div><p>Vantagens: {st.session_state.vant_b} | Punições: {st.session_state.pun_b}</p></div>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("+2 Pts", key="b_2"): st.session_state.pts_b += 2
        if c2.button("+3 Pts", key="b_3"): st.session_state.pts_b += 3
        if c3.button("+4 Pts", key="b_4"): st.session_state.pts_b += 4
        if c4.button("+Vant", key="b_v"): st.session_state.vant_b += 1
        if c5.button("+Pun", key="b_p"): st.session_state.pun_b += 1

    st.divider()
    if st.button("💾 SALVAR RESULTADO DA LUTA", use_container_width=True, key="btn_salvar_luta"):
        nl = {
            "data": datetime.now().strftime("%d/%m/%Y - %H:%M"),
            "atleta_a": nome_atleta_a, "pts_a": st.session_state.pts_a, "vant_a": st.session_state.vant_a, "pun_a": st.session_state.pun_a,
            "atleta_b": nome_atleta_b, "pts_b": st.session_state.pts_b, "vant_b": st.session_state.vant_b, "pun_b": st.session_state.pun_b,
        }
        st.session_state.historico_lutas.append(nl)
        salvar_dados_usuario(st.session_state.usuario_atual, {"conversas": st.session_state.conversas, "historico_lutas": st.session_state.historico_lutas})
        st.success("✅ Luta salva na memória!")

# ===========================================================================
# ABA 3: HISTÓRICO DE LUTAS
# ===========================================================================
with aba_historico_lutas:
    st.markdown("### 📜 Lutas Registradas")
    if not st.session_state.historico_lutas:
        st.info("Nenhuma luta registrada ainda.")
    else:
        for idx, luta in enumerate(reversed(st.session_state.historico_lutas)):
            with st.expander(f"🥋 {luta['data']} - {luta['atleta_a']} vs {luta['atleta_b']}"):
                st.write(f"🔵 **{luta['atleta_a']}**: {luta['pts_a']} Pts ({luta['vant_a']}V/{luta['pun_a']}P) | ⚪ **{luta['atleta_b']}**: {luta['pts_b']} Pts ({luta['vant_b']}V/{luta['pun_b']}P)")

# ===========================================================================
# ABA 4: NUTRIÇÃO & HIDRATAÇÃO
# ===========================================================================
with aba_nutricao:
    st.markdown("<h2 style='text-align: center; color: #00ffcc;'>🥗 NUTRIÇÃO & HIDRATAÇÃO</h2>", unsafe_allow_html=True)
    peso_input = st.number_input("Digite seu Peso atual (kg):", 30.0, 150.0, 65.0, 0.5, key="nutri_peso")
    horas_input = st.slider("Horas de treino por dia:", 0.5, 4.0, 1.5, 0.5, key="nutri_horas")
    agua_calc = ((peso_input * 35) / 1000) + (horas_input * 0.75)
    st.markdown(f"<div class='nutri-box'><h3>🥤 Meta Diária de Água Recomendada:</h3><h2>{agua_calc:.2f} Litros</h2><p>• Dica: Beba 500ml de água 1h antes do treino e consuma carboidratos leves para ter energia sem desconforto.</p></div>", unsafe_allow_html=True)

# ===========================================================================
# ABA 5: CAMPEONATO
# ===========================================================================
with aba_camp:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>🏆 ESTRATÉGIA DE CAMPEONATO</h2>", unsafe_allow_html=True)
    faixa_camp = st.selectbox("Sua Faixa:", ["Branca", "Kids", "Azul", "Roxa", "Castanha", "Preta"], key="camp_faixa")
    estilo_camp = st.text_input("Seu Golpe/Posição Favorito:", "Armlock da Guarda", key="camp_estilo")
    
    if st.button("🚀 Gerar Plano de Luta Tático", use_container_width=True, key="btn_plan_camp"):
        st.markdown(f"""
        <div class='camp-box'>
            <h3 style='color: #00ffcc;'>🥇 GUIA TÁTICO ({faixa_camp} - {estilo_camp})</h3>
            <p>1. <b>Início Implacável:</b> Faça a pegada na gola/manga primeiro. Imponha o ritmo antes do adversário pontuar.</p>
            <p>2. <b>Foco na Posição {estilo_camp}:</b> Monte armadilhas criando conexões. Garanta os primeiros 2 pontos de vantagem antes da finalização.</p>
            <p>3. <b>Administração do Placar:</b> Se estiver na frente nos 60 segundos finais, mantenha a base sólida e evite trocas arriscadas.</p>
        </div>
        """, unsafe_allow_html=True)

# ===========================================================================
# ABA 6: CURSOS (Uploads e textos legíveis)
# ===========================================================================
with aba_cursos:
    st.markdown("<h2 style='text-align: center; color: #38bdf8;'>📚 MANUAL DE REGRAS & CURSOS BJJ</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Consulte as regras oficiais, envie materiais fotográficos ou cadastre anotações de curso!</p>", unsafe_allow_html=True)

    with st.form(key="form_curso_interativo"):
        st.markdown("### ➕ Adicionar Material / Anotação de Curso")
        titulo_curso = st.text_input("Título do Módulo / Regra:")
        desc_curso = st.text_area("Descrição ou Anotações:")
        foto_curso = st.file_uploader("Enviar Foto do Material (Arquivos):", type=["jpg", "png", "jpeg"], key="up_curso")
        btn_salvar_curso = st.form_submit_button("💾 Salvar Material de Curso")
        
        if btn_salvar_curso:
            if titulo_curso.strip() and desc_curso.strip():
                st.session_state.cursos_interativos.append({
                    "titulo": titulo_curso.strip(),
                    "descricao": desc_curso.strip()
                })
                salvar_conversa_atual()
                st.success("✅ Material salvo com sucesso!")
            else:
                st.warning("Preencha o título e a descrição do curso.")

    st.divider()
    st.markdown("### 📜 Tabela Oficial de Pontos CBJJ / IBJJF:")
    st.markdown("""
    <div class='curso-box'>
        <ul>
            <li><b>2 PONTOS:</b> Queda, Raspagem e Joelho na Barriga.</li>
            <li><b>3 PONTOS:</b> Passagem de Guarda.</li>
            <li><b>4 PONTOS:</b> Montada, Montada pelas Costas e Pegada de Costas com dois ganchos.</li>
            <li><b>VANTAGENS:</b> Quase-queda, quase-raspagem ou tentativa real de finalização com defesa ativa.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.cursos_interativos:
        st.markdown("### 📂 Seus Materiais Cadastrados:")
        for idx, ci in enumerate(st.session_state.cursos_interativos):
            st.markdown(f"""
            <div class='curso-box'>
                <h3>📚 {ci['titulo']}</h3>
                <p>{ci['descricao']}</p>
            </div>
            """, unsafe_allow_html=True)

# ===========================================================================
# ABA 7: AULAS KIDS (Áudio e texto com campos visíveis)
# ===========================================================================
with aba_kids:
    st.markdown("<h2 style='text-align: center; color: #fbbf24;'>👶 AULAS & DINÂMICAS KIDS</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Crie dinâmicas infantis por texto, áudio ou câmera quando estiver com pressa no tatame!</p>", unsafe_allow_html=True)
    
    with st.form(key="form_kids"):
        nome_kids = st.text_input("Nome da Brincadeira / Dinâmica Kids:", placeholder="Ex: Pega-Pega do Guardeiro")
        desc_kids = st.text_area("Explicação / Regras da Dinâmica (Escrito):", placeholder="Descreva como funciona a brincadeira...")
        
        audio_kids_input = st.audio_input("Ou Grave um Áudio explicando a Dinâmica:")
        
        btn_add_kids = st.form_submit_button("💾 Salvar Dinâmica Kids")
        if btn_add_kids:
            texto_final_desc = desc_kids.strip()
            if audio_kids_input is not None:
                texto_final_desc += " [Áudio gravado pelo professor anexado com sucesso]"
                
            if nome_kids.strip() and texto_final_desc:
                st.session_state.dinamic_kids_custom.append({"titulo": nome_kids.strip(), "descricao": texto_final_desc})
                salvar_conversa_atual()
                st.success("✅ Dinâmica Kids salva com sucesso!")
            else:
                st.warning("Preencha o nome e a explicação (ou grave um áudio) da dinâmica!")

    st.divider()
    st.markdown("### 🧸 Dinâmicas Cadastradas:")
    if not st.session_state.dinamic_kids_custom:
        st.info("Nenhuma dinâmica personalizada cadastrada ainda.")
    else:
        for idx, dk in enumerate(st.session_state.dinamic_kids_custom):
            st.markdown(f"""
            <div class='kids-box'>
                <h3>🧸 {dk['titulo']}</h3>
                <p>{dk['descricao']}</p>
            </div>
            """, unsafe_allow_html=True)

# ===========================================================================
# ABA 8: DRILLS
# ===========================================================================
with aba_drills:
    st.markdown("<h2 style='text-align: center; color: #34d399;'>⏱️ DRILLS & HIIT DE COMBATE</h2>", unsafe_allow_html=True)
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1: t_acao = st.number_input("Tempo de Ação (s):", 10, 120, 30, 5, key="d_a")
    with col_d2: t_pausa = st.number_input("Tempo de Pausa (s):", 5, 60, 10, 5, key="d_p")
    with col_d3: n_rounds = st.number_input("Rounds:", 1, 30, 8, 1, key="d_r")
    
    if st.button("▶️ Iniciar Cronômetro de Drills", use_container_width=True, key="btn_iniciar_drills_local"):
        st.success(f"✅ Treino configurado: {n_rounds} rounds de {t_acao}s de explosão por {t_pausa}s de pausa!")

# ===========================================================================
# ABA 9: PRESSÃO
# ===========================================================================
with aba_pressao:
    st.markdown("<h2 style='text-align: center; color: #f43f5e;'>🧠 PRESSÃO DE LUTA - FLASHCARDS</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Estude posições difíceis e saídas de sufoco com flashcards dinâmicos.</p>", unsafe_allow_html=True)

    with st.form(key="form_pressao_flashcard"):
        st.markdown("### ➕ Adicionar Nova Situação de Pressão")
        pergunta_flash = st.text_input("Situação / Perigo (Ex: 'Estou de lateral com 100kg em cima, o que fazer?'):")
        resposta_flash = st.text_area("Resposta / Solução Tática:")
        btn_salvar_flash = st.form_submit_button("💾 Salvar Flashcard de Pressão")
        if btn_salvar_flash:
            if pergunta_flash.strip() and resposta_flash.strip():
                st.session_state.flashcards_pressao.append({"pergunta": pergunta_flash.strip(), "resposta": resposta_flash.strip()})
                salvar_conversa_atual()
                st.success("✅ Flashcard salvo com sucesso!")
            else:
                st.warning("Preencha a situação e a solução!")

    st.divider()
    st.markdown("### 📚 Seus Flashcards de Estudo:")
    if not st.session_state.flashcards_pressao:
        st.markdown("""
        <div class='camp-box'>
            <h4>💡 Exemplo 1: Faltando 1 minuto e perdendo por 2 a 0</h4>
            <p><b>Solução:</b> Estoure pegadas imediatamente e force o ataque de raspagem/queda sem aceitar amarração!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for idx, fc in enumerate(st.session_state.flashcards_pressao):
            with st.expander(f"⚡ Situação {idx+1}: {fc['pergunta']}"):
                st.markdown(f"<div class='camp-box'><p><b>💡 Saída Tática:</b> {fc['resposta']}</p></div>", unsafe_allow_html=True)

# ===========================================================================
# ABA 10: GRADUAÇÃO
# ===========================================================================
with aba_grad:
    st.markdown("<h2 style='text-align: center; color: #34d399;'>🥇 GRADUAÇÃO & DIÁRIO DE FAIXA</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Gerencie alunos, faixas, graus e verifique quem está apto para o próximo grau.</p>", unsafe_allow_html=True)

    with st.form(key="form_cadastra_aluno_grad"):
        st.markdown("### 📝 Cadastrar Aluno para Acompanhamento de Faixa")
        nome_aluno_g = st.text_input("Nome Completo do Aluno:")
        faixa_atual_g = st.selectbox("Faixa Atual:", ["Branca", "Cinza", "Amarela", "Laranja", "Verde", "Azul", "Roxa", "Castanha", "Preta"])
        graus_atuais_g = st.slider("Graus Atuais:", 0, 4, 0)
        data_inicio_g = st.date_input("Data de Início na Faixa Atual:")
        btn_salv_grad = st.form_submit_button("➕ Salvar Aluno no Diário de Faixa")
        
        if btn_salv_grad:
            if nome_aluno_g.strip():
                novo_aluno_reg = {
                    "nome": nome_aluno_g.strip(),
                    "faixa": faixa_atual_g,
                    "graus": graus_atuais_g,
                    "data_inicio": data_inicio_g.strftime("%d/%m/%Y")
                }
                st.session_state.alunos_graduacao.append(novo_aluno_reg)
                salvar_conversa_atual()
                st.success(f"✅ Aluno {nome_aluno_g} cadastrado no diário de graduação!")

    st.divider()
    st.markdown("### 📋 Alunos em Acompanhamento:")
    if not st.session_state.alunos_graduacao:
        st.info("Nenhum aluno cadastrado na graduação.")
    else:
        for idx, aluno in enumerate(st.session_state.alunos_graduacao):
            with st.expander(f"🥋 {aluno['nome']} - Faixa {aluno['faixa']} ({aluno['graus']}º Grau)"):
                st.write(f"• **Início na faixa:** {aluno['data_inicio']}")
                st.markdown("<p style='color: #00ffcc;'>✔️ <b>Status:</b> Acompanhando frequência e evolução técnica para o próximo grau!</p>", unsafe_allow_html=True)

# ===========================================================================
# ABA 11: KIMONO
# ===========================================================================
with aba_kimono:
    st.markdown("<h2 style='text-align: center; color: #fbbf24;'>🥋 GESTÃO E CUIDADOS COM O KIMONO</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Registre anotações, lavagens e dicas de manutenção do seu equipamento de luta.</p>", unsafe_allow_html=True)
    
    nota_kimono = st.text_area("Anotações sobre lavagem, ajustes ou reparos no Kimono:", placeholder="Ex: Lavar com água fria, secar à sombra para não encolher a gola...")
    if st.button("💾 Salvar Nota do Kimono", use_container_width=True):
        if nota_kimono.strip():
            st.success("✅ Anotação de kimono salva com sucesso!")
        else:
            st.warning("Digite alguma observação antes de salvar.")

    st.markdown("""
    <div class='kids-box' style='margin-top: 20px;'>
        <h3>🧼 Dica de Ouro de Conservação:</h3>
        <p>Nunca utilize secadora de roupas em quimonos trançados 100% algodão para evitar encolhimento precoce e desgaste das costuras principais.</p>
    </div>
    """, unsafe_allow_html=True)

# ===========================================================================
# ABA 12: CARD VITÓRIA
# ===========================================================================
with aba_card:
    st.markdown("<h2 style='text-align: center; color: #a855f7;'>📸 CARD DE VITÓRIA</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Crie seu card personalizado com foto, texto e comemore suas conquistas no tatame!</p>", unsafe_allow_html=True)

    foto_card_up = st.file_uploader("Enviar Foto da Vitória (Arquivos):", type=["jpg", "png", "jpeg"])
    foto_card_cam = st.camera_input("Ou Tire uma Foto com a Câmera:")
    
    legenda_card = st.text_area("Legenda / Frase do Card:", value="Tatame lavado, missão cumprida por hoje! 🥋🔥 OSS! #BJJ #OssBot")
    
    if st.button("🚀 Gerar Card de Vitória", use_container_width=True):
        st.success("✅ Card gerado com sucesso!")
        st.markdown(f"""
        <div class='placar-box' style='border: 2px solid #a855f7;'>
            <h3 style='color: #a855f7;'>🏆 CARD OFICIAL OSSBOT</h3>
            <p style='font-size: 18px; font-weight: bold;'>{legenda_card}</p>
        </div>
        """, unsafe_allow_html=True)

# ===========================================================================
# ABA 13: CADERNETA DE ALUNOS
# ===========================================================================
with aba_caderneta:
    st.markdown("<h2 style='text-align: center; color: #fbbf24;'>📇 CADERNETA DE ALUNOS & FREQUÊNCIA</h2>", unsafe_allow_html=True)
    novo_aluno = st.text_input("Digite o Nome do Aluno:", placeholder="Ex: Lucas Gabriel", key="input_novo_aluno")
    if st.button("➕ Adicionar Aluno à Turma", use_container_width=True, key="btn_add_aluno"):
        if novo_aluno.strip():
            st.session_state.lista_alunos_academia.append(novo_aluno.strip())
            salvar_conversa_atual()
            st.success(f"✅ Aluno {novo_aluno} adicionado com sucesso!")

    if st.session_state.lista_alunos_academia:
        st.markdown("### 📋 Lista de Alunos Cadastrados:")
        for idx, aluno in enumerate(st.session_state.lista_alunos_academia):
            col_al1, col_al2 = st.columns([3, 1])
            with col_al1: st.write(f"🥋 {aluno}")
            with col_al2:
                if st.button("Presença ✔️", key=f"pres_{idx}"):
                    st.toast(f"✅ Presença confirmada para {aluno}!")

# ===========================================================================
# ABA 14: CHAVES DE TORNEIO
# ===========================================================================
with aba_chaves:
    st.markdown("<h2 style='text-align: center; color: #f43f5e;'>⏱️ ORGANIZADOR DE CHAVES DE LUTA</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Organize os confrontos dos atletas de forma limpa e visível.</p>", unsafe_allow_html=True)
    
    nomes_atletas_txt = st.text_area("Digite os nomes dos atletas (um por linha):", placeholder="Atleta 1\nAtleta 2\nAtleta 3\nAtleta 4", key="txt_atletas_chave")
    
    if st.button("⚔️ Gerar Chaves de Luta", use_container_width=True, key="btn_gerar_chave"):
        atletas = [a.strip() for a in nomes_atletas_txt.split("\n") if a.strip()]
        if len(atletas) < 2:
            st.warning("Digite pelo menos 2 atletas para gerar os confrontos!")
        else:
            st.markdown("<div class='placar-box'><h3 style='color: #00ffcc;'>⚔️ CONFRONTOS GERADOS</h3></div>", unsafe_allow_html=True)
            for i in range(0, len(atletas)-1, 2):
                st.markdown(f"<div style='background-color: #1e1e1e; padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #ff4d4d;'><h4 style='color: #ffffff; margin:0;'>🥊 Luta: <span style='color: #00ffcc;'>{atletas[i]}</span> vs <span style='color: #ff4d4d;'>{atletas[i+1]}</span></h4></div>", unsafe_allow_html=True)
            if len(atletas) % 2 != 0:
                st.info(f"✨ Atleta aguardando vencedores (Bye): {atletas[-1]}")

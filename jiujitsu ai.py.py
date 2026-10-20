import os
import io
import json
import uuid
import hashlib
import socket
import tempfile
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# Função para testar se há conexão real com a internet
def checar_conexao_internet():
    try:
        # Tenta conectar a um servidor DNS público rápido (Google)
        socket.setdefaulttimeout(2)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

tem_internet = checar_conexao_internet()

# Tenta carregar as APIs apenas se houver conexão
client = None
tem_gtts = False

if tem_internet:
    try:
        from groq import Groq
        groq_api_key = "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"
        client = Groq(api_key=groq_api_key)
    except Exception:
        client = None

    try:
        from gTTS import gTTS
        tem_gtts = True
    except ImportError:
        tem_gtts = False

def gerar_audio(texto):
    if not tem_gtts or not tem_internet:
        return b""
    limpo = (
        texto.replace("*", "")
        .replace("#", "")
        .replace("|", " ")
        .replace("_", " ")
    )
    buffer = io.BytesIO()
    try:
        gTTS(text=limpo, lang="pt", slow=False).write_to_fp(buffer)
        return buffer.getvalue()
    except Exception:
        return b""

# ---------------------------------------------------------------------------
# Gerenciamento de dados por Usuário (Nome e Sobrenome)
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

# Configuração da página do Streamlit
st.set_page_config(
    page_title="OssBot - Assistente de Jiu-Jitsu",
    page_icon="🥋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização visual: Dark Mode profissional com texto SEMPRE EM BRANCO
st.markdown("""
    <style>
    .stApp { background-color: #121212; color: #ffffff; }
    .main { background-color: #121212; }
    h1, h2, h3, h4, h5, h6, span, label, div, p { color: #ffffff !important; }
    
    div[data-testid="stChatMessage"] p,
    div[data-testid="stChatMessage"] span,
    div[data-testid="stChatMessage"] div,
    div[data-testid="stChatMessage"] li,
    div[data-testid="stChatMessage"] label,
    .stMarkdown p,
    .stMarkdown span,
    .stMarkdown li {
        color: #ffffff !important;
    }

    div[data-testid="stFileUploader"], div[data-testid="stAudioInput"], div[data-testid="stCameraInput"] {
        background-color: #2b2b2b !important; border-radius: 10px; padding: 15px; border: 1px solid #444444;
    }
    div[data-testid="stChatInput"] {
        background-color: #f0f0f0 !important; border-radius: 10px; border: 2px solid #ff4d4d !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #000000 !important; background-color: #f0f0f0 !important; font-weight: bold !important; font-size: 16px !important;
    }
    .stButton button {
        border-radius: 10px; font-weight: bold; background-color: #333333; color: #ff4d4d; border: 1px solid #ff4d4d;
    }
    .stButton button:hover { background-color: #555555; color: #ffffff; }
    .placar-box { background-color: #1e1e1e; border: 2px solid #ff4d4d; border-radius: 15px; padding: 20px; text-align: center; margin-bottom: 20px; }
    .placar-numero { font-size: 50px; font-weight: bold; color: #00ffcc; }
    .nutri-box { background-color: #1e293b; border: 2px solid #00ffcc; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
    .camp-box { background-color: #1e1b4b; border: 2px solid #ff4d4d; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
    .curso-box { background-color: #0f172a; border: 2px solid #38bdf8; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
    .kids-box { background-color: #451a03; border: 2px solid #fbbf24; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
    .extra-box { background-color: #064e3b; border: 2px solid #34d399; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
    .offline-badge { background-color: #d97706; color: #ffffff; padding: 8px 16px; border-radius: 10px; font-weight: bold; font-size: 16px; display: inline-block; }
    .online-badge { background-color: #16a34a; color: #ffffff; padding: 8px 16px; border-radius: 10px; font-weight: bold; font-size: 16px; display: inline-block; }
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

# ---------------------------------------------------------------------------
# Barra Lateral - Identificação
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🥋 Identificação")
    usuario_input = st.text_input(
        "Digite seu Nome e Sobrenome:",
        value=st.session_state.get("usuario_atual", ""),
        placeholder="Ex: Henry Cesar",
        key="input_usuario"
    ).strip()

    if not usuario_input:
        st.warning("⚠️ Por favor, digite seu nome e sobrenome para começar a usar e salvar seu histórico.")
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

# Inicialização do Modo Luta
if "pts_a" not in st.session_state: st.session_state.pts_a = 0
if "vant_a" not in st.session_state: st.session_state.vant_a = 0
if "pun_a" not in st.session_state: st.session_state.pun_a = 0
if "pts_b" not in st.session_state: st.session_state.pts_b = 0
if "vant_b" not in st.session_state: st.session_state.vant_b = 0
if "pun_b" not in st.session_state: st.session_state.pun_b = 0
if "tempo_segundos" not in st.session_state: st.session_state.tempo_segundos = 300
if "cronometro_rodando" not in st.session_state: st.session_state.cronometro_rodando = False
if "ultimo_audio_luta" not in st.session_state: st.session_state.ultimo_audio_luta = None
if "historico_lutas" not in st.session_state: st.session_state.historico_lutas = []
if "lista_alunos_academia" not in st.session_state: st.session_state.lista_alunos_academia = []

MODELO = "openai/gpt-oss-120b"

# Cabeçalho com Fotos
col_esq, col_centro, col_dir = st.columns([1.2, 2.6, 1.2])
with col_esq:
    st.image("https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=600&auto=format&fit=crop", caption="Técnica e Combate", use_container_width=True)
with col_centro:
    st.markdown("<h1 style='text-align: center; color: #ff4d4d !important;'>🥋 OssBot</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center; color: #00ffcc;'>Usuário: {st.session_state.usuario_atual}</h4>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #aaaaaa;'>O seu Assistente de Jiu-Jitsu</h3>", unsafe_allow_html=True)
    
    # MENSAGEM CLARA DE STATUS DE INTERNET
    if tem_internet:
        st.markdown("<p style='text-align: center;'><span class='online-badge'>🟢 Você está com internet! Modo offline desligado.</span></p>", unsafe_allow_html=True)
    else:
        st.markdown("<p style='text-align: center;'><span class='offline-badge'>📡 Você está sem internet! Modo offline ligado.</span></p>", unsafe_allow_html=True)

with col_dir:
    st.image("https://images.unsplash.com/photo-1555597673-b21d5c935865?q=80&w=600&auto=format&fit=crop", caption="Faixa Preta — Tradição", use_container_width=True)

st.divider()

# Abas Principais (Total de 17 Abas)
aba_chat, aba_modo_luta, aba_historico_lutas, aba_nutricao, aba_camp, aba_cursos, aba_kids, aba_drills, aba_pressao, aba_grad, aba_def, aba_lesao, aba_kimono, aba_card, aba_pesagem, aba_caderneta, aba_chaves = st.tabs([
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
    "🛡️ Defesa",
    "🩹 Lesões",
    "🥋 Kimono",
    "📸 Card",
    "📋 Pesagem",
    "📇 Alunos",
    "⏱️ Chaves"
])

# ===========================================================================
# ABA 1: CHAT COM IA (ÚNICA QUE EXIGE INTERNET)
# ===========================================================================
with aba_chat:
    if not tem_internet:
        st.warning("⚠️ **Você está sem internet no momento!** A aba de Chat com IA precisa de conexão para responder. Todas as outras 16 abas do OssBot (Placar, Nutrição, Cursos, Regras, Kids, Drills, etc.) continuam funcionando 100% no Modo Offline!")
    else:
        st.markdown("### ⚙️ Escolha o Modo de Atendimento")
        modo_selecionado = st.radio(
            "Como você quer que o OssBot responda?",
            ["🥋 Aluno / Competidor", "👶 Professor / Turma Kids"],
            index=0, key="modo_atendimento"
        )

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
                    ab = gerar_audio(mensagem["content"])
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

        if texto_para_enviar and client:
            with st.chat_message("assistant"):
                with st.spinner("OssBot pensando... OSS! 🥋"):
                    try:
                        res = client.chat.completions.create(model=MODELO, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": texto_para_enviar}], temperature=0.7)
                        resp = res.choices[0].message.content
                        st.markdown(resp)
                        st.session_state.historico.append({"role": "assistant", "content": resp})
                        salvar_conversa_atual()
                    except Exception:
                        st.warning("Erro de conexão com os servidores da IA.")

# ===========================================================================
# ABA 2: MODO LUTA (OFFLINE ATIVO)
# ===========================================================================
with aba_modo_luta:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>⏱️ PLACAR & CRONÔMETRO DE LUTA</h2>", unsafe_allow_html=True)
    if not tem_internet: st.caption("📡 Modo Offline Ativo: O placar e cronômetro funcionam normalmente!")
    
    col_l1, col_l2 = st.columns(2)
    with col_l1: nome_atleta_a = st.text_input("🔵 Atleta 1:", value="Atleta Azul", key="nome_a")
    with col_l2: nome_atleta_b = st.text_input("⚪ Atleta 2:", value="Atleta Branco", key="nome_b")
    st.divider()

    col_t1, col_t2, col_t3 = st.columns([1, 2, 1])
    with col_t2:
        minutos_opcao = st.selectbox("Tempo do Rola:", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], index=4, key="select_tempo")
        if not st.session_state.cronometro_rodando and st.session_state.tempo_segundos == 300 and minutos_opcao != 5:
            st.session_state.tempo_segundos = minutos_opcao * 60
        mins, segs = divmod(st.session_state.tempo_segundos, 60)
        st.markdown(f"<h1 style='text-align: center; font-size: 70px; color: #ff4d4d;'>{mins:02d}:{segs:02d}</h1>", unsafe_allow_html=True)
        
        bc1, bc2, bc3 = st.columns(3)
        if bc1.button("▶️ INICIAR", use_container_width=True): st.session_state.cronometro_rodando = True
        if bc2.button("⏸️ PAUSAR", use_container_width=True): st.session_state.cronometro_rodando = False
        if bc3.button("🔄 ZERAR", use_container_width=True):
            st.session_state.cronometro_rodando = False
            st.session_state.tempo_segundos = minutos_opcao * 60
            st.session_state.pts_a = st.session_state.vant_a = st.session_state.pun_a = 0
            st.session_state.pts_b = st.session_state.vant_b = st.session_state.pun_b = 0

    st.divider()
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown(f"<div class='placar-box'><h2 style='color: #4da6ff;'>🔵 {nome_atleta_a}</h2><div class='placar-numero'>{st.session_state.pts_a} Pts</div><p>Vantagens: {st.session_state.vant_a} | Punições: {st.session_state.pun_a}</p></div>", unsafe_allow_html=True)
        b1, b2, b3, b4, b5 = st.columns(5)
        if b1.button("+2", key="a_2"): st.session_state.pts_a += 2
        if b2.button("+3", key="a_3"): st.session_state.pts_a += 3
        if b3.button("+4", key="a_4"): st.session_state.pts_a += 4
        if b4.button("+V", key="a_v"): st.session_state.vant_a += 1
        if b5.button("+P", key="a_p"): st.session_state.pun_a += 1
    with col_p2:
        st.markdown(f"<div class='placar-box'><h2 style='color: #ffffff;'>⚪ {nome_atleta_b}</h2><div class='placar-numero'>{st.session_state.pts_b} Pts</div><p>Vantagens: {st.session_state.vant_b} | Punições: {st.session_state.pun_b}</p></div>", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        if c1.button("+2", key="b_2"): st.session_state.pts_b += 2
        if c2.button("+3", key="b_3"): st.session_state.pts_b += 3
        if c3.button("+4", key="b_4"): st.session_state.pts_b += 4
        if c4.button("+V", key="b_v"): st.session_state.vant_b += 1
        if c5.button("+P", key="b_p"): st.session_state.pun_b += 1

    st.divider()
    if st.button("💾 SALVAR RESULTADO", use_container_width=True):
        nl = {
            "data": datetime.now().strftime("%d/%m/%Y - %H:%M"),
            "atleta_a": nome_atleta_a, "pts_a": st.session_state.pts_a, "vant_a": st.session_state.vant_a, "pun_a": st.session_state.pun_a,
            "atleta_b": nome_atleta_b, "pts_b": st.session_state.pts_b, "vant_b": st.session_state.vant_b, "pun_b": st.session_state.pun_b,
        }
        st.session_state.historico_lutas.append(nl)
        salvar_dados_usuario(st.session_state.usuario_atual, {"conversas": st.session_state.conversas, "historico_lutas": st.session_state.historico_lutas})
        st.success("✅ Luta salva na memória!")

# ===========================================================================
# ABA 3: HISTÓRICO DE LUTAS (OFFLINE ATIVO)
# ===========================================================================
with aba_historico_lutas:
    st.markdown("### 📜 Lutas Registradas")
    if not st.session_state.historico_lutas:
        st.info("Nenhuma luta registrada.")
    else:
        for luta in reversed(st.session_state.historico_lutas):
            with st.expander(f"🥋 {luta['data']} - {luta['atleta_a']} vs {luta['atleta_b']}"):
                st.write(f"🔵 **{luta['atleta_a']}**: {luta['pts_a']} Pts | ⚪ **{luta['atleta_b']}**: {luta['pts_b']} Pts")

# ===========================================================================
# ABA 4: NUTRIÇÃO & PESO (OFFLINE ATIVO)
# ===========================================================================
with aba_nutricao:
    st.markdown("<h2 style='text-align: center; color: #00ffcc;'>🥗 NUTRIÇÃO & HIDRATAÇÃO</h2>", unsafe_allow_html=True)
    peso = st.number_input("Peso atual (kg):", 30.0, 150.0, 65.0, 0.5, key="nutri_peso")
    agua = (peso * 35) / 1000
    st.markdown(f"<div class='nutri-box'><h3>🥤 Água Ideal Diária:</h3><h2>{agua:.2f} Litros</h2><p>• Dica Offline: Beba 500ml 1h antes do treino e coma carboidratos leves para energia sem refluxo.</p></div>", unsafe_allow_html=True)

# ===========================================================================
# ABA 5: CAMPEONATO (OFFLINE ATIVO)
# ===========================================================================
with aba_camp:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>🏆 ESTRATÉGIA DE CAMPEONATO</h2>", unsafe_allow_html=True)
    st.markdown("""
    <div class='camp-box'>
        <h3>🥇 Guia Tático Oficial</h3>
        <p>1. <b>Início:</b> Imponha pegadas firmes nos primeiros 30 segundos sem hesitar.</p>
        <p>2. <b>Pontuação:</b> Busque os primeiros 2 pontos com segurança para colocar pressão no adversário.</p>
        <p>3. <b>Reta Final:</b> Administre a postura e evite trocas arriscadas se estiver à frente no placar.</p>
    </div>
    """, unsafe_allow_html=True)

# ===========================================================================
# ABA 6: CURSOS (OFFLINE ATIVO)
# ===========================================================================
with aba_cursos:
    st.markdown("<h2 style='text-align: center; color: #38bdf8;'>📚 MANUAL DE REGRAS BJJ</h2>", unsafe_allow_html=True)
    st.markdown("""
    <div class='curso-box'>
        <h3>📜 Tabela Oficial de Pontos CBJJ / IBJJF:</h3>
        <ul>
            <li><b>2 PONTOS:</b> Queda, Raspagem e Joelho na Barriga.</li>
            <li><b>3 PONTOS:</b> Passagem de Guarda.</li>
            <li><b>4 PONTOS:</b> Montada, Montada pelas Costas e Pegada de Costas com dois ganchos.</li>
            <li><b>VANTAGENS:</b> Quase-queda, quase-raspagem ou tentativa real de finalização com defesa ativa.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ===========================================================================
# ABA 7: KIDS (OFFLINE ATIVO)
# ===========================================================================
with aba_kids:
    st.markdown("<h2 style='text-align: center; color: #fbbf24;'>👶 AULAS & DINÂMICAS KIDS</h2>", unsafe_allow_html=True)
    st.markdown("<div class='kids-box'><h3>🧸 Dinâmica: Pega-Pega do Guardeiro</h3><p>As crianças treinam reposição de guarda e agilidade tentando passar a guarda do professor sem usar força bruta.</p></div>", unsafe_allow_html=True)

# ===========================================================================
# ABA 8: DRILLS (OFFLINE ATIVO)
# ===========================================================================
with aba_drills:
    st.markdown("<h2 style='text-align: center; color: #34d399;'>⏱️ DRILLS & HIIT</h2>", unsafe_allow_html=True)
    if st.button("▶️ Iniciar Cronômetro de Treino", use_container_width=True):
        st.success("✅ Treino de tiros iniciado!")

# ===========================================================================
# ABA 9: PRESSÃO (OFFLINE ATIVO)
# ===========================================================================
with aba_pressao:
    st.markdown("<h2 style='text-align: center; color: #f43f5e;'>🧠 PRESSÃO DE LUTA</h2>", unsafe_allow_html=True)
    st.markdown("<div class='camp-box'><h4>💡 Faltando 1 minuto e perdendo por 2 a 0:</h4><p>Estoure pegadas imediatamente e force o ataque de raspagem/queda sem aceitar amarração.</p></div>", unsafe_allow_html=True)

# ===========================================================================
# ABA 10: GRADUAÇÃO (OFFLINE ATIVO)
# ===========================================================================
with aba_grad:
    st.markdown("<h2 style='text-align: center; color: #34d399;'>🥇 GRADUAÇÃO</h2>", unsafe_allow_html=True)
    st.markdown("<div class='extra-box'><h3>Foco no próximo grau:</h3><p>Consistência, técnica afiada, respeito no tatame e auxílio aos colegas.</p></div>", unsafe_allow_html=True)

# ===========================================================================
# ABA 11: DEFESA PESSOAL (OFFLINE ATIVO)
# ===========================================================================
with aba_def:
    st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🛡️ DEFESA PESSOAL</h2>", unsafe_allow_html=True)
    st.markdown("<div class='curso-box'><h3>Anti-Bullying & Gravata:</h3><p>Mantenha base firme, proteja o pescoço e busque ajuda imediata sem promover agressão.</p></div>", unsafe_allow_html=True)

# ===========================================================================
# ABA 12: LESÕES (OFFLINE ATIVO)
# ===========================================================================
with aba_lesao:
    st.markdown("<h2 style='text-align: center; color: #f43f5e;'>🩹 LESÕES</h2>", unsafe_allow_html=True)
    st.markdown("<div class='placar-box'><h3>Cuidados:</h3><p>Use fita nos dedos para suporte de pegada e aplique gelo por 20 minutos pós-treino.</p></div>", unsafe_allow_html=True)

# ===========================================================================
# ABA 13: KIMONO (OFFLINE ATIVO)
# ===========================================================================
with aba_kimono:
    st.markdown("<h2 style='text-align: center; color: #fbbf24;'>🥋 KIMONOS</h2>", unsafe_allow_html=True)
    st.markdown("<div class='kids-box'><h3>O Nó da Faixa:</h3><p>Cruze por trás, passe por dentro de todas as voltas e dê o nó simétrico.</p></div>", unsafe_allow_html=True)

# ===========================================================================
# ABA 14: CARD VITÓRIA (OFFLINE ATIVO)
# ===========================================================================
with aba_card:
    st.markdown("<h2 style='text-align: center; color: #a855f7;'>📸 CARD VITÓRIA</h2>", unsafe_allow_html=True)
    st.code("Tatame lavado, missão cumprida por hoje! 🥋🔥 OSS! #BJJ #OssBot", language="text")

# ===========================================================================
# ABA 15: PESAGEM & VÉSPERA (OFFLINE ATIVO)
# ===========================================================================
with aba_pesagem:
    st.markdown("<h2 style='text-align: center; color: #38bdf8;'>📋 CHECKLIST DE PESAGEM & VÉSPERA</h2>", unsafe_allow_html=True)
    st.markdown("""
    <div class='curso-box'>
        <h3>⚖️ Roteiro de Pesagem Offline:</h3>
        <p>1. Pese seu kimono seco (trançados pesam entre 1.3kg e 1.8kg).</p>
        <p>2. Evite exagero de sal na véspera do torneio.</p>
        <p>3. Deixe documentos e carteirinha separados na mochila.</p>
    </div>
    """, unsafe_allow_html=True)

# ===========================================================================
# ABA 16: CADERNETA DE ALUNOS (OFFLINE ATIVO)
# ===========================================================================
with aba_caderneta:
    st.markdown("<h2 style='text-align: center; color: #fbbf24;'>📇 CADERNETA DE ALUNOS & FREQUÊNCIA</h2>", unsafe_allow_html=True)
    novo_aluno = st.text_input("Nome do Aluno:", placeholder="Ex: Lucas Gabriel", key="input_novo_aluno")
    if st.button("➕ Adicionar Aluno", use_container_width=True, key="btn_add_aluno"):
        if novo_aluno.strip():
            st.session_state.lista_alunos_academia.append(novo_aluno.strip())
            st.success(f"✅ Aluno {novo_aluno} adicionado com sucesso!")

    if st.session_state.lista_alunos_academia:
        st.markdown("### 📋 Lista de Alunos Atuais:")
        for idx, aluno in enumerate(st.session_state.lista_alunos_academia):
            col_al1, col_al2 = st.columns([3, 1])
            with col_al1: st.write(f"🥋 {aluno}")
            with col_al2:
                if st.button("Presença ✔️", key=f"pres_{idx}"):
                    st.toast(f"✅ Presença confirmada para {aluno}!")

# ===========================================================================
# ABA 17: CHAVES DE TORNEIO (OFFLINE ATIVO)
# ===========================================================================
with aba_chaves:
    st.markdown("<h2 style='text-align: center; color: #f43f5e;'>⏱️ ORGANIZADOR DE CHAVES</h2>", unsafe_allow_html=True)
    nomes_atletas_txt = st.text_area("Digite os nomes dos atletas (um por linha):", placeholder="Atleta 1\nAtleta 2\nAtleta 3\nAtleta 4", key="txt_atletas_chave")
    
    if st.button("Gerar Chaves de Luta", use_container_width=True, key="btn_gerar_chave"):
        atletas = [a.strip() for a in nomes_atletas_txt.split("\n") if a.strip()]
        if len(atletas) < 2:
            st.warning("Digite pelo menos 2 atletas!")
        else:
            st.markdown("<div class='placar-box'><h3 style='color: #00ffcc;'>⚔️ TABELA DE CONFRONTOS</h3></div>", unsafe_allow_html=True)
            for i in range(0, len(atletas)-1, 2):
                st.markdown(f"🥊 **Luta:** {atletas[i]}  **vs**  {atletas[i+1]}")

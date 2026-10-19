import os
import io
import json
import uuid
import hashlib
import tempfile
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# Tenta carregar a API da Groq (IA online)
try:
    from groq import Groq
    tem_groq = True
except ImportError:
    tem_groq = False

# Tenta carregar a biblioteca de voz gTTS (Text-to-Speech)
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
    .offline-badge { background-color: #d97706; color: #ffffff; padding: 5px 12px; border-radius: 8px; font-weight: bold; font-size: 14px; }
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

# Cliente Groq com Tratamento para Modo Offline
groq_api_key = "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"
client = None
modo_offline = False

try:
    if tem_groq:
        client = Groq(api_key=groq_api_key)
    else:
        modo_offline = True
except Exception:
    modo_offline = True

MODELO = "openai/gpt-oss-120b"

# Cabeçalho com Fotos
col_esq, col_centro, col_dir = st.columns([1.2, 2.6, 1.2])
with col_esq:
    st.image("https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=600&auto=format&fit=crop", caption="Técnica e Combate", use_container_width=True)
with col_centro:
    st.markdown("<h1 style='text-align: center; color: #ff4d4d !important;'>🥋 OssBot</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center; color: #00ffcc;'>Usuário: {st.session_state.usuario_atual}</h4>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #aaaaaa;'>O seu Assistente de Jiu-Jitsu</h3>", unsafe_allow_html=True)
    if modo_offline:
        st.markdown("<p style='text-align: center;'><span class='offline-badge'>📡 MODO OFFLINE ATIVO (Placar, Regras e Campeonato Funcionando!)</span></p>", unsafe_allow_html=True)

with col_dir:
    st.image("https://images.unsplash.com/photo-1555597673-b21d5c935865?q=80&w=600&auto=format&fit=crop", caption="Faixa Preta — Tradição", use_container_width=True)

st.divider()

# Abas Principais (Total de 9 Abas)
aba_chat, aba_modo_luta, aba_historico_lutas, aba_nutricao, aba_camp, aba_cursos, aba_kids, aba_drills, aba_pressao = st.tabs([
    "💬 Chat IA", 
    "🤼 Modo Luta (Offline)", 
    "📜 Histórico",
    "🥗 Nutrição",
    "🏆 Campeonato (Offline)",
    "📚 Cursos (Offline)",
    "👶 Aulas Kids",
    "⏱️ Drills & HIIT",
    "🧠 Pressão de Luta"
])

# ===========================================================================
# ABA 1: CHAT COM IA
# ===========================================================================
with aba_chat:
    def gerar_titulo(pergunta, resposta):
        fallback = (pergunta[:40] + "…") if len(pergunta) > 40 else pergunta
        if not client: return fallback
        try:
            r = client.chat.completions.create(
                model=MODELO,
                messages=[
                    {"role": "system", "content": "Crie um título curto de jiu-jitsu, em português, max 6 palavras. Responda SOMENTE com o título, sem aspas."},
                    {"role": "user", "content": f"Pergunta: {pergunta}\n\nResposta: {resposta[:500]}"},
                ],
                temperature=0.3, max_tokens=300,
            )
            titulo = (r.choices[0].message.content or "").strip().split("\n")[0].strip('"\'*# ').rstrip(".")
            return titulo[:60] if titulo else fallback
        except Exception:
            return fallback

    st.markdown("### ⚙️ Escolha o Modo de Atendimento")
    modo_selecionado = st.radio(
        "Como você quer que o OssBot responda?",
        ["🥋 Aluno / Competidor (Treino, técnica e campeonatos)", "👶 Professor / Turma Kids (Didática infantil e aulas)"],
        index=0, key="modo_atendimento"
    )

    if "Aluno / Competidor" in modo_selecionado:
        system_prompt = "Você é o OssBot, assistente especialista em BJJ focado em atletas. Ajude com técnica, estratégias e preparação física/mental. Use termos como OSS, guarda, raspagem."
    else:
        system_prompt = "Você é o OssBot, assistente especialista em BJJ focado em professores e monitores kids. Ajude com dinâmicas divertidas, didática infantil e segurança."

    st.divider()
    st.markdown("### ⚡ Atalhos Inteligentes")
    atalhos_personalizados = gerar_atalhos_inteligentes(st.session_state.conversas)
    cols_atalhos = st.columns(len(atalhos_personalizados))
    for idx, atalho in enumerate(atalhos_personalizados):
        with cols_atalhos[idx]:
            if st.button(f"📌 {atalho}", key=f"atalho_{idx}", use_container_width=True):
                st.session_state.atalho_clicado = f"Quero dicas, técnicas e orientações sobre: {atalho}"

    st.divider()
    col_midia1, col_midia2 = st.columns(2)
    imagem_enviada = None
    with col_midia1:
        tipo_envio = st.radio("Como quer enviar a imagem?", ["Arquivo/Galeria", "Tirar Foto com Câmera"], key="tipo_envio_img")
        if tipo_envio == "Arquivo/Galeria":
            imagem_enviada = st.file_uploader("Escolha imagem de posição:", type=["jpg", "jpeg", "png"])
        else:
            imagem_enviada = st.camera_input("Tire uma foto:")

    with col_midia2:
        st.markdown("#### 🎙️ Gravação de Áudio")
        audio_enviado = st.audio_input("Grave sua voz:", key=f"audio_{st.session_state.audio_key}")
        if audio_enviado is not None and st.button("❌ Limpar áudio"):
            st.session_state.audio_key += 1
            st.rerun()

    st.divider()
    for i, mensagem in enumerate(st.session_state.historico):
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])
            if mensagem["role"] == "assistant" and st.button("🔊 Ouvir resposta", key=f"ouvir_{i}"):
                audio_bytes = gerar_audio(mensagem["content"])
                if audio_bytes: st.audio(audio_bytes, format="audio/mp3")

    texto_para_enviar = None
    pergunta_texto = st.chat_input("Digite sua dúvida (requer internet para IA)...")

    if st.session_state.atalho_clicado:
        texto_para_enviar = st.session_state.atalho_clicado
        st.session_state.atalho_clicado = None

    audio_hash = hashlib.md5(audio_enviado.getvalue()).hexdigest() if audio_enviado is not None else None
    imagem_hash = hashlib.md5(imagem_enviada.getvalue()).hexdigest() if imagem_enviada is not None else None

    def registrar_pergunta(conteudo, texto_titulo):
        st.session_state.historico.append({"role": "user", "content": conteudo})
        if not st.session_state.titulo:
            t = texto_titulo.strip().replace("\n", " ")
            st.session_state.titulo = (t[:40] + "…") if len(t) > 40 else t
        salvar_conversa_atual()

    if pergunta_texto:
        texto_para_enviar = pergunta_texto
        registrar_pergunta(pergunta_texto, pergunta_texto)
        with st.chat_message("user"): st.markdown(pergunta_texto)
    elif texto_para_enviar and not pergunta_texto and st.session_state.historico[-1]["content"] != texto_para_enviar:
        registrar_pergunta(texto_para_enviar, texto_para_enviar)
        with st.chat_message("user"): st.markdown(texto_para_enviar)
    elif audio_enviado is not None and audio_hash != st.session_state.ultimo_audio:
        st.session_state.ultimo_audio = audio_hash
        if client:
            with st.spinner("Transcrevendo áudio com Whisper... 🎧"):
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        tmp_file.write(audio_enviado.getvalue())
                        tmp_path = tmp_file.name
                    with open(tmp_path, "rb") as file_audio:
                        transcription = client.audio.transcriptions.create(file=(tmp_path, file_audio.read()), model="whisper-large-v3-turbo", language="pt", response_format="text")
                    texto_para_enviar = str(transcription).strip()
                    registrar_pergunta(f"🎙️ **Áudio transcrito:** {texto_para_enviar}", texto_para_enviar)
                    with st.chat_message("user"):
                        st.audio(audio_enviado)
                        st.markdown(f"🎙️ **Áudio transcrito:** {texto_para_enviar}")
                except Exception:
                    st.error("Sem conexão com a internet para transcrever áudio.")
                finally:
                    if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)
    elif imagem_enviada is not None and imagem_hash != st.session_state.ultima_imagem:
        st.session_state.ultima_imagem = imagem_hash
        texto_para_enviar = "Analise e me oriente com base na imagem enviada."
        registrar_pergunta("[Imagem enviada]", "Imagem enviada")
        with st.chat_message("user"): st.image(imagem_enviada, caption="Imagem", use_container_width=True)

    if texto_para_enviar:
        if not client:
            st.warning("⚠️ O Chat com IA precisa de conexão com a internet. Use as abas 'Modo Luta', 'Campeonato' ou 'Cursos' que funcionam 100% offline!")
        else:
            with st.chat_message("assistant"):
                with st.spinner("OssBot pensando... OSS! 🥋"):
                    try:
                        mensagens_chat = [{"role": "system", "content": system_prompt}]
                        for h in st.session_state.historico[-20:]:
                            mensagens_chat.append({"role": h["role"], "content": h["content"].replace("🎙️ **Áudio transcrito:** ", "")})
                        res = client.chat.completions.create(model=MODELO, messages=mensagens_chat, temperature=0.7)
                        resposta_texto = res.choices[0].message.content
                        st.markdown(resposta_texto)
                        st.session_state.historico.append({"role": "assistant", "content": resposta_texto})
                        if not st.session_state.titulo_ia:
                            p_perg = next((m["content"].replace("🎙️ **Áudio transcrito:** ", "") for m in st.session_state.historico if m["role"] == "user"), "")
                            st.session_state.titulo = gerar_titulo(p_perg, resposta_texto)
                            st.session_state.titulo_ia = True
                        salvar_conversa_atual()
                        if st.button("🔊 Ouvir resposta", key=f"ouvir_{len(st.session_state.historico)-1}"):
                            ab = gerar_audio(resposta_texto)
                            if ab: st.audio(ab, format="audio/mp3")
                    except Exception:
                        st.warning("Você está offline no momento. O placar e os manuais continuam disponíveis!")

# ===========================================================================
# ABA 2: MODO LUTA (100% OFFLINE)
# ===========================================================================
with aba_modo_luta:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>⏱️ PLACAR & CRONÔMETRO (MODO OFFLINE)</h2>", unsafe_allow_html=True)
    st.caption("✅ Funciona perfeitamente sem internet! Use os botões manuais para pontuar.")
    
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
        if bc1.button("▶️ INICIAR", use_container_width=True): st.session_state.cronometro_rodando = True
        if bc2.button("⏸️ PAUSAR", use_container_width=True): st.session_state.cronometro_rodando = False
        if bc3.button("🔄 ZERAR", use_container_width=True):
            st.session_state.cronometro_rodando = False
            st.session_state.tempo_segundos = minutos_opcao * 60
            st.session_state.pts_a = st.session_state.vant_a = st.session_state.pun_a = 0
            st.session_state.pts_b = st.session_state.vant_b = st.session_state.pun_b = 0

    st.divider()
    st.markdown("### 🎙️ Pontuação por Voz (Requer Internet)")
    audio_luta = st.audio_input("Grave o comando de voz da luta:", key="audio_comando_luta")
    if audio_luta is not None:
        if client:
            hash_luta = hashlib.md5(audio_luta.getvalue()).hexdigest()
            if hash_luta != st.session_state.ultimo_audio_luta:
                st.session_state.ultimo_audio_luta = hash_luta
                with st.spinner("Ouvindo voz... 🎧"):
                    tmp_path = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                            tmp_file.write(audio_luta.getvalue())
                            tmp_path = tmp_file.name
                        with open(tmp_path, "rb") as fa:
                            tr = client.audio.transcriptions.create(file=(tmp_path, fa.read()), model="whisper-large-v3-turbo", language="pt", response_format="text")
                        tz = str(tr).lower().strip()
                        st.success(f"🎙️ **Voz:** '{tz}'")
                        alvo = "a" if ("azul" in tz or "1" in tz or nome_atleta_a.lower() in tz) else "b"
                        if "queda" in tz or "raspagem" in tz or "2" in tz:
                            if alvo == "a": st.session_state.pts_a += 2
                            else: st.session_state.pts_b += 2
                        elif "passagem" in tz or "3" in tz:
                            if alvo == "a": st.session_state.pts_a += 3
                            else: st.session_state.pts_b += 3
                        elif "montada" in tz or "costas" in tz or "4" in tz:
                            if alvo == "a": st.session_state.pts_a += 4
                            else: st.session_state.pts_b += 4
                        elif "vantagem" in tz:
                            if alvo == "a": st.session_state.vant_a += 1
                            else: st.session_state.vant_b += 1
                        elif "punição" in tz:
                            if alvo == "a": st.session_state.pun_a += 1
                            else: st.session_state.pun_b += 1
                    except Exception:
                        st.warning("Comando por voz indisponível offline. Use os botões do placar abaixo!")
                    finally:
                        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)
        else:
            st.info("Comando por voz desativado no modo offline. Pontue usando os botões abaixo:")

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
    if st.button("💾 SALVAR RESULTADO DA LUTA NO HISTÓRICO", use_container_width=True):
        nl = {
            "data": datetime.now().strftime("%d/%m/%Y - %H:%M"),
            "atleta_a": nome_atleta_a, "pts_a": st.session_state.pts_a, "vant_a": st.session_state.vant_a, "pun_a": st.session_state.pun_a,
            "atleta_b": nome_atleta_b, "pts_b": st.session_state.pts_b, "vant_b": st.session_state.vant_b, "pun_b": st.session_state.pun_b,
        }
        st.session_state.historico_lutas.append(nl)
        salvar_dados_usuario(st.session_state.usuario_atual, {"conversas": st.session_state.conversas, "historico_lutas": st.session_state.historico_lutas})
        st.success("✅ Luta salva na memória local!")

# ===========================================================================
# ABA 3: HISTÓRICO DE LUTAS
# ===========================================================================
with aba_historico_lutas:
    st.markdown("### 📜 Lutas Registradas (Offline)")
    if not st.session_state.historico_lutas:
        st.info("Nenhuma luta registrada.")
    else:
        for idx, luta in enumerate(reversed(st.session_state.historico_lutas)):
            with st.expander(f"🥋 Luta {luta['data']} - {luta['atleta_a']} vs {luta['atleta_b']}"):
                col_h1, col_h2 = st.columns(2)
                with col_h1: st.write(f"🔵 **{luta['atleta_a']}**: {luta['pts_a']} Pts | {luta['vant_a']} Vant | {luta['pun_a']} Pun")
                with col_h2: st.write(f"⚪ **{luta['atleta_b']}**: {luta['pts_b']} Pts | {luta['vant_b']} Vant | {luta['pun_b']} Pun")

# ===========================================================================
# ABA 4: NUTRIÇÃO & PESO
# ===========================================================================
with aba_nutricao:
    st.markdown("<h2 style='text-align: center; color: #00ffcc;'>🥗 NUTRIÇÃO & HIDRATAÇÃO</h2>", unsafe_allow_html=True)
    col_n1, col_n2 = st.columns(2)
    with col_n1: peso_atleta = st.number_input("Peso atual (kg):", 30.0, 150.0, 65.0, 0.5, key="nutri_peso")
    with col_n2: horas_treino = st.slider("Horas de treino diário:", 0.5, 4.0, 1.5, 0.5, key="nutri_treino")
    agua_tot = ((peso_atleta * 35) / 1000) + (horas_treino * 0.75)
    st.markdown(f"<div class='nutri-box'><h3 style='color: #00ffcc;'>🥤 Água Ideal:</h3><h2>{agua_tot:.2f} Litros/dia</h2></div>", unsafe_allow_html=True)
    st.divider()
    if st.button("🥗 Pedir Dica Nutricional ao OssBot", key="btn_nutri"):
        if client:
            try:
                res = client.chat.completions.create(model=MODELO, messages=[{"role": "user", "content": f"Dê dicas de nutrição e pré-treino para um atleta de BJJ de {peso_atleta}kg que treina {horas_treino}h por dia."}], temperature=0.7)
                st.markdown(res.choices[0].message.content)
            except Exception:
                st.info("💡 **Dica Nutricional Offline:** Beba 500ml de água 1h antes do treino e coma carboidratos leveis (banana com mel) para ter energia rápida sem pesar no estômago!")
        else:
            st.info("💡 **Dica Nutricional Offline:** Beba 500ml de água 1h antes do treino e coma carboidratos leveis (banana com mel) para ter energia rápida sem pesar no estômago!")

# ===========================================================================
# ABA 5: CAMPEONATO (SUPORTE OFFLINE COMPLETO)
# ===========================================================================
with aba_camp:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>🏆 ESTRATÉGIA DE CAMPEONATO</h2>", unsafe_allow_html=True)
    c_fx = st.selectbox("Faixa:", ["Branca", "Kids", "Azul", "Roxa", "Castanha", "Preta"], key="cp_fx")
    c_est = st.text_input("Estilo / Golpe Favorito:", "Armlock da Guarda", key="cp_est")
    
    if st.button("🚀 Gerar Plano de Luta", key="btn_cp"):
        if client:
            try:
                r = client.chat.completions.create(model=MODELO, messages=[{"role": "user", "content": f"Crie um plano de campeonato para faixa {c_fx} com foco em {c_est}."}], temperature=0.7)
                st.markdown(r.choices[0].message.content)
            except Exception:
                st.markdown(f"""
                <div class='camp-box'>
                    <h3 style='color: #00ffcc;'>📡 GUIA OFFLINE DE LUTA PARA CAMPEONATO</h3>
                    <p><b>Faixa:</b> {c_fx} | <b>Especialidade:</b> {c_est}</p>
                    <hr>
                    <h4>1. Primeiros 30 Segundos:</h4>
                    <ul>
                        <li>Faça a pegada firme na gola/manga primeiro para evitar ser surpreendido.</li>
                        <li>Se o seu foco é <b>{c_est}</b>, imponha seu ritmo logo no início antes do adversário pontuar.</li>
                    </ul>
                    <h4>2. Estratégia de Pontos:</h4>
                    <ul>
                        <li><b>Queda/Raspagem (+2 Pts):</b> Garanta os primeiros pontos antes de arriscar a finalização.</li>
                        <li><b>Passagem de Guarda (+3 Pts):</b> Mantenha a pressão de ombro por 3 segundos para validar o placar.</li>
                    </ul>
                    <h4>3. Controle de Ansiedade:</h4>
                    <ul>
                        <li>Faça 3 respirações profundas no aquecimento antes de ser chamado para a área de luta.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class='camp-box'>
                <h3 style='color: #00ffcc;'>📡 GUIA OFFLINE DE LUTA PARA CAMPEONATO</h3>
                <p><b>Faixa:</b> {c_fx} | <b>Especialidade:</b> {c_est}</p>
                <hr>
                <h4>1. Primeiros 30 Segundos:</h4>
                <ul>
                    <li>Faça a pegada firme na gola/manga primeiro para evitar ser surpreendido.</li>
                    <li>Se o seu foco é <b>{c_est}</b>, imponha seu ritmo logo no início antes do adversário pontuar.</li>
                </ul>
                <h4>2. Estratégia de Pontos:</h4>
                <ul>
                    <li><b>Queda/Raspagem (+2 Pts):</b> Garanta os primeiros pontos antes de arriscar a finalização.</li>
                    <li><b>Passagem de Guarda (+3 Pts):</b> Mantenha a pressão de ombro por 3 segundos para validar o placar.</li>
                </ul>
                <h4>3. Controle de Ansiedade:</h4>
                <ul>
                    <li>Faça 3 respirações profundas no aquecimento antes de ser chamado para a área de luta.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

# ===========================================================================
# ABA 6: CURSOS (SUPORTE OFFLINE COMPLETO)
# ===========================================================================
with aba_cursos:
    st.markdown("<h2 style='text-align: center; color: #38bdf8;'>📚 CURSOS & REGRAS (MODO OFFLINE)</h2>", unsafe_allow_html=True)
    txt_c = st.text_area("Cole o texto do curso ou dúvida de regra:", placeholder="Ex: Quantos pontos vale a queda?", key="txt_curso")
    
    if st.button("🧠 Descomplicar Curso", key="btn_curs"):
        if txt_c and client:
            try:
                r = client.chat.completions.create(model=MODELO, messages=[{"role": "user", "content": f"Explique de forma simples este conteúdo de BJJ: {txt_c}"}], temperature=0.7)
                st.markdown(r.choices[0].message.content)
            except Exception:
                st.markdown("### 📜 MANUAL DE REGRAS RÁPIDO (OFFLINE):")
                st.markdown("""
                * **2 PONTOS:** Queda, Raspagem e Joelho na Barriga.
                * **3 PONTOS:** Passagem de Guarda.
                * **4 PONTOS:** Montada, Montada pelas Costas e Pegada de Costas com dois ganchos.
                * **VANTAGENS:** Quase-queda, quase-raspagem ou tentativa real de finalização em que o adversário teve que se defender ativamente.
                """)
        else:
            st.markdown("### 📜 MANUAL DE REGRAS RÁPIDO (OFFLINE):")
            st.markdown("""
            * **2 PONTOS:** Queda, Raspagem e Joelho na Barriga.
            * **3 PONTOS:** Passagem de Guarda.
            * **4 PONTOS:** Montada, Montada pelas Costas e Pegada de Costas com dois ganchos.
            * **VANTAGENS:** Quase-queda, quase-raspagem ou tentativa real de finalização em que o adversário teve que se defender ativamente.
            """)

# ===========================================================================
# ABA 7: AULAS KIDS
# ===========================================================================
with aba_kids:
    st.markdown("<h2 style='text-align: center; color: #fbbf24;'>👶 GERADOR DE PLANO DE AULA & DINÂMICAS KIDS</h2>", unsafe_allow_html=True)
    faixa_etaria = st.selectbox("Faixa Etária da Turma Kids:", ["Mubarak / Tiny Kids (4 a 6 anos)", "Infantil (7 a 10 anos)", "Infanto-Juvenil (11 a 14 anos)"], key="kids_idade")
    tema_aula = st.text_input("Tema Técnico da Aula:", value="Quedas Seguras e Defesa Pessoal", key="kids_tema")
    duracao_aula = st.selectbox("Duração da Aula:", ["45 minutos", "60 minutos (1 hora)"], key="kids_tempo")

    if st.button("🚀 Gerar Plano de Aula Kids Completo", use_container_width=True, key="btn_gerar_kids"):
        if client:
            try:
                p_kids = f"Você é o OssBot especialista em pedagogia infantil de Jiu-Jitsu. Crie um plano de aula lúdico para {faixa_etaria}, tema {tema_aula}, tempo {duracao_aula}."
                res = client.chat.completions.create(model=MODELO, messages=[{"role": "user", "content": p_kids}], temperature=0.7)
                txt_k = res.choices[0].message.content
                st.markdown("<div class='kids-box'><h3 style='color: #fbbf24;'>🧸 Plano de Aula Kids Pronto!</h3></div>", unsafe_allow_html=True)
                st.markdown(txt_k)
            except Exception:
                st.info("🧸 **Brincadeira Kids Offline - Pega-Pega do Guardeiro:** As crianças tentam passar a guarda do professor sem deixar serem agarradas pelos pés/canelas. Desenvolve agilidade e base!")
        else:
            st.info("🧸 **Brincadeira Kids Offline - Pega-Pega do Guardeiro:** As crianças tentam passar a guarda do professor sem deixar serem agarradas pelos pés/canelas. Desenvolve agilidade e base!")

# ===========================================================================
# ABA 8: DRILLS & HIIT (100% OFFLINE)
# ===========================================================================
with aba_drills:
    st.markdown("<h2 style='text-align: center; color: #34d399;'>⏱️ CRONÔMETRO DE DRILLS & INTERVALOS (HIIT)</h2>", unsafe_allow_html=True)
    st.caption("✅ Funciona 100% Offline!")

    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1: tempo_acao = st.number_input("Tempo de Ação (segundos):", 10, 120, 30, 5, key="drill_acao")
    with col_d2: tempo_descanso = st.number_input("Tempo de Descanso (segundos):", 5, 60, 10, 5, key="drill_pausa")
    with col_d3: num_rounds = st.number_input("Número de Rounds:", 1, 30, 8, 1, key="drill_rounds")

    st.info(f"💡 Configuração atual: {num_rounds} rounds de {tempo_acao}s de ação por {tempo_descanso}s de descanso.")
    if st.button("▶️ INICIAR TREINO DE DRILLS", use_container_width=True, key="btn_iniciar_drill"):
        st.success("✅ Treino de Drills configurado! Prepare-se para suar no tatame!")

# ===========================================================================
# ABA 9: PRESSÃO DE LUTA
# ===========================================================================
with aba_pressao:
    st.markdown("<h2 style='text-align: center; color: #f43f5e;'>🧠 SIMULADOR DE SITUAÇÕES & PRESSÃO DE LUTA</h2>", unsafe_allow_html=True)
    situacao_escolhida = st.selectbox(
        "Escolha o cenário de pressão:",
        [
            "Faltam 45 segundos, estou perdendo por 2 a 0 e o adversário está amarrando na guarda fechada.",
            "Acabei de raspar, fiz 2 pontos, faltam 30 segundos e o oponente é muito forte por baixo.",
            "O adversário me derrubou nos primeiros 10 segundos de luta. Como manter a calma e recuperar?"
        ],
        key="sit_escolhida"
    )

    if st.button("🎯 RESOLVER CENÁRIO COM O OSSBOT", use_container_width=True, key="btn_resolver_sit"):
        if client:
            try:
                p_sit = f"Atue como estrategista de BJJ. Diga exatamente a decisão perfeita para: '{situacao_escolhida}'."
                res = client.chat.completions.create(model=MODELO, messages=[{"role": "user", "content": p_sit}], temperature=0.7)
                st.markdown(res.choices[0].message.content)
            except Exception:
                st.info("💡 **Dica Offline para Pressão:** Se faltar menos de 1 minuto e estiver perdendo, estoure as pegadas imediatamente e force o ataque de raspagem/queda sem aceitar a amarração!")
        else:
            st.info("💡 **Dica Offline para Pressão:** Se faltar menos de 1 minuto e estiver perdendo, estoure as pegadas imediatamente e force o ataque de raspagem/queda sem aceitar a amarração!")

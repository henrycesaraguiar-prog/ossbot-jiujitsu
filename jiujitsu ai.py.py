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
from gtts import gTTS

# ---------------------------------------------------------------------------
# Funções de áudio
# ---------------------------------------------------------------------------
def gerar_audio(texto):
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
# Gerenciamento de histórico por Usuário (Nome e Sobrenome)
# ---------------------------------------------------------------------------
PASTA_DADOS = os.path.dirname(os.path.abspath(__file__))

def obter_caminho_usuario(nome_usuario):
    nome_limpo = "".join(c if c.isalnum() else "_" for c in nome_usuario.lower()).strip("_")
    return os.path.join(PASTA_DADOS, f"usuario_{nome_limpo}.json")

def carregar_conversas_usuario(nome_usuario):
    caminho = obter_caminho_usuario(nome_usuario)
    try:
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def salvar_conversas_usuario(nome_usuario, conversas):
    caminho = obter_caminho_usuario(nome_usuario)
    try:
        tmp = caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(conversas, f, ensure_ascii=False, indent=2)
        os.replace(tmp, caminho)
    except Exception as e:
        st.warning(f"Não consegui salvar o histórico: {e}")

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
    salvar_conversas_usuario(st.session_state.usuario_atual, st.session_state.conversas)

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
        salvar_conversas_usuario(st.session_state.usuario_atual, st.session_state.conversas)
    if cid == st.session_state.conversa_id:
        iniciar_nova_conversa()

# Configuração da página do Streamlit
st.set_page_config(
    page_title="OssBot - Assistente de Jiu-Jitsu",
    page_icon="🥋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização visual: Dark Mode profissional
st.markdown("""
    <style>
    .stApp {
        background-color: #121212;
        color: #e0e0e0;
    }
    .main {
        background-color: #121212;
    }
    h1, h2, h3, h4, h5, h6, span, label {
        color: #ffffff !important;
    }
    p {
        color: #ff4d4d !important;
    }
    div[data-testid="stFileUploader"], div[data-testid="stAudioInput"], div[data-testid="stCameraInput"] {
        background-color: #2b2b2b !important;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #444444;
    }
    div[data-testid="stFileUploader"] section, div[data-testid="stFileUploader"] span, div[data-testid="stFileUploader"] small, div[data-testid="stFileUploader"] div {
        color: #ff4d4d !important;
    }
    div[data-testid="stAudioInput"] label, div[data-testid="stCameraInput"] label {
        color: #ff4d4d !important;
    }
    div[data-testid="stChatInput"] {
        background-color: #f0f0f0 !important;
        border-radius: 10px;
        border: 2px solid #ff4d4d !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #000000 !important;
        background-color: #f0f0f0 !important;
        font-weight: bold !important;
        font-size: 16px !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder {
        color: #555555 !important;
    }
    .stButton button {
        border-radius: 10px;
        font-weight: bold;
        background-color: #333333;
        color: #ff4d4d;
        border: 1px solid #ff4d4d;
    }
    .stButton button:hover {
        background-color: #555555;
        color: #ffffff;
    }
    div[data-testid="stChatMessage"] p,
    div[data-testid="stChatMessage"] li,
    div[data-testid="stChatMessage"] td,
    div[data-testid="stChatMessage"] th,
    div[data-testid="stChatMessage"] span,
    div[data-testid="stChatMessage"] strong,
    div[data-testid="stChatMessage"] h1,
    div[data-testid="stChatMessage"] h2,
    div[data-testid="stChatMessage"] h3,
    div[data-testid="stChatMessage"] h4 {
        color: #ffffff !important;
    }
    .placar-box {
        background-color: #1e1e1e;
        border: 2px solid #ff4d4d;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
    }
    .placar-numero {
        font-size: 50px;
        font-weight: bold;
        color: #00ffcc;
    }
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
    position: fixed;
    right: 20px;
    bottom: 110px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    z-index: 999999;
  }
  #botoes-rolagem button {
    width: 64px;
    height: 64px;
    font-size: 28px;
    font-weight: bold;
    color: #ffffff;
    background-color: #e60000;
    border: 2px solid #ffffff;
    border-radius: 50%;
    cursor: pointer;
    box-shadow: 0 4px 10px rgba(0,0,0,0.6);
  }
  #botoes-rolagem button:hover {
    background-color: #ff4d4d;
  }
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
  doc.body.scrollTop = (direcao === 'cima') ? 0 : doc.body.scrollHeight;
}

const caixa = doc.createElement('div');
caixa.id = 'botoes-rolagem';

const subir = doc.createElement('button');
subir.type = 'button';
subir.title = 'Subir';
subir.textContent = '▲';
subir.addEventListener('click', function() { rolar('cima'); });

const descer = doc.createElement('button');
descer.type = 'button';
descer.title = 'Descer';
descer.textContent = '▼';
descer.addEventListener('click', function() { rolar('baixo'); });

caixa.appendChild(subir);
caixa.appendChild(descer);
doc.body.appendChild(caixa);
</script>
""", height=0)

# ---------------------------------------------------------------------------
# Tela de Identificação / Login por Nome e Sobrenome na Barra Lateral
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
        st.session_state.conversas = carregar_conversas_usuario(usuario_input)
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

    busca = st.text_input(
        "🔍 Pesquisar",
        placeholder="Ex.: guarda",
        key="busca_conversas",
    ).strip().lower()

    st.divider()

    conversas = st.session_state.conversas
    ids = sorted(conversas, key=lambda c: conversas[c].get("atualizada", ""), reverse=True)

    mostradas = 0
    for cid in ids:
        conv = conversas[cid]
        if busca:
            texto_total = conv["titulo"].lower() + " " + " ".join(
                m["content"].lower() for m in conv["mensagens"]
            )
            if busca not in texto_total:
                continue

        mostradas += 1
        atual = cid == st.session_state.conversa_id
        col_a, col_b = st.columns([5, 1])
        with col_a:
            st.button(
                ("▶ " if atual else "") + conv["titulo"],
                key=f"abrir_{cid}",
                on_click=abrir_conversa,
                args=(cid,),
            )
        with col_b:
            st.button(
                "🗑️",
                key=f"apagar_{cid}",
                on_click=apagar_conversa,
                args=(cid,),
                help="Apagar esta conversa",
            )

    if mostradas == 0:
        if busca:
            st.caption("Nenhuma conversa encontrada para essa pesquisa.")
        else:
            st.caption("Suas conversas vão aparecer aqui. 🥋")

# Inicialização de estados auxiliares
if "audio_key" not in st.session_state:
    st.session_state.audio_key = 0
if "ultimo_audio" not in st.session_state:
    st.session_state.ultimo_audio = None
if "ultima_imagem" not in st.session_state:
    st.session_state.ultima_imagem = None

# Inicialização do Modo Luta
if "pts_a" not in st.session_state:
    st.session_state.pts_a = 0
if "vant_a" not in st.session_state:
    st.session_state.vant_a = 0
if "pun_a" not in st.session_state:
    st.session_state.pun_a = 0

if "pts_b" not in st.session_state:
    st.session_state.pts_b = 0
if "vant_b" not in st.session_state:
    st.session_state.vant_b = 0
if "pun_b" not in st.session_state:
    st.session_state.pun_b = 0

if "tempo_segundos" not in st.session_state:
    st.session_state.tempo_segundos = 300
if "cronometro_rodando" not in st.session_state:
    st.session_state.cronometro_rodando = False
if "ultimo_audio_luta" not in st.session_state:
    st.session_state.ultimo_audio_luta = None

# Cliente da API Groq
groq_api_key = "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"
client = None
try:
    client = Groq(api_key=groq_api_key)
except Exception as e:
    st.error(f"Erro ao inicializar o cliente Groq: {e}")

MODELO = "openai/gpt-oss-120b"

# Layout do cabeçalho
col_esq, col_centro, col_dir = st.columns([1.2, 2.6, 1.2])

with col_esq:
    st.image("https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=600&auto=format&fit=crop", caption="Técnica e Combate", use_container_width=True)

with col_centro:
    st.markdown("<h1 style='text-align: center; color: #ff4d4d !important;'>🥋 OssBot</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center; color: #00ffcc;'>Usuário: {st.session_state.usuario_atual}</h4>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #aaaaaa;'>O seu Assistente de Jiu-Jitsu</h3>", unsafe_allow_html=True)

with col_dir:
    st.image("https://images.unsplash.com/photo-1555597673-b21d5c935865?q=80&w=600&auto=format&fit=crop", caption="Faixa Preta — Tradição", use_container_width=True)

st.divider()

# Abas Principais
aba_chat, aba_modo_luta = st.tabs(["💬 Chat com IA", "🤼 MODO LUTA (Placar, Tempo & Voz)"])

# ===========================================================================
# ABA 2: MODO LUTA (Cronômetro 1-10 min + Placar Manual + Áudio)
# ===========================================================================
with aba_modo_luta:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>⏱️ PLACAR, CRONÔMETRO E VOZ DA LUTA</h2>", unsafe_allow_html=True)
    
    col_luta1, col_luta2 = st.columns(2)
    
    with col_luta1:
        nome_atleta_a = st.text_input("🔵 Atleta 1 (Azul / Preto):", value="Atleta Azul", key="nome_atleta_a")
    with col_luta2:
        nome_atleta_b = st.text_input("⚪ Atleta 2 (Branco):", value="Atleta Branco", key="nome_atleta_b")
        
    st.divider()
    
    # Seção do Cronômetro e Seletor de Tempo (1 a 10 minutos)
    col_tempo1, col_tempo2, col_tempo3 = st.columns([1, 2, 1])
    
    with col_tempo2:
        st.markdown("<h3 style='text-align: center;'>⏱️ Tempo de Luta</h3>", unsafe_allow_html=True)
        
        minutos_opcao = st.selectbox(
            "Escolha o tempo do Rola (de 1 a 10 minutos):",
            [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            index=4, # Padrão em 5 minutos
            key="select_tempo"
        )
        
        if not st.session_state.cronometro_rodando and st.session_state.tempo_segundos == 300 and minutos_opcao != 5:
            st.session_state.tempo_segundos = minutos_opcao * 60

        mins = st.session_state.tempo_segundos // 60
        segs = st.session_state.tempo_segundos % 60
        
        st.markdown(f"<h1 style='text-align: center; font-size: 70px; color: #ff4d4d;'>{mins:02d}:{segs:02d}</h1>", unsafe_allow_html=True)
        
        btn_c1, btn_c2, btn_c3 = st.columns(3)
        with btn_c1:
            if st.button("▶️ INICIAR", use_container_width=True):
                st.session_state.cronometro_rodando = True
        with btn_c2:
            if st.button("⏸️ PAUSAR", use_container_width=True):
                st.session_state.cronometro_rodando = False
        with btn_c3:
            if st.button("🔄 ZERAR", use_container_width=True):
                st.session_state.cronometro_rodando = False
                st.session_state.tempo_segundos = minutos_opcao * 60
                st.session_state.pts_a = 0
                st.session_state.vant_a = 0
                st.session_state.pun_a = 0
                st.session_state.pts_b = 0
                st.session_state.vant_b = 0
                st.session_state.pun_b = 0

    st.divider()

    # Marcador de Áudio para Pontuação (Opcional)
    st.markdown("### 🎙️ Ajuda por Voz (Opcional)")
    st.info("💡 **Quer usar a voz?** Fale o golpe e o atleta: Exemplo: *'Queda do Atleta Azul'*, *'Passagem de guarda do Atleta 2'*, etc. Ou use os botões abaixo!")
    
    audio_luta = st.audio_input("Clique para gravar o comando de voz da luta:", key="audio_comando_luta")
    
    if audio_luta is not None and client:
        hash_luta = hashlib.md5(audio_luta.getvalue()).hexdigest()
        if hash_luta != st.session_state.ultimo_audio_luta:
            st.session_state.ultimo_audio_luta = hash_luta
            with st.spinner("O OssBot está ouvindo a pontuação por voz... 🎧"):
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        tmp_file.write(audio_luta.getvalue())
                        tmp_path = tmp_file.name

                    with open(tmp_path, "rb") as file_audio:
                        transcription = client.audio.transcriptions.create(
                            file=(tmp_path, file_audio.read()),
                            model="whisper-large-v3-turbo",
                            language="pt",
                            response_format="text"
                        )

                    texto_voz = str(transcription).lower().strip()
                    st.success(f"🎙️ **Voz identificada:** '{texto_voz}'")

                    atleta_alvo = "a" if ("azul" in texto_voz or "atleta 1" in texto_voz or "um" in texto_voz or nome_atleta_a.lower() in texto_voz) else "b"
                    
                    if "queda" in texto_voz or "raspagem" in texto_voz or "joelho" in texto_voz or "2 pontos" in texto_voz or "dois pontos" in texto_voz:
                        if atleta_alvo == "a": st.session_state.pts_a += 2
                        else: st.session_state.pts_b += 2
                        st.toast("✅ +2 Pontos adicionados!")
                        
                    elif "passagem" in texto_voz or "passou" in texto_voz or "3 pontos" in texto_voz or "três pontos" in texto_voz:
                        if atleta_alvo == "a": st.session_state.pts_a += 3
                        else: st.session_state.pts_b += 3
                        st.toast("✅ +3 Pontos adicionados!")
                        
                    elif "montada" in texto_voz or "costas" in texto_voz or "pega de costas" in texto_voz or "4 pontos" in texto_voz or "quatro pontos" in texto_voz:
                        if atleta_alvo == "a": st.session_state.pts_a += 4
                        else: st.session_state.pts_b += 4
                        st.toast("✅ +4 Pontos adicionados!")
                        
                    elif "vantagem" in texto_voz:
                        if atleta_alvo == "a": st.session_state.vant_a += 1
                        else: st.session_state.vant_b += 1
                        st.toast("✅ +1 Vantagem adicionada!")
                        
                    elif "punição" in texto_voz or "falta" in texto_voz:
                        if atleta_alvo == "a": st.session_state.pun_a += 1
                        else: st.session_state.pun_b += 1
                        st.toast("⚠️ +1 Punição adicionada!")

                except Exception as e:
                    st.error(f"Erro ao processar áudio da luta: {e}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)

    st.divider()

    # Placar Manual (Botões na mão para pontuar livremente)
    col_p1, col_p2 = st.columns(2)
    
    with col_p1:
        st.markdown(f"<div class='placar-box'><h2 style='color: #4da6ff;'>🔵 {nome_atleta_a}</h2>"
                    f"<div class='placar-numero'>{st.session_state.pts_a} Pts</div>"
                    f"<p style='color: #00ffcc;'>Vantagens: {st.session_state.vant_a} | Punições: {st.session_state.pun_a}</p></div>", unsafe_allow_html=True)
        
        st.markdown("#### Marcar na mão:")
        ba1, ba2, ba3, ba4 = st.columns(4)
        if ba1.button("+2 Pts", key="a_2"): st.session_state.pts_a += 2
        if ba2.button("+3 Pts", key="a_3"): st.session_state.pts_a += 3
        if ba3.button("+4 Pts", key="a_4"): st.session_state.pts_a += 4
        if ba4.button("+ Vant", key="a_v"): st.session_state.vant_a += 1
        
        ba5, ba6 = st.columns(2)
        if ba5.button("+ Punição", key="a_p"): st.session_state.pun_a += 1
        if ba6.button("➖ Desfazer Ponto", key="a_sub"): st.session_state.pts_a = max(0, st.session_state.pts_a - 1)

    with col_p2:
        st.markdown(f"<div class='placar-box'><h2 style='color: #ffffff;'>⚪ {nome_atleta_b}</h2>"
                    f"<div class='placar-numero'>{st.session_state.pts_b} Pts</div>"
                    f"<p style='color: #00ffcc;'>Vantagens: {st.session_state.vant_b} | Punições: {st.session_state.pun_b}</p></div>", unsafe_allow_html=True)
        
        st.markdown("#### Marcar na mão:")
        bb1, bb2, bb3, bb4 = st.columns(4)
        if bb1.button("+2 Pts", key="b_2"): st.session_state.pts_b += 2
        if bb2.button("+3 Pts", key="b_3"): st.session_state.pts_b += 3
        if bb3.button("+4 Pts", key="b_4"): st.session_state.pts_b += 4
        if bb4.button("+ Vant", key="b_v"): st.session_state.vant_b += 1
        
        bb5, bb6 = st.columns(2)
        if bb5.button("+ Punição", key="b_p"): st.session_state.pun_b += 1
        if bb6.button("➖ Desfazer Ponto", key="b_sub"): st.session_state.pts_b = max(0, st.session_state.pts_b - 1)

    st.divider()
    if st.button("🔄 ZERAR PLACAR DA LUTA COMPLETO", use_container_width=True):
        st.session_state.pts_a = 0
        st.session_state.vant_a = 0
        st.session_state.pun_a = 0
        st.session_state.pts_b = 0
        st.session_state.vant_b = 0
        st.session_state.pun_b = 0
        st.session_state.tempo_segundos = minutos_opcao * 60
        st.session_state.cronometro_rodando = False
        st.rerun()


# ===========================================================================
# ABA 1: CHAT COM IA
# ===========================================================================
with aba_chat:
    def gerar_titulo(pergunta, resposta):
        fallback = (pergunta[:40] + "…") if len(pergunta) > 40 else pergunta
        if not client:
            return fallback
        try:
            r = client.chat.completions.create(
                model=MODELO,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Crie um título curto para esta conversa de jiu-jitsu, em português, "
                            "no formato 'Tema: resumo', com no máximo 6 palavras no total. "
                            "O 'Tema' é a palavra-chave principal (ex.: Fuga, Raspagem, Kids, Campeonato). "
                            "Responda SOMENTE com o título, sem aspas e sem ponto final."
                        ),
                    },
                    {"role": "user", "content": f"Pergunta: {pergunta}\n\nResposta: {resposta[:500]}"},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            titulo = (r.choices[0].message.content or "").strip().split("\n")[0]
            titulo = titulo.strip('"\'*# ').rstrip(".")
            if not titulo:
                return fallback
            return titulo[:60]
        except Exception:
            return fallback

    # Seleção de Modo de Resposta
    st.markdown("### ⚙️ Escolha o Modo de Atendimento")
    modo_selecionado = st.radio(
        "Como você quer que o OssBot responda a sua próxima pergunta?",
        ["🥋 Aluno / Competidor (Foco em treino, técnica e campeonatos)", 
         "👶 Professor / Turma Kids (Foco em didática infantil, aulas e dinâmicas)"],
        index=0,
        key="modo_atendimento"
    )

    if "Aluno / Competidor" in modo_selecionado:
        system_prompt = (
            "Você é o OssBot, um assistente especialista em Jiu-Jitsu brasileiro (BJJ) focado em atletas e alunos praticantes. "
            "Ajude o usuário com detalhes técnicos avançados, ajustes de posições, estratégias de luta, preparação física e mental "
            "para campeonatos. Use termos corretos do jiu-jitsu (OSS, guarda, raspagem, finalização, faixa) e mantenha um tom motivador e técnico."
        )
    else:
        system_prompt = (
            "Você é o OssBot, um assistente especialista em Jiu-Jitsu brasileiro (BJJ) focado em auxiliar professores, monitores "
            "e auxiliares nas turmas kids (infantis). Ajude com dinâmicas de treino, didática divertida para crianças, segurança no tatame "
            "e progressões pedagógicas lúdicas. Use termos corretos do jiu-jitsu (OSS, professor, faixa) e mantenha um tom motivador e seguro."
        )

    st.divider()

    st.markdown("### 📥 Envio de Mídia e Captura")
    col_midia1, col_midia2 = st.columns(2)
    imagem_enviada = None

    with col_midia1:
        tipo_envio = st.radio("Como quer enviar a imagem?", ["Arquivo/Galeria", "Tirar Foto com Câmera"], key="tipo_envio_img")
        if tipo_envio == "Arquivo/Galeria":
            imagem_enviada = st.file_uploader("Escolha uma imagem de posição ou técnica:", type=["jpg", "jpeg", "png"])
        else:
            imagem_enviada = st.camera_input("Tire uma foto agora:")

    with col_midia2:
        st.markdown("#### 🎙️ Gravação de Áudio")
        st.info("Utilize a ferramenta de áudio para ditar sua dúvida ou comando para a IA.")
        audio_enviado = st.audio_input("Grave sua voz:", key=f"audio_{st.session_state.audio_key}")
        if audio_enviado is not None:
            if st.button("❌ Limpar áudio"):
                st.session_state.audio_key += 1
                st.rerun()

    st.divider()

    for i, mensagem in enumerate(st.session_state.historico):
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])
            if mensagem["role"] == "assistant":
                if st.button("🔊 Ouvir resposta", key=f"ouvir_{i}"):
                    try:
                        st.audio(gerar_audio(mensagem["content"]), format="audio/mp3")
                    except Exception as e:
                        st.error(f"Erro ao gerar o áudio: {e}")

    texto_para_enviar = None
    pergunta_texto = st.chat_input("Digite sua dúvida técnica, pedido de dinâmica kids ou estratégia...")

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
        with st.chat_message("user"):
            st.markdown(pergunta_texto)

    elif audio_enviado is not None and audio_hash != st.session_state.ultimo_audio:
        st.session_state.ultimo_audio = audio_hash
        if client:
            with st.spinner("Ouvindo e transcrevendo seu áudio com o Whisper... 🎧"):
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        tmp_file.write(audio_enviado.getvalue())
                        tmp_path = tmp_file.name

                    with open(tmp_path, "rb") as file_audio:
                        transcription = client.audio.transcriptions.create(
                            file=(tmp_path, file_audio.read()),
                            model="whisper-large-v3-turbo",
                            language="pt",
                            response_format="text"
                        )

                    texto_para_enviar = str(transcription).strip()
                    registrar_pergunta(f"🎙️ **Áudio transcrito:** {texto_para_enviar}", texto_para_enviar)
                    with st.chat_message("user"):
                        st.audio(audio_enviado)
                        st.markdown(f"🎙️ **Áudio transcrito:** {texto_para_enviar}")

                except Exception as e:
                    st.error(f"Erro ao transcrever o áudio: {e}")
                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)

    elif imagem_enviada is not None and imagem_hash != st.session_state.ultima_imagem:
        st.session_state.ultima_imagem = imagem_hash
        texto_para_enviar = "Analise e me oriente com base na imagem que enviei."
        registrar_pergunta("[Imagem enviada pelo usuário]", "Imagem enviada")
        with st.chat_message("user"):
            st.image(imagem_enviada, caption="Imagem enviada", use_container_width=True)

    if texto_para_enviar:
        if not client:
            st.error("Erro na chave de API da Groq.")
        else:
            with st.chat_message("assistant"):
                with st.spinner(f"O OssBot está preparando a resposta ({'Competidor' if 'Aluno' in modo_selecionado else 'Kids'})... OSS! 🥋"):
                    try:
                        mensagens_chat = [{"role": "system", "content": system_prompt}]
                        for h in st.session_state.historico[-20:]:
                            conteudo_limp = h["content"].replace("🎙️ **Áudio transcrito:** ", "")
                            mensagens_chat.append({"role": h["role"], "content": conteudo_limp})

                        chat_completion = client.chat.completions.create(
                            model=MODELO,
                            messages=mensagens_chat,
                            temperature=0.7,
                        )

                        resposta_texto = chat_completion.choices[0].message.content
                        st.markdown(resposta_texto)
                        st.session_state.historico.append({"role": "assistant", "content": resposta_texto})

                        if not st.session_state.titulo_ia:
                            primeira_pergunta = next(
                                (
                                    m["content"].replace("🎙️ **Áudio transcrito:** ", "")
                                    for m in st.session_state.historico
                                    if m["role"] == "user"
                                ),
                                "",
                            )
                            st.session_state.titulo = gerar_titulo(primeira_pergunta, resposta_texto)
                            st.session_state.titulo_ia = True

                        salvar_conversa_atual()

                        if st.button("🔊 Ouvir resposta", key=f"ouvir_{len(st.session_state.historico) - 1}"):
                            try:
                                st.audio(gerar_audio(resposta_texto), format="audio/mp3")
                            except Exception as e:
                                st.error(f"Erro ao gerar o áudio: {e}")
                    except Exception as e:
                        st.error(f"Erro ao conectar com a Groq: {e}")

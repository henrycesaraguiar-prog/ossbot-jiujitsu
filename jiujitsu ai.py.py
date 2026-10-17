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

SAUDACAO = (
    "Olá, Henry! OSS! 🥋 Como posso te ajudar hoje? Posso criar um cronograma de aula, "
    "montar uma dinâmica para a turma kids, tirar uma dúvida técnica ou preparar uma "
    "estratégia para campeonato."
)

def iniciar_nova_conversa():
    st.session_state.historico = [{"role": "assistant", "content": SAUDACAO}]

# Configuração da página do Streamlit
st.set_page_config(
    page_title="OssBot - Assistente de Jiu-Jitsu",
    page_icon="🥋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização visual: Dark Mode profissional com inputs legíveis
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

# Estado inicial da sessão individual
if "historico" not in st.session_state:
    iniciar_nova_conversa()
if "audio_key" not in st.session_state:
    st.session_state.audio_key = 0
if "ultimo_audio" not in st.session_state:
    st.session_state.ultimo_audio = None
if "ultima_imagem" not in st.session_state:
    st.session_state.ultima_imagem = None

# Layout em colunas
col_esq, col_centro, col_dir = st.columns([1.2, 2.6, 1.2])

with col_esq:
    st.image("https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=600&auto=format&fit=crop", caption="Técnica e Combate", use_container_width=True)

with col_centro:
    st.markdown("<h1 style='text-align: center; color: #ff4d4d !important;'>🥋 OssBot</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #aaaaaa;'>O seu Assistente de Jiu-Jitsu</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #ff4d4d !important;'>Focado em turmas kids, dinâmicas de treino, preparação e dúvidas técnicas avançadas.</p>", unsafe_allow_html=True)

with col_dir:
    st.image("https://images.unsplash.com/photo-1555597673-b21d5c935865?q=80&w=600&auto=format&fit=crop", caption="Faixa Preta — Tradição", use_container_width=True)

st.divider()

groq_api_key = "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"

client = None
try:
    client = Groq(api_key=groq_api_key)
except Exception as e:
    st.error(f"Erro ao inicializar o cliente Groq: {e}")

system_prompt = (
    "Você é o OssBot, um assistente especialista em Jiu-Jitsu brasileiro (BJJ), com foco especial em "
    "auxiliar professores e monitores nas turmas kids (infantis), dinâmicas de treino, didática para crianças, "
    "técnicas de solo e de pé, além de estratégias para campeonatos. Use termos corretos do jiu-jitsu (como OSS, guarda, "
    "raspagem, finalização, professor, faixa) e mantenha sempre um tom motivador, seguro e profissional."
)

MODELO = "openai/gpt-oss-120b"

st.markdown("### 📥 Envio de Mídia e Captura")
col_midia1, col_midia2 = st.columns(2)
imagem_enviada = None

with col_midia1:
    tipo_envio = st.radio("Como quer enviar a imagem?", ["Arquivo/Galeria", "Tirar Foto com Câmera"])
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

if pergunta_texto:
    texto_para_enviar = pergunta_texto
    st.session_state.historico.append({"role": "user", "content": pergunta_texto})
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
                st.session_state.historico.append({"role": "user", "content": f"🎙️ **Áudio transcrito:** {texto_para_enviar}"})
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
    st.session_state.historico.append({"role": "user", "content": "[Imagem enviada pelo usuário]"})
    with st.chat_message("user"):
        st.image(imagem_enviada, caption="Imagem enviada", use_container_width=True)

if texto_para_enviar:
    if not client:
        st.error("Erro na chave de API da Groq.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("O OssBot está preparando a resposta... OSS! 🥋"):
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

                    if st.button("🔊 Ouvir resposta", key=f"ouvir_{len(st.session_state.historico) - 1}"):
                        try:
                            st.audio(gerar_audio(resposta_texto), format="audio/mp3")
                        except Exception as e:
                            st.error(f"Erro ao gerar o áudio: {e}")
                except Exception as e:
                    st.error(f"Erro ao conectar com a Groq: {e}")

# Menu lateral com botão para limpar a conversa atual
with st.sidebar:
    st.markdown("## 🥋 Opções")
    if st.button("🔄 Nova Conversa (Limpar Chat)", key="btn_limpar_chat"):
        iniciar_nova_conversa()
        st.rerun()
    st.divider()
    st.caption("Cada pessoa que abre o link tem sua própria conversa privada e limpa. OSS! 🥋")

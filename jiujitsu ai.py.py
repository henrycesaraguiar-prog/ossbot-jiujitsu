import os
import io
import json
import uuid
import html as html_lib
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# Precisa ser o primeiro comando do Streamlit
st.set_page_config(
    page_title="OssBot - Assistente de Jiu-Jitsu",
    page_icon="🥋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Biblioteca de áudio (o nome correto do módulo é "gtts", em minúsculas)
try:
    from gtts import gTTS
    tem_gtts_lib = True
except Exception:
    tem_gtts_lib = False

MODELO = "openai/gpt-oss-120b"


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def esc(texto):
    """Escapa o texto digitado pelo usuário para não quebrar o HTML."""
    return html_lib.escape(str(texto)).replace("\n", "<br>")


def mostrar_html(codigo):
    """Mostra HTML sem linhas em branco/indentação (evita virar bloco de código)."""
    limpo = " ".join(linha.strip() for linha in codigo.splitlines() if linha.strip())
    st.markdown(limpo, unsafe_allow_html=True)


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


GROQ_API_KEY = "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"


def obter_chave_groq():
    return GROQ_API_KEY


@st.cache_resource
def criar_cliente_groq(chave):
    from groq import Groq
    return Groq(api_key=chave)


# ---------------------------------------------------------------------------
# Dados por usuário
# ---------------------------------------------------------------------------
PASTA_DADOS = os.path.dirname(os.path.abspath(__file__))

CAMPOS = [
    "conversas", "historico_lutas", "dinamic_kids_custom", "flashcards_pressao",
    "alunos_graduacao", "cards_vitoria", "cursos_interativos",
    "lista_alunos_academia", "notas_kimono",
]


def dados_vazios():
    return {campo: ({} if campo == "conversas" else []) for campo in CAMPOS}


def obter_caminho_usuario(nome_usuario):
    nome_limpo = "".join(c if c.isalnum() else "_" for c in nome_usuario.lower()).strip("_")
    return os.path.join(PASTA_DADOS, f"usuario_{nome_limpo}.json")


def carregar_dados_usuario(nome_usuario):
    dados = dados_vazios()
    caminho = obter_caminho_usuario(nome_usuario)
    try:
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                dados.update(json.load(f))
    except Exception:
        pass
    return dados


def salvar_dados_usuario(nome_usuario, dados):
    caminho = obter_caminho_usuario(nome_usuario)
    try:
        tmp = caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(tmp, caminho)
    except Exception:
        pass


def salvar_tudo():
    """Salva TODOS os dados do usuário de uma vez (nada fica de fora)."""
    usuario = st.session_state.get("usuario_atual")
    if not usuario:
        return
    salvar_dados_usuario(usuario, {campo: st.session_state[campo] for campo in CAMPOS})


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
    primeira = next((m["content"] for m in st.session_state.historico if m["role"] == "user"), None)
    if primeira is None:
        return
    if not st.session_state.titulo:
        st.session_state.titulo = primeira.strip().replace("\n", " ")[:40]
    st.session_state.conversas[st.session_state.conversa_id] = {
        "titulo": st.session_state.titulo or "Nova conversa",
        "titulo_ia": st.session_state.titulo_ia,
        "atualizada": datetime.now().isoformat(timespec="seconds"),
        "mensagens": st.session_state.historico,
    }
    salvar_tudo()


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
        salvar_tudo()
    if cid == st.session_state.conversa_id:
        iniciar_nova_conversa()


def carregar_usuario(nome):
    dados = carregar_dados_usuario(nome)
    st.session_state.usuario_atual = nome
    for campo in CAMPOS:
        st.session_state[campo] = dados[campo]
    if st.session_state.conversas:
        ultimo_id = max(st.session_state.conversas,
                        key=lambda c: st.session_state.conversas[c].get("atualizada", ""))
        abrir_conversa(ultimo_id)
    else:
        iniciar_nova_conversa()


def gerar_atalhos_inteligentes(conversas):
    palavras_chave = {}
    termos_comuns = {"como", "para", "qual", "uma", "com", "que", "dos", "das", "por",
                     "sobre", "mais", "isso", "ele", "ela", "quero", "dicas"}
    for conv in conversas.values():
        for m in conv.get("mensagens", []):
            if m["role"] == "user":
                for palavra in m["content"].lower().split():
                    p_limpa = "".join(c for c in palavra if c.isalnum())
                    if len(p_limpa) > 3 and p_limpa not in termos_comuns:
                        palavras_chave[p_limpa] = palavras_chave.get(p_limpa, 0) + 1
    ordenados = sorted(palavras_chave.items(), key=lambda x: x[1], reverse=True)
    top = [item[0].capitalize() for item in ordenados[:4]]
    return top if top else ["Guarda", "Raspagem", "Campeonato", "Kids"]


def definir_atalho(atalho):
    st.session_state.atalho_clicado = f"Quero dicas sobre: {atalho}"


# ---------------------------------------------------------------------------
# Funções do Modo Luta (callbacks: o placar atualiza no mesmo clique)
# ---------------------------------------------------------------------------
def somar(lado, campo, valor):
    st.session_state[f"{campo}_{lado}"] += valor


def definir_tempo():
    st.session_state.tempo_segundos = st.session_state.select_tempo * 60
    st.session_state.cronometro_rodando = False


def iniciar_cronometro():
    if st.session_state.tempo_segundos > 0:
        st.session_state.cronometro_rodando = True


def pausar_cronometro():
    st.session_state.cronometro_rodando = False


def zerar_luta():
    st.session_state.cronometro_rodando = False
    st.session_state.tempo_segundos = st.session_state.select_tempo * 60
    for lado in ("a", "b"):
        st.session_state[f"pts_{lado}"] = 0
        st.session_state[f"vant_{lado}"] = 0
        st.session_state[f"pun_{lado}"] = 0


# ---------------------------------------------------------------------------
# CSS (sem linhas em branco: compactado em uma linha para nunca "vazar")
# ---------------------------------------------------------------------------
CSS = """
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { background-color: #121212 !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background-color: #181818 !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp p, .stApp li, .stApp label, .stApp summary { color: #ffffff; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color: #aaaaaa !important; }

div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div { background-color: #1e1e1e !important; border-color: #ff4d4d !important; border-radius: 8px !important; }
div[data-baseweb="input"] input, div[data-baseweb="base-input"] input, div[data-baseweb="textarea"] textarea, div[data-baseweb="base-input"] textarea, input, textarea { background-color: #1e1e1e !important; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; caret-color: #ffffff !important; font-weight: bold !important; }
input::placeholder, textarea::placeholder { color: #9ca3af !important; -webkit-text-fill-color: #9ca3af !important; opacity: 1 !important; }
input:-webkit-autofill { -webkit-box-shadow: 0 0 0 1000px #1e1e1e inset !important; -webkit-text-fill-color: #ffffff !important; }
div[data-baseweb="select"] * { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
div[data-baseweb="select"] svg { fill: #ffffff !important; }

div[data-baseweb="popover"], div[data-baseweb="popover"] > div, ul[role="listbox"], [data-baseweb="menu"] { background-color: #1e1e1e !important; }
div[data-baseweb="popover"] li, div[data-baseweb="popover"] li *, ul[role="listbox"] li { background-color: #1e1e1e !important; color: #ffffff !important; }
div[data-baseweb="popover"] li:hover, ul[role="listbox"] li:hover { background-color: #3a1f1f !important; }
div[data-baseweb="calendar"], div[data-baseweb="calendar"] * { background-color: #1e1e1e !important; color: #ffffff !important; }
div[data-baseweb="calendar"] [aria-selected="true"] { background-color: #ff4d4d !important; }

[data-testid="stNumberInput"] button { background-color: #2a2a2a !important; color: #ffffff !important; border: none !important; }

[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploader"] section { background-color: #1e1e1e !important; border: 2px dashed #ff4d4d !important; border-radius: 10px !important; }
[data-testid="stFileUploader"] * { color: #ffffff !important; }
[data-testid="stFileUploader"] svg { fill: #ffffff !important; }
[data-testid="stFileUploader"] button { background-color: #ff4d4d !important; border: 2px solid #ffffff !important; }

[data-testid="stAudioInput"], [data-testid="stCameraInput"] { background-color: #1e1e1e !important; border-radius: 10px !important; padding: 15px; border: 1px solid #444444; }
[data-testid="stCameraInput"] button { background-color: #ff4d4d !important; color: #ffffff !important; }

[data-testid="stChatInput"] { background-color: #1e1e1e !important; border-radius: 10px !important; border: 2px solid #ff4d4d !important; }
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] div[data-baseweb="textarea"] { background-color: #1e1e1e !important; border: none !important; }
[data-testid="stChatInput"] textarea { font-size: 16px !important; }
[data-testid="stChatInput"] button { background-color: #ff4d4d !important; color: #ffffff !important; }
[data-testid="stChatMessage"] { background-color: #1a1a1a !important; border-radius: 10px !important; }

.stButton > button, div[data-testid="stFormSubmitButton"] > button { border-radius: 10px !important; font-weight: bold !important; background-color: #ff4d4d !important; color: #ffffff !important; border: 2px solid #ffffff !important; }
.stButton > button p, div[data-testid="stFormSubmitButton"] > button p { color: #ffffff !important; }
.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover { background-color: #e60000 !important; color: #ffffff !important; }

[data-testid="stExpander"] { background-color: #1e1e1e !important; border: 1px solid #444444 !important; border-radius: 10px !important; }
[data-testid="stForm"] { border: 1px solid #444444 !important; border-radius: 12px !important; }

.placar-box, .nutri-box, .camp-box, .curso-box, .kids-box { color: #ffffff; border-radius: 15px; padding: 20px; margin-bottom: 20px; }
.placar-box { background-color: #1e1e1e; border: 2px solid #ff4d4d; text-align: center; }
.placar-numero { font-size: 50px; font-weight: bold; color: #00ffcc; }
.nutri-box { background-color: #1e293b; border: 2px solid #00ffcc; }
.camp-box { background-color: #1e1b4b; border: 2px solid #ff4d4d; }
.curso-box { background-color: #0f172a; border: 2px solid #38bdf8; }
.kids-box { background-color: #451a03; border: 2px solid #fbbf24; }
"""
css_compacto = " ".join(CSS.split())
st.markdown(f"<style>{css_compacto}</style>", unsafe_allow_html=True)

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
  #botoes-rolagem { position: fixed; right: 20px; bottom: 110px; display: flex; flex-direction: column; gap: 12px; z-index: 999999; }
  #botoes-rolagem button { width: 64px; height: 64px; font-size: 28px; font-weight: bold; color: #ffffff; background-color: #e60000; border: 2px solid #ffffff; border-radius: 50%; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.6); }
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
  doc.body.scrollTop = (direcao === 'cima') ? 0 : doc.body.scrollHeight;
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
# Barra lateral
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🥋 Identificação")
    st.session_state.setdefault("input_usuario", "Henry Cesar")
    usuario_input = st.text_input(
        "Digite seu Nome e Sobrenome:",
        placeholder="Ex: Henry Cesar",
        key="input_usuario",
    ).strip() or "Visitante"

    if st.session_state.get("usuario_atual") != usuario_input:
        carregar_usuario(usuario_input)

    st.divider()
    st.markdown("## 🥋 Minhas conversas")
    st.button("➕ Nova conversa", on_click=iniciar_nova_conversa, key="btn_nova_conversa",
              use_container_width=True)

    busca = st.text_input("🔍 Pesquisar", placeholder="Ex.: guarda", key="busca_conversas").strip().lower()
    st.divider()

    conversas = st.session_state.conversas
    ids = sorted(conversas, key=lambda c: conversas[c].get("atualizada", ""), reverse=True)

    mostradas = 0
    for cid in ids:
        conv = conversas[cid]
        if busca:
            texto_total = conv["titulo"].lower() + " " + " ".join(m["content"].lower() for m in conv["mensagens"])
            if busca not in texto_total:
                continue
        mostradas += 1
        atual = cid == st.session_state.conversa_id
        col_a, col_b = st.columns([5, 1])
        with col_a:
            st.button(("▶ " if atual else "") + conv["titulo"], key=f"abrir_{cid}",
                      on_click=abrir_conversa, args=(cid,), use_container_width=True)
        with col_b:
            st.button("🗑️", key=f"apagar_{cid}", on_click=apagar_conversa, args=(cid,),
                      help="Apagar esta conversa")

    if mostradas == 0:
        st.caption("Nenhuma conversa encontrada." if busca else "Suas conversas vão aparecer aqui. 🥋")

# ---------------------------------------------------------------------------
# Estados auxiliares
# ---------------------------------------------------------------------------
for chave, valor in {
    "atalho_clicado": None,
    "pts_a": 0, "vant_a": 0, "pun_a": 0,
    "pts_b": 0, "vant_b": 0, "pun_b": 0,
    "tempo_segundos": 300, "cronometro_rodando": False,
}.items():
    st.session_state.setdefault(chave, valor)

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
col_esq, col_centro, col_dir = st.columns([1.2, 2.6, 1.2])
with col_esq:
    st.image("https://images.unsplash.com/photo-1517838277536-f5f99be501cd?q=80&w=600&auto=format&fit=crop",
             caption="Técnica e Combate", use_container_width=True)
with col_centro:
    st.markdown("<h1 style='text-align: center; color: #ff4d4d;'>🥋 OssBot App</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: center; color: #00ffcc;'>Usuário: {esc(st.session_state.usuario_atual)}</h4>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #aaaaaa;'>O seu Assistente de Jiu-Jitsu (PWA)</h3>", unsafe_allow_html=True)
with col_dir:
    st.image("https://images.unsplash.com/photo-1555597673-b21d5c935865?q=80&w=600&auto=format&fit=crop",
             caption="Faixa Preta — Tradição", use_container_width=True)

st.divider()

(aba_chat, aba_modo_luta, aba_historico_lutas, aba_nutricao, aba_camp, aba_cursos, aba_kids,
 aba_drills, aba_pressao, aba_grad, aba_kimono, aba_card, aba_caderneta, aba_chaves) = st.tabs([
    "💬 Chat IA", "🤼 Luta", "📜 Histórico", "🥗 Nutrição", "🏆 Camp", "📚 Cursos", "👶 Kids",
    "⏱️ Drills", "🧠 Pressão", "🥇 Graduação", "🥋 Kimono", "📸 Card", "📇 Alunos", "⏱️ Chaves",
])

# ===========================================================================
# ABA 1: CHAT COM IA
# ===========================================================================
def mostrar_historico():
    for i, mensagem in enumerate(st.session_state.historico):
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])
            if mensagem["role"] == "assistant" and st.button("🔊 Ouvir", key=f"ouvir_{i}"):
                ab = gerar_audio_local(mensagem["content"])
                if ab:
                    st.audio(ab, format="audio/mp3")
                else:
                    st.caption("Áudio indisponível (instale a biblioteca gTTS e verifique a internet).")


with aba_chat:
    st.markdown("### ⚙️ Escolha o Modo de Atendimento")
    modo_selecionado = st.radio(
        "Como você quer que o OssBot responda?",
        [
            "🥋 Aluno / Competidor (Online)",
            "👶 Professor / Turma Kids (Online)",
            "📡 Modo Offline (Economizar Dados Móveis / Sem Internet)",
        ],
        index=0, key="modo_atendimento",
    )

    if "Modo Offline" in modo_selecionado:
        st.info("📡 **Modo Offline Ativado!** Nenhuma requisição externa será feita nesta aba. "
                "Você pode usar 100% das outras abas sem gastar nada da sua rede!")
        st.divider()
        mostrar_historico()
    else:
        client = None
        chave_groq = obter_chave_groq()
        if chave_groq:
            try:
                client = criar_cliente_groq(chave_groq)
            except Exception:
                client = None

        if "Kids" in modo_selecionado:
            system_prompt = ("Você é o OssBot, assistente especialista em BJJ para professores de turmas kids. "
                             "Sugira dinâmicas lúdicas, seguras e divertidas. Use termos como OSS, guarda, raspagem.")
        else:
            system_prompt = ("Você é o OssBot, assistente especialista em BJJ focado em atletas e professores. "
                             "Use termos como OSS, guarda, raspagem.")

        st.divider()
        st.markdown("### ⚡ Atalhos Inteligentes")
        atalhos_personalizados = gerar_atalhos_inteligentes(st.session_state.conversas)
        cols_atalhos = st.columns(len(atalhos_personalizados))
        for idx, atalho in enumerate(atalhos_personalizados):
            with cols_atalhos[idx]:
                st.button(f"📌 {atalho}", key=f"atalho_{idx}", use_container_width=True,
                          on_click=definir_atalho, args=(atalho,))

        st.divider()

        pergunta_texto = st.chat_input("Digite sua dúvida...")
        atalho_pendente = st.session_state.pop("atalho_clicado", None)
        texto_para_enviar = pergunta_texto or atalho_pendente

        # A mensagem do usuário entra no histórico ANTES de desenhar a conversa
        if texto_para_enviar:
            st.session_state.historico.append({"role": "user", "content": texto_para_enviar})
            salvar_conversa_atual()

        mostrar_historico()

        if texto_para_enviar:
            if not client:
                st.warning("⚠️ Sem rede para a IA. Mude para a opção 'Modo Offline'!")
            else:
                with st.chat_message("assistant"):
                    with st.spinner("OssBot pensando... OSS! 🥋"):
                        try:
                            mensagens = [{"role": "system", "content": system_prompt}] + [
                                {"role": m["role"], "content": m["content"]}
                                for m in st.session_state.historico[-20:]
                            ]
                            res = client.chat.completions.create(model=MODELO, messages=mensagens, temperature=0.7)
                            resp = res.choices[0].message.content
                            st.markdown(resp)
                            st.session_state.historico.append({"role": "assistant", "content": resp})
                            salvar_conversa_atual()
                        except Exception:
                            st.warning("Erro de rede com a IA.")

# ===========================================================================
# ABA 2: MODO LUTA
# ===========================================================================
def bloco_placar(lado, nome, emoji, cor):
    pts = st.session_state[f"pts_{lado}"]
    vant = st.session_state[f"vant_{lado}"]
    pun = st.session_state[f"pun_{lado}"]
    mostrar_html(f"""
    <div class='placar-box'>
        <h2 style='color: {cor};'>{emoji} {esc(nome)}</h2>
        <div class='placar-numero'>{pts} Pts</div>
        <p>Vantagens: {vant} | Punições: {pun}</p>
    </div>
    """)
    cols = st.columns(5)
    botoes = [("+2 Pts", "pts", 2), ("+3 Pts", "pts", 3), ("+4 Pts", "pts", 4),
              ("+Vant", "vant", 1), ("+Pun", "pun", 1)]
    for col, (rotulo, campo, valor) in zip(cols, botoes):
        col.button(rotulo, key=f"{lado}_{campo}_{valor}", on_click=somar,
                   args=(lado, campo, valor), use_container_width=True)


with aba_modo_luta:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>⏱️ PLACAR & CRONÔMETRO DE LUTA</h2>", unsafe_allow_html=True)

    col_l1, col_l2 = st.columns(2)
    with col_l1:
        nome_atleta_a = st.text_input("🔵 Atleta 1 (Azul/Preto):", value="Atleta Azul", key="nome_a")
    with col_l2:
        nome_atleta_b = st.text_input("⚪ Atleta 2 (Branco):", value="Atleta Branco", key="nome_b")
    st.divider()

    col_t1, col_t2, col_t3 = st.columns([1, 2, 1])
    with col_t2:
        st.selectbox("Tempo do Rola:", list(range(1, 11)), index=4, key="select_tempo",
                     format_func=lambda m: f"{m} min", on_change=definir_tempo)

        # Fragmento que se atualiza sozinho a cada 1s enquanto o cronômetro roda
        @st.fragment(run_every=1 if st.session_state.cronometro_rodando else None)
        def painel_cronometro():
            if st.session_state.cronometro_rodando:
                if st.session_state.tempo_segundos > 0:
                    st.session_state.tempo_segundos -= 1
                if st.session_state.tempo_segundos <= 0:
                    st.session_state.cronometro_rodando = False
                    st.rerun(scope="app")
            mins, segs = divmod(st.session_state.tempo_segundos, 60)
            st.markdown(
                f"<h1 style='text-align: center; font-size: 70px; color: #ff4d4d;'>{mins:02d}:{segs:02d}</h1>",
                unsafe_allow_html=True,
            )

        painel_cronometro()

        bc1, bc2, bc3 = st.columns(3)
        bc1.button("▶️ INICIAR", use_container_width=True, key="btn_iniciar_luta", on_click=iniciar_cronometro)
        bc2.button("⏸️ PAUSAR", use_container_width=True, key="btn_pausar_luta", on_click=pausar_cronometro)
        bc3.button("🔄 ZERAR", use_container_width=True, key="btn_zerar_luta", on_click=zerar_luta)

    st.divider()
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        bloco_placar("a", nome_atleta_a, "🔵", "#4da6ff")
    with col_p2:
        bloco_placar("b", nome_atleta_b, "⚪", "#ffffff")

    st.divider()
    if st.button("💾 SALVAR RESULTADO DA LUTA", use_container_width=True, key="btn_salvar_luta"):
        st.session_state.historico_lutas.append({
            "data": datetime.now().strftime("%d/%m/%Y - %H:%M"),
            "atleta_a": nome_atleta_a, "pts_a": st.session_state.pts_a,
            "vant_a": st.session_state.vant_a, "pun_a": st.session_state.pun_a,
            "atleta_b": nome_atleta_b, "pts_b": st.session_state.pts_b,
            "vant_b": st.session_state.vant_b, "pun_b": st.session_state.pun_b,
        })
        salvar_tudo()
        st.success("✅ Luta salva na memória!")

# ===========================================================================
# ABA 3: HISTÓRICO DE LUTAS
# ===========================================================================
with aba_historico_lutas:
    st.markdown("### 📜 Lutas Registradas")
    if not st.session_state.historico_lutas:
        st.info("Nenhuma luta registrada ainda.")
    else:
        for luta in reversed(st.session_state.historico_lutas):
            with st.expander(f"🥋 {luta['data']} - {luta['atleta_a']} vs {luta['atleta_b']}"):
                st.write(f"🔵 **{luta['atleta_a']}**: {luta['pts_a']} Pts ({luta['vant_a']}V/{luta['pun_a']}P) | "
                         f"⚪ **{luta['atleta_b']}**: {luta['pts_b']} Pts ({luta['vant_b']}V/{luta['pun_b']}P)")

# ===========================================================================
# ABA 4: NUTRIÇÃO & HIDRATAÇÃO
# ===========================================================================
with aba_nutricao:
    st.markdown("<h2 style='text-align: center; color: #00ffcc;'>🥗 NUTRIÇÃO & HIDRATAÇÃO</h2>", unsafe_allow_html=True)
    peso_input = st.number_input("Digite seu Peso atual (kg):", 30.0, 150.0, 65.0, 0.5, key="nutri_peso")
    horas_input = st.slider("Horas de treino por dia:", 0.5, 4.0, 1.5, 0.5, key="nutri_horas")
    agua_calc = ((peso_input * 35) / 1000) + (horas_input * 0.75)
    mostrar_html(f"""
    <div class='nutri-box'>
        <h3>🥤 Meta Diária de Água Recomendada:</h3>
        <h2>{agua_calc:.2f} Litros</h2>
        <p>• Dica: Beba 500ml de água 1h antes do treino e consuma carboidratos leves para ter energia sem desconforto.</p>
    </div>
    """)

# ===========================================================================
# ABA 5: CAMPEONATO
# ===========================================================================
with aba_camp:
    st.markdown("<h2 style='text-align: center; color: #ff4d4d;'>🏆 ESTRATÉGIA DE CAMPEONATO</h2>", unsafe_allow_html=True)
    faixa_camp = st.selectbox("Sua Faixa:", ["Branca", "Kids", "Azul", "Roxa", "Castanha", "Preta"], key="camp_faixa")
    estilo_camp = st.text_input("Seu Golpe/Posição Favorito:", "Armlock da Guarda", key="camp_estilo")

    if st.button("🚀 Gerar Plano de Luta Tático", use_container_width=True, key="btn_plan_camp"):
        mostrar_html(f"""
        <div class='camp-box'>
            <h3 style='color: #00ffcc;'>🥇 GUIA TÁTICO ({esc(faixa_camp)} - {esc(estilo_camp)})</h3>
            <p>1. <b>Início Implacável:</b> Faça a pegada na gola/manga primeiro. Imponha o ritmo antes do adversário pontuar.</p>
            <p>2. <b>Foco na Posição {esc(estilo_camp)}:</b> Monte armadilhas criando conexões. Garanta os primeiros 2 pontos de vantagem antes da finalização.</p>
            <p>3. <b>Administração do Placar:</b> Se estiver na frente nos 60 segundos finais, mantenha a base sólida e evite trocas arriscadas.</p>
        </div>
        """)

# ===========================================================================
# ABA 6: CURSOS
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
                    "descricao": desc_curso.strip(),
                })
                salvar_tudo()
                st.success("✅ Material salvo com sucesso!")
            else:
                st.warning("Preencha o título e a descrição do curso.")

    st.divider()
    st.markdown("### 📜 Tabela Oficial de Pontos CBJJ / IBJJF:")
    mostrar_html("""
    <div class='curso-box'>
        <ul>
            <li><b>2 PONTOS:</b> Queda, Raspagem e Joelho na Barriga.</li>
            <li><b>3 PONTOS:</b> Passagem de Guarda.</li>
            <li><b>4 PONTOS:</b> Montada, Montada pelas Costas e Pegada de Costas com dois ganchos.</li>
            <li><b>VANTAGENS:</b> Quase-queda, quase-raspagem ou tentativa real de finalização com defesa ativa.</li>
        </ul>
    </div>
    """)

    if st.session_state.cursos_interativos:
        st.markdown("### 📂 Seus Materiais Cadastrados:")
        for ci in st.session_state.cursos_interativos:
            mostrar_html(f"""
            <div class='curso-box'>
                <h3>📚 {esc(ci['titulo'])}</h3>
                <p>{esc(ci['descricao'])}</p>
            </div>
            """)

# ===========================================================================
# ABA 7: AULAS KIDS
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
                salvar_tudo()
                st.success("✅ Dinâmica Kids salva com sucesso!")
            else:
                st.warning("Preencha o nome e a explicação (ou grave um áudio) da dinâmica!")

    st.divider()
    st.markdown("### 🧸 Dinâmicas Cadastradas:")
    if not st.session_state.dinamic_kids_custom:
        st.info("Nenhuma dinâmica personalizada cadastrada ainda.")
    else:
        for dk in st.session_state.dinamic_kids_custom:
            mostrar_html(f"""
            <div class='kids-box'>
                <h3>🧸 {esc(dk['titulo'])}</h3>
                <p>{esc(dk['descricao'])}</p>
            </div>
            """)

# ===========================================================================
# ABA 8: DRILLS
# ===========================================================================
with aba_drills:
    st.markdown("<h2 style='text-align: center; color: #34d399;'>⏱️ DRILLS & HIIT DE COMBATE</h2>", unsafe_allow_html=True)
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        t_acao = st.number_input("Tempo de Ação (s):", 10, 120, 30, 5, key="d_a")
    with col_d2:
        t_pausa = st.number_input("Tempo de Pausa (s):", 5, 60, 10, 5, key="d_p")
    with col_d3:
        n_rounds = st.number_input("Rounds:", 1, 30, 8, 1, key="d_r")

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
                st.session_state.flashcards_pressao.append(
                    {"pergunta": pergunta_flash.strip(), "resposta": resposta_flash.strip()})
                salvar_tudo()
                st.success("✅ Flashcard salvo com sucesso!")
            else:
                st.warning("Preencha a situação e a solução!")

    st.divider()
    st.markdown("### 📚 Seus Flashcards de Estudo:")
    if not st.session_state.flashcards_pressao:
        mostrar_html("""
        <div class='camp-box'>
            <h4>💡 Exemplo 1: Faltando 1 minuto e perdendo por 2 a 0</h4>
            <p><b>Solução:</b> Estoure pegadas imediatamente e force o ataque de raspagem/queda sem aceitar amarração!</p>
        </div>
        """)
    else:
        for idx, fc in enumerate(st.session_state.flashcards_pressao):
            with st.expander(f"⚡ Situação {idx + 1}: {fc['pergunta']}"):
                mostrar_html(f"<div class='camp-box'><p><b>💡 Saída Tática:</b> {esc(fc['resposta'])}</p></div>")

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
                st.session_state.alunos_graduacao.append({
                    "nome": nome_aluno_g.strip(),
                    "faixa": faixa_atual_g,
                    "graus": graus_atuais_g,
                    "data_inicio": data_inicio_g.strftime("%d/%m/%Y"),
                })
                salvar_tudo()
                st.success(f"✅ Aluno {nome_aluno_g} cadastrado no diário de graduação!")
            else:
                st.warning("Digite o nome do aluno.")

    st.divider()
    st.markdown("### 📋 Alunos em Acompanhamento:")
    if not st.session_state.alunos_graduacao:
        st.info("Nenhum aluno cadastrado na graduação.")
    else:
        for aluno in st.session_state.alunos_graduacao:
            with st.expander(f"🥋 {aluno['nome']} - Faixa {aluno['faixa']} ({aluno['graus']}º Grau)"):
                st.write(f"• **Início na faixa:** {aluno['data_inicio']}")
                st.markdown("<p style='color: #00ffcc;'>✔️ <b>Status:</b> Acompanhando frequência e evolução técnica para o próximo grau!</p>", unsafe_allow_html=True)

# ===========================================================================
# ABA 11: KIMONO
# ===========================================================================
with aba_kimono:
    st.markdown("<h2 style='text-align: center; color: #fbbf24;'>🥋 GESTÃO E CUIDADOS COM O KIMONO</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Registre anotações, lavagens e dicas de manutenção do seu equipamento de luta.</p>", unsafe_allow_html=True)

    nota_kimono = st.text_area("Anotações sobre lavagem, ajustes ou reparos no Kimono:",
                               placeholder="Ex: Lavar com água fria, secar à sombra para não encolher a gola...",
                               key="nota_kimono")
    if st.button("💾 Salvar Nota do Kimono", use_container_width=True, key="btn_salvar_kimono"):
        if nota_kimono.strip():
            st.session_state.notas_kimono.append(
                {"data": datetime.now().strftime("%d/%m/%Y"), "nota": nota_kimono.strip()})
            salvar_tudo()
            st.success("✅ Anotação de kimono salva com sucesso!")
        else:
            st.warning("Digite alguma observação antes de salvar.")

    for n in reversed(st.session_state.notas_kimono):
        mostrar_html(f"<div class='curso-box'><p><b>{esc(n['data'])}</b></p><p>{esc(n['nota'])}</p></div>")

    mostrar_html("""
    <div class='kids-box' style='margin-top: 20px;'>
        <h3>🧼 Dica de Ouro de Conservação:</h3>
        <p>Nunca utilize secadora de roupas em quimonos trançados 100% algodão para evitar encolhimento precoce e desgaste das costuras principais.</p>
    </div>
    """)

# ===========================================================================
# ABA 12: CARD VITÓRIA
# ===========================================================================
with aba_card:
    st.markdown("<h2 style='text-align: center; color: #a855f7;'>📸 CARD DE VITÓRIA</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Crie seu card personalizado com foto, texto e comemore suas conquistas no tatame!</p>", unsafe_allow_html=True)

    foto_card_up = st.file_uploader("Enviar Foto da Vitória (Arquivos):", type=["jpg", "png", "jpeg"], key="up_card")
    foto_card_cam = st.camera_input("Ou Tire uma Foto com a Câmera:", key="cam_card")
    legenda_card = st.text_area("Legenda / Frase do Card:",
                                value="Tatame lavado, missão cumprida por hoje! 🥋🔥 OSS! #BJJ #OssBot",
                                key="legenda_card")

    if st.button("🚀 Gerar Card de Vitória", use_container_width=True, key="btn_gerar_card"):
        st.success("✅ Card gerado com sucesso!")
        foto_final = foto_card_cam or foto_card_up
        if foto_final is not None:
            st.image(foto_final, use_container_width=True)
        mostrar_html(f"""
        <div class='placar-box' style='border: 2px solid #a855f7;'>
            <h3 style='color: #a855f7;'>🏆 CARD OFICIAL OSSBOT</h3>
            <p style='font-size: 18px; font-weight: bold;'>{esc(legenda_card)}</p>
        </div>
        """)

# ===========================================================================
# ABA 13: CADERNETA DE ALUNOS
# ===========================================================================
with aba_caderneta:
    st.markdown("<h2 style='text-align: center; color: #fbbf24;'>📇 CADERNETA DE ALUNOS & FREQUÊNCIA</h2>", unsafe_allow_html=True)
    novo_aluno = st.text_input("Digite o Nome do Aluno:", placeholder="Ex: Lucas Gabriel", key="input_novo_aluno")
    if st.button("➕ Adicionar Aluno à Turma", use_container_width=True, key="btn_add_aluno"):
        if novo_aluno.strip():
            st.session_state.lista_alunos_academia.append(novo_aluno.strip())
            salvar_tudo()
            st.success(f"✅ Aluno {novo_aluno} adicionado com sucesso!")
        else:
            st.warning("Digite o nome do aluno.")

    if st.session_state.lista_alunos_academia:
        st.markdown("### 📋 Lista de Alunos Cadastrados:")
        for idx, aluno in enumerate(st.session_state.lista_alunos_academia):
            col_al1, col_al2 = st.columns([3, 1])
            with col_al1:
                st.write(f"🥋 {aluno}")
            with col_al2:
                if st.button("Presença ✔️", key=f"pres_{idx}"):
                    st.toast(f"✅ Presença confirmada para {aluno}!")

# ===========================================================================
# ABA 14: CHAVES DE TORNEIO
# ===========================================================================
with aba_chaves:
    st.markdown("<h2 style='text-align: center; color: #f43f5e;'>⏱️ ORGANIZADOR DE CHAVES DE LUTA</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Organize os confrontos dos atletas de forma limpa e visível.</p>", unsafe_allow_html=True)

    nomes_atletas_txt = st.text_area("Digite os nomes dos atletas (um por linha):",
                                     placeholder="Atleta 1\nAtleta 2\nAtleta 3\nAtleta 4",
                                     key="txt_atletas_chave")

    if st.button("⚔️ Gerar Chaves de Luta", use_container_width=True, key="btn_gerar_chave"):
        atletas = [a.strip() for a in nomes_atletas_txt.split("\n") if a.strip()]
        if len(atletas) < 2:
            st.warning("Digite pelo menos 2 atletas para gerar os confrontos!")
        else:
            mostrar_html("<div class='placar-box'><h3 style='color: #00ffcc;'>⚔️ CONFRONTOS GERADOS</h3></div>")
            for i in range(0, len(atletas) - 1, 2):
                mostrar_html(
                    f"<div style='background-color: #1e1e1e; padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #ff4d4d;'>"
                    f"<h4 style='color: #ffffff; margin:0;'>🥊 Luta: <span style='color: #00ffcc;'>{esc(atletas[i])}</span> "
                    f"vs <span style='color: #ff4d4d;'>{esc(atletas[i + 1])}</span></h4></div>"
                )
            if len(atletas) % 2 != 0:
                st.info(f"✨ Atleta aguardando vencedores (Bye): {atletas[-1]}")

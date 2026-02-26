# ══════════════════════════════════════════════
# ✉️  COMPOSITOR DE MENSAGENS — INFO BOT PRO V4.0
# 👨‍💻 Créditos: Edivaldo Silva @Edkd1
# ══════════════════════════════════════════════
#
# Sistema completo para o dono compor e enviar
# mensagens personalizadas com:
#   - Markdown formatado
#   - Botões inline (URL e callback)
#   - Camuflagem de URL (texto personalizado + link)
#   - Seleção de grupo destino
#   - Preview antes de enviar
#
# ══════════════════════════════════════════════

import os
import json
import re
from datetime import datetime
from telethon import Button
from grupo import log

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(BASE_DIR, "data", "mensagens_templates.json")

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

# ── Estado dos compositores por chat ──
composer_state = {}


# ══════════════════════════════════════════════
# 📝  TEMPLATES
# ══════════════════════════════════════════════

def carregar_templates() -> list:
    if os.path.exists(TEMPLATES_PATH):
        try:
            with open(TEMPLATES_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def salvar_templates(templates: list):
    try:
        with open(TEMPLATES_PATH, 'w', encoding='utf-8') as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)
    except IOError as e:
        log(f"❌ Erro ao salvar templates: {e}")


def salvar_template(nome: str, mensagem: str, botoes: list):
    templates = carregar_templates()
    templates.append({
        "nome": nome,
        "mensagem": mensagem,
        "botoes": botoes,
        "criado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })
    salvar_templates(templates)


# ══════════════════════════════════════════════
# 🔗  PARSER DE BOTÕES
# ══════════════════════════════════════════════

def parse_botoes(texto_botoes: str) -> list:
    """
    Parseia texto de botões no formato:
      Texto do Botão | https://link.com
      Texto 1 | https://link1.com , Texto 2 | https://link2.com
    
    Cada linha = uma fileira de botões.
    Vírgula separa botões na mesma fileira.
    
    Retorna lista de fileiras, cada fileira = lista de (texto, url)
    """
    fileiras = []
    for linha in texto_botoes.strip().split('\n'):
        linha = linha.strip()
        if not linha:
            continue
        fileira = []
        for parte in linha.split(','):
            parte = parte.strip()
            if '|' in parte:
                texto, url = parte.split('|', 1)
                texto = texto.strip()
                url = url.strip()
                if texto and url:
                    fileira.append((texto, url))
        if fileira:
            fileiras.append(fileira)
    return fileiras


def criar_botoes_inline(fileiras: list) -> list:
    """Converte fileiras de (texto, url) em botões Telethon inline."""
    buttons = []
    for fileira in fileiras:
        row = []
        for texto, url in fileira:
            if url.startswith('http://') or url.startswith('https://'):
                row.append(Button.url(texto, url))
            else:
                # Callback button (uso interno)
                row.append(Button.inline(texto, url.encode()))
        if row:
            buttons.append(row)
    return buttons


# ══════════════════════════════════════════════
# 🎭  CAMUFLAGEM DE URL
# ══════════════════════════════════════════════

def camuflar_urls(texto: str) -> str:
    """
    Substitui marcações de URL camuflada no texto.
    Formato: [texto visível](url_real)
    Markdown nativo do Telegram suporta isso.
    """
    # Já é Markdown nativo, apenas retorna
    return texto


def formatar_preview(mensagem: str, botoes_texto: str = "") -> str:
    """Gera preview da mensagem formatada."""
    preview = f"""╔══════════════════════════════════╗
║  👁️ **PREVIEW DA MENSAGEM**       ║
╚══════════════════════════════════╝

━━━━ CONTEÚDO ━━━━
{mensagem}
━━━━━━━━━━━━━━━━━━"""

    if botoes_texto:
        fileiras = parse_botoes(botoes_texto)
        if fileiras:
            preview += "\n\n🔘 **Botões:**\n"
            for i, fileira in enumerate(fileiras, 1):
                btns = " | ".join([f"[{t}]({u})" for t, u in fileira])
                preview += f"  Fileira {i}: {btns}\n"

    return preview


# ══════════════════════════════════════════════
# 🎮  ESTADOS DO COMPOSITOR
# ══════════════════════════════════════════════

def iniciar_compositor(chat_id: int):
    """Inicia estado do compositor para um chat."""
    composer_state[chat_id] = {
        "etapa": "mensagem",      # mensagem → botoes → grupo → confirmar
        "mensagem": "",
        "botoes_texto": "",
        "botoes_parsed": [],
        "grupo_destino": None,
        "grupo_nome": ""
    }


def obter_estado(chat_id: int) -> dict:
    return composer_state.get(chat_id)


def definir_mensagem(chat_id: int, texto: str):
    if chat_id in composer_state:
        composer_state[chat_id]["mensagem"] = texto
        composer_state[chat_id]["etapa"] = "botoes_pergunta"


def definir_botoes(chat_id: int, texto: str):
    if chat_id in composer_state:
        composer_state[chat_id]["botoes_texto"] = texto
        composer_state[chat_id]["botoes_parsed"] = parse_botoes(texto)
        composer_state[chat_id]["etapa"] = "grupo"


def pular_botoes(chat_id: int):
    if chat_id in composer_state:
        composer_state[chat_id]["etapa"] = "grupo"


def definir_grupo(chat_id: int, grupo_id: str, grupo_nome: str):
    if chat_id in composer_state:
        composer_state[chat_id]["grupo_destino"] = grupo_id
        composer_state[chat_id]["grupo_nome"] = grupo_nome
        composer_state[chat_id]["etapa"] = "confirmar"


def limpar_compositor(chat_id: int):
    if chat_id in composer_state:
        del composer_state[chat_id]


# ══════════════════════════════════════════════
# 📤  ENVIO
# ══════════════════════════════════════════════

async def enviar_mensagem(bot_client, user_client, chat_id: int) -> tuple:
    """
    Envia a mensagem composta para o grupo destino.
    Retorna (sucesso, mensagem_status)
    """
    estado = composer_state.get(chat_id)
    if not estado:
        return False, "❌ Nenhuma mensagem sendo composta."

    grupo_destino = estado["grupo_destino"]
    mensagem = estado["mensagem"]
    botoes_parsed = estado["botoes_parsed"]

    if not grupo_destino or not mensagem:
        return False, "❌ Mensagem ou grupo não definidos."

    try:
        buttons = criar_botoes_inline(botoes_parsed) if botoes_parsed else None

        # Enviar via bot (suporta botões inline)
        await bot_client.send_message(
            int(grupo_destino),
            mensagem,
            parse_mode='md',
            buttons=buttons,
            link_preview=True
        )

        log(f"📤 Mensagem enviada para grupo {estado['grupo_nome']} ({grupo_destino})")
        limpar_compositor(chat_id)
        return True, f"✅ **Mensagem enviada com sucesso!**\n\n📍 Grupo: **{estado['grupo_nome']}**"

    except Exception as e:
        log(f"❌ Erro ao enviar mensagem: {e}")
        return False, f"❌ **Erro ao enviar:**\n`{e}`"


# ══════════════════════════════════════════════
# 🎨  BOTÕES DO COMPOSITOR
# ══════════════════════════════════════════════

def compositor_menu_buttons():
    """Botões do menu do compositor."""
    return [
        [Button.inline("✉️ Nova Mensagem", b"msg_nova")],
        [Button.inline("📋 Templates Salvos", b"msg_templates")],
        [Button.inline("📖 Guia de Formatação", b"msg_guia")],
        [Button.inline("🔙 Menu Principal", b"cmd_menu")]
    ]


def compositor_botoes_pergunta():
    """Pergunta se quer adicionar botões."""
    return [
        [Button.inline("✅ Sim, adicionar botões", b"msg_add_botoes")],
        [Button.inline("⏭️ Pular — Sem botões", b"msg_pular_botoes")],
        [Button.inline("❌ Cancelar", b"msg_cancelar")]
    ]


def compositor_confirmar_buttons():
    """Botões de confirmação."""
    return [
        [Button.inline("📤 Enviar Agora", b"msg_enviar")],
        [Button.inline("💾 Salvar Template", b"msg_salvar_template")],
        [Button.inline("✏️ Editar Mensagem", b"msg_editar")],
        [Button.inline("❌ Cancelar", b"msg_cancelar")]
    ]

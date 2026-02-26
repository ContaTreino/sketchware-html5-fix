# ══════════════════════════════════════════════
# 📡  AUTO-RESPOSTA EM GRUPOS — INFO BOT PRO V4.0
# 👨‍💻 Créditos: Edivaldo Silva @Edkd1
# ══════════════════════════════════════════════

import os
import json
from datetime import datetime
from grupo import log

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FOLDER_PATH = os.path.join(BASE_DIR, "data")
CONFIG_PATH = os.path.join(FOLDER_PATH, "grupos_config.json")
LOG_PATH = os.path.join(FOLDER_PATH, "bot_interacao.log")

OWNER_ID = 2061557102  # Edivaldo Silva @Edkd1

os.makedirs(FOLDER_PATH, exist_ok=True)


# ══════════════════════════════════════════════
# 📁  CONFIGURAÇÃO DE GRUPOS (JSON)
# ══════════════════════════════════════════════

def carregar_config() -> dict:
    """Carrega configuração dos grupos monitorados para auto-resposta."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"grupos": {}, "respostas_auto": True}
    return {"grupos": {}, "respostas_auto": True}


def salvar_config(config: dict):
    """Salva configuração dos grupos."""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError as e:
        log(f"❌ Erro ao salvar config auto-resposta: {e}")


def grupo_esta_configurado(chat_id: int) -> bool:
    """Verifica se o grupo está na lista de grupos configurados."""
    config = carregar_config()
    return str(chat_id) in config.get("grupos", {})


def adicionar_grupo(grupo_id: str, nome: str) -> bool:
    """Adiciona um grupo à lista de auto-resposta."""
    config = carregar_config()
    config["grupos"][grupo_id] = {
        "nome": nome,
        "adicionado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "resposta_padrao": ""
    }
    salvar_config(config)
    log(f"➕ Grupo auto-resposta adicionado: {nome} ({grupo_id})")
    return True


def remover_grupo(grupo_id: str) -> tuple:
    """Remove grupo. Retorna (sucesso, nome)."""
    config = carregar_config()
    grupos = config.get("grupos", {})
    if grupo_id in grupos:
        nome = grupos[grupo_id].get("nome", grupo_id)
        del grupos[grupo_id]
        config["grupos"] = grupos
        salvar_config(config)
        log(f"➖ Grupo auto-resposta removido: {nome} ({grupo_id})")
        return True, nome
    return False, ""


def definir_resposta(grupo_id: str, resposta: str) -> bool:
    """Define resposta padrão para um grupo."""
    config = carregar_config()
    if grupo_id in config.get("grupos", {}):
        config["grupos"][grupo_id]["resposta_padrao"] = resposta
        salvar_config(config)
        return True
    return False


def toggle_auto_resposta() -> bool:
    """Alterna estado de auto-resposta. Retorna novo estado."""
    config = carregar_config()
    config["respostas_auto"] = not config.get("respostas_auto", True)
    salvar_config(config)
    return config["respostas_auto"]


# ══════════════════════════════════════════════
# 📡  PROCESSAMENTO DE MENÇÕES
# ══════════════════════════════════════════════

async def processar_mencao_grupo(event, owner_id: int = OWNER_ID):
    """Processa menção ao dono em grupo configurado."""
    from consulta import extrair_cpf, consultar_cpf

    config = carregar_config()
    if not config.get("respostas_auto", True):
        return

    chat_id = str(event.chat_id)
    if chat_id not in config.get("grupos", {}):
        return

    # Verifica se a mensagem menciona o dono
    eh_mencao = False

    # Verifica reply
    if event.is_reply:
        try:
            replied = await event.get_reply_message()
            if replied and replied.sender_id == owner_id:
                eh_mencao = True
        except Exception:
            pass

    # Verifica menção direta
    if not eh_mencao and event.mentioned:
        eh_mencao = True

    # Verifica entidades
    if not eh_mencao and event.message.entities:
        for entity in event.message.entities:
            if hasattr(entity, 'user_id') and entity.user_id == owner_id:
                eh_mencao = True
                break

    if not eh_mencao:
        return

    # Pessoa mencionou o dono — processar
    texto = event.text or ""
    sender = await event.get_sender()
    nome_sender = f"{sender.first_name or ''} {sender.last_name or ''}".strip() if sender else "Alguém"

    log(f"📩 Menção recebida de {nome_sender} no grupo {chat_id}: {texto[:80]}")

    # Tenta extrair CPF da mensagem
    cpf = extrair_cpf(texto)

    if cpf:
        resultado = consultar_cpf(cpf)
        await event.reply(resultado, parse_mode='md')
        log(f"✅ Consulta CPF automática respondida para {nome_sender}")
    else:
        grupo_config = config["grupos"][chat_id]
        resposta_padrao = grupo_config.get("resposta_padrao", "")

        if resposta_padrao:
            await event.reply(resposta_padrao, parse_mode='md')
        else:
            await event.reply(
                f"👋 Olá **{nome_sender}**!\n\n"
                f"Vi que me mencionou. Como posso ajudar?\n\n"
                f"💡 **Dica:** Envie um CPF (11 dígitos) na mensagem que eu consulto automaticamente.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"_👨‍💻 @Edkd1 | Info Bot Pro v4.0_",
                parse_mode='md'
            )

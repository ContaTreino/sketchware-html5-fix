# ══════════════════════════════════════════════
# 🚀  INFO BOT PRO V4.0 — MAIN
# 👨‍💻 Créditos: Edivaldo Silva @Edkd1
# ══════════════════════════════════════════════
#
# Bot 100% funcional — ID detector, consulta CPF,
# compositor de mensagens, auto-resposta em grupos.
#
# Estrutura modular:
#   main.py          → Bot principal + handlers
#   grupo.py         → Funções de grupos e varredura
#   pagina.py        → Paginação
#   botoes.py        → Botões inline
#   consulta.py      → Consulta CPF via API
#   auto_resposta.py → Auto-resposta em grupos
#   mensagem.py      → Compositor de mensagens personalizadas
#   aplicativo.py    → API_ID, API_HASH, PHONE
#   token.json       → Token do bot
#
# ══════════════════════════════════════════════

import json
import os
import re
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button

# ── Módulos locais ──
from aplicativo import API_ID, API_HASH, PHONE
from grupo import (
    carregar_dados, salvar_dados, carregar_grupos_db, salvar_grupos_db,
    log, garantir_campos, registrar_interacao,
    consultar_telegram_api, verificar_status_em_grupos,
    buscar_usuario, formatar_perfil, formatar_perfil_api,
    executar_varredura, executar_threads_atualizacao, auto_scanner,
    set_clients, scan_running, scan_stats, thread_scan_active,
    FILE_PATH, GROUPS_DB_PATH, SCAN_INTERVAL, THREAD_SCAN_INTERVAL,
    MAX_HISTORY, BOT_VERSION
)
from botoes import (
    menu_principal_buttons, voltar_button, perfil_buttons,
    perfil_com_api_buttons, resultado_multiplo_buttons,
    auto_resposta_menu_buttons,
    set_owner, is_admin
)
from pagina import paginar_buttons, paginar_lista, ITEMS_PER_PAGE
from consulta import consultar_cpf, extrair_cpf, validar_cpf, limpar_cpf
from auto_resposta import (
    carregar_config as ar_carregar_config,
    salvar_config as ar_salvar_config,
    adicionar_grupo as ar_adicionar_grupo,
    remover_grupo as ar_remover_grupo,
    definir_resposta as ar_definir_resposta,
    toggle_auto_resposta as ar_toggle,
    processar_mencao_grupo,
    CONFIG_PATH as AR_CONFIG_PATH
)
from mensagem import (
    iniciar_compositor, obter_estado, definir_mensagem,
    definir_botoes, pular_botoes, definir_grupo,
    limpar_compositor, enviar_mensagem, formatar_preview,
    compositor_menu_buttons, compositor_botoes_pergunta,
    compositor_confirmar_buttons, parse_botoes, criar_botoes_inline,
    salvar_template, carregar_templates
)

# ── Configurações ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")
SESSION_USER = os.path.join(BASE_DIR, "session_monitor")
SESSION_BOT = os.path.join(BASE_DIR, "session_bot")

BOT_CODENAME = "773H Ultra"

def carregar_token() -> str:
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("bot_token", "")
        except (json.JSONDecodeError, IOError):
            pass
    return ""

def carregar_owner_id() -> int:
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("owner_id", 2061557102)
        except (json.JSONDecodeError, IOError):
            pass
    return 2061557102

BOT_TOKEN = carregar_token()
OWNER_ID = carregar_owner_id()

if not BOT_TOKEN:
    print("❌ Token não encontrado! Configure token.json")
    exit(1)

if not API_ID or not API_HASH or not PHONE:
    print("❌ Credenciais API não configuradas! Configure aplicativo.py")
    exit(1)

# ── Clientes Telethon ──
user_client = TelegramClient(SESSION_USER, API_ID, API_HASH)
bot = TelegramClient(SESSION_BOT, API_ID, API_HASH)

# Configurar módulos
set_owner(OWNER_ID)
set_clients(bot, OWNER_ID)

# ── Estados temporários ──
search_pending = {}
tg_search_pending = {}
cpf_pending = {}
pending_action = {}  # Para auto-resposta e compositor

# ══════════════════════════════════════════════
# 🎮  HANDLERS DO BOT
# ══════════════════════════════════════════════

@bot.on(events.NewMessage(pattern='/start'))
async def cmd_start(event):
    await registrar_interacao(event)
    sender = await event.get_sender()
    uid = sender.id if sender else 0

    db = carregar_dados()
    user_info = ""
    uid_str = str(uid)
    if uid_str in db:
        d = db[uid_str]
        user_info = f"""
━━━━━━━━━━━━━━━━━━━━━
📌 **Seu Perfil no Sistema:**
├ 👤 `{d.get('nome_atual', 'N/A')}`
├ 📂 Grupos: **{len(d.get('grupos', []))}** | 👑 Admin: **{len(d.get('grupos_admin', []))}** | 🚫 Bans: **{len(d.get('grupos_banido', []))}**
├ 📝 Alterações: **{len(d.get('historico', []))}**
└ 🕐 Desde: `{d.get('primeiro_registro', 'N/A')}`"""

    await event.respond(
        f"""╔══════════════════════════════════╗
║  🕵️ **User Info Bot Pro v{BOT_VERSION}**     ║
║  _{BOT_CODENAME}_                     ║
╚══════════════════════════════════╝

🔍 **Busque** por ID, @username ou nome
🌐 **Consulte** via API Telegram
🔎 **Consulte** CPF via API
📊 **Monitore** alterações em tempo real
✉️ **Componha** mensagens personalizadas
📡 **Auto-resposta** em grupos
👑 **Descubra** grupos como admin
🚫 **Verifique** bans registrados
🧵 **Threads** atualizando em tempo real
{user_info}

━━━━━━━━━━━━━━━━━━━━━
👨‍💻 _Créditos: Edivaldo Silva @Edkd1_
⚡ _Powered by {BOT_CODENAME}_
━━━━━━━━━━━━━━━━━━━━━""",
        parse_mode='md', buttons=menu_principal_buttons(uid))

@bot.on(events.NewMessage(pattern='/menu'))
async def cmd_menu_msg(event):
    await registrar_interacao(event)
    await cmd_start(event)

@bot.on(events.NewMessage(pattern='/id'))
async def cmd_get_id(event):
    await registrar_interacao(event)
    chat = await event.get_chat()
    sender = await event.get_sender()
    await event.reply(
        f"🔢 **IDs**\n"
        f"├ 💬 Chat: `{event.chat_id}`\n"
        f"├ 👤 Seu: `{sender.id if sender else 'N/A'}`\n"
        f"└ 📛 `{chat.title if hasattr(chat, 'title') else 'DM'}`",
        parse_mode='md'
    )

@bot.on(events.NewMessage(pattern=r'/buscar\s+(.+)'))
async def cmd_buscar_text(event):
    await registrar_interacao(event)
    query = event.pattern_match.group(1).strip()
    results = buscar_usuario(query)

    if not results:
        await event.reply("🔎 _Não encontrado no banco. Consultando API..._", parse_mode='md')
        dados_api = await consultar_telegram_api(user_client, query)
        if dados_api:
            uid = str(dados_api["id"])
            db = carregar_dados()
            if uid in db:
                status = await verificar_status_em_grupos(user_client, dados_api["id"])
                db[uid]["grupos_admin"] = [{"grupo": g["grupo"], "cargo": g["cargo"]} for g in status["admin_em"]]
                db[uid]["grupos_banido"] = [{"grupo": g["grupo"]} for g in status["banido_de"]]
                salvar_dados(db)
                await event.reply(
                    formatar_perfil(db[uid]), parse_mode='md',
                    buttons=perfil_com_api_buttons(uid)
                )
            else:
                await event.reply(
                    formatar_perfil_api(dados_api), parse_mode='md',
                    buttons=voltar_button()
                )
            return
        await event.reply(
            "❌ **Nenhum usuário encontrado.**\n💡 Tente ID, @username ou nome.",
            parse_mode='md', buttons=voltar_button()
        )
        return

    if len(results) == 1:
        uid = str(results[0]["id"])
        await event.reply(
            formatar_perfil(results[0]), parse_mode='md',
            buttons=perfil_buttons(uid)
        )
    else:
        text = f"🔍 **{len(results)} resultados para** `{query}`:\n\n"
        await event.reply(text, parse_mode='md', buttons=resultado_multiplo_buttons(results))

@bot.on(events.NewMessage(pattern=r'/cpf\s+(.+)'))
async def cmd_cpf_direto(event):
    """Consulta CPF diretamente via comando."""
    await registrar_interacao(event)
    texto = event.pattern_match.group(1).strip()
    cpf = limpar_cpf(texto)

    if not cpf.isdigit() or len(cpf) != 11:
        await event.reply(
            "❌ **CPF inválido.**\nUse: `/cpf 12345678900`",
            parse_mode='md'
        )
        return

    await event.reply("🔍 **Consultando...**", parse_mode='md')
    resultado = consultar_cpf(cpf)
    await event.reply(resultado, parse_mode='md', buttons=voltar_button())

# ══════════════════════════════════════════════
# 🔘  HANDLERS DE CALLBACK
# ══════════════════════════════════════════════

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    import grupo
    data = event.data.decode()
    chat_id = event.chat_id
    sender_id = event.sender_id

    try:
        message = await event.get_message()

        # ── Menu Principal ──
        if data == "cmd_menu":
            # Limpar estados pendentes
            search_pending.pop(chat_id, None)
            tg_search_pending.pop(chat_id, None)
            cpf_pending.pop(chat_id, None)
            pending_action.pop(chat_id, None)
            limpar_compositor(chat_id)

            await message.edit(
                f"╔══════════════════════════════════╗\n"
                f"║  🕵️ **User Info Bot Pro v{BOT_VERSION}**     ║\n"
                f"╚══════════════════════════════════╝\n\n"
                f"Selecione uma opção:",
                parse_mode='md', buttons=menu_principal_buttons(sender_id)
            )

        # ══════════════════════════════════════
        # 🔍  CONSULTA CPF
        # ══════════════════════════════════════
        elif data == "cmd_consultar_cpf":
            cpf_pending[chat_id] = True
            await message.edit(
                "╔══════════════════════════════════╗\n"
                "║  🔎 **CONSULTA CPF**               ║\n"
                "╚══════════════════════════════════╝\n\n"
                "📝 **Envie o CPF** (apenas números):\n\n"
                "• Exemplo: `12345678900`\n"
                "• Ou com pontuação: `123.456.789-00`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "_Aguardando CPF..._",
                parse_mode='md', buttons=voltar_button()
            )

        # ══════════════════════════════════════
        # 📡  AUTO-RESPOSTA EM GRUPOS
        # ══════════════════════════════════════
        elif data == "cmd_auto_resposta":
            if not is_admin(sender_id):
                await event.answer("🔒 Apenas o administrador.", alert=True)
                return
            config = ar_carregar_config()
            total = len(config.get("grupos", {}))
            auto = "✅ Ativo" if config.get("respostas_auto", True) else "❌ Desativado"
            await message.edit(
                f"╔══════════════════════════════════╗\n"
                f"║  📡 **AUTO-RESPOSTA EM GRUPOS**    ║\n"
                f"╚══════════════════════════════════╝\n\n"
                f"📊 Grupos configurados: **{total}**\n"
                f"🔄 Auto-resposta: **{auto}**\n\n"
                f"**Como funciona:**\n"
                f"Quando alguém te menciona em um grupo configurado:\n"
                f"• Se enviar CPF → Consulta automática\n"
                f"• Sem CPF → Resposta padrão\n\n"
                f"_Configure os grupos abaixo:_",
                parse_mode='md', buttons=auto_resposta_menu_buttons()
            )

        elif data == "ar_add_grupo":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            pending_action[chat_id] = "ar_aguardando_grupo_id"
            await message.edit(
                "➕ **Adicionar Grupo para Auto-Resposta**\n\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "📝 **Envie o ID do grupo** (número negativo):\n\n"
                "• Exemplo: `-1001234567890`\n\n"
                "💡 Para descobrir o ID, adicione o bot ao grupo e use `/id` lá.\n\n"
                "_Aguardando ID do grupo..._",
                parse_mode='md', buttons=voltar_button()
            )

        elif data == "ar_rem_grupo":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            config = ar_carregar_config()
            grupos = config.get("grupos", {})
            if not grupos:
                await message.edit(
                    "❌ **Nenhum grupo configurado.**\nAdicione um grupo primeiro.",
                    parse_mode='md', buttons=auto_resposta_menu_buttons()
                )
                return
            btns = []
            for gid, info in grupos.items():
                nome = info.get("nome", gid)
                btns.append([Button.inline(f"🗑️ {nome} ({gid})", f"ar_remover_{gid}".encode())])
            btns.append([Button.inline("🔙 Voltar", b"cmd_auto_resposta")])
            await message.edit("➖ **Selecione o grupo para remover:**", parse_mode='md', buttons=btns)

        elif data.startswith("ar_remover_"):
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            gid = data.replace("ar_remover_", "")
            sucesso, nome = ar_remover_grupo(gid)
            if sucesso:
                await message.edit(
                    f"✅ **Grupo removido!**\n\n🗑️ `{nome}` (`{gid}`)",
                    parse_mode='md', buttons=auto_resposta_menu_buttons()
                )
            else:
                await event.answer("❌ Grupo não encontrado.", alert=True)

        elif data == "ar_set_resposta":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            config = ar_carregar_config()
            grupos = config.get("grupos", {})
            if not grupos:
                await message.edit(
                    "❌ **Nenhum grupo configurado.**",
                    parse_mode='md', buttons=auto_resposta_menu_buttons()
                )
                return
            btns = []
            for gid, info in grupos.items():
                nome = info.get("nome", gid)
                btns.append([Button.inline(f"💬 {nome}", f"ar_setresp_{gid}".encode())])
            btns.append([Button.inline("🔙 Voltar", b"cmd_auto_resposta")])
            await message.edit(
                "💬 **Selecione o grupo para definir resposta padrão:**\n\n"
                "_A resposta padrão é enviada quando você é citado mas não há CPF._",
                parse_mode='md', buttons=btns
            )

        elif data.startswith("ar_setresp_"):
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            gid = data.replace("ar_setresp_", "")
            pending_action[chat_id] = f"ar_aguardando_resposta_{gid}"
            config = ar_carregar_config()
            resp_atual = config.get("grupos", {}).get(gid, {}).get("resposta_padrao", "Nenhuma")
            await message.edit(
                f"💬 **Definir Resposta Padrão**\n\n"
                f"📍 Grupo: `{gid}`\n"
                f"📝 Atual: _{resp_atual}_\n\n"
                f"**Envie a nova resposta padrão:**\n"
                f"_Suporta Markdown. Envie `limpar` para remover._",
                parse_mode='md', buttons=voltar_button()
            )

        elif data == "ar_listar_grupos":
            config = ar_carregar_config()
            grupos = config.get("grupos", {})
            if not grupos:
                await message.edit(
                    "📋 **Nenhum grupo configurado.**",
                    parse_mode='md', buttons=auto_resposta_menu_buttons()
                )
                return
            text = "📋 **Grupos de Auto-Resposta:**\n\n"
            for i, (gid, info) in enumerate(grupos.items(), 1):
                nome = info.get("nome", "Sem nome")
                resp = info.get("resposta_padrao", "Padrão")
                text += f"**{i}.** `{nome}`\n   🔢 ID: `{gid}`\n"
                text += f"   💬 _{resp[:30] if resp else 'Padrão'}{'...' if resp and len(resp) > 30 else ''}_\n\n"
            auto = "✅" if config.get("respostas_auto", True) else "❌"
            text += f"🔄 Auto-resposta: {auto}"
            await message.edit(text, parse_mode='md', buttons=auto_resposta_menu_buttons())

        elif data == "ar_toggle":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            novo_estado = ar_toggle()
            estado = "✅ Ativado" if novo_estado else "❌ Desativado"
            await event.answer(f"Auto-resposta: {estado}", alert=True)
            await message.edit(
                f"📡 **Auto-Resposta: {estado}**\n\n_Alteração aplicada._",
                parse_mode='md', buttons=auto_resposta_menu_buttons()
            )

        # ══════════════════════════════════════
        # ✉️  COMPOSITOR DE MENSAGENS
        # ══════════════════════════════════════
        elif data == "cmd_compositor":
            if not is_admin(sender_id):
                await event.answer("🔒 Apenas o administrador.", alert=True)
                return
            await message.edit(
                "╔══════════════════════════════════╗\n"
                "║  ✉️ **COMPOSITOR DE MENSAGENS**    ║\n"
                "╚══════════════════════════════════╝\n\n"
                "📝 Crie mensagens **Markdown** personalizadas\n"
                "🔘 Adicione **botões inline** com URLs\n"
                "🔗 Use **camuflagem de URL** no texto\n"
                "📤 Envie para **qualquer grupo**\n\n"
                "**Funcionalidades:**\n"
                "• ✍️ Texto Markdown completo\n"
                "• 🔘 Botões inline com URLs\n"
                "• 🔗 Links camuflados `[texto](url)`\n"
                "• 📤 Seleção de grupo destino\n"
                "• 👁️ Preview antes de enviar\n"
                "• 💾 Salvar como template\n\n"
                "_Selecione uma opção:_",
                parse_mode='md', buttons=compositor_menu_buttons()
            )

        elif data == "msg_nova":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            iniciar_compositor(chat_id)
            pending_action[chat_id] = "msg_aguardando_texto"
            await message.edit(
                "╔══════════════════════════════════╗\n"
                "║  ✍️ **ETAPA 1 — TEXTO**            ║\n"
                "╚══════════════════════════════════╝\n\n"
                "📝 **Envie o texto da mensagem.**\n\n"
                "**Formatação Markdown suportada:**\n"
                "• `**negrito**` → **negrito**\n"
                "• `_itálico_` → _itálico_\n"
                "• `` `código` `` → `código`\n"
                "• `[texto](url)` → link camuflado\n\n"
                "**Exemplo com URL camuflada:**\n"
                "`Acesse [nosso site](https://exemplo.com) agora!`\n\n"
                "_Envie o texto completo da mensagem:_",
                parse_mode='md', buttons=[
                    [Button.inline("❌ Cancelar", b"msg_cancelar")]
                ]
            )

        elif data == "msg_add_botoes":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            pending_action[chat_id] = "msg_aguardando_botoes"
            await message.edit(
                "╔══════════════════════════════════╗\n"
                "║  🔘 **ETAPA 2 — BOTÕES INLINE**   ║\n"
                "╚══════════════════════════════════╝\n\n"
                "📝 **Envie os botões no formato:**\n\n"
                "```\n"
                "Texto do Botão | https://link.com\n"
                "```\n\n"
                "**Para múltiplos botões na mesma linha:**\n"
                "```\n"
                "Botão 1 | https://link1.com , Botão 2 | https://link2.com\n"
                "```\n\n"
                "**Para fileiras separadas, use linhas separadas:**\n"
                "```\n"
                "Site Oficial | https://site.com\n"
                "Canal | https://t.me/canal , Grupo | https://t.me/grupo\n"
                "```\n\n"
                "_Envie os botões:_",
                parse_mode='md', buttons=[
                    [Button.inline("⏭️ Pular — Sem botões", b"msg_pular_botoes")],
                    [Button.inline("❌ Cancelar", b"msg_cancelar")]
                ]
            )

        elif data == "msg_pular_botoes":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            pular_botoes(chat_id)
            await _mostrar_selecao_grupo(message, chat_id, sender_id)

        elif data.startswith("msg_grupo_"):
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            grupo_id = data.replace("msg_grupo_", "")
            # Buscar nome do grupo
            try:
                entity = await user_client.get_entity(int(grupo_id))
                grupo_nome = getattr(entity, 'title', None) or "Grupo"
            except Exception:
                grupo_nome = grupo_id
            definir_grupo(chat_id, grupo_id, grupo_nome)
            # Mostrar preview + confirmação
            estado = obter_estado(chat_id)
            preview = formatar_preview(estado["mensagem"], estado["botoes_texto"])
            await message.edit(
                f"{preview}\n\n"
                f"📍 **Destino:** {grupo_nome} (`{grupo_id}`)\n\n"
                f"_Confirme o envio:_",
                parse_mode='md', buttons=compositor_confirmar_buttons()
            )

        elif data == "msg_enviar":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            sucesso, status_msg = await enviar_mensagem(bot, user_client, chat_id)
            await message.edit(status_msg, parse_mode='md', buttons=compositor_menu_buttons())

        elif data == "msg_salvar_template":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            pending_action[chat_id] = "msg_aguardando_nome_template"
            await message.edit(
                "💾 **Salvar Template**\n\n"
                "📝 Envie um nome para este template:\n\n"
                "_Ex: Promoção Semanal, Aviso Geral, etc._",
                parse_mode='md', buttons=[
                    [Button.inline("❌ Cancelar", b"msg_cancelar")]
                ]
            )

        elif data == "msg_editar":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            iniciar_compositor(chat_id)
            pending_action[chat_id] = "msg_aguardando_texto"
            await message.edit(
                "✏️ **Reescrevendo...**\n\n📝 Envie o novo texto da mensagem:",
                parse_mode='md', buttons=[
                    [Button.inline("❌ Cancelar", b"msg_cancelar")]
                ]
            )

        elif data == "msg_cancelar":
            limpar_compositor(chat_id)
            pending_action.pop(chat_id, None)
            await message.edit(
                "❌ **Composição cancelada.**",
                parse_mode='md', buttons=compositor_menu_buttons()
            )

        elif data == "msg_templates":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            templates = carregar_templates()
            if not templates:
                await message.edit(
                    "📋 **Nenhum template salvo.**\n\nCrie um com ✉️ Nova Mensagem.",
                    parse_mode='md', buttons=compositor_menu_buttons()
                )
                return
            text = "📋 **Templates Salvos:**\n\n"
            btns = []
            for i, t in enumerate(templates[-10:]):
                text += f"**{i+1}.** {t['nome']} — `{t['criado_em']}`\n"
                btns.append([Button.inline(f"📄 {t['nome']}", f"msg_tpl_{i}".encode())])
            btns.append([Button.inline("🔙 Voltar", b"cmd_compositor")])
            await message.edit(text, parse_mode='md', buttons=btns)

        elif data.startswith("msg_tpl_"):
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            idx = int(data.replace("msg_tpl_", ""))
            templates = carregar_templates()
            if idx < len(templates):
                t = templates[idx]
                iniciar_compositor(chat_id)
                definir_mensagem(chat_id, t["mensagem"])
                if t.get("botoes"):
                    botoes_texto = "\n".join([
                        ", ".join([f"{b[0]} | {b[1]}" for b in fileira])
                        for fileira in t["botoes"]
                    ])
                    definir_botoes(chat_id, botoes_texto)
                else:
                    pular_botoes(chat_id)
                await _mostrar_selecao_grupo(message, chat_id, sender_id)
            else:
                await event.answer("❌ Template não encontrado.", alert=True)

        elif data == "msg_guia":
            await message.edit(
                "╔══════════════════════════════════╗\n"
                "║  📖 **GUIA DE FORMATAÇÃO**         ║\n"
                "╚══════════════════════════════════╝\n\n"
                "**Markdown:**\n"
                "• `**negrito**` → **negrito**\n"
                "• `_itálico_` → _itálico_\n"
                "• `` `código` `` → `código`\n"
                "• `~~riscado~~` → ~~riscado~~\n\n"
                "**Links Camuflados:**\n"
                "• `[Clique Aqui](https://site.com)`\n"
                "→ Mostra 'Clique Aqui' como link\n\n"
                "**Botões Inline:**\n"
                "```\n"
                "Texto | https://link.com\n"
                "Btn1 | url1 , Btn2 | url2\n"
                "```\n"
                "• Cada **linha** = uma fileira\n"
                "• **Vírgula** separa botões na mesma fileira\n"
                "• Pipe `|` separa texto da URL\n\n"
                "**Exemplo Completo:**\n"
                "```\n"
                "🎉 **Promoção Especial!**\n"
                "\n"
                "Aproveite [esta oferta](https://link.com)\n"
                "com **desconto exclusivo**!\n"
                "```\n"
                "Botões:\n"
                "```\n"
                "🛒 Comprar | https://loja.com\n"
                "📱 Canal | https://t.me/canal , 💬 Suporte | https://t.me/suporte\n"
                "```",
                parse_mode='md', buttons=compositor_menu_buttons()
            )

        # ══════════════════════════════════════
        # 🔍  BUSCA E PERFIL (existentes)
        # ══════════════════════════════════════
        elif data == "cmd_buscar":
            search_pending[chat_id] = True
            await message.edit(
                "🔍 **Modo de Busca Ativo**\n\n"
                "• 🔢 **ID** — ex: `123456789`\n"
                "• 🆔 **@username** — ex: `@exemplo`\n"
                "• 📛 **Nome** — ex: `João`\n\n"
                "💡 _Busca no banco local primeiro, depois API!_\n\n"
                "_Aguardando..._",
                parse_mode='md', buttons=voltar_button()
            )

        elif data == "cmd_tg_search":
            tg_search_pending[chat_id] = True
            await message.edit(
                "🌐 **Consulta Direta — API Telegram**\n\n"
                "• 🔢 **ID numérico**\n"
                "• 🆔 **@username**\n\n"
                "⚡ _Salva automaticamente no banco_\n\n"
                "_Aguardando..._",
                parse_mode='md', buttons=voltar_button()
            )

        elif data == "cmd_stats":
            db = carregar_dados()
            groups_db = carregar_grupos_db()
            total_users = len(db)
            total_changes = sum(len(d.get("historico", [])) for d in db.values())
            total_names = sum(1 for d in db.values() for h in d.get("historico", []) if h["tipo"] == "NOME")
            total_usernames = sum(1 for d in db.values() for h in d.get("historico", []) if h["tipo"] == "USER")
            with_history = sum(1 for d in db.values() if d.get("historico"))
            total_admins = sum(1 for d in db.values() if d.get("grupos_admin"))
            total_bans = sum(len(d.get("grupos_banido", [])) for d in db.values())
            total_groups_db = len(groups_db)
            scan_possiveis = sum(1 for g in groups_db.values() if g.get("scan_possivel", False))
            last = grupo.scan_stats.get("last_scan", "Nunca")

            origens = {}
            for d in db.values():
                o = d.get("origem", "?")
                origens[o] = origens.get(o, 0) + 1
            origem_text = "".join(
                f"├ 🏷️ {o}: **{c}**\n"
                for o, c in sorted(origens.items(), key=lambda x: -x[1])
            )

            await message.edit(
                f"╔══════════════════════════════════╗\n"
                f"║  📊 **ESTATÍSTICAS COMPLETAS**     ║\n"
                f"╚══════════════════════════════════╝\n\n"
                f"👥 **Banco:** **{total_users}** usuários | **{total_groups_db}** grupos ({scan_possiveis} com scan)\n"
                f"├ 🔔 Com alterações: **{with_history}** | 👑 Admins: **{total_admins}** | 🚫 Bans: **{total_bans}**\n"
                f"└ 📊 Cobertura: **{(with_history/total_users*100) if total_users else 0:.1f}%**\n\n"
                f"📝 **Alterações:** 📛 Nomes: **{total_names}** | 🆔 Users: **{total_usernames}** | Total: **{total_changes}**\n\n"
                f"🏷️ **Origens:**\n{origem_text}\n"
                f"⚙️ Última varredura: `{last}` | Threads: **{'✅' if grupo.thread_scan_active else '❌'}**\n"
                f"🔄 Ciclo: Completa → {SCAN_INTERVAL // 60}min → Leve → {THREAD_SCAN_INTERVAL // 60}min\n"
                f"💾 Banco: **{os.path.getsize(FILE_PATH) // 1024 if os.path.exists(FILE_PATH) else 0} KB**",
                parse_mode='md', buttons=voltar_button()
            )

        elif data == "cmd_scan":
            if not is_admin(sender_id):
                await event.answer("🔒 Apenas o administrador.", alert=True)
                return
            if grupo.scan_running:
                await event.answer("⏳ Já em andamento!", alert=True)
            else:
                await event.answer("🔄 Varredura completa iniciada!")
                asyncio.create_task(executar_varredura(user_client, notify_chat=chat_id))

        elif data == "cmd_groups" or data.startswith("groups_page_"):
            if not is_admin(sender_id):
                await event.answer("🔒 Apenas o administrador.", alert=True)
                return
            page = int(data.split("_")[-1]) if data.startswith("groups_page_") else 0
            groups_db = carregar_grupos_db()
            all_groups = sorted(groups_db.values(), key=lambda x: x.get("nome", ""))
            chunk, page, total_pages = paginar_lista(all_groups, page)

            if not chunk:
                text = "📂 **Nenhum grupo registrado.**\nInicie uma varredura."
            else:
                text = f"📂 **Grupos Monitorados** (pág. {page + 1}/{total_pages})\n\n"
                for g in chunk:
                    icon = "✅" if g.get("scan_possivel") else "🔒"
                    text += f"{icon} **{g.get('nome', '?')}**\n   👥 {g.get('membros_coletados', 0)} | `{g.get('ultimo_scan', 'Nunca')}`\n\n"
            await message.edit(text, parse_mode='md', buttons=paginar_buttons("groups", page, total_pages))

        elif data == "cmd_threads":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            await message.edit(
                f"🧵 **Threads de Varredura Leve**\n\n"
                f"📡 Status: {'✅ ATIVAS' if grupo.thread_scan_active else '❌ PAUSADAS'}\n"
                f"⏱️ Intervalo: **{THREAD_SCAN_INTERVAL // 60} min**\n\n"
                f"_Varrem todos os grupos ligeiramente a cada ciclo._",
                parse_mode='md', buttons=[
                    [Button.inline(
                        "⏸️ Pausar Threads" if grupo.thread_scan_active else "▶️ Ativar Threads",
                        b"toggle_threads"
                    )],
                    [Button.inline("🔙 Menu", b"cmd_menu")]
                ]
            )

        elif data == "toggle_threads":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            grupo.thread_scan_active = not grupo.thread_scan_active
            await event.answer(
                f"Threads {'ativadas ✅' if grupo.thread_scan_active else 'pausadas ⏸️'}!",
                alert=True
            )
            await message.edit(
                f"🧵 **Threads:** {'✅ ATIVAS' if grupo.thread_scan_active else '❌ PAUSADAS'}\n\n"
                f"_Alteração aplicada._",
                parse_mode='md', buttons=[
                    [Button.inline(
                        "⏸️ Pausar Threads" if grupo.thread_scan_active else "▶️ Ativar Threads",
                        b"toggle_threads"
                    )],
                    [Button.inline("🔙 Menu", b"cmd_menu")]
                ]
            )

        elif data == "cmd_recent" or data.startswith("recent_page_"):
            page = int(data.split("_")[-1]) if data.startswith("recent_page_") else 0
            db = carregar_dados()
            all_changes = []
            for uid, dados in db.items():
                for h in dados.get("historico", []):
                    all_changes.append({**h, "uid": uid, "nome": dados["nome_atual"]})
            all_changes.sort(key=lambda x: x["data"], reverse=True)
            chunk, page, total_pages = paginar_lista(all_changes, page)

            if not chunk:
                text = "📋 **Nenhuma alteração registrada.**"
            else:
                text = f"📋 **Últimas Alterações** (pág. {page + 1}/{total_pages})\n\n"
                for c in chunk:
                    emoji = "📛" if c["tipo"] == "NOME" else "🆔"
                    text += f"{emoji} `{c['data']}`\n   👤 {c['nome']} — {c['de']} ➜ {c['para']}\n\n"
            await message.edit(text, parse_mode='md', buttons=paginar_buttons("recent", page, total_pages))

        elif data == "cmd_export":
            if not is_admin(sender_id):
                await event.answer("🔒", alert=True); return
            if os.path.exists(FILE_PATH):
                await bot.send_file(
                    chat_id, FILE_PATH,
                    caption=f"📤 **Banco exportado!** 👥 {len(carregar_dados())} usuários",
                    parse_mode='md'
                )
                if os.path.exists(GROUPS_DB_PATH):
                    await bot.send_file(
                        chat_id, GROUPS_DB_PATH,
                        caption="📂 **Grupos exportado!**",
                        parse_mode='md'
                    )
                await event.answer("✅ Enviado!")
            else:
                await event.answer("❌ Banco vazio!", alert=True)

        elif data == "cmd_config":
            await message.edit(
                f"⚙️ **Configurações do Bot**\n\n"
                f"🔄 **Ciclo de Varredura:**\n"
                f"├ 📡 Completa → aguarda **{SCAN_INTERVAL // 60} min** → repete\n"
                f"├ 🧵 Leve → aguarda **{THREAD_SCAN_INTERVAL // 60} min** → repete\n"
                f"└ Threads: {'✅ Ativas' if grupo.thread_scan_active else '❌ Pausadas'}\n\n"
                f"📜 Máx hist: **{MAX_HISTORY}** | 📄 Pág: **{ITEMS_PER_PAGE}**\n"
                f"💾 `{FILE_PATH}`\n📂 `{GROUPS_DB_PATH}`",
                parse_mode='md', buttons=voltar_button()
            )

        elif data == "cmd_about":
            await message.edit(
                f"╔══════════════════════════════════╗\n"
                f"║  ℹ️ **SOBRE O BOT**                ║\n"
                f"╚══════════════════════════════════╝\n\n"
                f"🕵️ **User Info Bot Pro v{BOT_VERSION}** — _{BOT_CODENAME}_\n\n"
                f"• 🔍 Busca local + 🌐 API Telegram\n"
                f"• 🔎 Consulta CPF via API\n"
                f"• 📡 Auto-resposta em grupos\n"
                f"• ✉️ Compositor de mensagens com botões inline\n"
                f"• 🔗 Camuflagem de URLs\n"
                f"• 📡 Varredura completa sequencial\n"
                f"• 🧵 Varredura leve contínua\n"
                f"• 👑 Detecção admins + 🚫 Registro bans\n"
                f"• 📜 Histórico paginado + 📤 Exportação\n"
                f"• 🆔 Auto-registro de usuários\n\n"
                f"⚡ Telethon asyncio | 💾 JSON persistente | 🛡️ Anti-flood\n\n"
                f"👨‍💻 **Edivaldo Silva** @Edkd1 | v{BOT_VERSION}",
                parse_mode='md', buttons=voltar_button()
            )

        # ── Perfis ──
        elif data.startswith("profile_"):
            uid = data.replace("profile_", "")
            db = carregar_dados()
            if uid in db:
                await message.edit(
                    formatar_perfil(db[uid]), parse_mode='md',
                    buttons=perfil_buttons(uid)
                )
            else:
                await event.answer("❌ Não encontrado.")

        elif data.startswith("apilookup_"):
            uid = data.replace("apilookup_", "")
            await event.answer("🌐 Consultando...")
            dados_api = await consultar_telegram_api(user_client, uid)
            if dados_api:
                status = await verificar_status_em_grupos(user_client, int(uid))
                db = carregar_dados()
                if uid in db:
                    db[uid]["grupos_admin"] = [{"grupo": g["grupo"], "cargo": g["cargo"]} for g in status["admin_em"]]
                    db[uid]["grupos_banido"] = [{"grupo": g["grupo"]} for g in status["banido_de"]]
                    db[uid]["dados_api"] = dados_api
                    salvar_dados(db)
                await message.edit(
                    formatar_perfil_api(dados_api), parse_mode='md',
                    buttons=[
                        [Button.inline("👤 Perfil Completo", f"profile_{uid}".encode())],
                        [Button.inline("🔙 Menu", b"cmd_menu")]
                    ]
                )
            else:
                await message.edit(
                    "❌ **Não foi possível consultar.**", parse_mode='md',
                    buttons=[
                        [Button.inline("👤 Perfil Local", f"profile_{uid}".encode())],
                        [Button.inline("🔙 Menu", b"cmd_menu")]
                    ]
                )

        elif data.startswith("apiview_"):
            uid = data.replace("apiview_", "")
            db = carregar_dados()
            if uid in db and "dados_api" in db[uid]:
                await message.edit(
                    formatar_perfil_api(db[uid]["dados_api"]), parse_mode='md',
                    buttons=[
                        [Button.inline("👤 Perfil", f"profile_{uid}".encode()),
                         Button.inline("🔄 Atualizar", f"apilookup_{uid}".encode())],
                        [Button.inline("🔙 Menu", b"cmd_menu")]
                    ]
                )
            else:
                await event.answer("Sem dados API. Use Consultar API.")

        elif data.startswith("gadmin_"):
            parts = data.split("_")
            uid, page = parts[1], int(parts[2]) if len(parts) > 2 else 0
            db = carregar_dados()
            if uid not in db:
                await event.answer("❌"); return
            lista = db[uid].get("grupos_admin", [])
            chunk, page, total_pages = paginar_lista(lista, page)
            text = f"👑 **Admin** — `{db[uid]['nome_atual']}`\nPág. {page+1}/{total_pages} | Total: **{len(lista)}**\n\n"
            for g in chunk:
                e = "👑" if g.get("cargo") == "Criador" else "🛡️"
                text += f"{e} **{g.get('grupo', '?')}** — _{g.get('cargo', 'Admin')}_\n"
            if not chunk: text += "_Nenhum._\n💡 _Use varredura ou API._"
            btns = paginar_buttons(f"gadmin_{uid}", page, total_pages)
            btns.insert(0, [Button.inline("👤 Perfil", f"profile_{uid}".encode())])
            await message.edit(text, parse_mode='md', buttons=btns)

        elif data.startswith("gban_"):
            parts = data.split("_")
            uid, page = parts[1], int(parts[2]) if len(parts) > 2 else 0
            db = carregar_dados()
            if uid not in db:
                await event.answer("❌"); return
            lista = db[uid].get("grupos_banido", [])
            chunk, page, total_pages = paginar_lista(lista, page)
            text = f"🚫 **Bans** — `{db[uid]['nome_atual']}`\nPág. {page+1}/{total_pages} | Total: **{len(lista)}**\n\n"
            for g in chunk:
                text += f"🚫 **{g.get('grupo', '?')}** — `{g.get('data', 'N/A')}`\n"
            if not chunk: text += "_Nenhum ban._"
            btns = paginar_buttons(f"gban_{uid}", page, total_pages)
            btns.insert(0, [Button.inline("👤 Perfil", f"profile_{uid}".encode())])
            await message.edit(text, parse_mode='md', buttons=btns)

        elif data.startswith("gmember_"):
            parts = data.split("_")
            uid, page = parts[1], int(parts[2]) if len(parts) > 2 else 0
            db = carregar_dados()
            if uid not in db:
                await event.answer("❌"); return
            lista = db[uid].get("grupos", [])
            chunk, page, total_pages = paginar_lista(lista, page)
            text = f"📂 **Grupos Membro** — `{db[uid]['nome_atual']}`\nPág. {page+1}/{total_pages} | Total: **{len(lista)}**\n\n"
            for g in chunk:
                text += f"📂 {g}\n"
            if not chunk: text += "_Nenhum._"
            btns = paginar_buttons(f"gmember_{uid}", page, total_pages)
            btns.insert(0, [Button.inline("👤 Perfil", f"profile_{uid}".encode())])
            await message.edit(text, parse_mode='md', buttons=btns)

        elif data.startswith("hist_"):
            parts = data.split("_")
            uid, page = parts[1], int(parts[2]) if len(parts) > 2 else 0
            db = carregar_dados()
            if uid not in db:
                await event.answer("❌"); return
            historico = list(reversed(db[uid].get("historico", [])))
            chunk, page, total_pages = paginar_lista(historico, page)
            text = f"📜 **Histórico** — `{db[uid]['nome_atual']}`\nPág. {page+1}/{total_pages} | Total: **{len(historico)}**\n\n"
            for h in chunk:
                emoji = "📛" if h.get("tipo") == "NOME" else "🆔"
                text += f"{emoji} `{h['data']}`\n   {h['de']} ➜ {h['para']}\n   📍 _{h.get('grupo', 'N/A')}_\n\n"
            if not chunk: text += "_Nenhum registro._"
            btns = paginar_buttons(f"hist_{uid}", page, total_pages)
            btns.insert(0, [Button.inline("👤 Perfil", f"profile_{uid}".encode())])
            await message.edit(text, parse_mode='md', buttons=btns)

        elif data == "noop":
            await event.answer()
        else:
            await event.answer("⚠️ Ação não reconhecida.")

        try:
            await event.answer()
        except:
            pass

    except Exception as e:
        log(f"❌ Callback error: {e}")
        try:
            await event.answer("❌ Erro interno.")
        except:
            pass


# ══════════════════════════════════════════════
# 📤  HELPER — SELEÇÃO DE GRUPO PARA COMPOSITOR
# ══════════════════════════════════════════════

async def _mostrar_selecao_grupo(message, chat_id, sender_id):
    """Mostra lista de grupos para seleção no compositor."""
    try:
        btns = []
        async for dialog in user_client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                btns.append([Button.inline(
                    f"📂 {dialog.name[:35]}",
                    f"msg_grupo_{dialog.id}".encode()
                )])
            if len(btns) >= 15:
                break

        # Também adicionar grupos de auto-resposta
        config = ar_carregar_config()
        for gid, info in config.get("grupos", {}).items():
            nome = info.get("nome", gid)
            existe = any(f"msg_grupo_{gid}" in str(b) for row in btns for b in row)
            if not existe:
                btns.append([Button.inline(f"📡 {nome[:35]}", f"msg_grupo_{gid}".encode())])

        btns.append([Button.inline("❌ Cancelar", b"msg_cancelar")])

        await message.edit(
            "╔══════════════════════════════════╗\n"
            "║  📍 **ETAPA 3 — GRUPO DESTINO**    ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📂 **Selecione o grupo destino:**\n\n"
            "_Escolha onde a mensagem será enviada:_",
            parse_mode='md', buttons=btns
        )
    except Exception as e:
        await message.edit(
            f"❌ **Erro ao listar grupos:**\n`{e}`",
            parse_mode='md', buttons=compositor_menu_buttons()
        )


# ══════════════════════════════════════════════
# 💬  HANDLER: TEXTO LIVRE (PRIVADO)
# ══════════════════════════════════════════════

@bot.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))
async def text_handler(event):
    await registrar_interacao(event)
    chat_id = event.chat_id
    texto = event.text.strip()

    # ── Consulta CPF ──
    if chat_id in cpf_pending:
        del cpf_pending[chat_id]
        cpf = limpar_cpf(texto)
        if not cpf.isdigit() or len(cpf) != 11:
            await event.reply(
                "❌ **CPF inválido.**\n\nEnvie 11 dígitos numéricos.\nExemplo: `12345678900`",
                parse_mode='md', buttons=voltar_button()
            )
            return
        await event.reply("🔍 **Consultando...**", parse_mode='md')
        resultado = consultar_cpf(cpf)
        await event.reply(resultado, parse_mode='md', buttons=voltar_button())
        return

    # ── Ações pendentes (auto-resposta e compositor) ──
    action = pending_action.get(chat_id)

    if action == "ar_aguardando_grupo_id":
        del pending_action[chat_id]
        grupo_id = re.sub(r'[^\d\-]', '', texto)
        if not grupo_id or not grupo_id.lstrip('-').isdigit():
            await event.reply(
                "❌ **ID inválido.**\nExemplo: `-1001234567890`",
                parse_mode='md', buttons=voltar_button()
            )
            return
        nome_grupo = "Grupo"
        try:
            entity = await user_client.get_entity(int(grupo_id))
            nome_grupo = getattr(entity, 'title', None) or "Grupo"
        except Exception:
            pass
        ar_adicionar_grupo(grupo_id, nome_grupo)
        await event.reply(
            f"✅ **Grupo adicionado!**\n\n"
            f"📍 Nome: **{nome_grupo}**\n🔢 ID: `{grupo_id}`\n\n"
            f"_Agora quando citado nesse grupo, o bot responderá._",
            parse_mode='md', buttons=auto_resposta_menu_buttons()
        )
        return

    if action and action.startswith("ar_aguardando_resposta_"):
        gid = action.replace("ar_aguardando_resposta_", "")
        del pending_action[chat_id]
        if texto.lower() == "limpar":
            ar_definir_resposta(gid, "")
            await event.reply(
                "✅ **Resposta padrão removida!**\n_O bot usará a resposta genérica._",
                parse_mode='md', buttons=auto_resposta_menu_buttons()
            )
        else:
            ar_definir_resposta(gid, texto)
            await event.reply(
                f"✅ **Resposta padrão definida!**\n\n📍 Grupo: `{gid}`\n💬 _{texto}_",
                parse_mode='md', buttons=auto_resposta_menu_buttons()
            )
        return

    # ── Compositor: texto da mensagem ──
    if action == "msg_aguardando_texto":
        del pending_action[chat_id]
        definir_mensagem(chat_id, texto)
        preview = formatar_preview(texto)
        await event.reply(
            f"{preview}\n\n"
            f"✅ **Texto salvo!**\n\n"
            f"🔘 Deseja adicionar **botões inline**?",
            parse_mode='md', buttons=compositor_botoes_pergunta()
        )
        return

    # ── Compositor: botões ──
    if action == "msg_aguardando_botoes":
        del pending_action[chat_id]
        definir_botoes(chat_id, texto)
        estado = obter_estado(chat_id)
        preview = formatar_preview(estado["mensagem"], texto)
        await event.reply(
            f"{preview}\n\n✅ **Botões salvos!**",
            parse_mode='md'
        )
        # Mostrar seleção de grupo
        msg = await event.reply("⏳ _Carregando grupos..._", parse_mode='md')
        await _mostrar_selecao_grupo(msg, chat_id, event.sender_id)
        return

    # ── Compositor: nome do template ──
    if action == "msg_aguardando_nome_template":
        del pending_action[chat_id]
        estado = obter_estado(chat_id)
        if estado:
            salvar_template(texto, estado["mensagem"], estado["botoes_parsed"])
            await event.reply(
                f"💾 **Template salvo!**\n\n📝 Nome: **{texto}**",
                parse_mode='md', buttons=compositor_menu_buttons()
            )
        else:
            await event.reply("❌ Nenhuma mensagem para salvar.", buttons=compositor_menu_buttons())
        return

    # ── Busca Telegram API ──
    if chat_id in tg_search_pending:
        del tg_search_pending[chat_id]
        query = texto
        await event.reply("🌐 _Consultando..._", parse_mode='md')
        dados_api = await consultar_telegram_api(user_client, query)
        if dados_api:
            uid = str(dados_api["id"])
            status = await verificar_status_em_grupos(user_client, dados_api["id"])
            db = carregar_dados()
            if uid in db:
                db[uid]["grupos_admin"] = [{"grupo": g["grupo"], "cargo": g["cargo"]} for g in status["admin_em"]]
                db[uid]["grupos_banido"] = [{"grupo": g["grupo"]} for g in status["banido_de"]]
                salvar_dados(db)
                await event.reply(
                    formatar_perfil(db[uid]), parse_mode='md',
                    buttons=[
                        [Button.inline("🌐 API", f"apiview_{uid}".encode())],
                        [Button.inline("📜 Hist", f"hist_{uid}_0".encode())],
                        [Button.inline("👑", f"gadmin_{uid}_0".encode()),
                         Button.inline("🚫", f"gban_{uid}_0".encode())],
                        [Button.inline("🔙 Menu", b"cmd_menu")]
                    ]
                )
            else:
                await event.reply(
                    formatar_perfil_api(dados_api), parse_mode='md',
                    buttons=voltar_button()
                )
        else:
            await event.reply(
                f"❌ **Não encontrado** `{query}`",
                parse_mode='md', buttons=voltar_button()
            )
        return

    # ── Busca local ──
    if chat_id in search_pending:
        del search_pending[chat_id]
        query = texto
        results = buscar_usuario(query)

        if not results:
            await event.reply("🔎 _Consultando API..._", parse_mode='md')
            dados_api = await consultar_telegram_api(user_client, query)
            if dados_api:
                uid = str(dados_api["id"])
                db = carregar_dados()
                if uid in db:
                    await event.reply(
                        formatar_perfil(db[uid]), parse_mode='md',
                        buttons=[
                            [Button.inline("🌐 API", f"apiview_{uid}".encode())],
                            [Button.inline("📜 Hist", f"hist_{uid}_0".encode())],
                            [Button.inline("🔙 Menu", b"cmd_menu")]
                        ]
                    )
                else:
                    await event.reply(
                        formatar_perfil_api(dados_api), parse_mode='md',
                        buttons=voltar_button()
                    )
            else:
                await event.reply(
                    f"❌ **Nenhum resultado** `{query}`",
                    parse_mode='md', buttons=voltar_button()
                )
            return

        if len(results) == 1:
            uid = str(results[0]["id"])
            await event.reply(
                formatar_perfil(results[0]), parse_mode='md',
                buttons=perfil_buttons(uid)
            )
        else:
            text = f"🔍 **{len(results)} resultados** `{query}`:\n\n"
            await event.reply(text, parse_mode='md', buttons=resultado_multiplo_buttons(results))
        return

    # ── Sem ação — tenta CPF direto ou mostra menu ──
    cpf = limpar_cpf(texto)
    if cpf.isdigit() and len(cpf) == 11:
        await event.reply("🔍 **Consultando CPF...**", parse_mode='md')
        resultado = consultar_cpf(cpf)
        await event.reply(resultado, parse_mode='md', buttons=voltar_button())
    else:
        sender = await event.get_sender()
        await event.reply(
            "💡 Use o menu ou `/buscar termo` ou envie um CPF.",
            parse_mode='md',
            buttons=menu_principal_buttons(sender.id if sender else 0)
        )


# ══════════════════════════════════════════════
# 📡  HANDLER: MENSAGENS EM GRUPOS (USER CLIENT)
# ══════════════════════════════════════════════

@user_client.on(events.NewMessage(func=lambda e: e.is_group or e.is_channel))
async def grupo_handler(event):
    """Detecta menções ao dono em grupos configurados para auto-resposta."""
    try:
        await processar_mencao_grupo(event, OWNER_ID)
    except Exception as e:
        log(f"⚠️ Erro no handler de grupo: {e}")


# ══════════════════════════════════════════════
# 🚀  INICIALIZAÇÃO
# ══════════════════════════════════════════════

async def main():
    await user_client.start(PHONE)
    await bot.start(bot_token=BOT_TOKEN)

    log(f"🚀 ═══════════════════════════════════════")
    log(f"🚀 User Info Bot Pro v{BOT_VERSION} ({BOT_CODENAME})")
    log(f"🚀 👨‍💻 Créditos: Edivaldo Silva @Edkd1")
    log(f"🚀 👑 Dono: Edivaldo Silva (ID: {OWNER_ID})")
    log(f"🚀 ═══════════════════════════════════════")
    log(f"📡 Módulos ativos:")
    log(f"   🔍 Consulta CPF — API integrada")
    log(f"   📡 Auto-resposta em grupos")
    log(f"   ✉️ Compositor de mensagens")
    log(f"   📡 Varredura de grupos")
    log(f"📡 Ciclo de varredura:")
    log(f"   1️⃣  Varredura COMPLETA — todos os grupos")
    log(f"   2️⃣  Aguarda {SCAN_INTERVAL // 60} minutos")
    log(f"   3️⃣  Varredura LEVE (threads)")
    log(f"   4️⃣  Aguarda {THREAD_SCAN_INTERVAL // 60} minutos")
    log(f"   🔁 Repete o ciclo")
    log(f"")
    log(f"📡 Executando primeira varredura completa...")

    # 1. Primeira varredura completa imediata
    await executar_varredura(user_client, notify_chat=OWNER_ID)

    # 2. Iniciar ciclos automáticos
    asyncio.create_task(auto_scanner(user_client))
    asyncio.create_task(executar_threads_atualizacao(user_client))

    # 3. Notificar dono
    ar_config = ar_carregar_config()
    ar_total = len(ar_config.get("grupos", {}))
    ar_auto = "✅" if ar_config.get("respostas_auto", True) else "❌"

    await bot.send_message(
        OWNER_ID,
        f"🚀 **Bot Info Pro v{BOT_VERSION} iniciado!**\n\n"
        f"📡 **Módulos ativos:**\n"
        f"├ 🔍 Consulta CPF\n"
        f"├ 📡 Auto-resposta: {ar_auto} ({ar_total} grupos)\n"
        f"├ ✉️ Compositor de mensagens\n"
        f"├ 🔄 Varredura de grupos\n"
        f"└ 🧵 Threads de atualização\n\n"
        f"_Use /start para acessar o menu._",
        parse_mode='md'
    )

    print("✅ Bot ativo! Use /start, /buscar, /cpf ou /id")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        bot.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n👋 Bot finalizado com segurança!")
        log("Bot encerrado pelo usuário")

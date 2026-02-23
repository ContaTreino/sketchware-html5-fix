"""
🕵️ User Info Bot Pro v3.0 — Telethon Edition
Monitor profissional de alterações de nome/username em grupos do Telegram.

Créditos de criação: Edivaldo Silva @Edkd1
Refatorado e otimizado para Telethon (asyncio) com menus inline e paginação.

Funcionalidades:
- Monitoramento automático de grupos/canais
- Detecção de mudanças de nome e username
- Notificações em tempo real via bot
- Busca por ID, username ou nome parcial
- Histórico completo com paginação inline
- Estatísticas do banco de dados
- Painel administrativo com controles
- Exportação de dados em JSON/TXT
- Agendamento de varreduras automáticas
"""

import json
import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.errors import FloodWaitError
from telethon.tl.functions.users import GetFullUserRequest

# ══════════════════════════════════════════════
# ⚙️  CONFIGURAÇÕES
# ══════════════════════════════════════════════
API_ID = 00000                        # Obtenha em https://my.telegram.org
API_HASH = "xxxxxx"                   # Obtenha em https://my.telegram.org
PHONE = "+5511123456789"              # Seu número com código do país
BOT_TOKEN = "xxxxxxxxxx"             # Token do @BotFather
OWNER_ID = 2061557102                 # Edivaldo Silva @Edkd1

FOLDER_PATH = "data"
FILE_PATH = os.path.join(FOLDER_PATH, "user_database.json")
LOG_PATH = os.path.join(FOLDER_PATH, "monitor.log")
SESSION_USER = "session_monitor"
SESSION_BOT = "session_bot"

ITEMS_PER_PAGE = 8                    # Itens por página na paginação
SCAN_INTERVAL = 3600                  # Intervalo de varredura automática (segundos)
MAX_HISTORY = 50                      # Máximo de entradas no histórico por user

# ══════════════════════════════════════════════
# 📁  BANCO DE DADOS JSON
# ══════════════════════════════════════════════
os.makedirs(FOLDER_PATH, exist_ok=True)

def carregar_dados() -> dict:
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def salvar_dados(db: dict):
    try:
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
    except IOError as e:
        log(f"❌ Erro ao salvar banco: {e}")

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except IOError:
        pass

# ══════════════════════════════════════════════
# 🤖  CLIENTES TELETHON
# ══════════════════════════════════════════════
user_client = TelegramClient(SESSION_USER, API_ID, API_HASH)
bot = TelegramClient(SESSION_BOT, API_ID, API_HASH)

# Estado global
scan_running = False
scan_stats = {"last_scan": None, "users_scanned": 0, "groups_scanned": 0, "changes_detected": 0}


def is_admin(user_id: int) -> bool:
    """Verifica se o usuário é o administrador/dono do bot."""
    return user_id == OWNER_ID


async def registrar_interacao(event):
    """Registra automaticamente o usuário que interage com o bot no banco."""
    try:
        user = await event.get_sender()
        if not user or getattr(user, 'bot', False):
            return
        uid = str(user.id)
        db = carregar_dados()
        nome = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Sem nome"
        username = f"@{user.username}" if user.username else "Nenhum"
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        if uid not in db:
            db[uid] = {
                "id": user.id,
                "nome_atual": nome,
                "username_atual": username,
                "grupos": [],
                "primeiro_registro": agora,
                "historico": [],
                "origem": "interacao_bot"
            }
            salvar_dados(db)
            log(f"➕ Novo usuário registrado via interação: {nome} ({uid})")
        else:
            changed = False
            if db[uid]["nome_atual"] != nome:
                db[uid]["historico"].append({
                    "data": agora, "tipo": "NOME",
                    "de": db[uid]["nome_atual"], "para": nome,
                    "grupo": "Bot DM"
                })
                db[uid]["nome_atual"] = nome
                changed = True
            if db[uid]["username_atual"] != username:
                db[uid]["historico"].append({
                    "data": agora, "tipo": "USER",
                    "de": db[uid]["username_atual"], "para": username,
                    "grupo": "Bot DM"
                })
                db[uid]["username_atual"] = username
                changed = True
            if changed:
                if len(db[uid]["historico"]) > MAX_HISTORY:
                    db[uid]["historico"] = db[uid]["historico"][-MAX_HISTORY:]
                salvar_dados(db)
    except Exception as e:
        log(f"⚠️ Erro ao registrar interação: {e}")


# ══════════════════════════════════════════════
# 🔔  NOTIFICAÇÃO
# ══════════════════════════════════════════════
async def notificar(texto: str):
    try:
        await bot.send_message(OWNER_ID, texto, parse_mode='md')
    except Exception as e:
        log(f"Erro notificação: {e}")


# ══════════════════════════════════════════════
# 🎨  INTERFACE — MENUS INLINE
# ══════════════════════════════════════════════

def menu_principal_buttons(user_id: int = 0):
    btns = [
        [Button.inline("🔍 Buscar Usuário", b"cmd_buscar"),
         Button.inline("📊 Estatísticas", b"cmd_stats")],
    ]
    # Botões administrativos — somente para o dono
    if is_admin(user_id):
        btns.append(
            [Button.inline("🔄 Iniciar Varredura", b"cmd_scan"),
             Button.inline("📋 Últimas Alterações", b"cmd_recent")]
        )
        btns.append(
            [Button.inline("📤 Exportar Banco", b"cmd_export"),
             Button.inline("⚙️ Configurações", b"cmd_config")]
        )
    else:
        btns.append(
            [Button.inline("📋 Últimas Alterações", b"cmd_recent")]
        )
    btns.append([Button.inline("ℹ️ Sobre", b"cmd_about")])
    return btns

def voltar_button():
    return [[Button.inline("🔙 Menu Principal", b"cmd_menu")]]

def paginar_buttons(prefix: str, page: int, total_pages: int):
    btns = []
    nav = []
    if page > 0:
        nav.append(Button.inline("◀️ Anterior", f"{prefix}_page_{page - 1}".encode()))
    nav.append(Button.inline(f"📄 {page + 1}/{total_pages}", b"noop"))
    if page < total_pages - 1:
        nav.append(Button.inline("Próxima ▶️", f"{prefix}_page_{page + 1}".encode()))
    btns.append(nav)
    btns.append([Button.inline("🔙 Menu Principal", b"cmd_menu")])
    return btns


# ══════════════════════════════════════════════
# 🔍  BUSCA AVANÇADA
# ══════════════════════════════════════════════

def buscar_usuario(query: str) -> list:
    """Busca por ID, @username ou nome parcial. Retorna lista de matches."""
    db = carregar_dados()
    query_lower = query.lower().lstrip('@')
    results = []

    for uid, dados in db.items():
        # Match exato por ID
        if query == uid:
            results.append(dados)
            continue
        # Match por username
        username = dados.get("username_atual", "").lower().lstrip('@')
        if username and query_lower == username:
            results.insert(0, dados)
            continue
        # Match parcial por nome
        nome = dados.get("nome_atual", "").lower()
        if query_lower in nome or query_lower in username:
            results.append(dados)

    return results


def formatar_perfil(dados: dict) -> str:
    """Formata perfil completo de um usuário."""
    uid = dados.get("id", "?")
    nome = dados.get("nome_atual", "Desconhecido")
    username = dados.get("username_atual", "Nenhum")
    historico = dados.get("historico", [])
    total_changes = len(historico)

    # Últimas 5 alterações
    recent = historico[-5:]
    hist_text = ""
    for h in reversed(recent):
        emoji = "📛" if h.get("tipo") == "NOME" else "🆔"
        hist_text += f"  {emoji} `{h['data']}` — {h['de']} ➜ {h['para']}\n"

    if not hist_text:
        hist_text = "  _Nenhuma alteração registrada_\n"

    first_seen = historico[0]["data"] if historico else "N/A"
    last_change = historico[-1]["data"] if historico else "N/A"

    return f"""╔══════════════════════════╗
║  🕵️ **PERFIL DO USUÁRIO**  ║
╚══════════════════════════╝

👤 **Nome:** `{nome}`
🆔 **Username:** `{username}`
🔢 **ID:** `{uid}`

📊 **Resumo:**
├ 📝 Total de alterações: **{total_changes}**
├ 📅 Primeiro registro: `{first_seen}`
└ 🕐 Última alteração: `{last_change}`

📜 **Últimas Alterações:**
{hist_text}
_Créditos: @Edkd1_"""


# ══════════════════════════════════════════════
# 📡  VARREDURA DE GRUPOS
# ══════════════════════════════════════════════

async def executar_varredura(notify_chat=None):
    global scan_running, scan_stats
    if scan_running:
        if notify_chat:
            await bot.send_message(notify_chat, "⚠️ Uma varredura já está em andamento!")
        return

    scan_running = True
    scan_stats = {"last_scan": None, "users_scanned": 0, "groups_scanned": 0, "changes_detected": 0}
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    scan_stats["last_scan"] = agora
    db = carregar_dados()

    if notify_chat:
        await bot.send_message(
            notify_chat,
            "🔄 **Varredura iniciada...**\n\n⏳ Analisando todos os grupos e canais.\nVocê será notificado ao finalizar.",
            parse_mode='md'
        )

    log("🔄 Varredura iniciada")

    try:
        async for dialog in user_client.iter_dialogs():
            if not (dialog.is_group or dialog.is_channel):
                continue

            nome_grupo = dialog.name
            scan_stats["groups_scanned"] += 1
            log(f"📂 Varrendo: {nome_grupo}")

            try:
                async for user in user_client.iter_participants(dialog.id):
                    if user.bot:
                        continue

                    uid = str(user.id)
                    nome_atual = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Sem nome"
                    user_atual = f"@{user.username}" if user.username else "Nenhum"
                    scan_stats["users_scanned"] += 1

                    if uid not in db:
                        db[uid] = {
                            "id": user.id,
                            "nome_atual": nome_atual,
                            "username_atual": user_atual,
                            "grupos": [nome_grupo],
                            "primeiro_registro": agora,
                            "historico": []
                        }
                    else:
                        # Atualiza lista de grupos
                        if "grupos" not in db[uid]:
                            db[uid]["grupos"] = []
                        if nome_grupo not in db[uid]["grupos"]:
                            db[uid]["grupos"].append(nome_grupo)

                        # Detecta mudança de nome
                        if db[uid]["nome_atual"] != nome_atual:
                            scan_stats["changes_detected"] += 1
                            db[uid]["historico"].append({
                                "data": agora,
                                "tipo": "NOME",
                                "de": db[uid]["nome_atual"],
                                "para": nome_atual,
                                "grupo": nome_grupo
                            })
                            await notificar(
                                f"🔔 **ALTERAÇÃO DE NOME**\n\n"
                                f"👤 ID: `{uid}`\n"
                                f"❌ Antigo: `{db[uid]['nome_atual']}`\n"
                                f"✅ Novo: `{nome_atual}`\n"
                                f"📍 Grupo: _{nome_grupo}_"
                            )
                            db[uid]["nome_atual"] = nome_atual

                        # Detecta mudança de username
                        if db[uid]["username_atual"] != user_atual:
                            scan_stats["changes_detected"] += 1
                            db[uid]["historico"].append({
                                "data": agora,
                                "tipo": "USER",
                                "de": db[uid]["username_atual"],
                                "para": user_atual,
                                "grupo": nome_grupo
                            })
                            await notificar(
                                f"🆔 **MUDANÇA DE USERNAME**\n\n"
                                f"👤 Nome: `{nome_atual}`\n"
                                f"❌ Antigo: `{db[uid]['username_atual']}`\n"
                                f"✅ Novo: `{user_atual}`\n"
                                f"📍 Grupo: _{nome_grupo}_"
                            )
                            db[uid]["username_atual"] = user_atual

                        # Limita histórico
                        if len(db[uid]["historico"]) > MAX_HISTORY:
                            db[uid]["historico"] = db[uid]["historico"][-MAX_HISTORY:]

            except FloodWaitError as e:
                log(f"⏳ FloodWait: aguardando {e.seconds}s")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                log(f"⚠️ Erro no grupo {nome_grupo}: {e}")
                continue

    except Exception as e:
        log(f"❌ Erro na varredura: {e}")
    finally:
        salvar_dados(db)
        scan_running = False
        log(f"✅ Varredura concluída: {scan_stats['groups_scanned']} grupos, "
            f"{scan_stats['users_scanned']} usuários, {scan_stats['changes_detected']} alterações")

    if notify_chat:
        await bot.send_message(
            notify_chat,
            f"""✅ **Varredura Concluída!**

╔═══════════════════════╗
║  📊 **RESULTADO**       ║
╚═══════════════════════╝

📂 Grupos analisados: **{scan_stats['groups_scanned']}**
👥 Usuários verificados: **{scan_stats['users_scanned']}**
🔔 Alterações detectadas: **{scan_stats['changes_detected']}**
🕐 Horário: `{agora}`

_Próxima varredura automática em {SCAN_INTERVAL // 60} min_""",
            parse_mode='md',
            buttons=voltar_button()
        )


# ══════════════════════════════════════════════
# 🎮  HANDLERS DO BOT
# ══════════════════════════════════════════════

@bot.on(events.NewMessage(pattern='/start'))
async def cmd_start(event):
    await registrar_interacao(event)
    sender = await event.get_sender()
    uid = sender.id if sender else 0
    await event.respond(
        f"""╔══════════════════════════════╗
║  🕵️ **User Info Bot Pro v3.0**  ║
╚══════════════════════════════╝

Bem-vindo ao monitor profissional de usuários!

🔍 **Busque** por ID, @username ou nome
📊 **Monitore** alterações em tempo real
📜 **Histórico** completo de mudanças

━━━━━━━━━━━━━━━━━━━━━
👨‍💻 _Créditos: Edivaldo Silva @Edkd1_
⚡ _Powered by Telethon_
━━━━━━━━━━━━━━━━━━━━━

Selecione uma opção abaixo:""",
        parse_mode='md',
        buttons=menu_principal_buttons(uid)
    )


@bot.on(events.NewMessage(pattern='/menu'))
async def cmd_menu_msg(event):
    await registrar_interacao(event)
    await cmd_start(event)


@bot.on(events.NewMessage(pattern=r'/buscar\s+(.+)'))
async def cmd_buscar_text(event):
    await registrar_interacao(event)
    query = event.pattern_match.group(1).strip()
    results = buscar_usuario(query)

    if not results:
        await event.reply(
            "❌ **Nenhum usuário encontrado.**\n\n💡 Tente buscar por ID numérico, @username ou parte do nome.",
            parse_mode='md',
            buttons=voltar_button()
        )
        return

    if len(results) == 1:
        await event.reply(formatar_perfil(results[0]), parse_mode='md', buttons=voltar_button())
    else:
        # Múltiplos resultados — mostra lista paginada
        text = f"🔍 **{len(results)} resultados para** `{query}`:\n\n"
        btns = []
        for r in results[:10]:
            label = f"👤 {r['nome_atual']} | {r['username_atual']}"
            btns.append([Button.inline(label[:40], f"profile_{r['id']}".encode())])
        btns.append([Button.inline("🔙 Menu Principal", b"cmd_menu")])
        await event.reply(text, parse_mode='md', buttons=btns)


# ══════════════════════════════════════════════
# 🔘  HANDLERS DE CALLBACK (BOTÕES INLINE)
# ══════════════════════════════════════════════

# Estado de busca por chat
search_pending = {}

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode()
    chat_id = event.chat_id
    sender_id = event.sender_id

    try:
        message = await event.get_message()

        # ── Menu Principal ──
        if data == "cmd_menu":
            await message.edit(
                f"""╔══════════════════════════════╗
║  🕵️ **User Info Bot Pro v3.0**  ║
╚══════════════════════════════╝

Selecione uma opção:""",
                parse_mode='md',
                buttons=menu_principal_buttons(sender_id)
            )

        # ── Buscar ──
        elif data == "cmd_buscar":
            search_pending[chat_id] = True
            await message.edit(
                """🔍 **Modo de Busca Ativo**

━━━━━━━━━━━━━━━━━━━━━
📝 **Envie** um dos seguintes:

• 🔢 **ID numérico** — ex: `123456789`
• 🆔 **@username** — ex: `@exemplo`
• 📛 **Nome** (parcial) — ex: `João`

━━━━━━━━━━━━━━━━━━━━━
_Aguardando sua busca..._""",
                parse_mode='md',
                buttons=voltar_button()
            )

        # ── Estatísticas ──
        elif data == "cmd_stats":
            db = carregar_dados()
            total_users = len(db)
            total_changes = sum(len(d.get("historico", [])) for d in db.values())
            total_names = sum(1 for d in db.values() for h in d.get("historico", []) if h["tipo"] == "NOME")
            total_usernames = sum(1 for d in db.values() for h in d.get("historico", []) if h["tipo"] == "USER")

            with_history = sum(1 for d in db.values() if d.get("historico"))
            groups = set()
            for d in db.values():
                groups.update(d.get("grupos", []))

            last = scan_stats.get("last_scan", "Nunca")

            await message.edit(
                f"""╔══════════════════════════╗
║  📊 **ESTATÍSTICAS**       ║
╚══════════════════════════╝

👥 **Banco de Dados:**
├ 📋 Total de usuários: **{total_users}**
├ 📂 Grupos monitorados: **{len(groups)}**
├ 🔔 Usuários com alterações: **{with_history}**
└ 📊 Cobertura: **{(with_history/total_users*100) if total_users else 0:.1f}%**

📝 **Alterações Registradas:**
├ 📛 Mudanças de nome: **{total_names}**
├ 🆔 Mudanças de username: **{total_usernames}**
└ 📊 Total: **{total_changes}**

⚙️ **Sistema:**
├ 🕐 Última varredura: `{last}`
├ 🔄 Intervalo: `{SCAN_INTERVAL // 60} min`
└ 💾 Tamanho do banco: **{os.path.getsize(FILE_PATH) // 1024 if os.path.exists(FILE_PATH) else 0} KB**

_Créditos: @Edkd1_""",
                parse_mode='md',
                buttons=voltar_button()
            )

        # ── Iniciar Varredura (ADMIN ONLY) ──
        elif data == "cmd_scan":
            if not is_admin(sender_id):
                await event.answer("🔒 Apenas o administrador pode iniciar varreduras.", alert=True)
                return
            if scan_running:
                await event.answer("⏳ Varredura já em andamento!", alert=True)
            else:
                await event.answer("🔄 Varredura iniciada!")
                asyncio.create_task(executar_varredura(notify_chat=chat_id))

        # ── Últimas Alterações ──
        elif data == "cmd_recent" or data.startswith("recent_page_"):
            page = 0
            if data.startswith("recent_page_"):
                page = int(data.split("_")[-1])

            db = carregar_dados()
            all_changes = []
            for uid, dados in db.items():
                for h in dados.get("historico", []):
                    all_changes.append({
                        **h,
                        "uid": uid,
                        "nome": dados["nome_atual"]
                    })

            all_changes.sort(key=lambda x: x["data"], reverse=True)
            total = len(all_changes)
            total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
            page = min(page, total_pages - 1)
            start = page * ITEMS_PER_PAGE
            chunk = all_changes[start:start + ITEMS_PER_PAGE]

            if not chunk:
                text = "📋 **Nenhuma alteração registrada ainda.**\n\nInicie uma varredura para detectar mudanças."
            else:
                text = f"📋 **Últimas Alterações** (pág. {page + 1}/{total_pages})\n\n"
                for c in chunk:
                    emoji = "📛" if c["tipo"] == "NOME" else "🆔"
                    text += f"{emoji} `{c['data']}`\n"
                    text += f"   👤 {c['nome']} — {c['de']} ➜ {c['para']}\n\n"

            await message.edit(text, parse_mode='md', buttons=paginar_buttons("recent", page, total_pages))

        # ── Exportar (ADMIN ONLY) ──
        elif data == "cmd_export":
            if not is_admin(sender_id):
                await event.answer("🔒 Apenas o administrador pode exportar o banco.", alert=True)
                return
            if os.path.exists(FILE_PATH):
                await bot.send_file(
                    chat_id, FILE_PATH,
                    caption="📤 **Banco de dados exportado com sucesso!**\n\n_Créditos: @Edkd1_",
                    parse_mode='md'
                )
                await event.answer("✅ Arquivo enviado!")
            else:
                await event.answer("❌ Banco vazio!", alert=True)

        # ── Configurações ──
        elif data == "cmd_config":
            await message.edit(
                f"""⚙️ **Configurações Atuais**

━━━━━━━━━━━━━━━━━━━━━
🔄 Intervalo de varredura: **{SCAN_INTERVAL // 60} min**
📜 Máx. histórico/usuário: **{MAX_HISTORY}**
📄 Itens por página: **{ITEMS_PER_PAGE}**
💾 Banco: `{FILE_PATH}`
📝 Logs: `{LOG_PATH}`
━━━━━━━━━━━━━━━━━━━━━

_Para alterar, edite as constantes no código._
_Créditos: @Edkd1_""",
                parse_mode='md',
                buttons=voltar_button()
            )

        # ── Sobre ──
        elif data == "cmd_about":
            await message.edit(
                """╔══════════════════════════════╗
║  ℹ️ **SOBRE O BOT**           ║
╚══════════════════════════════╝

🕵️ **User Info Bot Pro v3.0**
_Monitor profissional de usuários_

━━━━━━━━━━━━━━━━━━━━━
**Funcionalidades:**
• 🔍 Busca por ID, @user ou nome
• 📡 Varredura automática de grupos
• 🔔 Notificações de alterações
• 📜 Histórico paginado
• 📤 Exportação de dados
• 📊 Estatísticas detalhadas

**Tecnologia:**
• ⚡ Telethon (asyncio)
• 💾 Banco JSON local
• 🛡️ Anti-flood integrado

━━━━━━━━━━━━━━━━━━━━━
👨‍💻 **Criado por:** Edivaldo Silva
📱 **Contato:** @Edkd1
🔖 **Versão:** 3.0 (Telethon)
━━━━━━━━━━━━━━━━━━━━━""",
                parse_mode='md',
                buttons=voltar_button()
            )

        # ── Perfil individual ──
        elif data.startswith("profile_"):
            uid = data.replace("profile_", "")
            db = carregar_dados()
            if uid in db:
                await message.edit(formatar_perfil(db[uid]), parse_mode='md', buttons=[
                    [Button.inline(f"📜 Histórico Completo", f"hist_{uid}_0".encode())],
                    [Button.inline("🔙 Menu Principal", b"cmd_menu")]
                ])
            else:
                await event.answer("❌ Usuário não encontrado no banco.")

        # ── Histórico paginado de um usuário ──
        elif data.startswith("hist_"):
            parts = data.split("_")
            uid = parts[1]
            page = int(parts[2]) if len(parts) > 2 else 0

            db = carregar_dados()
            if uid not in db:
                await event.answer("❌ Usuário não encontrado.")
                return

            dados = db[uid]
            historico = list(reversed(dados.get("historico", [])))
            total = len(historico)
            total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
            page = min(page, total_pages - 1)
            start = page * ITEMS_PER_PAGE
            chunk = historico[start:start + ITEMS_PER_PAGE]

            text = f"📜 **Histórico de** `{dados['nome_atual']}`\n"
            text += f"🔢 ID: `{uid}` — Página {page + 1}/{total_pages}\n\n"

            for h in chunk:
                emoji = "📛" if h.get("tipo") == "NOME" else "🆔"
                grupo = h.get("grupo", "N/A")
                text += f"{emoji} `{h['data']}`\n"
                text += f"   {h['de']} ➜ {h['para']}\n"
                text += f"   📍 _{grupo}_\n\n"

            if not chunk:
                text += "_Nenhum registro._"

            btns = paginar_buttons(f"hist_{uid}", page, total_pages)
            await message.edit(text, parse_mode='md', buttons=btns)

        # ── Noop (indicador de página) ──
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


# ── Handler: texto livre (busca quando modo ativo) ──
@bot.on(events.NewMessage(func=lambda e: e.is_private and not e.text.startswith('/')))
async def text_handler(event):
    await registrar_interacao(event)
    chat_id = event.chat_id

    if chat_id in search_pending:
        del search_pending[chat_id]
        query = event.text.strip()
        results = buscar_usuario(query)

        if not results:
            await event.reply(
                f"❌ **Nenhum resultado para** `{query}`\n\n💡 Tente outro termo.",
                parse_mode='md',
                buttons=voltar_button()
            )
            return

        if len(results) == 1:
            await event.reply(formatar_perfil(results[0]), parse_mode='md', buttons=voltar_button())
        else:
            text = f"🔍 **{len(results)} resultados para** `{query}`:\n\n"
            btns = []
            for r in results[:10]:
                label = f"👤 {r['nome_atual']} | {r['username_atual']}"
                btns.append([Button.inline(label[:40], f"profile_{r['id']}".encode())])
            btns.append([Button.inline("🔙 Menu Principal", b"cmd_menu")])
            await event.reply(text, parse_mode='md', buttons=btns)
    else:
        await event.reply(
            "💡 Use o menu para navegar ou `/buscar termo` para buscar.",
            parse_mode='md',
            buttons=menu_principal_buttons(event.chat_id)
        )


# ══════════════════════════════════════════════
# 🔁  VARREDURA AUTOMÁTICA
# ══════════════════════════════════════════════

async def auto_scanner():
    """Executa varreduras periódicas automaticamente."""
    while True:
        await asyncio.sleep(SCAN_INTERVAL)
        log("🔄 Varredura automática iniciada")
        await executar_varredura()


# ══════════════════════════════════════════════
# 🚀  MAIN
# ══════════════════════════════════════════════

async def main():
    await user_client.start(PHONE)
    await bot.start(bot_token=BOT_TOKEN)

    log("🚀 User Info Bot Pro v3.0 iniciado!")
    log("👨‍💻 Créditos: Edivaldo Silva @Edkd1")
    log(f"🔄 Varredura automática a cada {SCAN_INTERVAL // 60} min")
    log("📡 Executando primeira varredura...")

    # Primeira varredura ao iniciar
    await executar_varredura(notify_chat=OWNER_ID)

    # Agenda varreduras automáticas
    asyncio.create_task(auto_scanner())

    print("✅ Bot ativo! Use /start ou /buscar")
    await bot.run_until_disconnected()


if __name__ == "__main__":
    try:
        bot.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n👋 Bot finalizado com segurança!")
        log("Bot encerrado pelo usuário")

# ══════════════════════════════════════════════
# 🎨  BOTÕES INLINE — INFO BOT PRO V4.0
# 👨‍💻 Créditos: Edivaldo Silva @Edkd1
# ══════════════════════════════════════════════

from telethon import Button

BOT_VERSION = "4.0"
BOT_CODENAME = "773H Ultra"
OWNER_ID = 2061557102  # Edivaldo Silva @Edkd1

def set_owner(owner_id: int):
    global OWNER_ID
    OWNER_ID = owner_id

def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID

def menu_principal_buttons(user_id: int = 0):
    """Menu principal com botões inline — inclui consulta CPF e compositor."""
    btns = [
        [Button.inline("🔍 Buscar Usuário", b"cmd_buscar"),
         Button.inline("📊 Estatísticas", b"cmd_stats")],
        [Button.inline("🌐 Consultar Telegram", b"cmd_tg_search"),
         Button.inline("📋 Últimas Alterações", b"cmd_recent")],
        [Button.inline("🔎 Consultar CPF", b"cmd_consultar_cpf")],
    ]
    if is_admin(user_id):
        btns.append([
            Button.inline("🔄 Iniciar Varredura", b"cmd_scan"),
            Button.inline("📂 Grupos Monitorados", b"cmd_groups")
        ])
        btns.append([
            Button.inline("📤 Exportar Banco", b"cmd_export"),
            Button.inline("⚙️ Configurações", b"cmd_config")
        ])
        btns.append([
            Button.inline("🧵 Threads", b"cmd_threads"),
            Button.inline("✉️ Compositor", b"cmd_compositor")
        ])
        btns.append([
            Button.inline("📡 Auto-Resposta", b"cmd_auto_resposta"),
        ])
    btns.append([Button.inline("ℹ️ Sobre", b"cmd_about")])
    return btns

def voltar_button():
    """Botão de voltar ao menu."""
    return [[Button.inline("🔙 Menu Principal", b"cmd_menu")]]

def perfil_buttons(uid: str):
    """Botões do perfil de um usuário."""
    return [
        [Button.inline("🌐 API", f"apilookup_{uid}".encode())],
        [Button.inline("📜 Histórico", f"hist_{uid}_0".encode())],
        [Button.inline("👑 Admin", f"gadmin_{uid}_0".encode()),
         Button.inline("🚫 Bans", f"gban_{uid}_0".encode())],
        [Button.inline("📂 Grupos", f"gmember_{uid}_0".encode())],
        [Button.inline("🔙 Menu", b"cmd_menu")]
    ]

def perfil_com_api_buttons(uid: str):
    """Botões do perfil com dados API já existentes."""
    return [
        [Button.inline("🌐 Dados API", f"apiview_{uid}".encode())],
        [Button.inline("📜 Histórico", f"hist_{uid}_0".encode())],
        [Button.inline("👑 Admin", f"gadmin_{uid}_0".encode()),
         Button.inline("🚫 Bans", f"gban_{uid}_0".encode())],
        [Button.inline("🔙 Menu", b"cmd_menu")]
    ]

def resultado_multiplo_buttons(results: list):
    """Botões para múltiplos resultados de busca."""
    btns = []
    for r in results[:10]:
        label = f"👤 {r['nome_atual']} | {r['username_atual']}"
        btns.append([Button.inline(label[:40], f"profile_{r['id']}".encode())])
    btns.append([Button.inline("🔙 Menu", b"cmd_menu")])
    return btns

def auto_resposta_menu_buttons():
    """Botões do menu de auto-resposta em grupos."""
    return [
        [Button.inline("➕ Adicionar Grupo", b"ar_add_grupo"),
         Button.inline("➖ Remover Grupo", b"ar_rem_grupo")],
        [Button.inline("💬 Definir Resposta", b"ar_set_resposta")],
        [Button.inline("📋 Ver Grupos Ativos", b"ar_listar_grupos")],
        [Button.inline("🔄 Toggle Auto-Resposta", b"ar_toggle")],
        [Button.inline("🔙 Menu Principal", b"cmd_menu")]
    ]

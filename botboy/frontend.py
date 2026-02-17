from telethon import Button
from typing import Dict, List, Optional, Any
from datetime import datetime
from config import ITEMS_PER_PAGE, MAX_BUTTON_TEXT


class IPTVFrontend:
    def __init__(self, client):
        self.client = client
        self.items_per_page = ITEMS_PER_PAGE
        self.max_button_text = MAX_BUTTON_TEXT

    def truncate_text(self, text: str, max_length: int = None) -> str:
        if max_length is None:
            max_length = self.max_button_text
        return text[:max_length - 3] + "..." if len(text) > max_length else text

    def create_error_buttons(self, back_callback: str = "menu_principal") -> list:
        return [[Button.inline("🔙 Voltar", data=back_callback.encode())]]

    def create_pagination_buttons(self, page: int, total_items: int, callback_prefix: str, *args) -> list:
        buttons = []
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page

        if page > 0:
            cb = f"{callback_prefix}_{'_'.join(map(str, args))}_{page - 1}"
            buttons.append(Button.inline("⬅️ Anterior", data=cb.encode()))

        buttons.append(Button.inline(f"📄 {page + 1}/{total_pages}", data=b"page_info"))

        if (page + 1) * self.items_per_page < total_items:
            cb = f"{callback_prefix}_{'_'.join(map(str, args))}_{page + 1}"
            buttons.append(Button.inline("➡️ Próximo", data=cb.encode()))

        return buttons

    async def show_main_menu(self, chat_id: int, message=None):
        buttons = [
            [Button.inline("📺 Canais de TV", data=b"menu_canais")],
            [Button.inline("🎬 Filmes", data=b"menu_filmes")],
            [Button.inline("📺 Séries", data=b"menu_series")],
            [Button.inline("⭐ Minhas Seleções", data=b"menu_selections"),
             Button.inline("ℹ️ Info do Servidor", data=b"server_info")],
            [Button.inline("🔄 Nova Playlist", data=b"nova_playlist")],
        ]

        text = """🎯 **MENU PRINCIPAL**

🚀 **Bot IPTV Profissional v3.0 (Telethon)**

**Funcionalidades disponíveis:**
📺 **Canais** - TV ao vivo com categorias
🎬 **Filmes** - Catálogo completo com info
📺 **Séries** - Temporadas e episódios
⭐ **Seleções** - Seus favoritos salvos
ℹ️ **Info** - Dados do servidor/usuário
🔄 **Playlist** - Configurar nova URL

**💡 Recursos únicos:**
• Geração de arquivos M3U personalizados
• Sistema anti-spam e cache inteligente
• Interface profissional com paginação
• Categorias personalizáveis"""

        try:
            if message:
                await message.edit(text, buttons=buttons, parse_mode='md')
            else:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')
        except Exception as e:
            print(f"Error showing main menu: {e}")
            await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

    async def show_server_info(self, chat_id: int, message, server_info: Dict):
        buttons = [[Button.inline("🔙 Menu Principal", data=b"menu_principal")]]

        if not server_info:
            text = "❌ **Erro ao obter informações do servidor**"
        else:
            exp_date = server_info.get('exp_date', 'N/A')
            if exp_date and exp_date != 'N/A' and str(exp_date).isdigit():
                exp_date = datetime.fromtimestamp(int(exp_date)).strftime('%d/%m/%Y %H:%M')

            text = f"""ℹ️ **INFORMAÇÕES DO SERVIDOR**

**🖥️ Servidor:**
• URL: `{server_info.get('server', 'N/A')}`
• Status: {'🟢 Ativo' if server_info.get('status') == 'Active' else '🔴 Inativo'}

**👤 Usuário:**
• Login: `{server_info.get('username', 'N/A')}`
• Expira em: {exp_date}
• Conexões ativas: {server_info.get('active_cons', '0')}/{server_info.get('max_connections', '1')}

**📊 Conteúdo disponível:**
• 📺 Canais: {server_info.get('available_channels', '0')}
• 🎬 Filmes: {server_info.get('available_movies', '0')}
• 📺 Séries: {server_info.get('available_series', '0')}

**⚡ Status da conexão:** 🟢 Estável"""

        try:
            await message.edit(text, buttons=buttons, parse_mode='md')
        except Exception as e:
            print(f"Error showing server info: {e}")

    async def show_selections_menu(self, chat_id: int, message, selections: Dict):
        channels_count = len(selections.get('channels', []))
        movies_count = len(selections.get('movies', []))
        series_count = len(selections.get('series', []))
        total = channels_count + movies_count + series_count

        buttons = []

        if total > 0:
            buttons.append([
                Button.inline(f"📺 Canais ({channels_count})", data=b"view_selected_channels"),
                Button.inline(f"🎬 Filmes ({movies_count})", data=b"view_selected_movies"),
            ])
            buttons.append([Button.inline(f"📺 Séries ({series_count})", data=b"view_selected_series")])
            buttons.append([Button.inline("📄 Gerar M3U", data=b"generate_m3u")])
            buttons.append([Button.inline("🗑️ Limpar Tudo", data=b"clear_selections")])

        buttons.append([Button.inline("🔙 Menu Principal", data=b"menu_principal")])

        text = f"""⭐ **SUAS SELEÇÕES**

**📊 Resumo:**
• 📺 Canais selecionados: **{channels_count}**
• 🎬 Filmes selecionados: **{movies_count}**
• 📺 Séries selecionadas: **{series_count}**
• **Total:** {total} itens

{'**🎉 Você pode gerar arquivos M3U personalizados!**' if total > 0 else '**📝 Nenhum item selecionado ainda.**'}

**💡 Dica:** Use os botões 📥 ao navegar pelos conteúdos para adicionar às suas seleções."""

        try:
            await message.edit(text, buttons=buttons, parse_mode='md')
        except Exception as e:
            print(f"Error showing selections menu: {e}")

    async def show_rate_limit_error(self, chat_id: int):
        text = """⚠️ **Muitas solicitações!**

Você está fazendo muitas solicitações muito rapidamente.
Aguarde alguns segundos antes de tentar novamente.

**⏰ Limite:** 20 solicitações por minuto
**🛡️ Proteção:** Anti-spam ativada"""
        try:
            await self.client.send_message(chat_id, text, parse_mode='md')
        except Exception as e:
            print(f"Error showing rate limit: {e}")

from telethon import Button
from typing import Optional


class CanalManager:
    def __init__(self, client, backend, frontend):
        self.client = client
        self.backend = backend
        self.frontend = frontend

    def get_categories(self, config):
        """Obtém categorias de canais"""
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_live_categories'
        }
        return self.backend.make_api_request(config, params) or []

    def get_channels(self, config, category_id=None):
        """Obtém lista de canais"""
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_live_streams'
        }
        if category_id:
            params['category_id'] = category_id

        channels = self.backend.make_api_request(config, params) or []

        categories = self.get_categories(config)
        category_map = {str(cat.get('category_id')): cat.get('category_name', 'Canais') for cat in categories}

        for channel in channels:
            channel['play_url'] = f"{config['server']}/live/{config['username']}/{config['password']}/{channel['stream_id']}.{channel.get('container_extension', 'ts')}"
            if not channel.get('category_name') and category_id:
                channel['category_name'] = category_map.get(str(category_id), 'Canais')

        return channels

    async def show_categories(self, chat_id, message, config):
        """Mostra categorias de canais"""
        try:
            categories = self.get_categories(config)

            if not categories:
                buttons = self.frontend.create_error_buttons("menu_principal")
                await message.edit("❌ Não foi possível carregar as categorias de canais.", buttons=buttons)
                return

            buttons = [[Button.inline("📺 Todos os Canais", data=b"canal_list_all_0")]]

            for category in categories[:12]:
                cat_name = self.frontend.truncate_text(category['category_name'], 25)
                cat_id = category['category_id']
                buttons.append([
                    Button.inline(f"📁 {cat_name}", data=f"canal_list_{cat_id}_0".encode()),
                    Button.inline("📥➕", data=f"add_full_category_channels_{cat_id}".encode()),
                ])

            buttons.append([Button.inline("🔙 Menu Principal", data=b"menu_principal")])

            text = f"""📺 **CATEGORIAS DE CANAIS**

📊 **{len(categories)} categorias encontradas**
🎯 **Navegação otimizada**

**💡 Como usar:**
• 📁 **Nome da categoria**: Navegar pelos canais
• 📥➕ **Adicionar categoria**: Adiciona todos ao M3U

**🏷️ Dica:** Ao adicionar categoria completa, você pode renomear!

Escolha uma categoria:"""

            try:
                await message.edit(text, buttons=buttons, parse_mode='md')
            except:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error showing channel categories: {e}")
            buttons = self.frontend.create_error_buttons("menu_principal")
            await message.edit("❌ Erro ao carregar categorias.", buttons=buttons)

    async def show_channels(self, chat_id, message, config, category_id, page=0):
        """Mostra lista de canais com paginação"""
        try:
            channels = self.get_channels(config) if category_id == "all" else self.get_channels(config, category_id)

            if not channels:
                buttons = self.frontend.create_error_buttons("menu_canais")
                await message.edit("❌ Nenhum canal encontrado nesta categoria.", buttons=buttons)
                return

            start_idx = page * self.frontend.items_per_page
            end_idx = start_idx + self.frontend.items_per_page
            page_channels = channels[start_idx:end_idx]

            buttons = []
            for channel in page_channels:
                ch_name = self.frontend.truncate_text(channel['name'], 32)
                sid = channel['stream_id']
                buttons.append([
                    Button.inline(f"📺 {ch_name}", data=f"canal_play_{sid}".encode()),
                    Button.inline("📥", data=f"canal_add_{sid}".encode()),
                ])

            nav = self.frontend.create_pagination_buttons(page, len(channels), "canal_list", category_id)
            if nav:
                buttons.append(nav)

            buttons.append([Button.inline("🔙 Categorias", data=b"menu_canais")])

            total_pages = (len(channels) + self.frontend.items_per_page - 1) // self.frontend.items_per_page
            text = f"""📺 **CANAIS DE TV**

📊 **Página {page + 1} de {total_pages}**
📺 **Total: {len(channels)} canais**
📥 **Use o botão 📥 para adicionar ao M3U**

Escolha um canal:"""

            try:
                await message.edit(text, buttons=buttons, parse_mode='md')
            except:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error showing channels: {e}")
            buttons = self.frontend.create_error_buttons("menu_canais")
            await message.edit("❌ Erro ao carregar canais.", buttons=buttons)

    async def play_channel(self, chat_id, message, config, stream_id):
        """Mostra detalhes de um canal"""
        try:
            channels = self.get_channels(config)
            channel = next((ch for ch in channels if str(ch['stream_id']) == str(stream_id)), None)

            if not channel:
                buttons = self.frontend.create_error_buttons("menu_canais")
                await message.edit("❌ Canal não encontrado.", buttons=buttons)
                return

            buttons = [
                [Button.url("▶️ Reproduzir", channel['play_url']),
                 Button.inline("📥 Adicionar ao M3U", data=f"canal_add_{stream_id}".encode())],
                [Button.inline("🔙 Voltar", data=b"canal_list_all_0")],
            ]

            text = f"""📺 **{channel['name']}**

🆔 **Stream ID:** {channel['stream_id']}
📡 **Categoria:** {channel.get('category_name', 'Geral')}
🌐 **Servidor:** {config['server'].split('//')[1] if '//' in config['server'] else config['server']}

🔗 **URL de reprodução:**
`{channel['play_url']}`

**💡 Como reproduzir:**
• Clique em "▶️ Reproduzir" para abrir no player
• Use 📥 para adicionar ao M3U
• Copie a URL para usar em outro player"""

            # Tenta enviar com imagem
            if channel.get('stream_icon') and channel['stream_icon'].startswith('http'):
                try:
                    await message.delete()
                    await self.client.send_file(chat_id, channel['stream_icon'], caption=text, buttons=buttons, parse_mode='md')
                    return
                except:
                    pass

            try:
                await message.edit(text, buttons=buttons, parse_mode='md')
            except:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error playing channel: {e}")
            buttons = self.frontend.create_error_buttons("menu_canais")
            await message.edit("❌ Erro ao carregar canal.", buttons=buttons)

    async def add_to_m3u(self, event, config, stream_id):
        """Adiciona canal ao M3U preservando categoria original"""
        try:
            channels = self.get_channels(config)
            channel = next((ch for ch in channels if str(ch['stream_id']) == str(stream_id)), None)

            if not channel:
                await event.answer("❌ Canal não encontrado!")
                return

            channel_data = {
                'id': channel['stream_id'],
                'name': channel['name'],
                'logo': channel.get('stream_icon', ''),
                'container': channel.get('container_extension', 'ts'),
                'category': channel.get('category_name', 'Canais')
            }

            added = self.backend.add_to_selection(event.chat_id, 'channels', channel_data)

            if added:
                await event.answer(f"📥 {channel['name']} adicionado ao M3U!")
            else:
                await event.answer(f"ℹ️ {channel['name']} já está no M3U!")

        except Exception as e:
            print(f"Error adding to M3U: {e}")
            await event.answer("❌ Erro ao adicionar ao M3U")

    async def handle_callback(self, event, config):
        """Manipula callbacks de canais"""
        if not config:
            await event.answer("❌ Configure uma playlist primeiro!")
            return

        data = event.data.decode()
        chat_id = event.chat_id
        message = await event.get_message()

        try:
            if data.startswith("canal_list_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    category_id = parts[2]
                    page = int(parts[3])
                    await self.show_channels(chat_id, message, config, category_id, page)

            elif data.startswith("canal_play_"):
                stream_id = data.split("_")[2]
                await self.play_channel(chat_id, message, config, stream_id)

            elif data.startswith("canal_add_"):
                stream_id = data.split("_")[2]
                await self.add_to_m3u(event, config, stream_id)

        except Exception as e:
            print(f"Error in channel callback: {e}")
            await event.answer("❌ Erro interno")

from telethon import Button


class SerieManager:
    def __init__(self, client, backend, frontend):
        self.client = client
        self.backend = backend
        self.frontend = frontend

    def get_categories(self, config):
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_series_categories'
        }
        return self.backend.make_api_request(config, params) or []

    def get_series(self, config, category_id=None):
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_series'
        }
        if category_id:
            params['category_id'] = category_id
        return self.backend.make_api_request(config, params) or []

    def get_episodes(self, config, series_id, season=None):
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_series_info',
            'series_id': series_id
        }
        series_info = self.backend.make_api_request(config, params) or {}

        if season:
            return series_info.get('episodes', {}).get(str(season), [])

        all_episodes = []
        for season_num, episodes in series_info.get('episodes', {}).items():
            for ep in episodes:
                ep['season'] = season_num
            all_episodes.extend(episodes)
        return all_episodes

    async def show_categories(self, chat_id, message, config):
        try:
            categories = self.get_categories(config)

            if not categories:
                buttons = self.frontend.create_error_buttons("menu_principal")
                await message.edit("❌ Nenhuma categoria de séries encontrada.", buttons=buttons)
                return

            buttons = [[Button.inline("📺 Todas as Séries", data=b"serie_list_all_0")]]

            for category in categories[:12]:
                cat_name = self.frontend.truncate_text(category['category_name'], 25)
                cat_id = category['category_id']
                buttons.append([
                    Button.inline(f"📁 {cat_name}", data=f"serie_list_{cat_id}_0".encode()),
                    Button.inline("📥➕", data=f"add_full_category_series_{cat_id}".encode()),
                ])

            buttons.append([Button.inline("🔙 Menu Principal", data=b"menu_principal")])

            text = f"""📺 **CATEGORIAS DE SÉRIES**

📊 **{len(categories)} categorias encontradas**
🎯 **Navegação otimizada**

**💡 Como usar:**
• 📁 **Nome da categoria**: Navegar pelas séries
• 📥➕ **Adicionar categoria**: Adiciona todas ao M3U

**🏷️ Dica:** Ao adicionar categoria completa, você pode renomear!

Escolha uma categoria:"""

            try:
                await message.edit(text, buttons=buttons, parse_mode='md')
            except:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error showing series categories: {e}")
            buttons = self.frontend.create_error_buttons("menu_principal")
            await message.edit("❌ Erro ao carregar categorias.", buttons=buttons)

    async def show_series_list(self, chat_id, message, config, category_id, page=0):
        try:
            series = self.get_series(config) if category_id == "all" else self.get_series(config, category_id)

            if not series:
                buttons = self.frontend.create_error_buttons("menu_series")
                await message.edit("❌ Nenhuma série encontrada.", buttons=buttons)
                return

            start_idx = page * self.frontend.items_per_page
            end_idx = start_idx + self.frontend.items_per_page
            page_series = series[start_idx:end_idx]

            buttons = []
            for s in page_series:
                s_name = self.frontend.truncate_text(s.get('name', 'Sem nome'), 28)
                sid = s.get('series_id', s.get('id', '0'))
                buttons.append([
                    Button.inline(f"📺 {s_name}", data=f"serie_episodes_{sid}".encode()),
                    Button.inline("📥", data=f"serie_add_{sid}".encode()),
                ])

            nav = self.frontend.create_pagination_buttons(page, len(series), "serie_list", category_id)
            if nav:
                buttons.append(nav)

            buttons.append([Button.inline("🔙 Categorias", data=b"menu_series")])

            total_pages = (len(series) + self.frontend.items_per_page - 1) // self.frontend.items_per_page
            text = f"""📺 **SÉRIES**

📊 **Página {page + 1} de {total_pages}**
📺 **Total: {len(series)} séries**
📥 **Use o botão 📥 para adicionar ao M3U**

Escolha uma série:"""

            try:
                await message.edit(text, buttons=buttons, parse_mode='md')
            except:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error showing series: {e}")
            buttons = self.frontend.create_error_buttons("menu_series")
            await message.edit("❌ Erro ao carregar séries.", buttons=buttons)

    async def show_episodes(self, chat_id, message, config, series_id, page=0):
        try:
            episodes = self.get_episodes(config, series_id)

            if not episodes:
                buttons = self.frontend.create_error_buttons("menu_series")
                await message.edit("❌ Nenhum episódio encontrado.", buttons=buttons)
                return

            start_idx = page * self.frontend.items_per_page
            end_idx = start_idx + self.frontend.items_per_page
            page_episodes = episodes[start_idx:end_idx]

            buttons = []
            for ep in page_episodes:
                ep_title = ep.get('title', f"Episódio {ep.get('episode_num', '?')}")
                season = ep.get('season', '?')
                ep_num = ep.get('episode_num', '?')
                btn_text = f"▶️ S{season}E{ep_num} - {self.frontend.truncate_text(ep_title, 25)}"
                ep_id = ep.get('id', '0')

                buttons.append([
                    Button.inline(btn_text, data=f"serie_play_{ep_id}".encode()),
                    Button.inline("📥", data=f"serie_add_episode_{ep_id}".encode()),
                    Button.inline("💾", data=f"download_options_episode_{ep_id}".encode()),
                ])

            nav = self.frontend.create_pagination_buttons(page, len(episodes), "serie_episodes", series_id)
            if nav:
                buttons.append(nav)

            buttons.append([Button.inline("🔙 Séries", data=b"menu_series")])

            total_pages = (len(episodes) + self.frontend.items_per_page - 1) // self.frontend.items_per_page
            text = f"""📺 **EPISÓDIOS DA SÉRIE**

📊 **Página {page + 1} de {total_pages}**
📺 **Total: {len(episodes)} episódios**
📥 **Use 📥 para adicionar ao M3U**
💾 **Use 💾 para download**

Escolha um episódio:"""

            try:
                await message.edit(text, buttons=buttons, parse_mode='md')
            except:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error showing episodes: {e}")
            buttons = self.frontend.create_error_buttons("menu_series")
            await message.edit("❌ Erro ao carregar episódios.", buttons=buttons)

    async def add_to_m3u(self, event, config, series_id):
        """Adiciona série ao M3U"""
        try:
            series_list = self.get_series(config)
            serie = next((s for s in series_list if str(s.get('series_id', s.get('id'))) == str(series_id)), None)

            if not serie:
                await event.answer("❌ Série não encontrada!")
                return

            episodes = self.get_episodes(config, series_id)
            added_count = 0

            for ep in episodes:
                ep_data = {
                    'id': ep.get('id'),
                    'name': f"{serie.get('name', 'Série')} - S{ep.get('season', '?')}E{ep.get('episode_num', '?')} - {ep.get('title', 'Episódio')}",
                    'logo': serie.get('cover', ''),
                    'container': ep.get('container_extension', 'mp4'),
                    'category': serie.get('category_name', 'Séries')
                }
                if self.backend.add_to_selection(event.chat_id, 'series', ep_data):
                    added_count += 1

            if added_count > 0:
                await event.answer(f"📥 {added_count} episódios adicionados ao M3U!")
            else:
                await event.answer("ℹ️ Todos os episódios já estão no M3U!")

        except Exception as e:
            print(f"Error adding series to M3U: {e}")
            await event.answer("❌ Erro ao adicionar ao M3U")

    async def add_episode_to_m3u(self, event, config, episode_id):
        """Adiciona episódio individual ao M3U"""
        try:
            ep_data = {
                'id': episode_id,
                'name': f"Episódio {episode_id}",
                'logo': '',
                'container': 'mp4',
                'category': 'Séries'
            }
            added = self.backend.add_to_selection(event.chat_id, 'series', ep_data)

            if added:
                await event.answer("📥 Episódio adicionado ao M3U!")
            else:
                await event.answer("ℹ️ Episódio já está no M3U!")

        except Exception as e:
            print(f"Error adding episode: {e}")
            await event.answer("❌ Erro ao adicionar episódio")

    async def handle_callback(self, event, config):
        if not config:
            await event.answer("❌ Configure uma playlist primeiro!")
            return

        data = event.data.decode()
        chat_id = event.chat_id
        message = await event.get_message()

        try:
            if data.startswith("serie_list_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    category_id = parts[2]
                    page = int(parts[3])
                    await self.show_series_list(chat_id, message, config, category_id, page)

            elif data.startswith("serie_episodes_"):
                parts = data.split("_")
                series_id = parts[2]
                page = int(parts[3]) if len(parts) > 3 else 0
                await self.show_episodes(chat_id, message, config, series_id, page)

            elif data.startswith("serie_add_episode_"):
                episode_id = data.split("_")[3]
                await self.add_episode_to_m3u(event, config, episode_id)

            elif data.startswith("serie_add_"):
                series_id = data.split("_")[2]
                await self.add_to_m3u(event, config, series_id)

            elif data.startswith("serie_play_"):
                episode_id = data.split("_")[2]
                # Para episódios, mostra a URL direta
                play_url = f"{config['server']}/series/{config['username']}/{config['password']}/{episode_id}.mp4"
                buttons = [
                    [Button.url("▶️ Reproduzir", play_url)],
                    [Button.inline("🔙 Voltar", data=b"menu_series")],
                ]
                text = f"▶️ **Reproduzir Episódio**\n\n🔗 `{play_url}`"
                try:
                    await message.edit(text, buttons=buttons, parse_mode='md')
                except:
                    await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error in series callback: {e}")
            await event.answer("❌ Erro interno")

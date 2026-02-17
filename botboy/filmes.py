from telethon import Button


class FilmeManager:
    def __init__(self, client, backend, frontend):
        self.client = client
        self.backend = backend
        self.frontend = frontend

    def get_categories(self, config):
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_vod_categories'
        }
        return self.backend.make_api_request(config, params) or []

    def get_movies(self, config, category_id=None):
        params = {
            'username': config['username'],
            'password': config['password'],
            'action': 'get_vod_streams'
        }
        if category_id:
            params['category_id'] = category_id

        movies = self.backend.make_api_request(config, params) or []

        categories = self.get_categories(config)
        category_map = {str(cat.get('category_id')): cat.get('category_name', 'Filmes') for cat in categories}

        for movie in movies:
            movie['play_url'] = f"{config['server']}/movie/{config['username']}/{config['password']}/{movie['stream_id']}.{movie.get('container_extension', 'mp4')}"
            if not movie.get('category_name') and category_id:
                movie['category_name'] = category_map.get(str(category_id), 'Filmes')

        return movies

    async def show_categories(self, chat_id, message, config):
        try:
            categories = self.get_categories(config)

            if not categories:
                buttons = self.frontend.create_error_buttons("menu_principal")
                await message.edit("❌ Nenhuma categoria de filmes encontrada.", buttons=buttons)
                return

            buttons = [[Button.inline("🎬 Todos os Filmes", data=b"filme_list_all_0")]]

            for category in categories[:12]:
                cat_name = self.frontend.truncate_text(category['category_name'], 25)
                cat_id = category['category_id']
                buttons.append([
                    Button.inline(f"📁 {cat_name}", data=f"filme_list_{cat_id}_0".encode()),
                    Button.inline("📥➕", data=f"add_full_category_movies_{cat_id}".encode()),
                ])

            buttons.append([Button.inline("🔙 Menu Principal", data=b"menu_principal")])

            text = f"""🎬 **CATEGORIAS DE FILMES**

📊 **{len(categories)} categorias encontradas**
🎯 **Navegação otimizada**

**💡 Como usar:**
• 📁 **Nome da categoria**: Navegar pelos filmes
• 📥➕ **Adicionar categoria**: Adiciona todos ao M3U

**🏷️ Dica:** Ao adicionar categoria completa, você pode renomear!

Escolha uma categoria:"""

            try:
                await message.edit(text, buttons=buttons, parse_mode='md')
            except:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error showing movie categories: {e}")
            buttons = self.frontend.create_error_buttons("menu_principal")
            await message.edit("❌ Erro ao carregar categorias.", buttons=buttons)

    async def show_movies(self, chat_id, message, config, category_id, page=0):
        try:
            movies = self.get_movies(config) if category_id == "all" else self.get_movies(config, category_id)

            if not movies:
                buttons = self.frontend.create_error_buttons("menu_filmes")
                await message.edit("❌ Nenhum filme encontrado nesta categoria.", buttons=buttons)
                return

            start_idx = page * self.frontend.items_per_page
            end_idx = start_idx + self.frontend.items_per_page
            page_movies = movies[start_idx:end_idx]

            buttons = []
            for movie in page_movies:
                mv_name = self.frontend.truncate_text(movie['name'], 28)
                sid = movie['stream_id']
                buttons.append([
                    Button.inline(f"🎬 {mv_name}", data=f"filme_play_{sid}".encode()),
                    Button.inline("📥", data=f"filme_add_{sid}".encode()),
                    Button.inline("💾", data=f"download_options_movie_{sid}".encode()),
                ])

            nav = self.frontend.create_pagination_buttons(page, len(movies), "filme_list", category_id)
            if nav:
                buttons.append(nav)

            buttons.append([Button.inline("🔙 Categorias", data=b"menu_filmes")])

            total_pages = (len(movies) + self.frontend.items_per_page - 1) // self.frontend.items_per_page
            text = f"""🎬 **FILMES**

📊 **Página {page + 1} de {total_pages}**
🎬 **Total: {len(movies)} filmes**
📥 **Use o botão 📥 para adicionar ao M3U**
💾 **Use o botão 💾 para fazer download**

Escolha um filme:"""

            try:
                await message.edit(text, buttons=buttons, parse_mode='md')
            except:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error showing movies: {e}")
            buttons = self.frontend.create_error_buttons("menu_filmes")
            await message.edit("❌ Erro ao carregar filmes.", buttons=buttons)

    async def play_movie(self, chat_id, message, config, stream_id):
        try:
            movies = self.get_movies(config)
            movie = next((mv for mv in movies if str(mv['stream_id']) == str(stream_id)), None)

            if not movie:
                buttons = self.frontend.create_error_buttons("menu_filmes")
                await message.edit("❌ Filme não encontrado.", buttons=buttons)
                return

            buttons = [
                [Button.url("▶️ Reproduzir", movie['play_url']),
                 Button.inline("📥 Adicionar ao M3U", data=f"filme_add_{stream_id}".encode())],
                [Button.inline("💾 Download", data=f"download_options_movie_{stream_id}".encode())],
                [Button.inline("🔙 Voltar", data=b"filme_list_all_0")],
            ]

            text = f"""🎬 **{movie['name']}**

🆔 **Stream ID:** {movie['stream_id']}
📡 **Categoria:** {movie.get('category_name', 'Geral')}
🌐 **Servidor:** {config['server'].split('//')[1] if '//' in config['server'] else config['server']}

🔗 **URL de reprodução:**
`{movie['play_url']}`

**💡 Como reproduzir:**
• Clique em "▶️ Reproduzir" para abrir no player
• Use 📥 para adicionar ao M3U
• Use 💾 para baixar o filme"""

            if movie.get('stream_icon') and movie['stream_icon'].startswith('http'):
                try:
                    await message.delete()
                    await self.client.send_file(chat_id, movie['stream_icon'], caption=text, buttons=buttons, parse_mode='md')
                    return
                except:
                    pass

            try:
                await message.edit(text, buttons=buttons, parse_mode='md')
            except:
                await self.client.send_message(chat_id, text, buttons=buttons, parse_mode='md')

        except Exception as e:
            print(f"Error playing movie: {e}")
            buttons = self.frontend.create_error_buttons("menu_filmes")
            await message.edit("❌ Erro ao carregar filme.", buttons=buttons)

    async def add_to_m3u(self, event, config, stream_id):
        try:
            movies = self.get_movies(config)
            movie = next((mv for mv in movies if str(mv['stream_id']) == str(stream_id)), None)

            if not movie:
                await event.answer("❌ Filme não encontrado!")
                return

            movie_data = {
                'id': movie['stream_id'],
                'name': movie['name'],
                'logo': movie.get('stream_icon', ''),
                'container': movie.get('container_extension', 'mp4'),
                'category': movie.get('category_name', 'Filmes')
            }

            added = self.backend.add_to_selection(event.chat_id, 'movies', movie_data)

            if added:
                await event.answer(f"📥 {movie['name']} adicionado ao M3U!")
            else:
                await event.answer(f"ℹ️ {movie['name']} já está no M3U!")

        except Exception as e:
            print(f"Error adding movie to M3U: {e}")
            await event.answer("❌ Erro ao adicionar ao M3U")

    async def handle_callback(self, event, config):
        if not config:
            await event.answer("❌ Configure uma playlist primeiro!")
            return

        data = event.data.decode()
        chat_id = event.chat_id
        message = await event.get_message()

        try:
            if data.startswith("filme_list_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    category_id = parts[2]
                    page = int(parts[3])
                    await self.show_movies(chat_id, message, config, category_id, page)

            elif data.startswith("filme_play_"):
                stream_id = data.split("_")[2]
                await self.play_movie(chat_id, message, config, stream_id)

            elif data.startswith("filme_add_"):
                stream_id = data.split("_")[2]
                await self.add_to_m3u(event, config, stream_id)

        except Exception as e:
            print(f"Error in movie callback: {e}")
            await event.answer("❌ Erro interno")

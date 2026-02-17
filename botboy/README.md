# 🎬 BotBoy - IPTV Bot Profissional v3.0 (Telethon)

Bot Telegram para gerenciamento de playlists IPTV, convertido de pyTelegramBotAPI para **Telethon** (asyncio).

## ✨ Funcionalidades

- 📺 **Canais de TV** - Navegação por categorias com paginação
- 🎬 **Filmes** - Catálogo completo com detalhes e poster
- 📺 **Séries** - Temporadas e episódios organizados
- ⭐ **Seleções** - Favoritos individuais e por categoria completa
- 📄 **M3U** - Geração de playlists personalizadas com categorias
- 🏷️ **Renomeação** - Categorias personalizáveis no M3U
- 💾 **Download** - Filmes e episódios (apenas dono)
- 📤 **Compartilhar** - Envio para grupos (apenas dono)
- 👑 **Admin** - Painel com estatísticas e controles
- 🛡️ **Anti-spam** - Rate limiting inteligente
- 🔄 **Cache** - Respostas rápidas com cache automático

## 📁 Estrutura

```
botboy/
├── bot.py           # Arquivo principal (handlers + main)
├── config.py        # Configurações centralizadas
├── backend.py       # Lógica de negócio, cache, API, M3U
├── frontend.py      # Interface do Telegram (menus, botões)
├── canais.py        # Gerenciamento de canais
├── filmes.py        # Gerenciamento de filmes
├── series.py        # Gerenciamento de séries
├── comandos.py      # Comandos admin e compartilhamento
├── download.py      # Sistema de download
├── requirements.txt # Dependências Python
└── README.md        # Documentação
```

## 🚀 Instalação

### 1. Pré-requisitos

- Python 3.8+
- Token de bot do Telegram (@BotFather)
- API ID e API Hash do Telegram (https://my.telegram.org)

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar

Edite o arquivo `config.py`:

```python
BOT_TOKEN = "SEU_TOKEN_AQUI"
API_ID = 12345          # Seu api_id
API_HASH = "abc123def"  # Seu api_hash
OWNER_ID = 123456789    # Seu user_id do Telegram
```

### 4. Executar

```bash
python bot.py
```

## 🎯 Como usar

1. Envie `/start` no bot
2. Cole a URL da sua playlist IPTV: `http://servidor.com/get.php?username=user&password=pass`
3. Navegue pelos menus de canais, filmes e séries
4. Selecione itens individuais (📥) ou categorias inteiras (📥➕)
5. Gere seu arquivo M3U personalizado

## 🔄 Migração de telebot para Telethon

| telebot | Telethon |
|---------|----------|
| `telebot.TeleBot(TOKEN)` | `TelegramClient('bot', API_ID, API_HASH).start(bot_token=TOKEN)` |
| `types.InlineKeyboardButton` | `Button.inline()` / `Button.url()` |
| `bot.send_message()` | `await client.send_message()` |
| `bot.edit_message_text()` | `await message.edit()` |
| `bot.answer_callback_query()` | `await event.answer()` |
| `@bot.message_handler()` | `@client.on(events.NewMessage())` |
| `@bot.callback_query_handler()` | `@client.on(events.CallbackQuery)` |
| `bot.infinity_polling()` | `await client.run_until_disconnected()` |

## 📝 Licença

Uso pessoal.

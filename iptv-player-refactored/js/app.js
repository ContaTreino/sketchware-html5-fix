// ===== MAIN APPLICATION CLASS =====

/**
 * IPTV Player Application
 * Main class that handles all the application functionality
 */
class IPTVApp {
  constructor() {
    this.config = this.loadConfig();
    this.cache = new SimpleCache();
    this.progressTracker = new ProgressTracker();
    this.favoritesBackend = new FavoritesBackend();
    
    // Player state
    this.player = null;
    this.currentChannel = null;
    this.currentMovie = null;
    this.currentSeries = null;
    this.currentEpisode = null;
    this.currentRadio = null;
    this.radioVideoMode = false;
    this.metadataInterval = null;
    this.pendingRetryAction = null;

    // Data arrays
    this.channels = [];
    this.movies = [];
    this.series = [];
    this.radios = [];
    this.channelCategories = [];
    this.movieCategories = [];
    this.seriesCategories = [];

    // Active categories
    this.activeChannelCategory = 'all';
    this.activeMovieCategory = 'all';
    this.activeSeriesCategory = 'all';
    this.activeRadioCategory = 'all';

    this.init();
  }

  /**
   * Initialize the application
   */
  async init() {
    try {
      this.setupEventListeners();
      this.loadRadios();
      
      // Load initial content if config exists
      if (this.config.server) {
        await Promise.all([
          this.loadCategories(),
          this.loadMovieCategories(),
          this.loadSeriesCategories()
        ]);
      }
      
      this.loadGames();
      this.renderFavorites();
    } catch (error) {
      console.error('Error initializing app:', error);
    }
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Main navigation
    document.querySelectorAll('.main-nav .nav-link').forEach(link => {
      link.addEventListener('click', (e) => {
        const content = e.target.getAttribute('data-content');
        if (content) {
          this.showContentSection(content);
          
          // Update active nav
          document.querySelectorAll('.main-nav .nav-link').forEach(l => l.classList.remove('active'));
          e.target.classList.add('active');
        }
      });
    });

    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
      searchInput.addEventListener('input', Utils.debounce((e) => {
        this.performSearch(e.target.value);
      }, 300));
    }

    // Progress tracking
    this.setupProgressTracking();
    
    // Keyboard shortcuts
    this.setupKeyboardShortcuts();
  }

  /**
   * Setup progress tracking for videos
   */
  setupProgressTracking() {
    setInterval(() => {
      if (this.player && !this.player.paused()) {
        const currentTime = this.player.currentTime();
        const duration = this.player.duration();
        
        if (currentTime > 0 && duration > 0) {
          let itemId = null;
          
          if (this.currentChannel) {
            itemId = `channel_${this.currentChannel}`;
          } else if (this.currentMovie) {
            itemId = `movie_${this.currentMovie.id}`;
          } else if (this.currentEpisode) {
            itemId = `episode_${this.currentEpisode.id}`;
          }
          
          if (itemId) {
            this.progressTracker.setProgress(itemId, currentTime, duration);
          }
        }
      }
    }, 10000); // Save progress every 10 seconds
  }

  /**
   * Setup keyboard shortcuts
   */
  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return; // Don't handle shortcuts when typing
      }

      switch (e.key.toLowerCase()) {
        case ' ':
          e.preventDefault();
          this.togglePlayPause();
          break;
        case 'f':
          this.toggleFullscreen();
          break;
        case 'm':
          this.toggleMute();
          break;
        case 'arrowleft':
          this.seekBackward();
          break;
        case 'arrowright':
          this.seekForward();
          break;
      }
    });
  }

  /**
   * Load configuration from localStorage
   */
  loadConfig() {
    const defaultConfig = {
      server: '',
      username: '',
      password: ''
    };

    const saved = Utils.localStorage.get('iptv_config', defaultConfig);
    return { ...defaultConfig, ...saved };
  }

  /**
   * Save configuration to localStorage
   */
  saveConfig() {
    Utils.localStorage.set('iptv_config', this.config);
  }

  /**
   * Show content section
   */
  showContentSection(section) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(s => {
      s.classList.remove('active');
    });

    // Show target section
    const targetSection = document.getElementById(`${section}Section`);
    if (targetSection) {
      targetSection.classList.add('active');
    }

    // Load content if needed
    switch (section) {
      case 'channels':
        this.renderChannels();
        break;
      case 'movies':
        this.renderMovies();
        break;
      case 'series':
        this.renderSeries();
        break;
      case 'radios':
        this.renderRadios();
        break;
      case 'favorites':
        this.renderFavorites();
        break;
    }
  }

  /**
   * Load radio stations (static data)
   */
  loadRadios() {
    this.radios = [
      // Sample radio data - replace with actual data
      {
        id: 'radio_1',
        name: 'Rádio Nacional',
        url: 'https://streaming.example.com/radio1',
        frequency: '101.1 FM',
        category: 'nacional',
        city: 'Rio de Janeiro',
        icon: '',
        letter: 'R'
      }
      // Add more radio stations here
    ];

    this.renderRadios();
  }

  /**
   * Load channel categories from API
   */
  async loadCategories() {
    if (!this.config.server) return;

    try {
      const cached = this.cache.get('categories');
      if (cached) {
        this.channelCategories = cached;
        this.renderChannelTabs();
        return;
      }

      const url = `${this.config.server}/player_api.php?username=${this.config.username}&password=${this.config.password}&action=get_live_categories`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const categories = await response.json();
      this.channelCategories = Array.isArray(categories) ? categories : [];
      
      this.cache.set('categories', this.channelCategories);
      this.renderChannelTabs();
      
      // Load channels for first category
      if (this.channelCategories.length > 0) {
        await this.loadChannels('all');
      }
    } catch (error) {
      console.error('Error loading categories:', error);
      this.showErrorOverlay('Erro ao carregar categorias', () => this.loadCategories());
    }
  }

  /**
   * Load movie categories
   */
  async loadMovieCategories() {
    if (!this.config.server) return;

    try {
      const cached = this.cache.get('movie_categories');
      if (cached) {
        this.movieCategories = cached;
        this.renderMovieTabs();
        return;
      }

      const url = `${this.config.server}/player_api.php?username=${this.config.username}&password=${this.config.password}&action=get_vod_categories`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const categories = await response.json();
      this.movieCategories = Array.isArray(categories) ? categories : [];
      
      this.cache.set('movie_categories', this.movieCategories);
      this.renderMovieTabs();
    } catch (error) {
      console.error('Error loading movie categories:', error);
      this.showError('Erro ao carregar categorias de filmes');
    }
  }

  /**
   * Load series categories
   */
  async loadSeriesCategories() {
    if (!this.config.server) return;

    try {
      const cached = this.cache.get('series_categories');
      if (cached) {
        this.seriesCategories = cached;
        this.renderSeriesTabs();
        return;
      }

      const url = `${this.config.server}/player_api.php?username=${this.config.username}&password=${this.config.password}&action=get_series_categories`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const categories = await response.json();
      this.seriesCategories = Array.isArray(categories) ? categories : [];
      
      this.cache.set('series_categories', this.seriesCategories);
      this.renderSeriesTabs();
    } catch (error) {
      console.error('Error loading series categories:', error);
      this.showError('Erro ao carregar categorias de séries');
    }
  }

  /**
   * Load channels by category
   */
  async loadChannels(categoryId = 'all') {
    if (!this.config.server) return;

    try {
      const cacheKey = `channels_${categoryId}`;
      const cached = this.cache.get(cacheKey);
      
      if (cached) {
        this.channels = cached;
        this.renderChannels();
        return;
      }

      let url = `${this.config.server}/player_api.php?username=${this.config.username}&password=${this.config.password}&action=get_live_streams`;
      
      if (categoryId !== 'all') {
        url += `&category_id=${categoryId}`;
      }

      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const channels = await response.json();
      
      // Process channels data
      this.channels = Array.isArray(channels) ? channels.map(channel => ({
        id: channel.stream_id || channel.id,
        name: channel.name || 'Canal sem nome',
        url: `${this.config.server}/live/${this.config.username}/${this.config.password}/${channel.stream_id}.m3u8`,
        icon: channel.stream_icon || null,
        letter: Utils.getFirstLetter(channel.name),
        category: channel.category_name || 'Geral',
        type: 'channel'
      })) : [];

      this.cache.set(cacheKey, this.channels);
      this.renderChannels();
    } catch (error) {
      console.error('Error loading channels:', error);
      this.showErrorOverlay('Erro ao carregar canais', () => this.loadChannels(categoryId));
    }
  }

  /**
   * Load movies by category
   */
  async loadMovies(categoryId = 'all') {
    if (!this.config.server) return;

    try {
      const cacheKey = `movies_${categoryId}`;
      const cached = this.cache.get(cacheKey);
      
      if (cached) {
        this.movies = cached;
        this.renderMovies();
        return;
      }

      let url = `${this.config.server}/player_api.php?username=${this.config.username}&password=${this.config.password}&action=get_vod_streams`;
      
      if (categoryId !== 'all') {
        url += `&category_id=${categoryId}`;
      }

      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const movies = await response.json();
      
      // Process movies data
      this.movies = Array.isArray(movies) ? movies.map(movie => ({
        id: movie.stream_id || movie.id,
        name: movie.name || 'Filme sem nome',
        url: `${this.config.server}/movie/${this.config.username}/${this.config.password}/${movie.stream_id}.${movie.container_extension || 'mp4'}`,
        icon: movie.stream_icon || null,
        letter: Utils.getFirstLetter(movie.name),
        category: movie.category_name || 'Geral',
        year: movie.year || null,
        rating: movie.rating || null,
        type: 'movie'
      })) : [];

      this.cache.set(cacheKey, this.movies);
      this.renderMovies();
    } catch (error) {
      console.error('Error loading movies:', error);
      this.showErrorOverlay('Erro ao carregar filmes', () => this.loadMovies(categoryId));
    }
  }

  /**
   * Load series by category
   */
  async loadSeries(categoryId = 'all') {
    if (!this.config.server) return;

    try {
      const cacheKey = `series_${categoryId}`;
      const cached = this.cache.get(cacheKey);
      
      if (cached) {
        this.series = cached;
        this.renderSeries();
        return;
      }

      let url = `${this.config.server}/player_api.php?username=${this.config.username}&password=${this.config.password}&action=get_series`;
      
      if (categoryId !== 'all') {
        url += `&category_id=${categoryId}`;
      }

      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const series = await response.json();
      
      // Process series data
      this.series = Array.isArray(series) ? series.map(serie => ({
        id: serie.series_id || serie.id,
        name: serie.name || 'Série sem nome',
        icon: serie.cover || null,
        letter: Utils.getFirstLetter(serie.name),
        category: serie.category_name || 'Geral',
        year: serie.year || null,
        rating: serie.rating || null,
        type: 'series'
      })) : [];

      this.cache.set(cacheKey, this.series);
      this.renderSeries();
    } catch (error) {
      console.error('Error loading series:', error);
      this.showErrorOverlay('Erro ao carregar séries', () => this.loadSeries(categoryId));
    }
  }

  /**
   * Render channel tabs
   */
  renderChannelTabs() {
    const tabNav = document.getElementById('channelTabs');
    if (!tabNav) return;

    tabNav.innerHTML = `
      <button class="tab-btn active" data-category="all">Todos</button>
      ${this.channelCategories.map(cat => 
        `<button class="tab-btn" data-category="${cat.category_id}">${cat.category_name}</button>`
      ).join('')}
    `;

    // Add event listeners
    tabNav.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const category = e.target.getAttribute('data-category');
        this.activeChannelCategory = category;
        
        // Update active tab
        tabNav.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        // Load channels
        this.loadChannels(category);
      });
    });
  }

  /**
   * Render movie tabs
   */
  renderMovieTabs() {
    const tabNav = document.getElementById('movieTabs');
    if (!tabNav) return;

    tabNav.innerHTML = `
      <button class="tab-btn active" data-category="all">Todos</button>
      ${this.movieCategories.map(cat => 
        `<button class="tab-btn" data-category="${cat.category_id}">${cat.category_name}</button>`
      ).join('')}
    `;

    // Add event listeners
    tabNav.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const category = e.target.getAttribute('data-category');
        this.activeMovieCategory = category;
        
        // Update active tab
        tabNav.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        // Load movies
        this.loadMovies(category);
      });
    });
  }

  /**
   * Render series tabs
   */
  renderSeriesTabs() {
    const tabNav = document.getElementById('seriesTabs');
    if (!tabNav) return;

    tabNav.innerHTML = `
      <button class="tab-btn active" data-category="all">Todas</button>
      ${this.seriesCategories.map(cat => 
        `<button class="tab-btn" data-category="${cat.category_id}">${cat.category_name}</button>`
      ).join('')}
    `;

    // Add event listeners
    tabNav.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const category = e.target.getAttribute('data-category');
        this.activeSeriesCategory = category;
        
        // Update active tab
        tabNav.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        // Load series
        this.loadSeries(category);
      });
    });
  }

  /**
   * Render radio tabs
   */
  renderRadioTabs() {
    const tabNav = document.getElementById('radioTabs');
    if (!tabNav) return;

    // Radio tabs are hardcoded in the HTML
    tabNav.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const category = e.target.getAttribute('data-category');
        this.activeRadioCategory = category;
        
        // Update active tab
        tabNav.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        // Render radios
        this.renderRadios();
      });
    });
  }

  /**
   * Render channels list
   */
  renderChannels() {
    const channelsList = document.getElementById('channelsList');
    if (!channelsList) return;

    let filteredChannels = this.channels;
    
    if (this.activeChannelCategory !== 'all') {
      const category = this.channelCategories.find(cat => cat.category_id === this.activeChannelCategory);
      if (category) {
        filteredChannels = this.channels.filter(channel => channel.category === category.category_name);
      }
    }

    if (filteredChannels.length === 0) {
      channelsList.innerHTML = `
        <div class="text-center p-4">
          <i class="fas fa-tv fa-3x text-muted mb-3"></i>
          <p class="text-muted">Nenhum canal encontrado</p>
        </div>
      `;
      return;
    }

    channelsList.innerHTML = '';
    filteredChannels.forEach(channel => {
      const item = this.createContentItem(channel, 'channel');
      channelsList.appendChild(item);
    });
  }

  /**
   * Render movies list
   */
  renderMovies() {
    const moviesList = document.getElementById('moviesList');
    if (!moviesList) return;

    let filteredMovies = this.movies;
    
    if (this.activeMovieCategory !== 'all') {
      const category = this.movieCategories.find(cat => cat.category_id === this.activeMovieCategory);
      if (category) {
        filteredMovies = this.movies.filter(movie => movie.category === category.category_name);
      }
    }

    if (filteredMovies.length === 0) {
      moviesList.innerHTML = `
        <div class="text-center p-4">
          <i class="fas fa-film fa-3x text-muted mb-3"></i>
          <p class="text-muted">Nenhum filme encontrado</p>
        </div>
      `;
      return;
    }

    moviesList.innerHTML = '';
    filteredMovies.forEach(movie => {
      const item = this.createContentItem(movie, 'movie');
      moviesList.appendChild(item);
    });
  }

  /**
   * Render series list
   */
  renderSeries() {
    const seriesList = document.getElementById('seriesList');
    if (!seriesList) return;

    let filteredSeries = this.series;
    
    if (this.activeSeriesCategory !== 'all') {
      const category = this.seriesCategories.find(cat => cat.category_id === this.activeSeriesCategory);
      if (category) {
        filteredSeries = this.series.filter(serie => serie.category === category.category_name);
      }
    }

    if (filteredSeries.length === 0) {
      seriesList.innerHTML = `
        <div class="text-center p-4">
          <i class="fas fa-tv fa-3x text-muted mb-3"></i>
          <p class="text-muted">Nenhuma série encontrada</p>
        </div>
      `;
      return;
    }

    seriesList.innerHTML = '';
    filteredSeries.forEach(series => {
      const item = this.createContentItem(series, 'series');
      seriesList.appendChild(item);
    });
  }

  /**
   * Render radios list
   */
  renderRadios() {
    const radiosList = document.getElementById('radiosList');
    if (!radiosList) return;

    let filteredRadios = this.radios;
    
    if (this.activeRadioCategory !== 'all') {
      filteredRadios = this.radios.filter(radio => radio.category === this.activeRadioCategory);
    }

    if (filteredRadios.length === 0) {
      radiosList.innerHTML = `
        <div class="text-center p-4">
          <i class="fas fa-radio fa-3x text-muted mb-3"></i>
          <p class="text-muted">Nenhuma rádio encontrada nesta categoria</p>
        </div>
      `;
      return;
    }

    radiosList.innerHTML = '';
    filteredRadios.forEach(radio => {
      const item = this.createContentItem(radio, 'radio');
      radiosList.appendChild(item);
    });
  }

  /**
   * Create content item element
   */
  createContentItem(content, type) {
    const item = document.createElement('div');
    item.className = 'content-item';
    item.setAttribute('data-id', content.id);
    
    const isPlaying = (type === 'channel' && this.currentChannel === content.id) ||
                     (type === 'movie' && this.currentMovie?.id === content.id) ||
                     (type === 'series' && this.currentSeries?.id === content.id) ||
                     (type === 'radio' && this.currentRadio?.id === content.id);

    if (isPlaying) {
      item.classList.add('playing');
    }

    const avatarStyle = content.icon ? 
      `background-image: url('${content.icon}'); background-size: cover; background-position: center;` : '';

    // Check for watch progress
    const progressKey = `${type}_${content.id}`;
    const progress = this.progressTracker.getProgress(progressKey);
    let progressIndicator = '';
    
    if (progress && progress.percentage > 5 && progress.percentage < 90) {
      progressIndicator = `<div class="progress-indicator">${Math.round(progress.percentage)}%</div>`;
    }

    let details = this.getContentDetails(content, type, isPlaying);

    item.innerHTML = `
      <div class="content-avatar" style="${avatarStyle}">
        ${!content.icon ? content.letter : ''}
      </div>
      <div class="content-info">
        <div class="content-name">${Utils.sanitizeHtml(content.name)}</div>
        <div class="content-details">
          ${details}
          ${content.rating ? ` • ⭐ ${content.rating}` : ''}
          ${progressIndicator}
        </div>
      </div>
      ${isPlaying ? '<div class="playing-indicator">Tocando</div>' : ''}
      <button class="favorite-btn ${this.favoritesBackend.isFavorite(content.id) ? 'active' : ''}" 
              data-id="${content.id}">
        <i class="fas fa-heart"></i>
      </button>
    `;

    // Content click event
    item.addEventListener('click', (e) => {
      if (!e.target.classList.contains('favorite-btn') && !e.target.closest('.favorite-btn')) {
        this.playContent(content, type);
      }
    });

    // Favorite button event
    const favoriteBtn = item.querySelector('.favorite-btn');
    favoriteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleFavorite(content.id);
    });

    return item;
  }

  /**
   * Get content details text
   */
  getContentDetails(content, type, isPlaying) {
    if (type === 'channel') {
      return isPlaying ? 'Reproduzindo agora' : 'Toque para assistir';
    } else if (type === 'movie') {
      return content.year ? `Ano: ${content.year}` : 'Filme';
    } else if (type === 'series') {
      return 'Série';
    } else if (type === 'radio') {
      let details = content.frequency || 'Rádio';
      if (content.city) details += ` • ${content.city}`;
      
      const hasVideo = content.video && content.video.trim() !== '' && content.video !== 'url_vídeo';
      if (hasVideo) {
        details += ' • 📺';
      }
      
      if (isPlaying) details = 'Tocando agora';
      return details;
    }
    return '';
  }

  /**
   * Play content based on type
   */
  playContent(content, type) {
    switch (type) {
      case 'channel':
        this.playChannel(content);
        break;
      case 'movie':
        this.playMovie(content);
        break;
      case 'series':
        this.showSeriesEpisodes(content);
        break;
      case 'radio':
        this.playRadio(content);
        break;
    }
  }

  /**
   * Setup advanced video player with HLS support
   */
  setupAdvancedPlayer(url, type) {
    try {
      // Dispose existing player
      if (this.player) {
        this.player.dispose();
      }

      // Create new player instance
      this.player = videojs('videoPlayer', {
        controls: true,
        responsive: true,
        fluid: true,
        playbackRates: [0.5, 1, 1.25, 1.5, 2],
        plugins: {
          hotkeys: {
            volumeStep: 0.1,
            seekStep: 5,
            enableModifiersForNumbers: false
          }
        }
      });

      // Load source
      if (Hls.isSupported()) {
        const hls = new Hls({
          enableWorker: false,
          lowLatencyMode: true,
          backBufferLength: 90
        });
        
        hls.loadSource(url);
        hls.attachMedia(this.player.el().querySelector('video'));
        
        hls.on(Hls.Events.ERROR, (event, data) => {
          console.error('HLS Error:', data);
          if (data.fatal) {
            this.showErrorOverlay('Erro na transmissão', () => {
              this.setupAdvancedPlayer(url, type);
            });
          }
        });
      } else {
        this.player.src({ src: url, type: 'application/x-mpegURL' });
      }

      // Setup player events
      this.setupPlayerEvents(type);

    } catch (error) {
      console.error('Error setting up player:', error);
      this.showErrorOverlay('Erro ao configurar player', () => {
        this.setupAdvancedPlayer(url, type);
      });
    }
  }

  /**
   * Setup player events
   */
  setupPlayerEvents(type) {
    if (!this.player) return;

    this.player.on('loadstart', () => {
      console.log('Player loading started');
    });

    this.player.on('canplay', () => {
      console.log('Player can play');
    });

    this.player.on('error', (error) => {
      console.error('Player error:', error);
      this.showErrorOverlay('Erro de reprodução', () => {
        if (this.currentChannel) {
          const channel = this.channels.find(c => c.id === this.currentChannel);
          if (channel) this.playChannel(channel);
        }
      });
    });

    this.player.on('ended', () => {
      console.log('Playback ended');
      if (type === 'movie') {
        this.progressTracker.removeProgress(`movie_${this.currentMovie.id}`);
      }
    });
  }

  /**
   * Play channel
   */
  playChannel(channel) {
    try {
      this.animateLogo();
      this.currentChannel = channel.id;
      this.currentMovie = null;
      this.currentSeries = null;
      this.currentEpisode = null;
      this.currentRadio = null;

      this.setupAdvancedPlayer(channel.url, 'channel');

      this.player.ready(() => {
        this.player.play();
      });

      document.getElementById('videoPlaceholder').style.display = 'none';
      this.renderChannels();
      this.hideRadioInfo();
      this.hideRadioVisualDisplay();
    } catch (error) {
      console.error('Error playing channel:', error);
      this.showErrorOverlay('Erro ao reproduzir canal', () => this.playChannel(channel));
    }
  }

  /**
   * Play movie
   */
  playMovie(movie) {
    try {
      this.animateLogo();
      this.currentMovie = movie;
      this.currentChannel = null;
      this.currentSeries = null;
      this.currentEpisode = null;
      this.currentRadio = null;

      this.setupAdvancedPlayer(movie.url, 'movie');

      this.player.ready(() => {
        this.player.play();
      });

      document.getElementById('videoPlaceholder').style.display = 'none';
      this.renderMovies();
      this.hideRadioInfo();
      this.hideRadioVisualDisplay();
    } catch (error) {
      console.error('Error playing movie:', error);
      this.showErrorOverlay('Erro ao reproduzir filme', () => this.playMovie(movie));
    }
  }

  /**
   * Play radio
   */
  playRadio(radio) {
    try {
      this.animateLogo();
      this.currentRadio = radio;
      this.currentChannel = null;
      this.currentMovie = null;
      this.currentSeries = null;
      this.currentEpisode = null;

      const hasVideoStream = radio.video && radio.video.trim() !== '' && radio.video !== 'url_vídeo';
      
      if (hasVideoStream) {
        console.log('Playing radio with video stream:', radio.video);
        this.radioVideoMode = true;
        this.setupAdvancedPlayer(radio.video, 'radio-video');
        this.hideRadioVisualDisplay();
        this.showRadioInfo(radio);
      } else {
        console.log('Playing radio in audio-only mode:', radio.url);
        this.radioVideoMode = false;
        this.setupAdvancedPlayer(radio.url, 'radio');
        this.showRadioVisualDisplay(radio);
        this.startMetadataFetching(radio);
      }
      
      this.player.ready(() => {
        this.player.play();
      });

      document.getElementById('videoPlaceholder').style.display = 'none';
      this.renderRadios();
    } catch (error) {
      console.error('Error playing radio:', error);
      this.showErrorOverlay('Erro ao reproduzir rádio', () => this.playRadio(radio));
    }
  }

  /**
   * Animate logo
   */
  animateLogo() {
    const logo = document.getElementById('playerLogo');
    if (!logo) return;
    
    logo.classList.remove('animate-center', 'animate-to-position');
    logo.offsetHeight; // Force reflow
    logo.classList.add('animate-center');
    
    setTimeout(() => {
      logo.classList.remove('animate-center');
      logo.classList.add('animate-to-position');
      
      setTimeout(() => {
        logo.classList.remove('animate-to-position');
      }, 1200);
    }, 1500);
  }

  /**
   * Show radio visual display
   */
  showRadioVisualDisplay(radio) {
    if (this.radioVideoMode) return;
    
    const visualDisplay = document.getElementById('radioVisualDisplay');
    const background = document.getElementById('radioBackground');
    const mainImage = document.getElementById('radioMainImage');
    const mainName = document.getElementById('radioMainName');
    const mainFrequency = document.getElementById('radioMainFrequency');

    mainName.textContent = radio.name;
    mainFrequency.textContent = `${radio.frequency}${radio.city ? ' • ' + radio.city : ''}`;

    if (radio.icon) {
      background.style.backgroundImage = `url(${radio.icon})`;
      mainImage.src = radio.icon;
      mainImage.alt = radio.name;
      
      mainImage.onerror = function() {
        background.style.backgroundImage = 'linear-gradient(135deg, var(--primary-color), var(--bg-secondary))';
        this.style.display = 'none';
      };
      mainImage.onload = function() {
        this.style.display = 'block';
      };
    } else {
      background.style.backgroundImage = 'linear-gradient(135deg, var(--primary-color), var(--bg-secondary))';
      mainImage.style.display = 'none';
    }

    visualDisplay.classList.add('active');
    this.showRadioInfo(radio);
  }

  /**
   * Hide radio visual display
   */
  hideRadioVisualDisplay() {
    const visualDisplay = document.getElementById('radioVisualDisplay');
    visualDisplay.classList.remove('active');
    this.stopMetadataFetching();
    this.radioVideoMode = false;
  }

  /**
   * Show radio info overlay
   */
  showRadioInfo(radio) {
    const overlay = document.getElementById('radioInfoOverlay');
    const logoSmall = document.getElementById('radioLogoSmall');
    const nameOverlay = document.getElementById('radioOverlayName');
    const frequencyOverlay = document.getElementById('radioOverlayFrequency');

    logoSmall.src = radio.icon || '';
    logoSmall.alt = radio.name;
    logoSmall.onerror = function() { this.style.display = 'none'; };
    logoSmall.onload = function() { this.style.display = 'block'; };
    
    nameOverlay.textContent = radio.name;
    
    const hasVideo = radio.video && radio.video.trim() !== '' && radio.video !== 'url_vídeo';
    let frequencyText = `${radio.frequency}${radio.city ? ' • ' + radio.city : ''}`;
    if (hasVideo) {
      frequencyText += ' • 📺 Com Vídeo';
    }
    frequencyOverlay.textContent = frequencyText;

    overlay.classList.add('visible');

    const hideDelay = hasVideo ? 5000 : 10000;
    setTimeout(() => {
      overlay.classList.remove('visible');
    }, hideDelay);
  }

  /**
   * Hide radio info overlay
   */
  hideRadioInfo() {
    const overlay = document.getElementById('radioInfoOverlay');
    overlay.classList.remove('visible');
  }

  /**
   * Start metadata fetching for radio
   */
  startMetadataFetching(radio) {
    if (this.metadataInterval) {
      clearInterval(this.metadataInterval);
      this.metadataInterval = null;
    }

    const metadataInfo = document.getElementById('radioMetadataInfo');
    if (!metadataInfo) return;

    metadataInfo.style.display = 'none';

    if (radio.metadata) {
      console.log('Starting metadata fetching for radio:', radio.name);
      metadataInfo.style.display = 'block';
      
      this.fetchRadioMetadata(radio);
      this.metadataInterval = setInterval(() => {
        this.fetchRadioMetadata(radio);
      }, 30000);
    }
  }

  /**
   * Fetch radio metadata
   */
  async fetchRadioMetadata(radio) {
    if (!radio.metadata || !radio.url) return;

    try {
      const metadataUrl = radio.metadata + encodeURIComponent(radio.url);
      const response = await fetch(metadataUrl, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data && data.title) {
        this.updateSongTitle(data.title);
      }
    } catch (error) {
      console.error('Error fetching metadata:', error);
    }
  }

  /**
   * Update song title in radio display
   */
  updateSongTitle(title) {
    const songTitleElement = document.getElementById('nowPlayingText');
    if (songTitleElement && title) {
      songTitleElement.textContent = title;
    }
  }

  /**
   * Stop metadata fetching
   */
  stopMetadataFetching() {
    if (this.metadataInterval) {
      clearInterval(this.metadataInterval);
      this.metadataInterval = null;
    }
    
    const metadataInfo = document.getElementById('radioMetadataInfo');
    if (metadataInfo) {
      metadataInfo.style.display = 'none';
    }
  }

  /**
   * Show series episodes
   */
  async showSeriesEpisodes(series) {
    try {
      this.currentSeries = series;
      
      document.getElementById('seriesList').style.display = 'none';
      const episodesList = document.getElementById('episodesList');
      episodesList.style.display = 'grid';

      episodesList.innerHTML = `
        <div class="episode-back-button">
          <button class="btn btn-secondary" onclick="iptvApp.hideSeriesEpisodes()">
            <i class="fas fa-arrow-left"></i> Voltar para Séries
          </button>
        </div>
        <div class="text-center p-4" style="grid-column: 1 / -1;">
          <div class="loading-spinner"></div>
          <p class="mt-2 mb-0">Carregando episódios...</p>
        </div>
      `;

      // Load episodes from API
      const episodes = await this.loadSeriesEpisodes(series.id);
      this.renderEpisodes(episodes);
    } catch (error) {
      console.error('Error showing series episodes:', error);
      this.showError('Erro ao carregar episódios');
    }
  }

  /**
   * Hide series episodes and return to series list
   */
  hideSeriesEpisodes() {
    document.getElementById('episodesList').style.display = 'none';
    document.getElementById('seriesList').style.display = 'block';
    this.currentSeries = null;
  }

  /**
   * Load series episodes from API
   */
  async loadSeriesEpisodes(seriesId) {
    if (!this.config.server) return [];

    try {
      const cacheKey = `episodes_${seriesId}`;
      const cached = this.cache.get(cacheKey);
      
      if (cached) return cached;

      const url = `${this.config.server}/player_api.php?username=${this.config.username}&password=${this.config.password}&action=get_series_info&series_id=${seriesId}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const episodes = [];

      if (data.episodes) {
        Object.values(data.episodes).forEach(season => {
          Object.values(season).forEach(episode => {
            episodes.push({
              id: episode.id,
              title: episode.title || `Episódio ${episode.episode_num}`,
              episode_num: episode.episode_num,
              season_num: episode.season,
              url: `${this.config.server}/series/${this.config.username}/${this.config.password}/${episode.id}.${episode.container_extension || 'mp4'}`,
              info: episode.info || {}
            });
          });
        });
      }

      this.cache.set(cacheKey, episodes);
      return episodes;
    } catch (error) {
      console.error('Error loading episodes:', error);
      return [];
    }
  }

  /**
   * Render episodes
   */
  renderEpisodes(episodes) {
    const episodesList = document.getElementById('episodesList');
    if (!episodesList) return;

    if (episodes.length === 0) {
      episodesList.innerHTML = `
        <div class="episode-back-button">
          <button class="btn btn-secondary" onclick="iptvApp.hideSeriesEpisodes()">
            <i class="fas fa-arrow-left"></i> Voltar para Séries
          </button>
        </div>
        <div class="text-center p-4" style="grid-column: 1 / -1;">
          <i class="fas fa-tv fa-3x text-muted mb-3"></i>
          <p class="text-muted">Nenhum episódio encontrado</p>
        </div>
      `;
      return;
    }

    // Group episodes by season
    const episodesBySeasons = {};
    episodes.forEach(episode => {
      const season = episode.season_num || 1;
      if (!episodesBySeasons[season]) {
        episodesBySeasons[season] = [];
      }
      episodesBySeasons[season].push(episode);
    });

    let html = `
      <div class="episode-back-button">
        <button class="btn btn-secondary" onclick="iptvApp.hideSeriesEpisodes()">
          <i class="fas fa-arrow-left"></i> Voltar para Séries
        </button>
      </div>
    `;

    Object.keys(episodesBySeasons).sort((a, b) => a - b).forEach(season => {
      const seasonEpisodes = episodesBySeasons[season].sort((a, b) => a.episode_num - b.episode_num);
      
      seasonEpisodes.forEach(episode => {
        const isCurrentEpisode = this.currentEpisode?.id === episode.id;
        
        html += `
          <div class="episode-card ${isCurrentEpisode ? 'current' : ''}" data-episode-id="${episode.id}">
            <div class="episode-number">T${season} • E${episode.episode_num}</div>
            <div class="episode-title">${Utils.sanitizeHtml(episode.title)}</div>
            <div class="episode-info">
              ${episode.info.plot ? Utils.sanitizeHtml(episode.info.plot.substring(0, 100)) + '...' : 'Clique para assistir'}
            </div>
          </div>
        `;
      });
    });

    episodesList.innerHTML = html;

    // Add click events to episode cards
    episodesList.querySelectorAll('.episode-card').forEach(card => {
      card.addEventListener('click', () => {
        const episodeId = card.getAttribute('data-episode-id');
        const episode = episodes.find(ep => ep.id === episodeId);
        if (episode) {
          this.playEpisode(episode);
        }
      });
    });
  }

  /**
   * Play episode
   */
  playEpisode(episode) {
    try {
      this.animateLogo();
      this.currentEpisode = episode;
      this.currentChannel = null;
      this.currentMovie = null;
      this.currentRadio = null;

      this.setupAdvancedPlayer(episode.url, 'episode');

      this.player.ready(() => {
        this.player.play();
      });

      document.getElementById('videoPlaceholder').style.display = 'none';
      this.hideRadioInfo();
      this.hideRadioVisualDisplay();
      
      // Re-render episodes to show current playing
      this.renderEpisodes(this.currentEpisodes || []);
    } catch (error) {
      console.error('Error playing episode:', error);
      this.showErrorOverlay('Erro ao reproduzir episódio', () => this.playEpisode(episode));
    }
  }

  /**
   * Toggle favorite
   */
  toggleFavorite(itemId) {
    const isFavorite = this.favoritesBackend.isFavorite(itemId);
    
    if (isFavorite) {
      this.favoritesBackend.removeFavorite(itemId);
      this.showToast('Removido dos favoritos!', 'info');
    } else {
      // Find the item in current data
      let item = null;
      
      item = this.channels.find(c => c.id === itemId) ||
             this.movies.find(m => m.id === itemId) ||
             this.series.find(s => s.id === itemId) ||
             this.radios.find(r => r.id === itemId);
      
      if (item) {
        this.favoritesBackend.addFavorite(item);
        this.showToast('Adicionado aos favoritos!', 'success');
      }
    }
    
    // Update UI
    this.updateFavoriteButtons();
    this.renderFavorites();
  }

  /**
   * Update favorite buttons in UI
   */
  updateFavoriteButtons() {
    document.querySelectorAll('.favorite-btn').forEach(btn => {
      const itemId = btn.getAttribute('data-id');
      if (itemId) {
        const isFav = this.favoritesBackend.isFavorite(itemId);
        btn.classList.toggle('active', isFav);
      }
    });
  }

  /**
   * Render favorites section
   */
  renderFavorites() {
    const favoritesList = document.getElementById('favoritesList');
    const favoritesCount = document.getElementById('favoritesCount');
    
    if (!favoritesList) return;

    const favorites = this.favoritesBackend.getFavorites();
    
    if (favoritesCount) {
      favoritesCount.textContent = `(${favorites.length} ${favorites.length === 1 ? 'item' : 'itens'})`;
    }

    if (favorites.length === 0) {
      favoritesList.innerHTML = `
        <div class="favorites-empty">
          <i class="fas fa-heart-broken"></i>
          <h5>Nenhum favorito ainda</h5>
          <p>Adicione seus canais, filmes, séries e rádios favoritos clicando no coração <i class="fas fa-heart text-danger"></i></p>
        </div>
      `;
      return;
    }

    favoritesList.innerHTML = '';
    favorites.forEach(favorite => {
      const card = document.createElement('div');
      card.className = 'favorite-card';
      
      const iconStyle = favorite.icon ? 
        `background-image: url('${favorite.icon}'); background-size: cover; background-position: center;` : '';
      
      card.innerHTML = `
        <div class="favorite-header">
          <div class="favorite-avatar" style="${iconStyle}">
            ${!favorite.icon ? favorite.letter : ''}
          </div>
          <div class="favorite-info">
            <h6>${Utils.sanitizeHtml(favorite.name)}</h6>
            <small>
              <i class="fas fa-${this.getFavoriteIcon(favorite.type)}"></i>
              ${this.getTypeLabel(favorite.type)}
              ${favorite.category ? ` • ${favorite.category}` : ''}
            </small>
          </div>
        </div>
        <div class="favorite-actions">
          <button class="play-btn" data-favorite-id="${favorite.id}">
            <i class="fas fa-play"></i> Reproduzir
          </button>
          <button class="remove-favorite" data-favorite-id="${favorite.id}">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      `;

      // Play button event
      const playBtn = card.querySelector('.play-btn');
      playBtn.addEventListener('click', () => {
        this.playFavoriteItem(favorite);
      });

      // Remove button event
      const removeBtn = card.querySelector('.remove-favorite');
      removeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        
        if (confirm(`Tem certeza que deseja remover "${favorite.name}" dos favoritos?`)) {
          this.favoritesBackend.removeFavorite(favorite.id);
          this.renderFavorites();
          this.updateFavoriteButtons();
          this.showToast('Favorito removido!', 'info');
        }
      });
      
      favoritesList.appendChild(card);
    });
  }

  /**
   * Get favorite icon based on type
   */
  getFavoriteIcon(type) {
    const icons = {
      'channel': 'tv',
      'movie': 'film',
      'series': 'play-circle',
      'radio': 'radio'
    };
    return icons[type] || 'star';
  }

  /**
   * Get type label
   */
  getTypeLabel(type) {
    const labels = {
      'channel': 'Canal',
      'movie': 'Filme',
      'series': 'Série',
      'radio': 'Rádio'
    };
    return labels[type] || type;
  }

  /**
   * Play favorite item
   */
  playFavoriteItem(favorite) {
    if (favorite.type === 'channel') {
      this.showContentSection('channels');
      this.playChannel(favorite);
    } else if (favorite.type === 'movie') {
      this.showContentSection('movies');
      this.playMovie(favorite);
    } else if (favorite.type === 'series') {
      this.showContentSection('series');
      this.showSeriesEpisodes(favorite);
    } else if (favorite.type === 'radio') {
      this.showContentSection('radios');
      this.playRadio(favorite);
    }
    
    // Update navigation
    document.querySelectorAll('.main-nav .nav-link').forEach(l => l.classList.remove('active'));
    const targetContent = favorite.type === 'channel' ? 'channels' : 
                         favorite.type === 'movie' ? 'movies' : 
                         favorite.type === 'series' ? 'series' : 'radios';
    const targetLink = document.querySelector(`[data-content="${targetContent}"]`);
    if (targetLink) {
      targetLink.classList.add('active');
    }
  }

  /**
   * Perform search
   */
  performSearch(query) {
    const resultsContainer = document.getElementById('searchResults');
    
    if (!query || query.length < 2) {
      resultsContainer.innerHTML = `
        <div class="text-center">
          <i class="fas fa-search fa-2x mb-2" style="color: #666;"></i>
          <p>Digite pelo menos 2 caracteres para buscar</p>
        </div>
      `;
      return;
    }

    const searchChannels = document.getElementById('searchChannels')?.checked || false;
    const searchMovies = document.getElementById('searchMovies')?.checked || false;
    const searchSeries = document.getElementById('searchSeries')?.checked || false;
    const searchRadios = document.getElementById('searchRadios')?.checked || false;

    let results = [];
    
    if (searchChannels) {
      results.push(...this.channels.filter(item => 
        item.name.toLowerCase().includes(query.toLowerCase())
      ));
    }
    
    if (searchMovies) {
      results.push(...this.movies.filter(item => 
        item.name.toLowerCase().includes(query.toLowerCase())
      ));
    }
    
    if (searchSeries) {
      results.push(...this.series.filter(item => 
        item.name.toLowerCase().includes(query.toLowerCase())
      ));
    }
    
    if (searchRadios) {
      results.push(...this.radios.filter(item => 
        item.name.toLowerCase().includes(query.toLowerCase())
      ));
    }

    if (results.length === 0) {
      resultsContainer.innerHTML = `
        <div class="text-center p-4">
          <i class="fas fa-search fa-2x mb-2" style="color: #666;"></i>
          <p>Nenhum resultado encontrado para "${query}"</p>
        </div>
      `;
      return;
    }

    resultsContainer.innerHTML = '';
    results.slice(0, 50).forEach(item => {
      const searchItem = document.createElement('div');
      searchItem.className = 'search-item';
      
      const iconStyle = item.icon ? 
        `background-image: url('${item.icon}'); background-size: cover; background-position: center;` : '';
      
      searchItem.innerHTML = `
        <div class="item-icon" style="${iconStyle}">
          ${!item.icon ? item.letter : ''}
        </div>
        <div class="item-info">
          <div class="item-name">${Utils.sanitizeHtml(item.name)}</div>
          <div class="item-type">${this.getTypeLabel(item.type)}</div>
        </div>
      `;

      searchItem.addEventListener('click', () => {
        // Close search modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('searchModal'));
        if (modal) modal.hide();
        
        // Play the selected item
        this.playContent(item, item.type);
        
        // Navigate to appropriate section
        const targetContent = item.type === 'channel' ? 'channels' : 
                             item.type === 'movie' ? 'movies' : 
                             item.type === 'series' ? 'series' : 'radios';
        
        this.showContentSection(targetContent);
        
        // Update navigation
        document.querySelectorAll('.main-nav .nav-link').forEach(l => l.classList.remove('active'));
        const targetLink = document.querySelector(`[data-content="${targetContent}"]`);
        if (targetLink) {
          targetLink.classList.add('active');
        }
      });

      resultsContainer.appendChild(searchItem);
    });
  }

  /**
   * Save playlist configuration
   */
  async savePlaylist() {
    try {
      const url = document.getElementById('playlistUrl').value.trim();
      if (!url) {
        this.showError('Por favor, insira uma URL válida');
        return;
      }

      const newConfig = this.extractPlaylistInfo(url);
      this.config = newConfig;
      this.saveConfig();

      // Close modal
      const modal = bootstrap.Modal.getInstance(document.getElementById('playlistModal'));
      if (modal) modal.hide();
      
      document.getElementById('playlistForm').reset();

      // Clear cache when changing playlist
      this.cache.clear();

      await Promise.all([
        this.loadCategories(),
        this.loadMovieCategories(),
        this.loadSeriesCategories()
      ]);

      this.showSuccess('Playlist adicionada com sucesso!');
    } catch (error) {
      console.error('Error saving playlist:', error);
      this.showError(error.message);
    }
  }

  /**
   * Extract playlist info from URL
   */
  extractPlaylistInfo(url) {
    try {
      const urlObj = new URL(url);
      const server = `${urlObj.protocol}//${urlObj.host}`;
      const username = urlObj.searchParams.get('username');
      const password = urlObj.searchParams.get('password');

      if (!username || !password) {
        throw new Error('Username ou password não encontrado na URL');
      }

      return { server, username, password };
    } catch (error) {
      throw new Error('URL inválida. Verifique se contém username e password.');
    }
  }

  /**
   * Share app
   */
  shareApp() {
    const shareUrl = window.location.href;
    
    if (navigator.share) {
      navigator.share({
        title: 'IPTV Player v9 v3 - Canais, Filmes e Séries',
        text: 'Assista canais brasileiros, filmes e séries online',
        url: shareUrl
      }).catch(console.error);
    } else {
      navigator.clipboard.writeText(shareUrl).then(() => {
        this.showSuccess('Link copiado para a área de transferência!');
      }).catch(() => {
        this.showError('Não foi possível copiar o link');
      });
    }
  }

  /**
   * Show error overlay
   */
  showErrorOverlay(message, retryCallback) {
    const overlay = document.getElementById('errorOverlay');
    const messageEl = document.getElementById('errorMessage');
    
    messageEl.textContent = message;
    this.pendingRetryAction = retryCallback;
    overlay.style.display = 'flex';
  }

  /**
   * Retry action from error overlay
   */
  retryAction() {
    document.getElementById('errorOverlay').style.display = 'none';
    if (this.pendingRetryAction) {
      this.pendingRetryAction();
      this.pendingRetryAction = null;
    }
  }

  /**
   * Show error message
   */
  showError(message) {
    this.showAlert('Erro', message, 'error');
  }

  /**
   * Show success message
   */
  showSuccess(message) {
    this.showAlert('Sucesso', message, 'success');
  }

  /**
   * Show alert dialog
   */
  showAlert(title, message, type = 'info') {
    // Remove existing alerts
    document.querySelectorAll('.custom-alert, .alert-backdrop').forEach(el => el.remove());

    const backdrop = document.createElement('div');
    backdrop.className = 'alert-backdrop';
    backdrop.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.8);
      z-index: 9998;
      display: flex;
      align-items: center;
      justify-content: center;
    `;

    const alert = document.createElement('div');
    alert.className = 'custom-alert';
    alert.style.cssText = `
      background: var(--bg-tertiary);
      color: white;
      padding: 2rem;
      border-radius: 1rem;
      text-align: center;
      max-width: 90%;
      width: 400px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    `;

    const iconColor = type === 'error' ? '#EF4444' : type === 'success' ? '#10B981' : '#6B7280';
    const iconName = type === 'error' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle';

    alert.innerHTML = `
      <i class="fas fa-${iconName} fa-3x mb-3" style="color: ${iconColor}"></i>
      <h5 class="mb-3">${title}</h5>
      <p class="mb-4">${message}</p>
      <button class="btn btn-${type === 'error' ? 'danger' : 'success'}" onclick="this.closest('.alert-backdrop').remove()">
        OK
      </button>
    `;

    backdrop.appendChild(alert);
    document.body.appendChild(backdrop);

    if (type === 'success') {
      setTimeout(() => {
        if (backdrop.parentNode) {
          backdrop.remove();
        }
      }, 5000);
    }
  }

  /**
   * Show toast notification
   */
  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${type === 'success' ? '#28a745' : '#007bff'};
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      z-index: 10000;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      transform: translateX(100%);
      transition: transform 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.style.transform = 'translateX(0)';
    }, 100);
    
    setTimeout(() => {
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 300);
    }, 3000);
  }

  /**
   * Load games carousel
   */
  async loadGames() {
    try {
      const games = [
        // Add your games/events here
      ];
      
      const gamesScroll = document.getElementById('gamesScroll');
      if (gamesScroll) {
        gamesScroll.textContent = games.join(' • ');
      }
    } catch (error) {
      console.error('Error loading games:', error);
    }
  }

  /**
   * Player control methods
   */
  togglePlayPause() {
    if (this.player) {
      if (this.player.paused()) {
        this.player.play();
      } else {
        this.player.pause();
      }
    }
  }

  toggleMute() {
    if (this.player) {
      this.player.muted(!this.player.muted());
    }
  }

  toggleFullscreen() {
    if (this.player) {
      if (this.player.isFullscreen()) {
        this.player.exitFullscreen();
      } else {
        this.player.requestFullscreen();
      }
    }
  }

  seekForward() {
    if (this.player) {
      const currentTime = this.player.currentTime();
      this.player.currentTime(currentTime + 10);
    }
  }

  seekBackward() {
    if (this.player) {
      const currentTime = this.player.currentTime();
      this.player.currentTime(Math.max(0, currentTime - 10));
    }
  }
}

// Initialize app when DOM is loaded
let iptvApp;
document.addEventListener('DOMContentLoaded', () => {
  // Security measures
  document.addEventListener('contextmenu', function(e) {
    e.preventDefault();
    return false;
  });
  
  document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && (e.keyCode === 67 || e.keyCode === 65 || e.keyCode === 83 || e.keyCode === 85)) {
      e.preventDefault();
      return false;
    }
    if (e.keyCode === 123) {
      e.preventDefault();
      return false;
    }
  });
  
  document.addEventListener('selectstart', function(e) {
    e.preventDefault();
    return false;
  });
  
  document.addEventListener('dragstart', function(e) {
    e.preventDefault();
    return false;
  });
  
  // Initialize theme and app
  loadTheme();
  iptvApp = new IPTVApp();
});

// Export to global scope
window.IPTVApp = IPTVApp;
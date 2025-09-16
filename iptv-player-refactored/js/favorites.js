// ===== FAVORITES MANAGEMENT =====

/**
 * Favorites Backend Class - Handles favorites storage and management
 */
class FavoritesBackend {
  constructor() {
    this.storageKey = 'iptv_favorites_v2';
    this.favorites = this.loadFavorites();
  }

  /**
   * Load favorites from localStorage
   */
  loadFavorites() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      const favorites = stored ? JSON.parse(stored) : [];
      
      // Migrate old format if needed
      return this.migrateFavoritesFormat(favorites);
    } catch (error) {
      console.error('Error loading favorites:', error);
      return [];
    }
  }

  /**
   * Migrate old favorites format to new structure
   */
  migrateFavoritesFormat(favorites) {
    return favorites.map(fav => {
      // Ensure all required fields exist
      return {
        id: fav.id || Utils.generateId(),
        name: fav.name || 'Unknown',
        type: fav.type || 'channel',
        url: fav.url || '',
        icon: fav.icon || null,
        letter: fav.letter || Utils.getFirstLetter(fav.name),
        category: fav.category || 'Geral',
        addedAt: fav.addedAt || Date.now(),
        lastPlayed: fav.lastPlayed || null,
        playCount: fav.playCount || 0,
        ...fav // Preserve any additional fields
      };
    });
  }

  /**
   * Save favorites to localStorage
   */
  saveFavorites() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.favorites));
      return true;
    } catch (error) {
      console.error('Error saving favorites:', error);
      return false;
    }
  }

  /**
   * Add item to favorites
   */
  addFavorite(item) {
    // Check if already exists
    if (this.isFavorite(item.id)) {
      console.log('Item already in favorites:', item.id);
      return false;
    }

    const favoriteItem = {
      id: item.id,
      name: item.name,
      type: item.type,
      url: item.url,
      icon: item.icon || null,
      letter: Utils.getFirstLetter(item.name),
      category: item.category || 'Geral',
      addedAt: Date.now(),
      lastPlayed: null,
      playCount: 0,
      // Additional fields based on type
      ...(item.type === 'radio' && { frequency: item.frequency }),
      ...(item.type === 'series' && { 
        seasons: item.seasons,
        episodes: item.episodes 
      }),
      ...(item.type === 'movie' && { 
        duration: item.duration,
        year: item.year 
      })
    };

    this.favorites.push(favoriteItem);
    this.saveFavorites();
    
    console.log('Added to favorites:', favoriteItem);
    return true;
  }

  /**
   * Remove item from favorites
   */
  removeFavorite(itemId) {
    const initialLength = this.favorites.length;
    this.favorites = this.favorites.filter(fav => fav.id !== itemId);
    
    if (this.favorites.length < initialLength) {
      this.saveFavorites();
      console.log('Removed from favorites:', itemId);
      return true;
    }
    
    return false;
  }

  /**
   * Check if item is in favorites
   */
  isFavorite(itemId) {
    return this.favorites.some(fav => fav.id === itemId);
  }

  /**
   * Get all favorites
   */
  getFavorites() {
    return [...this.favorites];
  }

  /**
   * Get favorites by type
   */
  getFavoritesByType(type) {
    return this.favorites.filter(fav => fav.type === type);
  }

  /**
   * Get favorite by ID
   */
  getFavoriteById(itemId) {
    return this.favorites.find(fav => fav.id === itemId);
  }

  /**
   * Update favorite play statistics
   */
  updatePlayStats(itemId) {
    const favorite = this.favorites.find(fav => fav.id === itemId);
    if (favorite) {
      favorite.lastPlayed = Date.now();
      favorite.playCount = (favorite.playCount || 0) + 1;
      this.saveFavorites();
    }
  }

  /**
   * Get favorites count
   */
  getCount() {
    return this.favorites.length;
  }

  /**
   * Search favorites
   */
  searchFavorites(query) {
    const lowercaseQuery = query.toLowerCase();
    return this.favorites.filter(fav => 
      fav.name.toLowerCase().includes(lowercaseQuery) ||
      fav.category.toLowerCase().includes(lowercaseQuery)
    );
  }

  /**
   * Sort favorites
   */
  sortFavorites(sortBy = 'name') {
    const sortedFavorites = [...this.favorites];
    
    switch (sortBy) {
      case 'name':
        sortedFavorites.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case 'type':
        sortedFavorites.sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name));
        break;
      case 'recent':
        sortedFavorites.sort((a, b) => (b.addedAt || 0) - (a.addedAt || 0));
        break;
      case 'played':
        sortedFavorites.sort((a, b) => (b.lastPlayed || 0) - (a.lastPlayed || 0));
        break;
      case 'popular':
        sortedFavorites.sort((a, b) => (b.playCount || 0) - (a.playCount || 0));
        break;
    }
    
    return sortedFavorites;
  }

  /**
   * Clear all favorites
   */
  clearFavorites() {
    this.favorites = [];
    this.saveFavorites();
  }

  /**
   * Export favorites
   */
  exportFavorites() {
    return {
      favorites: this.favorites,
      exportDate: new Date().toISOString(),
      version: '2.0'
    };
  }

  /**
   * Import favorites
   */
  importFavorites(data) {
    try {
      if (data.favorites && Array.isArray(data.favorites)) {
        this.favorites = this.migrateFavoritesFormat(data.favorites);
        this.saveFavorites();
        return true;
      }
    } catch (error) {
      console.error('Error importing favorites:', error);
    }
    return false;
  }

  /**
   * Get statistics
   */
  getStatistics() {
    const stats = {
      total: this.favorites.length,
      byType: {},
      mostPlayed: null,
      recentlyAdded: []
    };

    // Count by type
    this.favorites.forEach(fav => {
      stats.byType[fav.type] = (stats.byType[fav.type] || 0) + 1;
    });

    // Most played
    const sortedByPlayCount = this.favorites
      .filter(fav => fav.playCount > 0)
      .sort((a, b) => b.playCount - a.playCount);
    
    if (sortedByPlayCount.length > 0) {
      stats.mostPlayed = sortedByPlayCount[0];
    }

    // Recently added (last 7 days)
    const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
    stats.recentlyAdded = this.favorites
      .filter(fav => fav.addedAt > weekAgo)
      .sort((a, b) => b.addedAt - a.addedAt);

    return stats;
  }

  /**
   * Cleanup old favorites (optional maintenance)
   */
  cleanup() {
    // Remove duplicates
    const seen = new Set();
    const uniqueFavorites = [];

    this.favorites.forEach(fav => {
      if (!seen.has(fav.id)) {
        seen.add(fav.id);
        uniqueFavorites.push(fav);
      }
    });

    if (uniqueFavorites.length !== this.favorites.length) {
      this.favorites = uniqueFavorites;
      this.saveFavorites();
      console.log('Cleaned up duplicate favorites');
    }
  }
}

// Export to global scope
window.FavoritesBackend = FavoritesBackend;
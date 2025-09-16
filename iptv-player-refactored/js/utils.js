// ===== UTILITY FUNCTIONS =====

/**
 * Cache utility for storing API responses
 */
class SimpleCache {
  constructor() {
    this.data = {};
    this.timestamps = {};
    this.ttl = 5 * 60 * 1000; // 5 minutes TTL
  }

  set(key, value) {
    this.data[key] = value;
    this.timestamps[key] = Date.now();
  }

  get(key) {
    const timestamp = this.timestamps[key];
    if (!timestamp || Date.now() - timestamp > this.ttl) {
      this.delete(key);
      return null;
    }
    return this.data[key];
  }

  delete(key) {
    delete this.data[key];
    delete this.timestamps[key];
  }

  clear() {
    this.data = {};
    this.timestamps = {};
  }
}

/**
 * Progress tracking utility
 */
class ProgressTracker {
  constructor() {
    this.storageKey = 'iptv_progress';
    this.data = this.loadFromStorage();
  }

  loadFromStorage() {
    try {
      const stored = localStorage.getItem(this.storageKey);
      return stored ? JSON.parse(stored) : {};
    } catch (error) {
      console.error('Error loading progress data:', error);
      return {};
    }
  }

  saveToStorage() {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.data));
    } catch (error) {
      console.error('Error saving progress data:', error);
    }
  }

  setProgress(itemId, currentTime, duration) {
    const percentage = (currentTime / duration) * 100;
    
    // Only save if meaningful progress (between 5% and 90%)
    if (percentage >= 5 && percentage <= 90) {
      this.data[itemId] = {
        currentTime: currentTime,
        duration: duration,
        percentage: percentage,
        timestamp: Date.now()
      };
      this.saveToStorage();
    }
  }

  getProgress(itemId) {
    const progress = this.data[itemId];
    if (!progress) return null;

    // Clean old entries (older than 30 days)
    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
    if (progress.timestamp < thirtyDaysAgo) {
      delete this.data[itemId];
      this.saveToStorage();
      return null;
    }

    return progress;
  }

  removeProgress(itemId) {
    delete this.data[itemId];
    this.saveToStorage();
  }

  cleanup() {
    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
    let cleaned = false;

    Object.keys(this.data).forEach(itemId => {
      if (this.data[itemId].timestamp < thirtyDaysAgo) {
        delete this.data[itemId];
        cleaned = true;
      }
    });

    if (cleaned) {
      this.saveToStorage();
    }
  }
}

/**
 * Generic utility functions
 */
const Utils = {
  // Generate random ID
  generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  },

  // Get first letter for avatars
  getFirstLetter(text) {
    if (!text || typeof text !== 'string') return '?';
    return text.trim().charAt(0).toUpperCase();
  },

  // Format duration
  formatDuration(seconds) {
    if (isNaN(seconds) || seconds < 0) return '00:00';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
      return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
  },

  // Debounce function
  debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        timeout = null;
        if (!immediate) func(...args);
      };
      const callNow = immediate && !timeout;
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      if (callNow) func(...args);
    };
  },

  // Throttle function
  throttle(func, limit) {
    let inThrottle;
    return function() {
      const args = arguments;
      const context = this;
      if (!inThrottle) {
        func.apply(context, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    }
  },

  // Check if URL is valid
  isValidUrl(string) {
    try {
      new URL(string);
      return true;
    } catch (_) {
      return false;
    }
  },

  // Sanitize HTML
  sanitizeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  // Copy to clipboard
  async copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.error('Failed to copy text: ', err);
      return false;
    }
  },

  // Format file size
  formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  },

  // Get device type
  getDeviceType() {
    const userAgent = navigator.userAgent.toLowerCase();
    const isMobile = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/.test(userAgent);
    const isTablet = /ipad|android(?!.*mobile)/.test(userAgent);
    
    if (isMobile && !isTablet) return 'mobile';
    if (isTablet) return 'tablet';
    return 'desktop';
  },

  // Check if device supports touch
  isTouchDevice() {
    return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  },

  // Get browser name
  getBrowserName() {
    const userAgent = navigator.userAgent;
    
    if (userAgent.includes('Chrome')) return 'Chrome';
    if (userAgent.includes('Firefox')) return 'Firefox';
    if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) return 'Safari';
    if (userAgent.includes('Edge')) return 'Edge';
    if (userAgent.includes('Opera')) return 'Opera';
    
    return 'Unknown';
  },

  // Local storage with error handling
  localStorage: {
    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
      } catch (error) {
        console.error('localStorage.setItem error:', error);
        return false;
      }
    },

    get(key, defaultValue = null) {
      try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
      } catch (error) {
        console.error('localStorage.getItem error:', error);
        return defaultValue;
      }
    },

    remove(key) {
      try {
        localStorage.removeItem(key);
        return true;
      } catch (error) {
        console.error('localStorage.removeItem error:', error);
        return false;
      }
    },

    clear() {
      try {
        localStorage.clear();
        return true;
      } catch (error) {
        console.error('localStorage.clear error:', error);
        return false;
      }
    }
  }
};

// Export utilities to global scope
window.Utils = Utils;
window.SimpleCache = SimpleCache;
window.ProgressTracker = ProgressTracker;
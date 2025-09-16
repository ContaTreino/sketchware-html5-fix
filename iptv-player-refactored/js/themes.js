// ===== THEME MANAGEMENT =====

/**
 * Theme Manager Class
 */
class ThemeManager {
  constructor() {
    this.storageKey = 'iptv_theme';
    this.defaultTheme = 'default';
    
    // Available themes configuration
    this.themes = {
      default: {
        name: 'Padrão',
        colors: ['#00A848', '#00c851', '#1f1f1f', '#252525']
      },
      black: {
        name: 'Preto',
        colors: ['#ffffff', '#333333', '#000000', '#111111']
      },
      claro: {
        name: 'Claro',
        colors: ['#007bff', '#0056b3', '#ffffff', '#f8f9fa']
      },
      azul: {
        name: 'Azul',
        colors: ['#007bff', '#0056b3', '#0d1117', '#161b22']
      },
      vermelho: {
        name: 'Vermelho',
        colors: ['#dc3545', '#c82333', '#1a0d0d', '#2d1b1b']
      },
      verde: {
        name: 'Verde',
        colors: ['#28a745', '#1e7e34', '#0d1a0d', '#1b2d1b']
      }
    };

    this.currentTheme = this.loadTheme();
    this.initializeThemeOptions();
  }

  /**
   * Load theme from localStorage or use default
   */
  loadTheme() {
    const savedTheme = Utils.localStorage.get(this.storageKey, this.defaultTheme);
    this.applyTheme(savedTheme);
    return savedTheme;
  }

  /**
   * Apply theme to document
   */
  applyTheme(themeName) {
    if (!this.themes[themeName]) {
      themeName = this.defaultTheme;
    }

    document.body.setAttribute('data-theme', themeName);
    this.currentTheme = themeName;
    
    // Save to localStorage
    Utils.localStorage.set(this.storageKey, themeName);

    // Update theme options UI if available
    this.updateThemeOptionsUI();
  }

  /**
   * Get current theme
   */
  getCurrentTheme() {
    return this.currentTheme;
  }

  /**
   * Get all available themes
   */
  getThemes() {
    return this.themes;
  }

  /**
   * Switch to a specific theme
   */
  switchTheme(themeName) {
    if (this.themes[themeName]) {
      this.applyTheme(themeName);
      
      // Show feedback
      if (window.iptvApp && window.iptvApp.showToast) {
        window.iptvApp.showToast(`Tema "${this.themes[themeName].name}" aplicado!`, 'success');
      }
    }
  }

  /**
   * Initialize theme options in modal
   */
  initializeThemeOptions() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.renderThemeOptions());
    } else {
      this.renderThemeOptions();
    }
  }

  /**
   * Render theme options in the modal
   */
  renderThemeOptions() {
    const themeOptionsContainer = document.getElementById('themeOptions');
    if (!themeOptionsContainer) return;

    themeOptionsContainer.innerHTML = '';

    Object.entries(this.themes).forEach(([themeKey, themeConfig]) => {
      const themeOption = document.createElement('div');
      themeOption.className = 'col-6 col-md-4';
      
      themeOption.innerHTML = `
        <div class="theme-option ${this.currentTheme === themeKey ? 'active' : ''}" data-theme="${themeKey}">
          <div class="theme-preview">
            ${themeConfig.colors.map(color => `<div class="theme-preview-color" style="background-color: ${color}"></div>`).join('')}
          </div>
          <div class="theme-name">${themeConfig.name}</div>
        </div>
      `;

      // Add click event
      const themeOptionElement = themeOption.querySelector('.theme-option');
      themeOptionElement.addEventListener('click', () => {
        this.switchTheme(themeKey);
      });

      themeOptionsContainer.appendChild(themeOption);
    });
  }

  /**
   * Update theme options UI to reflect current theme
   */
  updateThemeOptionsUI() {
    const themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach(option => {
      const themeKey = option.getAttribute('data-theme');
      option.classList.toggle('active', themeKey === this.currentTheme);
    });
  }

  /**
   * Auto-detect system theme preference
   */
  detectSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'default'; // Use default dark theme
    } else {
      return 'claro'; // Use light theme
    }
  }

  /**
   * Listen for system theme changes
   */
  listenForSystemThemeChanges() {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      
      mediaQuery.addListener((e) => {
        // Only auto-switch if user hasn't manually selected a theme
        const hasUserTheme = Utils.localStorage.get(this.storageKey);
        if (!hasUserTheme) {
          const systemTheme = this.detectSystemTheme();
          this.applyTheme(systemTheme);
        }
      });
    }
  }

  /**
   * Reset to default theme
   */
  resetToDefault() {
    this.applyTheme(this.defaultTheme);
    Utils.localStorage.remove(this.storageKey);
  }

  /**
   * Export current theme settings
   */
  exportTheme() {
    return {
      currentTheme: this.currentTheme,
      timestamp: Date.now()
    };
  }

  /**
   * Import theme settings
   */
  importTheme(themeData) {
    if (themeData && themeData.currentTheme && this.themes[themeData.currentTheme]) {
      this.switchTheme(themeData.currentTheme);
      return true;
    }
    return false;
  }
}

/**
 * Global theme functions for backward compatibility
 */
function loadTheme() {
  if (!window.themeManager) {
    window.themeManager = new ThemeManager();
  }
  return window.themeManager.loadTheme();
}

function changeTheme(themeName) {
  if (window.themeManager) {
    window.themeManager.switchTheme(themeName);
  }
}

function getCurrentTheme() {
  return window.themeManager ? window.themeManager.getCurrentTheme() : 'default';
}

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  if (!window.themeManager) {
    window.themeManager = new ThemeManager();
    window.themeManager.listenForSystemThemeChanges();
  }
});

// Export to global scope
window.ThemeManager = ThemeManager;
window.loadTheme = loadTheme;
window.changeTheme = changeTheme;
window.getCurrentTheme = getCurrentTheme;
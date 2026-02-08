/**
 * Sidebar Navigation Controller - Sprint 24
 * 
 * Manages the left sidebar navigation system that replaces horizontal tabs
 * Based on menu_changes.md specifications
 * 
 * Features:
 * - Collapsible sidebar (250px ↔ 60px)
 * - Filter column for Pattern Discovery
 * - Content area management
 * - Theme-aware styling
 * - Mobile responsive behavior
 */

// Debug flag for service loading (set to false to reduce console noise)
const SIDEBAR_DEBUG = true;

class SidebarNavigationController {
    constructor(options = {}) {
        this.options = {
            defaultSection: 'dummy1',
            rememberState: true,
            storageKey: 'tickstock-sidebar-state',
            animations: true,
            ...options
        };
        
        // State management
        this.currentSection = this.options.defaultSection;
        this.isCollapsed = false;
        this.isFilterOpen = false;
        this.isMobile = window.innerWidth < 768;
        this.eventHandlers = new Map();
        this.currentTooltip = null;
        this.tooltipTimeout = null;
        
        // Navigation sections configuration - SIMPLIFIED TO TWO DUMMY LINKS + MARKET OVERVIEW + STOCK GROUPS
        this.sections = {
            'dummy1': {
                title: 'Dummy1',
                icon: 'fas fa-chart-line',
                hasFilters: false,
                component: null,
                description: 'Dummy1 page placeholder'
            },
            'dummy2': {
                title: 'Dummy2',
                icon: 'fas fa-chart-bar',
                hasFilters: false,
                component: null,
                description: 'Dummy2 page placeholder'
            },
            'market-overview': {
                title: 'Market Overview',
                icon: 'fas fa-chart-line',
                hasFilters: false,
                component: 'initializeMarketOverview',
                description: 'Sprint 64: Threshold bars market sentiment visualization'
            },
            'market-breadth': {
                title: 'Market Breadth',
                icon: 'fas fa-chart-bar',
                hasFilters: false,
                component: 'initializeBreadthMetrics_default',
                description: 'Sprint 66: Market breadth metrics showing up/down participation'
            },
            'stock-groups': {
                title: 'Stock Groups',
                icon: 'fas fa-layer-group',
                hasFilters: false,
                component: null,
                description: 'Sprint 65: Search and filter stock groups (ETFs, sectors, themes, universes)'
            }
        };
        
        this.init();
    }
    
    /**
     * Initialize the sidebar navigation
     */
    init() {
        
        // Load saved state
        this.loadState();
        
        // Create the sidebar structure
        this.createSidebarStructure();
        
        // Setup event handlers
        this.setupEventHandlers();
        
        // Setup responsive behavior
        this.setupResponsiveHandlers();
        
        // Load initial section
        this.navigateToSection(this.currentSection);
        
    }
    
    /**
     * Create the main sidebar structure
     */
    createSidebarStructure() {
        // Find the container where we'll insert the sidebar
        const container = document.querySelector('.main-layout-container');
        if (!container) {
            console.error('Main layout container not found for sidebar insertion');
            // Try fallback container
            const fallbackContainer = document.querySelector('.container-fluid');
            if (fallbackContainer) {
                fallbackContainer.className = 'main-layout-container';
                this.insertSidebarHTML(fallbackContainer);
                return;
            } else {
                console.error('No suitable container found for sidebar');
                return;
            }
        } else {
            this.insertSidebarHTML(container);
        }
    }
    
    insertSidebarHTML(container) {
        
        // Create sidebar HTML
        const sidebarHTML = this.generateSidebarHTML();
        
        // Insert sidebar before main content
        container.insertAdjacentHTML('afterbegin', sidebarHTML);
        
        // Add class to body to indicate sidebar is active
        document.body.classList.add('sidebar-navigation-active');
        
        // Cache DOM references
        this.sidebar = document.querySelector('.app-sidebar');
        this.filterColumn = document.querySelector('.filter-column');
        this.mainContent = document.querySelector('.main-content-area');
        this.toggleBtn = document.querySelector('.sidebar-toggle');
        this.filterCloseBtn = document.querySelector('.filter-close-btn');
        this.overlay = document.querySelector('.sidebar-overlay');
        
        // Apply initial state
        this.applySidebarState();
        this.updateToggleIcon();
    }
    
    /**
     * Generate the complete sidebar HTML structure
     */
    generateSidebarHTML() {
        const navItems = Object.entries(this.sections).map(([key, section]) => `
            <li class="sidebar-nav-item" data-section="${key}">
                <a class="sidebar-nav-link" href="#" data-section="${key}" data-tooltip="${section.title}">
                    <i class="sidebar-nav-icon ${section.icon}"></i>
                    <span class="sidebar-nav-text">${section.title}</span>
                </a>
            </li>
        `).join('');
        
        return `
            <!-- Sidebar Navigation -->
            <div class="app-sidebar" id="app-sidebar">
                <div class="sidebar-header">
                    <h6 class="sidebar-title">Navigation</h6>
                    <button class="sidebar-toggle" id="sidebar-toggle" title="Toggle sidebar">
                        <i class="fas fa-bars"></i>
                    </button>
                </div>
                <nav class="sidebar-nav-wrapper">
                    <ul class="sidebar-nav" id="sidebar-nav">
                        ${navItems}
                    </ul>
                </nav>
            </div>
            
            <!-- Filter Column (for Pattern Discovery) -->
            <div class="filter-column" id="filter-column">
                <div class="filter-column-header">
                    <h6 class="filter-column-title">
                        <i class="fas fa-filter me-2"></i>
                        Filters
                    </h6>
                    <button class="filter-close-btn" id="filter-close-btn" title="Close filters">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="filter-column-content" id="filter-column-content">
                    <!-- Filter content will be inserted here -->
                </div>
                <div class="filter-column-footer">
                    <div class="d-flex gap-2">
                        <button class="btn btn-outline-secondary flex-fill btn-sm" id="filter-clear-btn">
                            <i class="fas fa-undo me-1"></i>Clear
                        </button>
                        <button class="btn btn-primary flex-fill btn-sm" id="filter-apply-btn">
                            <i class="fas fa-check me-1"></i>Apply
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Mobile Overlay -->
            <div class="sidebar-overlay" id="sidebar-overlay"></div>
            
            <!-- Main Content Area -->
            <div class="main-content-area" id="main-content-area">
                <!-- Existing content will be moved here -->
            </div>
        `;
    }
    
    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Sidebar toggle
        if (this.toggleBtn) {
            this.addEventHandler(this.toggleBtn, 'click', () => {
                this.toggleSidebar();
            });
        } else {
            console.warn('Sidebar toggle button not found');
        }
        
        // Navigation items - use larger hover area (entire nav item)
        const navItems = document.querySelectorAll('.sidebar-nav-item');
        navItems.forEach(item => {
            const link = item.querySelector('.sidebar-nav-link');
            
            // Click handler on the link
            this.addEventHandler(link, 'click', (e) => {
                e.preventDefault();
                const section = link.getAttribute('data-section');
                this.navigateToSection(section);
            });
            
            // Tooltip functionality on the entire nav item for larger hover area
            this.addEventHandler(item, 'mouseenter', (e) => {
                if (this.isCollapsed || this.sidebar.classList.contains('narrow')) {
                    this.showTooltip(link, link.getAttribute('data-tooltip'));
                }
            });
            
            this.addEventHandler(item, 'mouseleave', (e) => {
                this.hideTooltip();
            });
        });
        
        // Filter column close
        if (this.filterCloseBtn) {
            this.addEventHandler(this.filterCloseBtn, 'click', () => {
                this.closeFilters();
            });
        }
        
        // Mobile overlay
        if (this.overlay) {
            this.addEventHandler(this.overlay, 'click', () => {
                this.closeMobileSidebar();
            });
        }
        
        // Filter buttons
        const filterApplyBtn = document.getElementById('filter-apply-btn');
        const filterClearBtn = document.getElementById('filter-clear-btn');
        
        if (filterApplyBtn) {
            this.addEventHandler(filterApplyBtn, 'click', () => {
                this.applyFilters();
            });
        }
        
        if (filterClearBtn) {
            this.addEventHandler(filterClearBtn, 'click', () => {
                this.clearFilters();
            });
        }
        
        // Escape key to close
        this.addEventHandler(document, 'keydown', (e) => {
            if (e.key === 'Escape') {
                if (this.isFilterOpen) {
                    this.closeFilters();
                } else if (this.isMobile && this.sidebar.classList.contains('mobile-open')) {
                    this.closeMobileSidebar();
                }
                // Also hide tooltips on escape
                this.hideTooltip();
            }
        });
        
        // Global mouse monitoring to hide tooltips when mouse leaves sidebar area
        this.addEventHandler(document, 'mousemove', (e) => {
            if (this.currentTooltip && this.sidebar) {
                const sidebarRect = this.sidebar.getBoundingClientRect();
                const mouseX = e.clientX;
                const mouseY = e.clientY;
                
                // Hide tooltip if mouse is outside sidebar area (with some buffer)
                const buffer = 50; // 50px buffer zone
                if (mouseX < sidebarRect.left - buffer || 
                    mouseX > sidebarRect.right + buffer ||
                    mouseY < sidebarRect.top - buffer || 
                    mouseY > sidebarRect.bottom + buffer) {
                    this.hideTooltip();
                }
            }
        });
    }
    
    /**
     * Setup responsive behavior handlers
     */
    setupResponsiveHandlers() {
        const resizeHandler = () => {
            const wasMobile = this.isMobile;
            this.isMobile = window.innerWidth < 768;
            
            // Handle mobile/desktop transitions
            if (wasMobile !== this.isMobile) {
                if (!this.isMobile) {
                    // Switched to desktop
                    this.sidebar.classList.remove('mobile-open');
                    this.overlay.classList.remove('active');
                    document.body.classList.remove('sidebar-mobile-open');
                } else {
                    // Switched to mobile
                    this.closeFilters();
                }
                this.applySidebarState();
            }
        };
        
        this.addEventHandler(window, 'resize', this.debounce(resizeHandler, 150));
    }
    
    /**
     * Navigate to a specific section
     */
    navigateToSection(sectionKey) {
        if (!this.sections[sectionKey]) {
            console.warn(`Section '${sectionKey}' not found`);
            return;
        }

        const section = this.sections[sectionKey];

        // Update current section
        this.currentSection = sectionKey;

        // Update active states
        this.updateActiveNavItem(sectionKey);

        // Handle filters based on section configuration
        if (section.hasFilters && !this.isMobile) {
            this.openFilters();
        } else {
            this.closeFilters();
        }

        // Load content for the section
        this.loadSectionContent(sectionKey);

        // Close mobile sidebar if open
        if (this.isMobile) {
            this.closeMobileSidebar();
        }

        // Save state
        this.saveState();
    }
    
    /**
     * Update active navigation item
     */
    updateActiveNavItem(sectionKey) {
        // Remove active from all items
        document.querySelectorAll('.sidebar-nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active to current item
        const activeItem = document.querySelector(`[data-section="${sectionKey}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }
    }
    
    /**
     * Load content for a section
     */
    loadSectionContent(sectionKey) {
        const section = this.sections[sectionKey];
        const contentArea = document.getElementById('main-content-area');
        
        if (!contentArea) {
            console.error('Main content area not found');
            return;
        }
        
        // Show loading state
        contentArea.innerHTML = `
            <div class="d-flex align-items-center justify-content-center py-5">
                <div class="spinner-border text-primary me-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="text-muted">Loading ${section.title}...</div>
            </div>
        `;
        
        // Load the appropriate content based on section
        setTimeout(() => {
            this.loadComponentContent(sectionKey, section);
        }, 500);
    }
    
    /**
     * Load component-specific content
     */
    loadComponentContent(sectionKey, section) {
        const contentArea = document.getElementById('main-content-area');

        // Handle dummy sections
        if (sectionKey === 'dummy1' || sectionKey === 'dummy2') {
            // Load dummy content from hidden divs
            const dummyContent = document.getElementById(`${sectionKey}-content`);
            if (dummyContent) {
                contentArea.innerHTML = `
                    <div class="container-fluid p-4">
                        <h2><i class="${section.icon} me-2"></i>${section.title}</h2>
                        <div class="mt-4">
                            ${dummyContent.innerHTML}
                        </div>
                    </div>
                `;
            } else {
                contentArea.innerHTML = `
                    <div class="container-fluid p-4">
                        <h2><i class="${section.icon} me-2"></i>${section.title}</h2>
                        <p class="text-muted">${section.description}</p>
                        <p>Content area ready for development.</p>
                    </div>
                `;
            }
        } else if (sectionKey === 'market-overview') {
            // Load Market Overview content from hidden div
            const marketOverviewContent = document.getElementById('market-overview-content');
            if (marketOverviewContent) {
                contentArea.innerHTML = `
                    <div class="container-fluid p-4">
                        ${marketOverviewContent.innerHTML}
                    </div>
                `;

                // Initialize Market Overview after content is loaded
                setTimeout(() => {
                    if (typeof window.initializeMarketOverview === 'function') {
                        window.initializeMarketOverview();
                    }
                }, 200);
            } else {
                contentArea.innerHTML = `
                    <div class="container-fluid p-4">
                        <h2><i class="${section.icon} me-2"></i>${section.title}</h2>
                        <p class="text-muted">${section.description}</p>
                        <p>Market Overview content not found.</p>
                    </div>
                `;
            }
        } else if (sectionKey === 'market-breadth') {
            // Load Market Breadth content from hidden div
            const marketBreadthContent = document.getElementById('market-breadth-content');
            if (marketBreadthContent) {
                contentArea.innerHTML = `
                    <div class="container-fluid p-4">
                        ${marketBreadthContent.innerHTML}
                    </div>
                `;

                // Initialize Market Breadth after content is loaded
                setTimeout(() => {
                    if (typeof window.initializeBreadthMetrics_default === 'function') {
                        window.initializeBreadthMetrics_default();
                    }
                }, 200);
            } else {
                contentArea.innerHTML = `
                    <div class="container-fluid p-4">
                        <h2><i class="${section.icon} me-2"></i>${section.title}</h2>
                        <p class="text-muted">${section.description}</p>
                        <p>Market Breadth content not found.</p>
                    </div>
                `;
            }
        } else if (sectionKey === 'stock-groups') {
            // Load Stock Groups content from hidden div
            const stockGroupsContent = document.getElementById('stock-groups-content');
            if (stockGroupsContent) {
                contentArea.innerHTML = `
                    <div class="container-fluid p-4">
                        ${stockGroupsContent.innerHTML}
                    </div>
                `;

                // Initialize Stock Group Selector after content is loaded
                setTimeout(() => {
                    if (typeof StockGroupSelector !== 'undefined') {
                        console.log('Initializing Stock Group Selector from sidebar navigation...');
                        const selector = new StockGroupSelector({
                            containerId: 'stock-group-selector-content',
                            apiEndpoint: '/api/stock-groups',
                            csrfToken: document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
                        });

                        // Refresh button handler
                        const refreshBtn = document.getElementById('refresh-stock-groups-btn');
                        if (refreshBtn) {
                            refreshBtn.addEventListener('click', function() {
                                location.reload();
                            });
                        }
                    } else {
                        console.error('StockGroupSelector class not found');
                    }
                }, 200);
            } else {
                contentArea.innerHTML = `
                    <div class="container-fluid p-4">
                        <h2><i class="${section.icon} me-2"></i>${section.title}</h2>
                        <p class="text-muted">${section.description}</p>
                        <p>Stock Groups content not found.</p>
                    </div>
                `;
            }
        } else if (section.component && window[section.component]) {
            // Load component if it exists
            const component = window[section.component];
            if (typeof component.renderUI === 'function') {
                component.renderUI();
            }
        } else {
            // Load section content using analytics services
            this.loadAnalyticsContent(sectionKey, section, contentArea);
        }
    }
    
    /**
     * Load analytics content for each section (from the original horizontal tabs)
     */
    loadAnalyticsContent(sectionKey, section, contentArea) {
        // Show loading state first
        contentArea.innerHTML = `
            <div id="${sectionKey}-dashboard">
                <div class="d-flex align-items-center justify-content-center py-5" id="${sectionKey}-loading">
                    <div class="spinner-border text-primary me-3" role="status">
                        <span class="visually-hidden">Loading ${section.title}...</span>
                    </div>
                    <div class="text-muted">Initializing ${section.title} Dashboard...</div>
                </div>
            </div>
        `;

        // Try to initialize content using analytics services
        setTimeout(() => {
            this.initializeAnalyticsTab(sectionKey, section, contentArea);
        }, 500);
    }

    /**
     * Initialize analytics tab content (from original implementation)
     */
    initializeAnalyticsTab(sectionKey, section, contentArea) {

        // Special handling for different section types
        if (sectionKey === 'streaming') {
            this.initializeStreamingSection(contentArea, section);
            return;
        } else if (sectionKey === 'sprint25') {
            this.initializeSprint25Section(contentArea, section);
            return;
        } else if (sectionKey === 'compare') {
            this.initializeCompareSection(contentArea, section);
            return;
        } else if (['correlations', 'temporal'].includes(sectionKey)) {
            this.initializeAdvancedAnalyticsSection(sectionKey, contentArea, section);
            return;
        } else if (['overview', 'performance', 'distribution', 'historical', 'market'].includes(sectionKey)) {
            this.initializePatternAnalyticsSection(sectionKey, contentArea, section);
            return;
        }
        
        // Check if PatternAnalyticsService is available
        if (window.patternAnalyticsService && typeof window.patternAnalyticsService.renderTab === 'function') {
            try {
                const content = this.getAnalyticsTabContent(sectionKey);
                
                if (content) {
                    contentArea.innerHTML = `<div id="${sectionKey}-dashboard">${content}</div>`;
                    
                    // Initialize charts after content is rendered
                    setTimeout(() => {
                        this.initializeTabCharts(sectionKey);
                    }, 200);
                } else {
                    this.showFallbackContent(sectionKey, section, contentArea);
                }
            } catch (error) {
                console.error(`Error loading ${sectionKey} content:`, error);
                this.showFallbackContent(sectionKey, section, contentArea);
            }
        } else {
            this.showFallbackContent(sectionKey, section, contentArea);
        }
    }

    /**
     * Get analytics tab content using the original tab rendering methods
     */
    getAnalyticsTabContent(sectionKey) {
        if (!window.patternAnalyticsService) return null;

        try {
            switch (sectionKey) {
                case 'overview':
                    return window.patternAnalyticsService.renderOverviewTab ? 
                           window.patternAnalyticsService.renderOverviewTab() : null;
                case 'performance':
                    return window.patternAnalyticsService.renderPerformanceTab ? 
                           window.patternAnalyticsService.renderPerformanceTab() : null;
                case 'distribution':
                    return window.patternAnalyticsService.renderDistributionTab ? 
                           window.patternAnalyticsService.renderDistributionTab() : null;
                case 'historical':
                    return window.patternAnalyticsService.renderHistoricalTab ? 
                           window.patternAnalyticsService.renderHistoricalTab() : null;
                case 'market':
                    return window.patternAnalyticsService.renderMarketTab ? 
                           window.patternAnalyticsService.renderMarketTab() : null;
                case 'correlations':
                    return window.patternCorrelations && window.patternCorrelations.renderDashboard ? 
                           window.patternCorrelations.renderDashboard() : null;
                case 'temporal':
                    return window.patternTemporal && window.patternTemporal.renderDashboard ? 
                           window.patternTemporal.renderDashboard() : null;
                case 'compare':
                    return this.tryGetCompareContent();
                default:
                    return null;
            }
        } catch (error) {
            console.error(`Error getting content for ${sectionKey}:`, error);
            return null;
        }
    }

    /**
     * Initialize charts for the loaded tab (from original implementation)
     */
    initializeTabCharts(sectionKey) {
        
        if (!window.patternAnalyticsService) return;

        try {
            switch (sectionKey) {
                case 'overview':
                    // Overview uses velocity chart - ensure it's called after content loads
                    setTimeout(() => {
                        if (window.patternAnalyticsService.createVelocityChart) {
                            window.patternAnalyticsService.createVelocityChart();
                        }
                    }, 100);
                    break;
                case 'performance':
                    // Initialize all performance charts after content loads
                    setTimeout(() => {
                        if (window.patternAnalyticsService.createPerformanceComparisonChart) {
                            window.patternAnalyticsService.createPerformanceComparisonChart();
                        }
                    }, 100);
                    break;
                case 'distribution':
                    // Initialize all distribution charts after content loads
                    setTimeout(() => {
                        if (window.patternAnalyticsService.createPatternFrequencyChart) {
                            window.patternAnalyticsService.createPatternFrequencyChart();
                        }
                        if (window.patternAnalyticsService.createConfidenceDistributionChart) {
                            window.patternAnalyticsService.createConfidenceDistributionChart();
                        }
                        if (window.patternAnalyticsService.createSectorChart) {
                            window.patternAnalyticsService.createSectorChart();
                        }
                    }, 100);
                    break;
                case 'historical':
                    // Initialize historical content and charts after content loads
                    if (window.patternAnalyticsService.loadHistoricalTabContent) {
                        setTimeout(() => {
                            window.patternAnalyticsService.loadHistoricalTabContent();
                            // Also initialize the trend chart
                            if (window.patternAnalyticsService.createHistoricalTrendChart) {
                                window.patternAnalyticsService.createHistoricalTrendChart();
                            }
                        }, 100);
                    }
                    break;
                case 'market':
                    // Initialize market chart after content loads
                    if (window.patternAnalyticsService.createMarketActivityChart) {
                        setTimeout(() => {
                            window.patternAnalyticsService.createMarketActivityChart();
                        }, 100);
                    }
                    break;
                // Advanced analytics services handle their own chart initialization
                case 'correlations':
                case 'temporal':
                case 'compare':
                    break;
            }
        } catch (error) {
            console.error(`Error initializing charts for ${sectionKey}:`, error);
        }
    }

    /**
     * Initialize Compare section with service retry logic
     */
    initializeCompareSection(contentArea, section) {
        
        // Try to load Compare service content
        const content = this.tryGetCompareContent();
        
        if (content) {
            contentArea.innerHTML = `<div id="compare-dashboard">${content}</div>`;
        } else {
            // Show loading state and retry
            this.showCompareLoadingState(contentArea, section);
            this.retryCompareInitialization(contentArea, section);
        }
    }

    /**
     * Show loading state specific to Compare section
     */
    showCompareLoadingState(contentArea, section) {
        contentArea.innerHTML = `
            <div id="compare-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title} Dashboard</h4>
                <div class="alert alert-info d-flex align-items-center">
                    <i class="fas fa-info-circle me-3 fa-2x"></i>
                    <div>
                        <h5 class="alert-heading mb-1">Compare Analytics</h5>
                        <p class="mb-0">The compare analytics service is initializing. Please wait...</p>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">Analytics Loading</h5>
                                <div class="d-flex justify-content-center py-3">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <p class="card-text">Chart visualization will appear here once the service is ready.</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">Metrics</h5>
                                <div class="d-flex justify-content-center py-3">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <p class="card-text">Performance metrics will be displayed here.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Retry Compare initialization with exponential backoff
     */
    retryCompareInitialization(contentArea, section, attempts = 0) {
        const maxAttempts = 5;
        const baseDelay = 500; // Start with 500ms
        
        if (attempts >= maxAttempts) {
            console.warn('Max retry attempts reached for Compare service initialization');
            this.showCompareErrorState(contentArea, section);
            return;
        }
        
        const delay = baseDelay * Math.pow(1.5, attempts); // Exponential backoff
        
        setTimeout(() => {
            const content = this.tryGetCompareContent();
            
            if (content && this.currentSection === 'compare') {
                contentArea.innerHTML = `<div id="compare-dashboard">${content}</div>`;
                
                // Initialize charts after content is loaded
                setTimeout(() => {
                    if (window.patternComparison && window.patternComparison.createComparisonCharts) {
                        window.patternComparison.createComparisonCharts();
                    }
                }, 200);
            } else if (this.currentSection === 'compare') {
                // Only retry if we're still on the compare section
                this.retryCompareInitialization(contentArea, section, attempts + 1);
            }
        }, delay);
    }

    /**
     * Initialize Pattern Analytics sections (Overview, Performance, Distribution, Historical, Market)
     */
    initializePatternAnalyticsSection(sectionKey, contentArea, section) {
        
        // Try to load Pattern Analytics service content
        const content = this.tryGetPatternAnalyticsContent(sectionKey);
        
        if (content) {
            contentArea.innerHTML = `<div id="${sectionKey}-dashboard">${content}</div>`;
            
            // Initialize charts after content is loaded
            setTimeout(() => {
                this.initializeTabCharts(sectionKey);
            }, 200);
        } else {
            // Show loading state and retry
            this.showPatternAnalyticsLoadingState(sectionKey, contentArea, section);
            this.retryPatternAnalyticsInitialization(sectionKey, contentArea, section);
        }
    }

    /**
     * Initialize Advanced Analytics sections (Correlations, Temporal)
     */
    initializeAdvancedAnalyticsSection(sectionKey, contentArea, section) {
        
        // Try to load Advanced Analytics service content
        const content = this.tryGetAdvancedAnalyticsContent(sectionKey);
        
        if (content) {
            contentArea.innerHTML = `<div id="${sectionKey}-dashboard">${content}</div>`;
            
            // Special handling for services that need post-load initialization
            if (sectionKey === 'temporal' && window.patternTemporal && window.patternTemporal.initializeEventHandlers) {
                setTimeout(() => {
                    window.patternTemporal.initializeEventHandlers();
                }, 200);
            } else if (sectionKey === 'correlations' && window.patternCorrelations) {
                setTimeout(() => {
                    // Initialize the correlations service with the container
                    if (window.patternCorrelations.renderMockData) {
                        window.patternCorrelations.renderMockData();
                    }
                    if (window.patternCorrelations.setupEventHandlers) {
                        window.patternCorrelations.setupEventHandlers();
                    }
                }, 200);
            }
        } else {
            // Show loading state and retry
            this.showAdvancedAnalyticsLoadingState(sectionKey, contentArea, section);
            this.retryAdvancedAnalyticsInitialization(sectionKey, contentArea, section);
        }
    }

    /**
     * Try to get Pattern Analytics content
     */
    tryGetPatternAnalyticsContent(sectionKey) {
        if (SIDEBAR_DEBUG) {
        }
        
        if (!window.patternAnalyticsService && !window.patternAnalytics) {
            return null;
        }

        const service = window.patternAnalyticsService || window.patternAnalytics;
        
        if (SIDEBAR_DEBUG) {
            
            if (service) {
            }
        }
        
        try {
            let renderMethod;
            switch (sectionKey) {
                case 'overview':
                    renderMethod = 'renderOverviewTab';
                    break;
                case 'performance':
                    renderMethod = 'renderPerformanceTab';
                    break;
                case 'distribution':
                    renderMethod = 'renderDistributionTab';
                    break;
                case 'historical':
                    renderMethod = 'renderHistoricalTab';
                    break;
                case 'market':
                    renderMethod = 'renderMarketTab';
                    break;
                default:
                    return null;
            }
            
            if (SIDEBAR_DEBUG) {
            }
            
            if (typeof service[renderMethod] === 'function') {
                return service[renderMethod]();
            } else {
                console.warn(`Method ${renderMethod} not available on service`);
                return null;
            }
        } catch (error) {
            console.error(`Error getting Pattern Analytics content for ${sectionKey}:`, error);
            return null;
        }
    }

    /**
     * Try to get Advanced Analytics content
     */
    tryGetAdvancedAnalyticsContent(sectionKey) {
        if (SIDEBAR_DEBUG) {
        }
        
        try {
            switch (sectionKey) {
                case 'correlations':
                    if (window.patternCorrelations) {
                        if (typeof window.patternCorrelations.createCorrelationInterface === 'function') {
                            return window.patternCorrelations.createCorrelationInterface();
                        } else {
                            console.warn('Correlations service exists but createCorrelationInterface method not available');
                        }
                    } else {
                    }
                    break;
                case 'temporal':
                    if (window.patternTemporal) {
                        if (typeof window.patternTemporal.createTemporalInterface === 'function') {
                            return window.patternTemporal.createTemporalInterface();
                        } else {
                            console.warn('Temporal service exists but createTemporalInterface method not available');
                        }
                    } else {
                    }
                    break;
                default:
                    return null;
            }
        } catch (error) {
            console.error(`Error getting Advanced Analytics content for ${sectionKey}:`, error);
            return null;
        }
        
        return null;
    }

    /**
     * Show loading state for Pattern Analytics sections
     */
    showPatternAnalyticsLoadingState(sectionKey, contentArea, section) {
        contentArea.innerHTML = `
            <div id="${sectionKey}-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title} Dashboard</h4>
                <div class="alert alert-info d-flex align-items-center">
                    <i class="fas fa-info-circle me-3 fa-2x"></i>
                    <div>
                        <h5 class="alert-heading mb-1">${section.title} Analytics</h5>
                        <p class="mb-0">The ${section.title.toLowerCase()} analytics service is initializing. Please wait...</p>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">Analytics Loading</h5>
                                <div class="d-flex justify-content-center py-3">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <p class="card-text">Chart visualization will appear here once the service is ready.</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">Metrics</h5>
                                <div class="d-flex justify-content-center py-3">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <p class="card-text">Performance metrics will be displayed here.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Show loading state for Advanced Analytics sections
     */
    showAdvancedAnalyticsLoadingState(sectionKey, contentArea, section) {
        contentArea.innerHTML = `
            <div id="${sectionKey}-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title} Dashboard</h4>
                <div class="alert alert-info d-flex align-items-center">
                    <i class="fas fa-info-circle me-3 fa-2x"></i>
                    <div>
                        <h5 class="alert-heading mb-1">${section.title} Analytics</h5>
                        <p class="mb-0">The ${section.title.toLowerCase()} analytics service is initializing. Please wait...</p>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">Analytics Loading</h5>
                                <div class="d-flex justify-content-center py-3">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <p class="card-text">Advanced analytics will appear here once the service is ready.</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">Insights</h5>
                                <div class="d-flex justify-content-center py-3">
                                    <div class="spinner-border text-primary" role="status">
                                        <span class="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                                <p class="card-text">Advanced insights will be displayed here.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Retry Pattern Analytics initialization with exponential backoff
     */
    retryPatternAnalyticsInitialization(sectionKey, contentArea, section, attempts = 0) {
        const maxAttempts = 5;
        const baseDelay = 500; // Start with 500ms
        
        if (attempts >= maxAttempts) {
            console.warn(`Max retry attempts reached for ${sectionKey} service initialization`);
            this.showPatternAnalyticsErrorState(sectionKey, contentArea, section);
            return;
        }
        
        const delay = baseDelay * Math.pow(1.5, attempts); // Exponential backoff
        
        setTimeout(() => {
            const content = this.tryGetPatternAnalyticsContent(sectionKey);
            
            if (content && this.currentSection === sectionKey) {
                contentArea.innerHTML = `<div id="${sectionKey}-dashboard">${content}</div>`;
                
                // Initialize charts after content is loaded
                setTimeout(() => {
                    this.initializeTabCharts(sectionKey);
                }, 200);
            } else if (this.currentSection === sectionKey) {
                // Only retry if we're still on the same section
                this.retryPatternAnalyticsInitialization(sectionKey, contentArea, section, attempts + 1);
            }
        }, delay);
    }

    /**
     * Retry Advanced Analytics initialization with exponential backoff
     */
    retryAdvancedAnalyticsInitialization(sectionKey, contentArea, section, attempts = 0) {
        const maxAttempts = 5;
        const baseDelay = 500; // Start with 500ms
        
        if (attempts >= maxAttempts) {
            console.warn(`Max retry attempts reached for ${sectionKey} service initialization`);
            this.showAdvancedAnalyticsErrorState(sectionKey, contentArea, section);
            return;
        }
        
        const delay = baseDelay * Math.pow(1.5, attempts); // Exponential backoff
        
        setTimeout(() => {
            const content = this.tryGetAdvancedAnalyticsContent(sectionKey);
            
            if (content && this.currentSection === sectionKey) {
                contentArea.innerHTML = `<div id="${sectionKey}-dashboard">${content}</div>`;
                
                // Special handling for services that need post-load initialization
                if (sectionKey === 'temporal' && window.patternTemporal && window.patternTemporal.initializeEventHandlers) {
                    setTimeout(() => {
                        window.patternTemporal.initializeEventHandlers();
                    }, 200);
                } else if (sectionKey === 'correlations' && window.patternCorrelations) {
                    setTimeout(() => {
                        // Initialize the correlations service with the container
                        if (window.patternCorrelations.renderMockData) {
                            window.patternCorrelations.renderMockData();
                        }
                        if (window.patternCorrelations.setupEventHandlers) {
                            window.patternCorrelations.setupEventHandlers();
                        }
                    }, 200);
                }
            } else if (this.currentSection === sectionKey) {
                // Only retry if we're still on the same section
                this.retryAdvancedAnalyticsInitialization(sectionKey, contentArea, section, attempts + 1);
            }
        }, delay);
    }

    /**
     * Show error state for Pattern Analytics sections
     */
    showPatternAnalyticsErrorState(sectionKey, contentArea, section) {
        contentArea.innerHTML = `
            <div id="${sectionKey}-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title} Dashboard</h4>
                <div class="alert alert-warning d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle me-3 fa-2x"></i>
                    <div>
                        <h5 class="alert-heading mb-1">Service Unavailable</h5>
                        <p class="mb-2">The ${section.title.toLowerCase()} analytics service could not be loaded. This may be due to:</p>
                        <ul class="mb-2">
                            <li>Service initialization delay</li>
                            <li>Pattern Analytics Service loading issues</li>
                            <li>JavaScript module dependencies</li>
                        </ul>
                        <button class="btn btn-outline-primary btn-sm" onclick="location.reload()">
                            <i class="fas fa-refresh me-1"></i>Refresh Page
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Show error state for Advanced Analytics sections
     */
    showAdvancedAnalyticsErrorState(sectionKey, contentArea, section) {
        contentArea.innerHTML = `
            <div id="${sectionKey}-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title} Dashboard</h4>
                <div class="alert alert-warning d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle me-3 fa-2x"></i>
                    <div>
                        <h5 class="alert-heading mb-1">Service Unavailable</h5>
                        <p class="mb-2">The ${section.title.toLowerCase()} analytics service could not be loaded. This may be due to:</p>
                        <ul class="mb-2">
                            <li>Service initialization delay</li>
                            <li>Advanced Analytics Service loading issues</li>
                            <li>Network connectivity problems</li>
                        </ul>
                        <button class="btn btn-outline-primary btn-sm" onclick="location.reload()">
                            <i class="fas fa-refresh me-1"></i>Refresh Page
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Show error state if Compare service fails to load
     */
    showCompareErrorState(contentArea, section) {
        contentArea.innerHTML = `
            <div id="compare-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title} Dashboard</h4>
                <div class="alert alert-warning d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle me-3 fa-2x"></i>
                    <div>
                        <h5 class="alert-heading mb-1">Service Unavailable</h5>
                        <p class="mb-2">The compare analytics service could not be loaded. This may be due to:</p>
                        <ul class="mb-2">
                            <li>Service initialization delay</li>
                            <li>JavaScript loading issues</li>
                            <li>Network connectivity problems</li>
                        </ul>
                        <button class="btn btn-outline-primary btn-sm" onclick="location.reload()">
                            <i class="fas fa-refresh me-1"></i>Refresh Page
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Try to get Compare content, with retries if service not loaded yet
     */
    tryGetCompareContent() {
        if (window.patternComparison && window.patternComparison.renderDashboard) {
            return window.patternComparison.renderDashboard();
        }
        
        return null;
    }

    /**
     * Show fallback content (enhanced version of original)
     */
    showFallbackContent(sectionKey, section, contentArea) {
        
        // Special fallback for overview (from original)
        if (sectionKey === 'overview') {
            contentArea.innerHTML = `
                <div id="overview-dashboard" class="p-4">
                    <h4><i class="${section.icon} me-2"></i>Overview Dashboard</h4>
                    <div class="row mb-3">
                        <div class="col-md-3 col-6 mb-2">
                            <div class="text-center">
                                <div class="h4 text-primary mb-0">Loading...</div>
                                <small class="text-muted">Patterns Today</small>
                            </div>
                        </div>
                        <div class="col-md-3 col-6 mb-2">
                            <div class="text-center">
                                <div class="h4 text-success mb-0">Loading...</div>
                                <small class="text-muted">Success Rate</small>
                            </div>
                        </div>
                        <div class="col-md-3 col-6 mb-2">
                            <div class="text-center">
                                <div class="h4 text-warning mb-0">Loading...</div>
                                <small class="text-muted">Avg Confidence</small>
                            </div>
                        </div>
                        <div class="col-md-3 col-6 mb-2">
                            <div class="text-center">
                                <div class="h4 text-info mb-0">Loading...</div>
                                <small class="text-muted">Active Patterns</small>
                            </div>
                        </div>
                    </div>
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        Overview analytics are loading. If this continues, the analytics service may not be available.
                    </div>
                </div>
            `;
        } else {
            // Standard fallback for other sections
            contentArea.innerHTML = `
                <div id="${sectionKey}-dashboard" class="p-4">
                    <h4><i class="${section.icon} me-2"></i>${section.title} Dashboard</h4>
                    <div class="alert alert-info d-flex align-items-center">
                        <i class="fas fa-info-circle me-3 fa-2x"></i>
                        <div>
                            <h5 class="alert-heading mb-1">${section.title} Analytics</h5>
                            <p class="mb-0">The ${section.title.toLowerCase()} analytics service is initializing. Please wait...</p>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-body">
                                    <h5 class="card-title">Analytics Loading</h5>
                                    <p class="card-text">Chart visualization will appear here once the service is ready.</p>
                                    <div class="bg-light p-3 rounded text-center">
                                        <i class="${section.icon} fa-3x text-muted"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-body">
                                    <h5 class="card-title">Metrics</h5>
                                    <p class="card-text">Performance metrics will be displayed here.</p>
                                    <div class="d-flex justify-content-center">
                                        <div class="spinner-border text-primary" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
    }
    
    /**
     * Toggle sidebar collapsed/expanded
     */
    toggleSidebar() {
        this.isCollapsed = !this.isCollapsed;
        
        // Hide any active tooltips when toggling sidebar
        this.hideAllTooltips();
        
        this.applySidebarState();
        this.updateToggleIcon();
        this.saveState();
    }
    
    /**
     * Update toggle button icon
     */
    updateToggleIcon() {
        if (this.toggleBtn) {
            const icon = this.toggleBtn.querySelector('i');
            if (icon) {
                if (this.isCollapsed) {
                    icon.className = 'fas fa-chevron-right';
                    this.toggleBtn.title = 'Expand sidebar';
                } else {
                    icon.className = 'fas fa-bars';
                    this.toggleBtn.title = 'Collapse sidebar';
                }
            }
        }
    }
    
    /**
     * Open filters column
     */
    openFilters() {
        if (this.isMobile) return;
        
        if (!this.filterColumn) {
            console.warn('Filter column not available');
            return;
        }
        
        this.isFilterOpen = true;
        this.filterColumn.classList.add('active');
        
        // Load filter content for Pattern Discovery
        this.loadFilterContent();
        
        // Update filter indicator
        const patternDiscoveryItem = document.querySelector('[data-section="pattern-discovery"]');
        if (patternDiscoveryItem) {
            patternDiscoveryItem.classList.add('has-filters');
        }
    }
    
    /**
     * Close filters column
     */
    closeFilters() {
        this.isFilterOpen = false;
        
        if (this.filterColumn) {
            this.filterColumn.classList.remove('active');
        }
        
        // Update filter indicator
        const patternDiscoveryItem = document.querySelector('[data-section="pattern-discovery"]');
        if (patternDiscoveryItem) {
            patternDiscoveryItem.classList.remove('has-filters');
        }
    }
    
    /**
     * Load filter content
     */
    loadFilterContent() {
        const filterContent = document.getElementById('filter-column-content');
        if (!filterContent) return;
        
        // Load Pattern Discovery filters
        if (window.patternDiscovery && window.patternDiscovery.createFilterContent) {
            const filterHTML = window.patternDiscovery.createFilterContent();
            filterContent.innerHTML = filterHTML;
        } else {
            filterContent.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Loading filters...</span>
                    </div>
                    <p class="text-muted">Loading filter options...</p>
                </div>
            `;
        }
    }
    
    /**
     * Apply filters
     */
    applyFilters() {
        if (window.patternDiscovery && typeof window.patternDiscovery.loadPatterns === 'function') {
            window.patternDiscovery.loadPatterns();
            this.showNotification('Filters applied successfully', 'success');
        }
    }
    
    /**
     * Clear filters
     */
    clearFilters() {
        if (window.patternDiscovery && typeof window.patternDiscovery.clearFilters === 'function') {
            window.patternDiscovery.clearFilters();
            this.showNotification('Filters cleared', 'info');
        }
    }
    
    /**
     * Close mobile sidebar
     */
    closeMobileSidebar() {
        if (!this.isMobile) return;
        
        this.sidebar.classList.remove('mobile-open');
        this.overlay.classList.remove('active');
        document.body.classList.remove('sidebar-mobile-open');
    }
    
    /**
     * Apply sidebar state (collapsed/expanded)
     */
    applySidebarState() {
        if (!this.sidebar) return;
        
        // Always allow manual toggle on desktop/tablet
        if (!this.isMobile) {
            this.sidebar.classList.toggle('narrow', this.isCollapsed);
        }
    }
    
    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        if (typeof Swal !== 'undefined') {
            const icons = { success: 'success', error: 'error', warning: 'warning', info: 'info' };
            Swal.fire({
                title: message,
                icon: icons[type] || 'info',
                timer: 3000,
                timerProgressBar: true,
                showConfirmButton: false,
                position: 'top-end',
                toast: true
            });
        } else {
        }
    }
    
    /**
     * Add event handler with cleanup tracking
     */
    addEventHandler(element, event, handler) {
        if (!element) return;
        
        const wrappedHandler = (e) => {
            try {
                handler(e);
            } catch (error) {
                console.error('SidebarNavigationController: Event handler error:', error);
            }
        };
        
        element.addEventListener(event, wrappedHandler);
        
        // Track for cleanup
        if (!this.eventHandlers.has(element)) {
            this.eventHandlers.set(element, []);
        }
        this.eventHandlers.get(element).push({ event, handler: wrappedHandler });
    }
    
    /**
     * Load state from storage
     */
    loadState() {
        if (!this.options.rememberState) return;
        
        try {
            const saved = localStorage.getItem(this.options.storageKey);
            if (saved) {
                const state = JSON.parse(saved);
                
                // Check if this is a page refresh by detecting if we're loading from a fresh page state
                // If Pattern Discovery Mode is enabled globally, always start with pattern-discovery
                if (window.PATTERN_DISCOVERY_MODE === true) {
                    // Page refresh with Pattern Discovery mode - always start with default section
                    this.currentSection = this.options.defaultSection;
                    console.log('SidebarNavigationController: Page refresh detected - using defaultSection:', this.currentSection);
                } else {
                    // Normal navigation - use saved state
                    this.currentSection = state.currentSection || this.options.defaultSection;
                }
                
                this.isCollapsed = state.isCollapsed || false;
            }
        } catch (error) {
            console.warn('SidebarNavigationController: Could not load state:', error);
        }
    }
    
    /**
     * Save state to storage
     */
    saveState() {
        if (!this.options.rememberState) return;
        
        try {
            const state = {
                currentSection: this.currentSection,
                isCollapsed: this.isCollapsed
            };
            localStorage.setItem(this.options.storageKey, JSON.stringify(state));
        } catch (error) {
            console.warn('SidebarNavigationController: Could not save state:', error);
        }
    }
    
    /**
     * Show tooltip for sidebar navigation item
     */
    showTooltip(element, text) {
        if (!text) return;
        
        // Remove any existing tooltip
        this.hideTooltip();
        
        // Create tooltip element
        const tooltip = document.createElement('div');
        tooltip.className = 'sidebar-tooltip';
        tooltip.textContent = text;
        tooltip.id = 'sidebar-tooltip';
        
        // Add to body to avoid positioning issues
        document.body.appendChild(tooltip);
        
        // Position tooltip
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        const left = rect.right + 12; // 12px offset from sidebar
        const top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
        
        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
        
        // Show tooltip with animation
        setTimeout(() => {
            tooltip.classList.add('show');
        }, 10);
        
        // Store reference for cleanup
        this.currentTooltip = tooltip;
    }
    
    /**
     * Hide current tooltip with improved cleanup
     */
    hideTooltip() {
        if (this.currentTooltip) {
            // Clear any pending show timeouts
            if (this.tooltipTimeout) {
                clearTimeout(this.tooltipTimeout);
                this.tooltipTimeout = null;
            }
            
            this.currentTooltip.classList.remove('show');
            
            // Store reference to remove
            const tooltipToRemove = this.currentTooltip;
            this.currentTooltip = null;
            
            // Remove after animation completes
            setTimeout(() => {
                if (tooltipToRemove && tooltipToRemove.parentNode) {
                    tooltipToRemove.parentNode.removeChild(tooltipToRemove);
                }
            }, 200);
        }
    }
    
    /**
     * Hide all tooltips (emergency cleanup)
     */
    hideAllTooltips() {
        // Remove any existing tooltips by class
        const existingTooltips = document.querySelectorAll('.sidebar-tooltip');
        existingTooltips.forEach(tooltip => {
            tooltip.parentNode.removeChild(tooltip);
        });
        
        // Clear current reference
        this.currentTooltip = null;
        
        // Clear any pending timeouts
        if (this.tooltipTimeout) {
            clearTimeout(this.tooltipTimeout);
            this.tooltipTimeout = null;
        }
    }
    
    /**
     * Utility: Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Get current state
     */
    getState() {
        return {
            currentSection: this.currentSection,
            isCollapsed: this.isCollapsed,
            isFilterOpen: this.isFilterOpen,
            isMobile: this.isMobile
        };
    }
    
    /**
     * Initialize Multi-Tier Pattern Dashboard section
     */
    initializeSprint25Section(contentArea, section) {
        if (SIDEBAR_DEBUG) console.log('[SidebarNavigation] Initializing Pattern Flow Display');

        // Check if Pattern Flow components are available
        if (typeof window.PatternFlowService !== 'undefined' && typeof window.TierPatternService !== 'undefined') {
            // Pattern Flow components already loaded - render the dashboard
            this.renderSprint25Dashboard(contentArea, section);
        } else {
            // Show loading state and initialize Pattern Flow components
            this.showSprint25LoadingState(contentArea, section);
            this.initializeSprint25Components(contentArea, section);
        }
    }
    
    /**
     * Show Pattern Flow loading state
     */
    showSprint25LoadingState(contentArea, section) {
        contentArea.innerHTML = `
            <div id="sprint25-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title}</h4>
                <div class="alert alert-info d-flex align-items-center">
                    <i class="fas fa-stream me-3 fa-2x"></i>
                    <div>
                        <h5 class="alert-heading mb-1">Pattern Flow</h5>
                        <p class="mb-0">Initializing real-time pattern flow display with 4-column layout...</p>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">Implementation Progress</h6>
                            </div>
                            <div class="card-body">
                                <div class="progress-item">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span>Week 1: WebSocket Scalability Foundation</span>
                                        <span class="badge bg-success">✅ Complete</span>
                                    </div>
                                    <small class="text-muted">UniversalWebSocketManager + SubscriptionIndexManager + ScalableBroadcaster + EventRouter</small>
                                </div>
                                <hr>
                                <div class="progress-item">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <span>Week 2: Multi-Tier Dashboard UI</span>
                                        <span class="badge bg-primary">🔄 Loading</span>
                                    </div>
                                    <small class="text-muted">Three-column layout with real-time pattern updates and WebSocket integration</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Initialize Pattern Dashboard components and render dashboard
     */
    initializeSprint25Components(contentArea, section) {
        // Try to initialize Pattern Flow components
        setTimeout(() => {
            // Check if services are loaded
            if (typeof TierPatternService !== 'undefined' && typeof PatternFlowService !== 'undefined') {
                this.renderSprint25Dashboard(contentArea, section);
            } else {
                // Try loading the scripts if not already loaded
                this.loadSprint25Scripts().then(() => {
                    this.renderSprint25Dashboard(contentArea, section);
                }).catch((error) => {
                    console.error('[SidebarNavigation] Failed to load Pattern Flow scripts:', error);
                    this.showSprint25ErrorState(contentArea, section);
                });
            }
        }, 1000);
    }
    
    /**
     * Load Pattern Flow JavaScript components dynamically
     */
    loadSprint25Scripts() {
        return new Promise((resolve, reject) => {
            const scripts = [
                '/static/js/services/tier_pattern_service.js',
                '/static/js/services/pattern_flow.js'
            ];
            
            let loadedCount = 0;
            const totalScripts = scripts.length;
            
            scripts.forEach(scriptSrc => {
                // Check if script is already loaded
                if (document.querySelector(`script[src="${scriptSrc}"]`)) {
                    loadedCount++;
                    if (loadedCount === totalScripts) resolve();
                    return;
                }
                
                const script = document.createElement('script');
                script.src = scriptSrc;
                script.onload = () => {
                    loadedCount++;
                    if (loadedCount === totalScripts) resolve();
                };
                script.onerror = () => reject(new Error(`Failed to load ${scriptSrc}`));
                document.head.appendChild(script);
            });
        });
    }
    
    /**
     * Render Multi-Tier Pattern Dashboard
     */
    renderSprint25Dashboard(contentArea, section) {
        contentArea.innerHTML = `
            <div id="sprint25-dashboard" class="sprint25-container">
                <!-- Pattern Flow Container -->
                <div id="pattern-flow-container" data-component="pattern-flow-container">
                    <!-- Pattern Flow content will be rendered here by PatternFlowService -->
                </div>
            </div>
        `;

        // Initialize the Pattern Flow Service
        setTimeout(async () => {
            try {
                // Check if container exists
                const container = document.getElementById('pattern-flow-container');
                if (!container) {
                    throw new Error('Pattern Flow container not found in DOM');
                }

                if (typeof PatternFlowService !== 'undefined') {
                    if (SIDEBAR_DEBUG) {
                        console.log('[SidebarNavigation] Initializing PatternFlowService with container:', container);
                    }

                    // Create new Pattern Flow instance
                    window.patternFlowService = new PatternFlowService();
                    await window.patternFlowService.initialize('#pattern-flow-container');

                    if (SIDEBAR_DEBUG) {
                        console.log('[SidebarNavigation] Pattern Flow Service initialized successfully');
                    }
                } else {
                    throw new Error('PatternFlowService class not available');
                }
            } catch (error) {
                console.error('[SidebarNavigation] Error initializing Pattern Flow:', error);
                console.error('[SidebarNavigation] Debug info:', {
                    PatternFlowService: typeof PatternFlowService,
                    TierPatternService: typeof TierPatternService,
                    containerExists: !!document.getElementById('pattern-flow-container'),
                    tierPatternService: !!window.tierPatternService
                });
                this.showSprint25ErrorState(contentArea, section);
            }
        }, 1000); // Increased delay to 1 second
    }
    
    /**
     * Initialize Streaming Dashboard section - Sprint 33 Phase 5
     */
    initializeStreamingSection(contentArea, section) {
        if (SIDEBAR_DEBUG) console.log('[SidebarNavigation] Initializing Streaming Dashboard');

        // Check if StreamingDashboardService is available
        if (typeof window.StreamingDashboardService !== 'undefined') {
            try {
                // Clean up existing instance if present
                if (window.streamingDashboard) {
                    if (window.streamingDashboard.cleanup) {
                        window.streamingDashboard.cleanup();
                    }
                    window.streamingDashboard = null;
                }

                // Set the content area as the main content
                contentArea.id = 'main-content';

                // Create new streaming dashboard instance
                window.streamingDashboard = new window.StreamingDashboardService();

                // Initialize the dashboard
                window.streamingDashboard.initialize('main-content');

                if (SIDEBAR_DEBUG) {
                    console.log('[SidebarNavigation] Streaming Dashboard initialized successfully');
                }
            } catch (error) {
                console.error('[SidebarNavigation] Error initializing Streaming Dashboard:', error);
                this.showStreamingErrorState(contentArea, section);
            }
        } else {
            // StreamingDashboardService not loaded yet - show loading and retry
            this.showStreamingLoadingState(contentArea, section);

            setTimeout(() => {
                if (typeof window.StreamingDashboardService !== 'undefined' && this.currentSection === 'streaming') {
                    this.initializeStreamingSection(contentArea, section);
                } else {
                    this.showStreamingErrorState(contentArea, section);
                }
            }, 1000);
        }
    }

    /**
     * Show Streaming Dashboard loading state
     */
    showStreamingLoadingState(contentArea, section) {
        contentArea.innerHTML = `
            <div id="streaming-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title}</h4>
                <div class="d-flex align-items-center justify-content-center py-5">
                    <div class="spinner-border text-primary me-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="text-muted">Initializing Streaming Dashboard...</div>
                </div>
            </div>
        `;
    }

    /**
     * Show Streaming Dashboard error state
     */
    showStreamingErrorState(contentArea, section) {
        contentArea.innerHTML = `
            <div id="streaming-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title}</h4>
                <div class="alert alert-warning d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle me-3 fa-2x"></i>
                    <div>
                        <h5 class="alert-heading mb-1">Streaming Dashboard Unavailable</h5>
                        <p class="mb-2">The streaming dashboard could not be loaded. This may be due to:</p>
                        <ul class="mb-2">
                            <li>WebSocket connection not established</li>
                            <li>Streaming service components not loaded</li>
                            <li>Redis event subscriber not active</li>
                        </ul>
                        <div class="mt-3">
                            <button class="btn btn-outline-primary btn-sm" onclick="location.reload()">
                                <i class="fas fa-sync-alt me-1"></i>Refresh Page
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Show Pattern Dashboard error state
     */
    showSprint25ErrorState(contentArea, section) {
        contentArea.innerHTML = `
            <div id="sprint25-dashboard" class="p-4">
                <h4><i class="${section.icon} me-2"></i>${section.title}</h4>
                <div class="alert alert-warning d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle me-3 fa-2x"></i>
                    <div>
                        <h5 class="alert-heading mb-1">Pattern Dashboard Components Unavailable</h5>
                        <p class="mb-2">The multi-tier pattern dashboard could not be loaded. This may be due to:</p>
                        <ul class="mb-2">
                            <li>Pattern Dashboard JavaScript components not loaded</li>
                            <li>WebSocket infrastructure initialization delay</li>
                            <li>Network connectivity issues</li>
                        </ul>
                        <div class="mt-3">
                            <button class="btn btn-outline-primary btn-sm me-2" onclick="location.reload()">
                                <i class="fas fa-refresh me-1"></i>Refresh Page
                            </button>
                            <a href="/dashboard/pattern-dashboard" class="btn btn-primary btn-sm" target="_blank">
                                <i class="fas fa-external-link-alt me-1"></i>Open Standalone Dashboard
                            </a>
                        </div>
                    </div>
                </div>
                
                <!-- Pattern Dashboard Information Card -->
                <div class="row">
                    <div class="col-md-12">
                        <div class="card">
                            <div class="card-header">
                                <h6 class="mb-0">Pattern Dashboard Architecture Overview</h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6>Week 1: WebSocket Foundation ✅</h6>
                                        <ul class="list-unstyled small">
                                            <li>• UniversalWebSocketManager</li>
                                            <li>• SubscriptionIndexManager (&lt;5ms filtering)</li>
                                            <li>• ScalableBroadcaster (&lt;100ms delivery)</li>
                                            <li>• EventRouter (&lt;20ms routing)</li>
                                            <li>• TierPatternWebSocketIntegration</li>
                                        </ul>
                                    </div>
                                    <div class="col-md-6">
                                        <h6>Week 2: Dashboard UI 🔄</h6>
                                        <ul class="list-unstyled small">
                                            <li>• Multi-Tier Dashboard Component</li>
                                            <li>• Tier Pattern Service (WebSocket Client)</li>
                                            <li>• API Endpoints (/api/patterns/*)</li>
                                            <li>• Real-time Updates (&lt;125ms total)</li>
                                            <li>• 500+ Concurrent Users Support</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Cleanup event handlers and DOM
     */
    destroy() {
        // Clean up all tooltips first
        this.hideAllTooltips();
        
        // Remove all event handlers
        for (const [element, handlers] of this.eventHandlers) {
            handlers.forEach(({ event, handler }) => {
                element.removeEventListener(event, handler);
            });
        }
        this.eventHandlers.clear();
        
        // Remove created DOM elements
        if (this.sidebar) this.sidebar.remove();
        if (this.filterColumn) this.filterColumn.remove();
        if (this.overlay) this.overlay.remove();
        
    }
}

// Export for use
window.SidebarNavigationController = SidebarNavigationController;
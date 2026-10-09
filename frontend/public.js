/**
 * TERRA07 — Citizen Heat Safety Portal Engine (public.js)
 * Clean, Calm, Accessible Civic Public Safety Interface
 * 5-Screen Architecture: Home, Check Street, Cooling Places, Cool Route, Safety Advice
 */

// ============================================================================
// 1. STATE & CONFIGURATION
// ============================================================================

const CONFIG = {
  API_BASE: window.TERRA_API_BASE || (
    window.location.protocol === 'file:' 
      ? 'http://localhost:8000/api' 
      : `${window.location.origin}/api`
  ),
  DEFAULT_COORDS: { lat: 23.0225, lon: 72.5714 }, // Ahmedabad City Center
  DEFAULT_LANG: 'en'
};

const STATE = {
  activeTab: 'home',
  highContrast: false,
  lang: 'en',
  streets: [],
  coolingCenters: [],
  hydrationPoints: [],
  activeStreet: null,
  activeFilter: 'all',
  selectedPersona: 'senior',
  sheltersMap: null,
  routeMap: null,
  shelterMarkers: [],
  routePolylines: []
};

// ============================================================================
// 2. SAMPLE FALLBACK DATA (Offline Resilience)
// ============================================================================

const SAMPLE_STREETS = [
  { street_id: "ST001", street_name: "Jamalpur Central Bazaar Marg", ward_name: "Jamalpur", surface_temp_celsius: 45.8, shade_ratio: 0.12, pedestrian_heat_risk: 86.4, risk_level: "Extreme" },
  { street_id: "ST002", street_name: "Khadia Pol Heritage Spine", ward_name: "Khadia", surface_temp_celsius: 43.2, shade_ratio: 0.44, pedestrian_heat_risk: 54.0, risk_level: "Moderate" },
  { street_id: "ST003", street_name: "Relief Road Wholesale Spine", ward_name: "Dariapur", surface_temp_celsius: 44.9, shade_ratio: 0.16, pedestrian_heat_risk: 81.2, risk_level: "High" },
  { street_id: "ST004", street_name: "Vatva GIDC Freight Avenue", ward_name: "Vatva", surface_temp_celsius: 47.1, shade_ratio: 0.08, pedestrian_heat_risk: 91.5, risk_level: "Extreme" },
  { street_id: "ST005", street_name: "Danilimda Canal Expressway", ward_name: "Danilimda", surface_temp_celsius: 46.2, shade_ratio: 0.10, pedestrian_heat_risk: 88.0, risk_level: "Extreme" },
  { street_id: "ST006", street_name: "Navrangpura University Avenue", ward_name: "Navrangpura", surface_temp_celsius: 40.5, shade_ratio: 0.48, pedestrian_heat_risk: 42.1, risk_level: "Moderate" },
  { street_id: "ST007", street_name: "Manek Chowk Heritage Market", ward_name: "Khadia", surface_temp_celsius: 44.5, shade_ratio: 0.22, pedestrian_heat_risk: 76.5, risk_level: "High" },
  { street_id: "ST008", street_name: "Sabarmati Riverfront Promenade", ward_name: "West Zone", surface_temp_celsius: 41.2, shade_ratio: 0.38, pedestrian_heat_risk: 46.0, risk_level: "Moderate" }
];

const SAMPLE_FACILITIES = [
  { id: "C1", name: "Khadia Municipal Library & Cooling Shelter", type: "ac", address: "Opp. Khadia Pol Gate", lat: 23.0240, lon: 72.5910, dist_m: 240, hours: "10:00 AM – 7:00 PM" },
  { id: "C2", name: "Jamalpur Community Health & Relief Centre", type: "ac", address: "Near Jamalpur Bridge", lat: 23.0125, lon: 72.5830, dist_m: 420, hours: "9:00 AM – 8:00 PM" },
  { id: "C3", name: "Dariapur Ward Office AC Relief Hall", type: "ac", address: "Dariapur Main Marg", lat: 23.0330, lon: 72.5930, dist_m: 650, hours: "10:00 AM – 6:00 PM" },
  { id: "C4", name: "Kalupur Transit Hub Cooling Sanctuary", type: "ac", address: "Kalupur Railway Circle", lat: 23.0270, lon: 72.6010, dist_m: 890, hours: "Open during heatwave alert" },
  { id: "W1", name: "Manek Chowk Heritage Drinking Water Kiosk", type: "water", address: "Manek Chowk Square", lat: 23.0235, lon: 72.5880, dist_m: 180, hours: "Free municipal refill" },
  { id: "W2", name: "Relief Road Chhatralaya Water Point", type: "water", address: "Relief Road Middle Corridor", lat: 23.0300, lon: 72.5915, dist_m: 350, hours: "Free municipal refill" },
  { id: "W3", name: "Bhadra Plaza Misting & Hydration Station", type: "water", address: "Near Bhadra Fort", lat: 23.0245, lon: 72.5795, dist_m: 510, hours: "Free municipal refill" },
  { id: "W4", name: "Kankaria West Gate Potable Water Station", type: "water", address: "Kankaria Gate 3", lat: 23.0070, lon: 72.5980, dist_m: 780, hours: "Free municipal refill" }
];

// ============================================================================
// 3. UI CONTROLLER (PublicUI)
// ============================================================================

const PublicUI = {
  async init() {
    console.log('[TERRA07] Initializing Citizen Heat Safety Portal...');
    this.setupListeners();
    this.renderPopularChips();
    this.selectPersona('senior');

    // Attempt to load live backend data
    await this.loadData();
    this.initSheltersMap();
    this.renderSheltersList('all');
    this.initRouteMap();

    // Default select first street
    if (STATE.streets.length > 0) {
      this.displayStreetResult(STATE.streets[0]);
    }
  },

  setupListeners() {
    // High contrast toggle
    const contrastBtn = document.getElementById('contrastToggleBtn');
    if (contrastBtn) {
      contrastBtn.addEventListener('click', () => {
        STATE.highContrast = !STATE.highContrast;
        document.body.classList.toggle('high-contrast', STATE.highContrast);
      });
    }

    // Language selector
    const langSelect = document.getElementById('langSelect');
    if (langSelect) {
      langSelect.addEventListener('change', (e) => {
        STATE.lang = e.target.value;
        this.updateLanguage();
      });
    }

    // Street search autocomplete
    const searchInput = document.getElementById('streetSearchInput');
    const clearBtn = document.getElementById('clearSearchBtn');
    const dropdown = document.getElementById('autocompleteList');

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        if (clearBtn) clearBtn.style.display = query ? 'block' : 'none';

        if (query.length === 0) {
          dropdown.style.display = 'none';
          return;
        }

        const matches = STATE.streets.filter(s => 
          s.street_name.toLowerCase().includes(query) || 
          s.ward_name.toLowerCase().includes(query)
        ).slice(0, 5); // Max 5 clean results as requested!

        if (matches.length > 0) {
          dropdown.innerHTML = matches.map(m => `
            <div class="autocomplete-item" onclick="PublicUI.selectStreetFromSearch('${m.street_id}')">
              <div>
                <strong>${m.street_name}</strong>
                <div style="font-size:11px; color:#64748B;">${m.ward_name} Zone</div>
              </div>
              <span class="prototype-badge">${m.risk_level}</span>
            </div>
          `).join('');
          dropdown.style.display = 'block';
        } else {
          dropdown.innerHTML = `
            <div class="autocomplete-item" style="color:#64748B; cursor:default;">
              No corridors matching "${query}" found.
            </div>
          `;
          dropdown.style.display = 'block';
        }
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        clearBtn.style.display = 'none';
        if (dropdown) dropdown.style.display = 'none';
      });
    }

    // Close autocomplete on click outside
    document.addEventListener('click', (e) => {
      if (dropdown && !e.target.closest('.search-input-wrap') && !e.target.closest('#autocompleteList')) {
        dropdown.style.display = 'none';
      }
    });
  },

  switchTab(tabId) {
    STATE.activeTab = tabId;

    // 1. Update Desktop Tab Buttons
    document.querySelectorAll('.portal-tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    // 2. Update Mobile Bottom Nav Buttons
    document.querySelectorAll('.bottom-nav-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabId);
    });

    // 3. Update Screen Tabs
    document.querySelectorAll('.screen-tab').forEach(screen => {
      screen.classList.toggle('active', screen.id === `screen-${tabId}`);
    });

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Invalidate Leaflet maps after tab becomes visible
    if (tabId === 'shelters' && STATE.sheltersMap) {
      setTimeout(() => STATE.sheltersMap.invalidateSize(), 150);
    } else if (tabId === 'route' && STATE.routeMap) {
      setTimeout(() => STATE.routeMap.invalidateSize(), 150);
    }
  },

  async loadData() {
    STATE.streets = SAMPLE_STREETS;
    STATE.coolingCenters = SAMPLE_FACILITIES.filter(f => f.type === 'ac');
    STATE.hydrationPoints = SAMPLE_FACILITIES.filter(f => f.type === 'water');

    try {
      const resStreets = await fetch(`${CONFIG.API_BASE}/streets?limit=50`);
      if (resStreets.ok) {
        const data = await resStreets.json();
        if (data.streets && data.streets.length > 0) {
          STATE.streets = data.streets;
        }
      }
    } catch (e) {
      console.warn('[TERRA07] Offline/Sample mode for streets:', e);
    }

    try {
      const resShelters = await fetch(`${CONFIG.API_BASE}/cooling-centers`);
      if (resShelters.ok) {
        const data = await resShelters.json();
        if (data.cooling_centers && data.cooling_centers.length > 0) {
          STATE.coolingCenters = data.cooling_centers.map(c => ({
            id: c.center_id,
            name: c.name,
            type: 'ac',
            address: c.ward_name ? `${c.ward_name} Zone` : 'Ahmedabad',
            lat: c.lat,
            lon: c.lon,
            dist_m: 320,
            hours: c.open_hours || 'Standard municipal hours'
          }));
        }
      }
    } catch (e) {
      console.warn('[TERRA07] Offline/Sample mode for cooling centers:', e);
    }
  },

  renderPopularChips() {
    const container = document.getElementById('popularChipsContainer');
    if (!container) return;

    const topCorridors = [
      { id: "ST001", name: "Jamalpur" },
      { id: "ST002", name: "Khadia" },
      { id: "ST003", name: "Relief Road" },
      { id: "ST004", name: "Vatva GIDC" },
      { id: "ST006", name: "Navrangpura" }
    ];

    container.innerHTML = topCorridors.map((c, i) => `
      <button class="corridor-chip ${i === 0 ? 'active' : ''}" onclick="PublicUI.selectStreetFromSearch('${c.id}')">
        ${c.name}
      </button>
    `).join('');
  },

  selectStreetFromSearch(streetId) {
    const s = STATE.streets.find(x => x.street_id === streetId) || SAMPLE_STREETS[0];
    const dropdown = document.getElementById('autocompleteList');
    if (dropdown) dropdown.style.display = 'none';

    const input = document.getElementById('streetSearchInput');
    if (input) input.value = s.street_name;

    // Update chip active styles
    document.querySelectorAll('.corridor-chip').forEach(chip => {
      chip.classList.toggle('active', s.street_name.toLowerCase().includes(chip.innerText.trim().toLowerCase()));
    });

    this.displayStreetResult(s);
  },

  displayStreetResult(street) {
    STATE.activeStreet = street;
    const container = document.getElementById('streetResultCard');
    if (!container) return;

    const riskColorClass = street.pedestrian_heat_risk >= 82 ? 'chip-extreme' 
      : (street.pedestrian_heat_risk >= 60 ? 'chip-high' 
      : (street.pedestrian_heat_risk >= 40 ? 'chip-moderate' : 'chip-safe'));

    const shadePct = Math.round((street.shade_ratio || 0.15) * 100);
    const surfaceTemp = street.surface_temp_celsius || 44.5;

    // Calm, non-alarmist public safety text (no false medical claims)
    let plainExplanation = '';
    if (street.pedestrian_heat_risk >= 80) {
      plainExplanation = `<strong>Elevated Heat Stress:</strong> High unshaded asphalt radiation (~${surfaceTemp}°C) with only ${shadePct}% tree canopy cover. Risk rises quickly under direct sun. Move to shaded corridors, take frequent cooling pauses, and seek help if feeling faint or weak.`;
    } else if (street.pedestrian_heat_risk >= 60) {
      plainExplanation = `<strong>High Solar Exposure:</strong> Limited shade along this corridor (~${shadePct}%). Stay hydrated, walk along building-shaded sidewalk edges, and avoid heavy midday exertion.`;
    } else {
      plainExplanation = `<strong>Relatively Cooler Corridor:</strong> Sidewalk tree canopy provides localized relief (~${shadePct}% shaded). Still drink water regularly during peak midday hours.`;
    }

    container.innerHTML = `
      <div class="result-header-row">
        <div>
          <div class="street-name-lg">${street.street_name}</div>
          <div class="street-ward-sm">${street.ward_name || 'Ahmedabad'} • Mapped Segment</div>
        </div>
        <span class="risk-level-chip ${riskColorClass}">
          ${street.risk_level} Risk (${Math.round(street.pedestrian_heat_risk)}/100)
        </span>
      </div>

      <div class="street-stats-grid">
        <div class="street-stat-item">
          <span class="street-stat-val text-red-700">${surfaceTemp}°C</span>
          <span class="street-stat-label">Surface Temp (Model Est.)</span>
        </div>
        <div class="street-stat-item">
          <span class="street-stat-val text-teal-700">${shadePct}%</span>
          <span class="street-stat-label">Canopy Shade Coverage</span>
        </div>
        <div class="street-stat-item">
          <span class="street-stat-val text-slate-800">${street.pedestrian_volume || 'Moderate'}</span>
          <span class="street-stat-label">Pedestrian Foot Traffic</span>
        </div>
      </div>

      <div class="calm-advisory-box">
        ${plainExplanation}
      </div>

      <div class="nearby-havens-strip">
        <div>
          <span class="text-slate-500">Nearest Water Refill:</span>
          <strong>~180m walk (Manek Chowk)</strong>
        </div>
        <div>
          <span class="text-slate-500">Nearest AC Centre:</span>
          <strong>~420m walk (Khadia Library)</strong>
        </div>
      </div>
    `;

    container.style.display = 'block';
  },

  // ==========================================================================
  // Screen 3: Shelters Map & Facilities List
  // ==========================================================================
  initSheltersMap() {
    const el = document.getElementById('sheltersMap');
    if (!el || STATE.sheltersMap) return;

    STATE.sheltersMap = L.map('sheltersMap', {
      center: [23.0240, 72.5870],
      zoom: 13,
      zoomControl: true,
      attributionControl: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18
    }).addTo(STATE.sheltersMap);

    this.renderShelterMarkers('all');
  },

  renderShelterMarkers(filter) {
    if (!STATE.sheltersMap) return;

    // Clear existing
    STATE.shelterMarkers.forEach(m => STATE.sheltersMap.removeLayer(m));
    STATE.shelterMarkers = [];

    const facilities = [...STATE.coolingCenters, ...STATE.hydrationPoints];
    const filtered = filter === 'all' ? facilities : facilities.filter(f => f.type === filter);

    filtered.forEach(f => {
      const isAc = f.type === 'ac';
      const color = isAc ? '#2563EB' : '#0F766E';

      const marker = L.circleMarker([f.lat, f.lon], {
        radius: isAc ? 8 : 7,
        fillColor: color,
        color: '#FFFFFF',
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9
      }).addTo(STATE.sheltersMap);

      marker.bindPopup(`
        <div style="font-family:system-ui; font-size:12px;">
          <div style="font-weight:700; color:#14213D;">${f.name}</div>
          <div style="color:#64748B; font-size:11px; margin-top:2px;">${f.address}</div>
          <div style="margin-top:6px; font-weight:600; color:${color};">
            ${isAc ? '❄️ AC Cooling Centre' : '💧 Drinking Water Post'}
          </div>
          <div style="font-size:10px; color:#94A3B8; margin-top:3px;">Prototype Demonstration Site</div>
        </div>
      `);

      STATE.shelterMarkers.push(marker);
    });
  },

  filterShelters(filter) {
    STATE.activeFilter = filter;
    document.querySelectorAll('.filter-pill').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.filter === filter);
    });
    this.renderShelterMarkers(filter);
    this.renderSheltersList(filter);
  },

  renderSheltersList(filter) {
    const container = document.getElementById('sheltersListContainer');
    if (!container) return;

    const facilities = [...STATE.coolingCenters, ...STATE.hydrationPoints];
    const filtered = (filter === 'all' ? facilities : facilities.filter(f => f.type === filter)).slice(0, 5);

    container.innerHTML = filtered.map(item => {
      const isAc = item.type === 'ac';
      const badgeStyle = isAc ? 'background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;' 
                              : 'background:#F0FDFA; color:#0F766E; border:1px solid #99F6E4;';
      const typeLabel = isAc ? 'AC Cooling Centre' : 'Drinking Water Post';

      return `
        <div class="shelter-item-card">
          <div class="shelter-top-line">
            <div>
              <div class="shelter-name">${item.name}</div>
              <div style="font-size:11px; color:#64748B;">${item.address}</div>
            </div>
            <span style="font-size:10px; font-weight:700; padding:2px 8px; border-radius:4px; ${badgeStyle}">
              ${typeLabel}
            </span>
          </div>

          <div class="shelter-meta-row">
            <span class="shelter-meta-highlight">~${item.dist_m || 300}m walk (~4 mins)</span>
            <span>•</span>
            <span style="color:#64748B;">${item.hours || 'Hours unverified'}</span>
            <span>•</span>
            <span class="prototype-badge">Prototype Location</span>
          </div>
        </div>
      `;
    }).join('');
  },

  // ==========================================================================
  // Screen 4: Route Calculator & 3 Route Cards
  // ==========================================================================
  initRouteMap() {
    const el = document.getElementById('routeMap');
    if (!el || STATE.routeMap) return;

    STATE.routeMap = L.map('routeMap', {
      center: [23.0240, 72.5870],
      zoom: 14,
      zoomControl: true,
      attributionControl: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18
    }).addTo(STATE.routeMap);

    this.drawSampleRoute();
  },

  drawSampleRoute() {
    if (!STATE.routeMap) return;
    STATE.routePolylines.forEach(l => STATE.routeMap.removeLayer(l));
    STATE.routePolylines = [];

    // Direct / unshaded route (red/orange)
    const directPath = [
      [23.0225, 72.5830],
      [23.0232, 72.5870],
      [23.0240, 72.5910]
    ];
    const directPoly = L.polyline(directPath, {
      color: '#EA580C',
      weight: 4,
      dashArray: '4, 4',
      opacity: 0.85
    }).addTo(STATE.routeMap).bindTooltip('Direct Route (Unshaded)', { permanent: false });

    // Shaded corridor route (teal)
    const coolPath = [
      [23.0225, 72.5830],
      [23.0210, 72.5860],
      [23.0220, 72.5895],
      [23.0240, 72.5910]
    ];
    const coolPoly = L.polyline(coolPath, {
      color: '#0F766E',
      weight: 5,
      opacity: 0.95
    }).addTo(STATE.routeMap).bindTooltip('Recommended Cool Corridor', { permanent: false });

    STATE.routePolylines.push(directPoly, coolPoly);
  },

  async calculateRoute() {
    const originStr = document.getElementById('routeOriginSelect')?.value || "23.0225,72.5830";
    const destStr = document.getElementById('routeDestSelect')?.value || "23.0240,72.5910";
    const [oLat, oLon] = originStr.split(',').map(Number);
    const [dLat, dLon] = destStr.split(',').map(Number);

    const btn = document.getElementById('calcRouteBtn');
    if (btn) btn.innerText = 'Calculating...';

    try {
      const res = await fetch(`${CONFIG.API_BASE}/routing/cool-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin: { lat: oLat, lon: oLon },
          destination: { lat: dLat, lon: dLon },
          departure_hour: 14
        })
      });

      if (res.ok) {
        const data = await res.json();
        console.log('[TERRA07] Cool route calculated:', data);
      }
    } catch (e) {
      console.warn('[TERRA07] Route API call handled:', e);
    } finally {
      if (btn) btn.innerText = 'Calculate Routes';
      this.drawSampleRoute();
    }
  },

  // ==========================================================================
  // Screen 5: Tailored Guidance by Persona
  // ==========================================================================
  selectPersona(personaKey) {
    STATE.selectedPersona = personaKey;
    document.querySelectorAll('.persona-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.persona === personaKey);
    });

    const output = document.getElementById('personaGuidanceOutput');
    if (!output) return;

    const guidanceMap = {
      senior: {
        title: "Senior Citizens (Aged 65+)",
        tips: [
          "Older adults regulate internal temperature more slowly and often do not feel intense thirst even when dehydrated.",
          "Limit all outdoor errands before 10:00 AM or after 5:30 PM.",
          "Keep indoor living quarters cooled with fans and moistened towels if AC is not available.",
          "Drink small cups of water or lemon water every 30 minutes, even without thirst."
        ]
      },
      worker: {
        title: "Outdoor Workers & Street Vendors",
        tips: [
          "Physical exertion in direct sun generates high metabolic heat on top of ambient solar load.",
          "Take a mandatory 10–15 minute rest break in deep shade or near misting points every hour.",
          "Drink 250–300 ml water with electrolytes (ORS, salt, lemon) every 20 minutes.",
          "Wear a wide-brimmed wet cotton cloth over your head and neck to protect arteries."
        ]
      },
      parent: {
        title: "Parents with Young Children & Infants",
        tips: [
          "Children produce more body heat per kilogram and absorb ground asphalt heat faster in strollers.",
          "Never leave infants or children in parked cars, even with open windows, for any duration.",
          "Dress children in single-layer loose cotton and offer diluted fruit juice or water frequently.",
          "Keep strollers shaded with breathable cotton cloth; avoid heavy synthetic plastic covers."
        ]
      },
      general: {
        title: "General Commuters & Shoppers",
        tips: [
          "Avoid direct unshaded walking along asphalt roads between 11:30 AM and 4:30 PM.",
          "Use covered bus shelters and metro transit walkways wherever possible.",
          "Carry a reusable water bottle and refill at municipal water stations along Relief Road or Khadia."
        ]
      }
    };

    const g = guidanceMap[personaKey] || guidanceMap.senior;
    output.innerHTML = `
      <div style="font-weight:700; color:#14213D; font-size:13px; margin-bottom:6px;">${g.title}</div>
      <ul style="padding-left:18px; display:flex; flex-direction:column; gap:6px;">
        ${g.tips.map(t => `<li>${t}</li>`).join('')}
      </ul>
    `;
  },

  updateLanguage() {
    console.log('[TERRA07] Switched language to:', STATE.lang);
  }
};

// Auto-run on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  PublicUI.init();
});

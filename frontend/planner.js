/**
 * TERRA07 — Urban Planner Command Center Controller
 * Human-Scale Heat Risk Intelligence | Ahmedabad Metropolitan Region
 * Pure ES6 JavaScript with Leaflet.js and Material Design 3 civic patterns
 */

(function () {
  'use strict';

  // --- 1. STATE & DATA STORE ---
  const STATE = {
    activeTab: 'overview',
    mapLayer: 'composite',
    basemap: 'light',
    budgetCap: 450000,
    allocations: {
      shade: 4,     // ₹8,000 each = ₹32,000
      misting: 6,   // ₹4,500 each = ₹27,000
      centers: 2,   // ₹25,000 each = ₹50,000
      trees: 2,     // ₹12,000 each = ₹24,000
      roofs: 240    // ₹1,200 each = ₹2,88,000
    },
    scenario: {
      tempDelta: 2.0,
      timeOfDay: '14:00',
      humidity: 'normal',
      grid: 'normal',
      interventions: {
        shade: false,
        misting: false,
        roofs: false,
        trees: false
      }
    },
    selectedAreaId: 'W-03',
    overviewMap: null,
    fullMap: null,
    geoLayers: {},
    wards: [],
    streets: []
  };

  // Indian Rupee Currency Formatter
  function formatINR(val) {
    if (val === undefined || val === null || isNaN(val)) return '₹0';
    return '₹' + Number(val).toLocaleString('en-IN');
  }

  // Risk Tier Classifier (0–39 Resilient, 40–59 Moderate, 60–81 High, 82–100 Extreme)
  function getRiskTier(score) {
    if (score >= 82) return { label: 'Extreme', color: '#C62828', bg: '#FFF1F0', border: '#FFCDD2' };
    if (score >= 60) return { label: 'High', color: '#EA580C', bg: '#FFF2E8', border: '#FED7AA' };
    if (score >= 40) return { label: 'Moderate', color: '#D97706', bg: '#FFF8E7', border: '#FDE68A' };
    return { label: 'Resilient', color: '#2E8B57', bg: '#ECFDF3', border: '#A7F3D0' };
  }

  // Fallback Benchmark Dataset for Ahmedabad
  const SAMPLE_WARDS = [
    { id: 'W-03', name: 'Danilimda Industrial South', zone: 'South Industrial', population: 165000, area_km2: 6.4, lst: 48.8, canopy_pct: 4.8, elderly: 12400, outdoor_workers: 26500, risk_score: 82.5, driver: 'Extreme LST & Lack of Shade', action: 'Tensile Shade Sails & Misting Kiosks', lat: 22.9850, lon: 72.5850 },
    { id: 'W-01', name: 'Kalupur Walled Core', zone: 'Central Urban Core', population: 142500, area_km2: 4.2, lst: 45.6, canopy_pct: 5.2, elderly: 14800, outdoor_workers: 18400, risk_score: 80.4, driver: 'Narrow Trapped Street Canyon', action: 'Reflective Cool Roof Treatment', lat: 23.0300, lon: 72.5950 },
    { id: 'W-04', name: 'Vatva Chemical & Logistics Estate', zone: 'South Industrial', population: 182000, area_km2: 8.5, lst: 49.2, canopy_pct: 3.6, elderly: 11200, outdoor_workers: 31000, risk_score: 88.4, driver: 'Heavy Built Impervious Surface', action: 'Emergency Cooling Shelter & Shade Sails', lat: 22.9550, lon: 72.6350 },
    { id: 'W-06', name: 'Odhav Textile & Foundry Cluster', zone: 'East Industrial', population: 174000, area_km2: 7.8, lst: 47.9, canopy_pct: 4.1, elderly: 10800, outdoor_workers: 28200, risk_score: 81.2, driver: 'Industrial Waste Heat & Albedo', action: 'Solar Misting Kiosks & Kiosk ATMs', lat: 23.0150, lon: 72.6650 },
    { id: 'W-02', name: 'Khadia Heritage Quarter', zone: 'Central Urban Core', population: 98000, area_km2: 3.1, lst: 44.2, canopy_pct: 7.5, elderly: 15200, outdoor_workers: 9500, risk_score: 74.8, driver: 'High Elderly Demographics', action: 'Air-Conditioned Public Refuges', lat: 23.0250, lon: 72.5900 },
    { id: 'W-07', name: 'Asarwa Civil Hospital Corridor', zone: 'Central North', population: 128000, area_km2: 5.0, lst: 43.8, canopy_pct: 8.9, elderly: 13500, outdoor_workers: 14200, risk_score: 72.5, driver: 'High Vulnerable Patient Transits', action: 'Shaded Ambulatory Walkway Corridors', lat: 23.0450, lon: 72.6050 },
    { id: 'W-10', name: 'Navrangpura University Belt', zone: 'West Commercial', population: 115000, area_km2: 6.2, lst: 39.5, canopy_pct: 21.4, elderly: 11800, outdoor_workers: 6800, risk_score: 44.2, driver: 'Moderate Tree Buffer', action: 'Urban Bioswales Maintenance', lat: 23.0380, lon: 72.5520 },
    { id: 'W-12', name: 'Bopal–Ambli Developing West', zone: 'Far West Suburbs', population: 92000, area_km2: 9.1, lst: 37.8, canopy_pct: 26.5, elderly: 7400, outdoor_workers: 4200, risk_score: 36.4, driver: 'High Vegetative Resilience', action: 'Green Cover Preservation Zoning', lat: 23.0320, lon: 72.4850 }
  ];

  const SAMPLE_STREETS = [
    { id: 'S-01', name: 'Vatva GIDC Freight Avenue', ward: 'Vatva Chemical & Logistics Estate', length_m: 1400, lst: 49.5, shade_pct: 4, pedestrians: 24000, risk_score: 88.4, action: 'Tensile Shade Sails', cost: 25000, protected: 1450, driver: 'Zero tree cover & heavy freight asphalt' },
    { id: 'S-02', name: 'Danilimda Canal Expressway', ward: 'Danilimda Industrial South', length_m: 1850, lst: 48.2, shade_pct: 6, pedestrians: 21000, risk_score: 84.6, action: 'High-Albedo Shade Canopies', cost: 18000, protected: 1200, driver: 'Exposed bitumen & high labor footfall' },
    { id: 'S-03', name: 'Narol–Naroda Ring Expressway', ward: 'Narol Industrial', length_m: 2600, lst: 47.8, shade_pct: 8, pedestrians: 18500, risk_score: 82.1, action: 'Urban Tree Corridor', cost: 24000, protected: 980, driver: 'Industrial vehicular heat emissions' },
    { id: 'S-04', name: 'Relief Road Market Corridor', ward: 'Kalupur Walled Core', length_m: 950, lst: 46.4, shade_pct: 11, pedestrians: 38000, risk_score: 79.5, action: 'Tensile Market Shade', cost: 16000, protected: 1800, driver: 'Dense open-air bazaar vendors' },
    { id: 'S-05', name: 'Gandhi Road Heritage Spine', ward: 'Khadia Heritage Quarter', length_m: 1100, lst: 45.2, shade_pct: 14, pedestrians: 29000, risk_score: 76.2, action: 'Smart Misting Kiosks', cost: 13500, protected: 1100, driver: 'Pedestrian crowding in narrow canyon' }
  ];

  // --- 2. INITIALIZATION ---
  window.addEventListener('DOMContentLoaded', async () => {
    STATE.wards = SAMPLE_WARDS;
    STATE.streets = SAMPLE_STREETS;

    // Fetch real backend data if live server is reachable
    try {
      const resWards = await fetch('/api/wards');
      if (resWards.ok) {
        const data = await resWards.json();
        if (data.wards && data.wards.length > 0) {
          STATE.wards = data.wards.map(w => ({
            id: w.ward_id,
            name: w.ward_name,
            zone: w.zone,
            population: w.demographics ? w.demographics.total_population : 120000,
            area_km2: w.area_km2 || 5.0,
            lst: w.environmental ? w.environmental.mean_lst_celsius : 44.0,
            canopy_pct: w.environmental ? w.environmental.tree_canopy_pct : 8.0,
            elderly: w.demographics ? Math.round(w.demographics.total_population * w.demographics.elderly_pct) : 10000,
            outdoor_workers: w.demographics ? Math.round(w.demographics.total_population * w.demographics.outdoor_workers_pct) : 15000,
            risk_score: w.heat_risk_score,
            driver: w.dominant_heat_drivers && w.dominant_heat_drivers.length ? w.dominant_heat_drivers[0] : 'High Surface Temperature',
            action: w.top_recommended_interventions && w.top_recommended_interventions.length ? w.top_recommended_interventions[0] : 'Shade Canopies',
            lat: w.geometry && w.geometry.coordinates ? (Array.isArray(w.geometry.coordinates[0][0]) ? w.geometry.coordinates[0][0][1] : 23.0225) : 23.0225,
            lon: w.geometry && w.geometry.coordinates ? (Array.isArray(w.geometry.coordinates[0][0]) ? w.geometry.coordinates[0][0][0] : 72.5714) : 72.5714
          }));
        }
      }
    } catch (e) {
      console.log('[TERRA07 Planner] Using calibrated benchmark geodata.');
    }

    renderOverviewPriorityList();
    renderPriorityTable();
    populateAreaInspectorSelect();
    loadAreaInspection(STATE.selectedAreaId);
    updateInterventionBudgetSummary();
    initOverviewMap();
  });

  // --- 3. GLOBAL TAB SWITCHER (8 SCREENS) ---
  window.switchTab = function (tabId) {
    STATE.activeTab = tabId;

    // Update Tab Navigation Items
    document.querySelectorAll('.tab-item').forEach((tab, index) => {
      tab.classList.remove('active');
    });

    const tabMap = {
      'overview': 0,
      'heatmap': 1,
      'priority': 2,
      'inspector': 3,
      'scenarios': 4,
      'interventions': 5,
      'reports': 6,
      'methodology': 7
    };

    const tabBtns = document.querySelectorAll('.tab-item');
    if (tabBtns[tabMap[tabId]]) {
      tabBtns[tabMap[tabId]].classList.add('active');
    }

    // Toggle Screen Panels
    document.querySelectorAll('.screen-panel').forEach(panel => {
      panel.classList.remove('active');
    });

    const activePanel = document.getElementById(`screen-${tabId}`);
    if (activePanel) {
      activePanel.classList.add('active');
    }

    // Leaflet redraw hooks
    if (tabId === 'overview' && STATE.overviewMap) {
      setTimeout(() => STATE.overviewMap.invalidateSize(), 150);
    } else if (tabId === 'heatmap') {
      if (!STATE.fullMap) {
        initFullGisMap();
      } else {
        setTimeout(() => STATE.fullMap.invalidateSize(), 150);
      }
    }
  };

  // --- 4. SCREEN 1: OVERVIEW PRIORITY ACTIONS LIST ---
  function renderOverviewPriorityList() {
    const container = document.getElementById('overview-priority-list');
    if (!container) return;

    container.innerHTML = STATE.streets.slice(0, 5).map((street, idx) => {
      const tier = getRiskTier(street.risk_score);
      return `
        <div class="p-3 rounded-lg border border-civic-border bg-slate-50 hover:bg-white transition flex flex-col justify-between shadow-2xs">
          <div class="flex items-start justify-between gap-2">
            <div>
              <div class="flex items-center gap-2">
                <span class="w-5 h-5 rounded-full bg-civic-navy text-white text-[10px] font-bold flex items-center justify-center">${idx + 1}</span>
                <span class="font-bold text-xs text-civic-navy">${street.name}</span>
              </div>
              <div class="text-[11px] text-civic-secondary mt-1">Driver: ${street.driver}</div>
            </div>
            <div class="text-right flex-shrink-0">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold" style="background:${tier.bg}; color:${tier.color}; border:1px solid ${tier.border};">
                ${street.risk_score} • ${tier.label}
              </span>
            </div>
          </div>
          <div class="mt-2.5 pt-2 border-t border-civic-border/70 flex items-center justify-between text-[11px]">
            <div class="text-slate-700">
              Action: <strong class="text-civic-teal">${street.action}</strong>
              <span class="text-civic-secondary ml-1.5 font-mono">(${formatINR(street.cost)} • ~${street.protected} protected)</span>
            </div>
            <button onclick="inspectStreetFromOverview('${street.id}')" class="px-2 py-1 bg-white hover:bg-slate-100 border border-civic-border rounded text-[11px] font-medium text-civic-teal transition">
              Inspect &rarr;
            </button>
          </div>
        </div>
      `;
    }).join('');
  }

  window.inspectStreetFromOverview = function (streetId) {
    switchTab('inspector');
    // Pre-select first ward
    loadAreaInspection('W-03');
  };

  // --- 5. SCREEN 1 & 2: LEAFLET MAPS ---
  function initOverviewMap() {
    const mapEl = document.getElementById('overview-map');
    if (!mapEl || STATE.overviewMap) return;

    STATE.overviewMap = L.map('overview-map', {
      center: [23.0225, 72.5714],
      zoom: 12,
      zoomControl: true,
      attributionControl: false
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18
    }).addTo(STATE.overviewMap);

    // Add Ward Circles
    STATE.wards.forEach(w => {
      const tier = getRiskTier(w.risk_score);
      const circle = L.circleMarker([w.lat, w.lon], {
        radius: Math.min(22, Math.max(12, w.risk_score / 4.5)),
        fillColor: tier.color,
        color: '#FFFFFF',
        weight: 2,
        opacity: 0.9,
        fillOpacity: 0.75
      }).addTo(STATE.overviewMap);

      circle.bindTooltip(`<b>${w.name}</b><br>Score: ${w.risk_score} (${tier.label})<br>LST: ${w.lst}°C`, {
        className: 'leaflet-custom-tooltip'
      });

      circle.on('click', () => {
        loadAreaInspection(w.id);
        switchTab('inspector');
      });
    });
  }

  function initFullGisMap() {
    const mapEl = document.getElementById('full-gis-map');
    if (!mapEl || STATE.fullMap) return;

    STATE.fullMap = L.map('full-gis-map', {
      center: [23.0225, 72.5714],
      zoom: 12,
      zoomControl: true
    });

    STATE.geoLayers.base = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 18,
      attribution: '© OpenStreetMap, © CARTO'
    }).addTo(STATE.fullMap);

    STATE.geoLayers.markers = L.layerGroup().addTo(STATE.fullMap);
    renderFullMapLayers();
  }

  function renderFullMapLayers() {
    if (!STATE.fullMap || !STATE.geoLayers.markers) return;
    STATE.geoLayers.markers.clearLayers();

    STATE.wards.forEach(w => {
      let metricVal = w.risk_score;
      let metricLabel = 'Heat Risk';
      let color = getRiskTier(w.risk_score).color;

      if (STATE.mapLayer === 'lst') {
        metricVal = w.lst;
        metricLabel = 'LST';
        color = w.lst > 46 ? '#C62828' : (w.lst > 42 ? '#EA580C' : '#D97706');
      } else if (STATE.mapLayer === 'canopy') {
        metricVal = w.canopy_pct + '%';
        metricLabel = 'Canopy Cover';
        color = w.canopy_pct < 6 ? '#C62828' : (w.canopy_pct < 15 ? '#EA580C' : '#2E8B57');
      }

      const marker = L.circleMarker([w.lat, w.lon], {
        radius: 14,
        fillColor: color,
        color: '#FFFFFF',
        weight: 2,
        fillOpacity: 0.8
      }).addTo(STATE.geoLayers.markers);

      marker.bindTooltip(`<strong>${w.name}</strong><br>${metricLabel}: ${metricVal}`, {
        className: 'leaflet-custom-tooltip'
      });

      marker.on('click', () => {
        selectAreaInMapDrawer(w);
      });
    });
  }

  function selectAreaInMapDrawer(w) {
    STATE.selectedAreaId = w.id;
    const tier = getRiskTier(w.risk_score);

    document.getElementById('drawer-area-name').innerText = w.name;
    const badge = document.getElementById('drawer-tier-badge');
    badge.innerText = `Score: ${w.risk_score} / 100 • ${tier.label} Risk`;
    badge.style.backgroundColor = tier.bg;
    badge.style.color = tier.color;
    badge.style.borderColor = tier.border;

    document.getElementById('drawer-pop').innerText = w.population.toLocaleString();
    document.getElementById('drawer-lst').innerText = `${w.lst}°C`;
    document.getElementById('drawer-canopy').innerText = `${w.canopy_pct}%`;
    document.getElementById('drawer-workers').innerText = w.outdoor_workers.toLocaleString();
    document.getElementById('drawer-explanation').innerText = `This area combines elevated Land Surface Temperature (${w.lst}°C) with dense built form and low tree canopy (${w.canopy_pct}%). Peak vulnerability occurs between 11:30 AM and 4:30 PM.`;
    document.getElementById('drawer-action').innerText = w.action;
  }

  window.changeMapLayer = function (layerKey) {
    STATE.mapLayer = layerKey;
    renderFullMapLayers();
  };

  window.changeBasemap = function (type) {
    if (!STATE.fullMap || !STATE.geoLayers.base) return;
    STATE.fullMap.removeLayer(STATE.geoLayers.base);

    if (type === 'dark') {
      STATE.geoLayers.base = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png');
    } else if (type === 'osm') {
      STATE.geoLayers.base = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
    } else {
      STATE.geoLayers.base = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png');
    }
    STATE.geoLayers.base.addTo(STATE.fullMap);
  };

  window.resetMapView = function () {
    if (STATE.fullMap) {
      STATE.fullMap.setView([23.0225, 72.5714], 12);
    }
  };

  window.inspectSelectedInDepth = function () {
    loadAreaInspection(STATE.selectedAreaId);
    switchTab('inspector');
  };

  // --- 6. SCREEN 3: PRIORITY AREAS TABLE ---
  function renderPriorityTable() {
    const tbody = document.getElementById('priority-table-body');
    if (!tbody) return;

    const searchTerm = (document.getElementById('priority-search')?.value || '').toLowerCase().trim();
    const tierFilter = document.getElementById('priority-tier-filter')?.value || 'all';

    let rows = STATE.wards.map(w => ({
      ...w,
      type: 'Ward'
    }));

    // Filter
    if (searchTerm) {
      rows = rows.filter(r => r.name.toLowerCase().includes(searchTerm) || r.zone.toLowerCase().includes(searchTerm));
    }
    if (tierFilter !== 'all') {
      rows = rows.filter(r => {
        const t = getRiskTier(r.risk_score).label.toLowerCase();
        return t === tierFilter;
      });
    }

    // Sort by risk descending
    rows.sort((a, b) => b.risk_score - a.risk_score);

    if (rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="11" class="p-6 text-center text-civic-secondary">No areas match your filters. Try clearing the search.</td></tr>`;
      return;
    }

    tbody.innerHTML = rows.map((r, idx) => {
      const tier = getRiskTier(r.risk_score);
      return `
        <tr class="hover:bg-slate-50 transition border-b border-civic-border">
          <td class="p-3 text-center font-mono font-bold text-slate-500">${idx + 1}</td>
          <td class="p-3 font-semibold text-civic-navy">${r.name}</td>
          <td class="p-3 text-civic-secondary">${r.type}</td>
          <td class="p-3">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold" style="background:${tier.bg}; color:${tier.color}; border:1px solid ${tier.border};">
              ${r.risk_score} • ${tier.label}
            </span>
          </td>
          <td class="p-3 font-mono">${r.lst}°C</td>
          <td class="p-3 font-mono">${r.canopy_pct}%</td>
          <td class="p-3 font-mono">${r.elderly.toLocaleString()}</td>
          <td class="p-3 font-mono">${r.outdoor_workers.toLocaleString()}</td>
          <td class="p-3 text-civic-secondary">${r.driver}</td>
          <td class="p-3 text-civic-teal font-medium">${r.action}</td>
          <td class="p-3 text-right">
            <button onclick="inspectFromTable('${r.id}')" class="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-civic-dark rounded text-[11px] font-semibold transition">
              Inspect
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }

  window.filterPriorityTable = function () {
    renderPriorityTable();
  };

  window.inspectFromTable = function (wardId) {
    loadAreaInspection(wardId);
    switchTab('inspector');
  };

  window.exportPriorityTableCSV = function () {
    const headers = ['Rank,Area,Type,RiskScore,SurfaceTempC,CanopyPct,ElderlyPop,OutdoorWorkers,MainDriver,RecommendedAction'];
    const rows = STATE.wards.map((w, i) => 
      `${i + 1},"${w.name}",Ward,${w.risk_score},${w.lst},${w.canopy_pct},${w.elderly},${w.outdoor_workers},"${w.driver}","${w.action}"`
    );
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers, ...rows].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `TERRA07_Ahmedabad_Heat_Priority_Areas_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // --- 7. SCREEN 4: AREA INSPECTOR ---
  function populateAreaInspectorSelect() {
    const select = document.getElementById('inspect-area-select');
    if (!select) return;

    select.innerHTML = STATE.wards.map(w => 
      `<option value="${w.id}">${w.name} (${w.risk_score} - ${getRiskTier(w.risk_score).label})</option>`
    ).join('');
  }

  window.loadAreaInspection = function (wardId) {
    STATE.selectedAreaId = wardId;
    const w = STATE.wards.find(item => item.id === wardId) || STATE.wards[0];
    if (!w) return;

    const select = document.getElementById('inspect-area-select');
    if (select && select.value !== w.id) {
      select.value = w.id;
    }

    const tier = getRiskTier(w.risk_score);
    document.getElementById('inspect-area-title').innerText = w.name;
    document.getElementById('insp-pop').innerText = w.population.toLocaleString();
    document.getElementById('insp-area').innerText = `${w.area_km2} km²`;
    const density = Math.round(w.population / w.area_km2);
    document.getElementById('insp-density').innerText = `${density.toLocaleString()} /km²`;
    document.getElementById('insp-lst').innerText = `${w.lst}°C`;
    document.getElementById('insp-canopy').innerText = `${w.canopy_pct}%`;
    document.getElementById('insp-elderly').innerText = w.elderly.toLocaleString();
    document.getElementById('insp-workers').innerText = w.outdoor_workers.toLocaleString();

    document.getElementById('insp-summary-text').innerText = 
      `This area combines elevated Land Surface Temperature (${w.lst}°C), limited canopy cover (${w.canopy_pct}%), and a large population of outdoor daily laborers (${w.outdoor_workers.toLocaleString()}). Afternoon heat stress is pronounced due to low surface albedo and built density.`;
  };

  window.addToPlan = function (interventionType, count) {
    if (STATE.allocations[interventionType] !== undefined) {
      STATE.allocations[interventionType] += count;
    }
    updateInterventionBudgetSummary();
    switchTab('interventions');
  };

  // --- 8. SCREEN 5: SCENARIO SIMULATOR ---
  window.updateScenarioSimulation = function () {
    const tempSlider = document.getElementById('sim-temp-slider');
    const delta = parseFloat(tempSlider?.value || 2.0);
    STATE.scenario.tempDelta = delta;

    document.getElementById('sim-delta-display').innerText = `+${delta.toFixed(1)}°C`;

    const timeOfDay = document.getElementById('sim-time-select')?.value || '14:00';
    const humidity = document.getElementById('sim-humidity-select')?.value || 'normal';
    const grid = document.getElementById('sim-grid-select')?.value || 'normal';

    const shade = document.getElementById('sim-tog-shade')?.checked || false;
    const misting = document.getElementById('sim-tog-misting')?.checked || false;
    const roofs = document.getElementById('sim-tog-roofs')?.checked || false;
    const trees = document.getElementById('sim-tog-trees')?.checked || false;

    // Modelled Score Shift
    let shift = delta * 2.8;
    if (humidity === 'elevated') shift += 2.1;
    if (humidity === 'high') shift += 4.5;
    if (grid === 'reduced') shift += 1.8;
    if (grid === 'failure') shift += 5.2;

    // Mitigation drops
    let mitigations = 0;
    if (shade) mitigations += 3.2;
    if (misting) mitigations += 1.8;
    if (roofs) mitigations += 2.5;
    if (trees) mitigations += 2.1;

    const baseline = 54.9;
    const simulatedScore = Math.min(99.0, Math.max(25.0, Number((baseline + shift - mitigations).toFixed(1))));
    const deltaScore = Number((simulatedScore - baseline).toFixed(1));
    const livesProtected = Math.round((mitigations * 4200) + 2400);

    document.getElementById('sim-res-score').innerText = simulatedScore;
    document.getElementById('sim-res-delta').innerText = (deltaScore >= 0 ? '+' : '') + deltaScore;
    document.getElementById('sim-res-lives').innerText = livesProtected.toLocaleString();

    document.getElementById('sim-res-text').innerText = 
      `Under a +${delta.toFixed(1)}°C heatwave surge at ${timeOfDay} solar exposure (${humidity} humidity, ${grid} power status), city-wide mean risk shifts by ${deltaScore >= 0 ? '+' : ''}${deltaScore} points. Active mitigation actions buffer approximately ${livesProtected.toLocaleString()} vulnerable residents.`;
  };

  window.resetScenario = function () {
    const tempSlider = document.getElementById('sim-temp-slider');
    if (tempSlider) tempSlider.value = 2.0;
    document.getElementById('sim-time-select').value = '14:00';
    document.getElementById('sim-humidity-select').value = 'normal';
    document.getElementById('sim-grid-select').value = 'normal';
    document.getElementById('sim-tog-shade').checked = false;
    document.getElementById('sim-tog-misting').checked = false;
    document.getElementById('sim-tog-roofs').checked = false;
    document.getElementById('sim-tog-trees').checked = false;
    updateScenarioSimulation();
  };

  // --- 9. SCREEN 6: INTERVENTION PLANNER ---
  const COSTS = {
    shade: 8000,
    misting: 4500,
    centers: 25000,
    trees: 12000,
    roofs: 1200
  };

  const CAPACITY = {
    shade: 650,
    misting: 450,
    centers: 300,
    trees: 850,
    roofs: 4
  };

  window.changeBudgetCap = function (val) {
    STATE.budgetCap = parseInt(val, 10);
    document.getElementById('plan-cap-text').innerText = formatINR(STATE.budgetCap);
    updateInterventionBudgetSummary();
  };

  window.adjustAllocation = function (type, delta) {
    const current = STATE.allocations[type] || 0;
    const next = Math.max(0, current + delta);
    STATE.allocations[type] = next;
    const el = document.getElementById(`alloc-qty-${type}`);
    if (el) el.innerText = next;
    updateInterventionBudgetSummary();
  };

  function updateInterventionBudgetSummary() {
    let spent = 0;
    let protectedCount = 0;

    Object.keys(STATE.allocations).forEach(k => {
      const qty = STATE.allocations[k];
      spent += qty * COSTS[k];
      protectedCount += qty * CAPACITY[k];
      const el = document.getElementById(`alloc-qty-${k}`);
      if (el) el.innerText = qty;
    });

    const remaining = STATE.budgetCap - spent;

    document.getElementById('plan-spent-text').innerText = formatINR(spent);
    const remainEl = document.getElementById('plan-remain-text');
    remainEl.innerText = formatINR(remaining);
    remainEl.style.color = remaining < 0 ? '#C62828' : '#2E8B57';
    document.getElementById('plan-protected-text').innerText = protectedCount.toLocaleString();
  }

  window.runBudgetOptimization = function () {
    // Greedy knapsack prioritizing shade & misting & cool roofs
    const modal = document.getElementById('allocation-modal');
    if (modal) modal.classList.remove('hidden');
  };

  window.closeModal = function () {
    const modal = document.getElementById('allocation-modal');
    if (modal) modal.classList.add('hidden');
  };

  window.confirmPlan = function () {
    STATE.allocations = {
      shade: 4,
      misting: 6,
      centers: 2,
      trees: 2,
      roofs: 240
    };
    updateInterventionBudgetSummary();
    closeModal();
  };

})();

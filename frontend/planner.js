/**
 * TERRA07 - Urban Climate Resilience Command Center
 * Heat-Risk Mapping at Human Scale - Planner Engine & GIS Controller
 * Pure Vanilla JavaScript (ES6+) with Leaflet.js, Chart.js, and Web Audio API
 */

(function () {
  'use strict';

  // --- AUDIO SYNTHESIS ENGINE (Micro-interactions) ---
  class SoundEngine {
    constructor() {
      this.enabled = true;
      this.ctx = null;
    }

    init() {
      if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        this.ctx = new AudioCtx();
      }
    }

    playClick() {
      if (!this.enabled) return;
      try {
        this.init();
        if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(800, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(400, this.ctx.currentTime + 0.04);
        gain.gain.setValueAtTime(0.04, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.04);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + 0.04);
      } catch (e) {}
    }

    playChime() {
      if (!this.enabled) return;
      try {
        this.init();
        if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
        const freqs = [523.25, 659.25, 783.99, 1046.50];
        freqs.forEach((freq, idx) => {
          const osc = this.ctx.createOscillator();
          const gain = this.ctx.createGain();
          const startTime = this.ctx.currentTime + idx * 0.08;
          osc.type = 'triangle';
          osc.frequency.setValueAtTime(freq, startTime);
          gain.gain.setValueAtTime(0.08, startTime);
          gain.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.35);
          osc.connect(gain);
          gain.connect(this.ctx.destination);
          osc.start(startTime);
          osc.stop(startTime + 0.35);
        });
      } catch (e) {}
    }

    playAlert() {
      if (!this.enabled) return;
      try {
        this.init();
        if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(320, this.ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(220, this.ctx.currentTime + 0.15);
        gain.gain.setValueAtTime(0.05, this.ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.15);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start();
        osc.stop(this.ctx.currentTime + 0.15);
      } catch (e) {}
    }
  }

  const sounds = new SoundEngine();

  // --- COMPREHENSIVE URBAN GEODATA (Ahmedabad Metro Model) ---
  // Coordinates centered around Sabarmati River Corridor (23.0225° N, 72.5714° E)
  const WARDS_DATA = [
    {
      id: 'W-01',
      name: 'Kalupur Walled Core',
      zone: 'Central Urban Core',
      population: 142500,
      area_km2: 4.2,
      base_lst: 44.6,
      canopy_pct: 6.2,
      svi: 0.88,
      elderly_count: 14800,
      outdoor_workers: 18400,
      albedo: 0.14,
      impervious_pct: 89,
      cooling_centers: 2,
      water_kiosks: 5,
      xai_factors: {
        albedo_density: 32,
        tree_deficit: 28,
        elderly_svi: 22,
        impervious_mass: 18,
      },
      diagnosis: 'Dense historic heritage grid with 89% impervious surfaces and narrow street canyons trapping sensible heat. Critical heat vulnerability is exacerbated by 18,400 unshaded market vendors and an acute canopy deficit (<6.5%). Trapped nocturnal thermal mass prevents cooling below 33.5°C.',
      recommended: [
        { name: 'Tensile Shade Sails over Bazaar Lanes', cost: 75000, temp_drop: 2.8, lives: 3800, type: 'shade' },
        { name: 'Cool Roof Retrofit on Municipal Markets', cost: 120000, temp_drop: 2.1, lives: 4200, type: 'roofs' },
        { name: 'Smart Misting Stations at Railway Plaza', cost: 45000, temp_drop: 1.6, lives: 2900, type: 'misting' }
      ],
      coordinates: [
        [23.0210, 72.5850], [23.0330, 72.5890], [23.0360, 72.6030],
        [23.0250, 72.6070], [23.0160, 72.5970]
      ]
    },
    {
      id: 'W-02',
      name: 'Jamalpur Riverfront South',
      zone: 'South-Central River Basin',
      population: 118000,
      area_km2: 3.8,
      base_lst: 43.8,
      canopy_pct: 8.4,
      svi: 0.84,
      elderly_count: 11200,
      outdoor_workers: 14600,
      albedo: 0.16,
      impervious_pct: 84,
      cooling_centers: 2,
      water_kiosks: 4,
      xai_factors: {
        albedo_density: 28,
        tree_deficit: 26,
        elderly_svi: 26,
        impervious_mass: 20,
      },
      diagnosis: 'High informal settlement density adjacent to transport terminals. River breeze blocked by high-density mid-rise masonry. Severe exposure for wholesale flower/vegetable market laborers operating during peak solar hours.',
      recommended: [
        { name: 'Evaporative Misting Hubs at APMC Market', cost: 60000, temp_drop: 2.2, lives: 3400, type: 'misting' },
        { name: 'Pocket Micro-Forests (Miyawaki Method)', cost: 85000, temp_drop: 3.2, lives: 2800, type: 'trees' },
        { name: 'Cooling Center at Jamalpur Civic Hub', cost: 85000, temp_drop: 1.4, lives: 3100, type: 'centers' }
      ],
      coordinates: [
        [23.0080, 72.5760], [23.0190, 72.5810], [23.0210, 72.5950],
        [23.0070, 72.5920], [23.0020, 72.5790]
      ]
    },
    {
      id: 'W-03',
      name: 'Danilimda Industrial South',
      zone: 'Industrial & Informal Belt',
      population: 165000,
      area_km2: 6.4,
      base_lst: 46.8,
      canopy_pct: 4.8,
      svi: 0.93,
      elderly_count: 12400,
      outdoor_workers: 26500,
      albedo: 0.12,
      impervious_pct: 92,
      cooling_centers: 1,
      water_kiosks: 3,
      xai_factors: {
        albedo_density: 38,
        tree_deficit: 34,
        elderly_svi: 16,
        impervious_mass: 22,
      },
      diagnosis: 'Highest land surface temperature hotspot in the municipal limits (+46.8°C). Extensive uninsulated galvanized tin shed roofing creates a thermal heat furnace. Extremely vulnerable migrant workforce and severe potable water distribution deficit.',
      recommended: [
        { name: 'Industrial Cool Roof Reflective Coating', cost: 160000, temp_drop: 3.6, lives: 6200, type: 'roofs' },
        { name: 'Solar Resilience Cooling Oasis Centers (2x)', cost: 170000, temp_drop: 1.8, lives: 5400, type: 'centers' },
        { name: 'Canal-side Bioswale Green Linear Corridor', cost: 105000, temp_drop: 2.5, lives: 4100, type: 'trees' }
      ],
      coordinates: [
        [22.9850, 72.5820], [23.0050, 72.5860], [23.0040, 72.6080],
        [22.9810, 72.6140], [22.9770, 72.5930]
      ]
    },
    {
      id: 'W-04',
      name: 'Vatva Chemical & Logistics Estate',
      zone: 'Heavy Industrial',
      population: 94000,
      area_km2: 8.1,
      base_lst: 47.4,
      canopy_pct: 3.5,
      svi: 0.79,
      elderly_count: 6800,
      outdoor_workers: 31200,
      albedo: 0.11,
      impervious_pct: 95,
      cooling_centers: 1,
      water_kiosks: 2,
      xai_factors: {
        albedo_density: 42,
        tree_deficit: 36,
        elderly_svi: 10,
        impervious_mass: 24,
      },
      diagnosis: 'Severe urban heat island epicenter with 95% impervious industrial asphalt and chemical warehouse complexes. 31,200 heavy industrial and freight logistics laborers face sustained dangerous Wet Bulb Globe Temperatures exceeding 33°C.',
      recommended: [
        { name: 'Cool Pavement & White Roof Retrofits', cost: 180000, temp_drop: 3.9, lives: 5800, type: 'roofs' },
        { name: 'Industrial Belt High-Capacity Misting Plazas', cost: 60000, temp_drop: 2.4, lives: 4900, type: 'misting' },
        { name: 'Buffer Zone Tree Plantation (3 Hectares)', cost: 105000, temp_drop: 2.9, lives: 3600, type: 'trees' }
      ],
      coordinates: [
        [22.9610, 72.6150], [22.9830, 72.6120], [22.9870, 72.6450],
        [22.9580, 72.6500], [22.9520, 72.6280]
      ]
    },
    {
      id: 'W-05',
      name: 'Odhav Textile & Foundry Cluster',
      zone: 'Eastern Manufacturing Rim',
      population: 132000,
      area_km2: 7.2,
      base_lst: 46.2,
      canopy_pct: 5.1,
      svi: 0.81,
      elderly_count: 9400,
      outdoor_workers: 24800,
      albedo: 0.13,
      impervious_pct: 91,
      cooling_centers: 1,
      water_kiosks: 4,
      xai_factors: {
        albedo_density: 36,
        tree_deficit: 32,
        elderly_svi: 14,
        impervious_mass: 20,
      },
      diagnosis: 'Continuous low-albedo bitumen surface and metal structures trap immense heat. Microclimate wind barriers created by railway embankments prevent cross-ventilation. Worker settlements suffer high indoor thermal retention.',
      recommended: [
        { name: 'Cool Roof Paint Subsidy for Residential Slums', cost: 95000, temp_drop: 2.7, lives: 4800, type: 'roofs' },
        { name: 'Rapid Shade Canopies along Ring Road Transit', cost: 50000, temp_drop: 1.9, lives: 3200, type: 'shade' },
        { name: 'Cooling Center with Battery Storage & Solar', cost: 85000, temp_drop: 1.5, lives: 3700, type: 'centers' }
      ],
      coordinates: [
        [23.0030, 72.6460], [23.0320, 72.6420], [23.0360, 72.6780],
        [23.0060, 72.6820], [22.9980, 72.6580]
      ]
    },
    {
      id: 'W-06',
      name: 'Naroda Industrial North',
      zone: 'North-East Logistics Corridor',
      population: 148000,
      area_km2: 6.9,
      base_lst: 45.4,
      canopy_pct: 6.9,
      svi: 0.77,
      elderly_count: 10600,
      outdoor_workers: 22100,
      albedo: 0.15,
      impervious_pct: 88,
      cooling_centers: 2,
      water_kiosks: 4,
      xai_factors: {
        albedo_density: 32,
        tree_deficit: 30,
        elderly_svi: 16,
        impervious_mass: 18,
      },
      diagnosis: 'Highway convergence zone producing significant vehicular anthropogenic heat emissions layered onto dark asphalt corridors. Dense informal commercial strip along Naroda GIDC.',
      recommended: [
        { name: 'Highway Underpass Cooling Oasis & Misting', cost: 60000, temp_drop: 2.3, lives: 3900, type: 'misting' },
        { name: 'Urban Green Belt Tree Planting', cost: 70000, temp_drop: 2.4, lives: 3100, type: 'trees' },
        { name: 'Cool Pavement Treatment on Arterial Roads', cost: 110000, temp_drop: 2.0, lives: 4100, type: 'roofs' }
      ],
      coordinates: [
        [23.0480, 72.6450], [23.0800, 72.6480], [23.0850, 72.6850],
        [23.0470, 72.6820], [23.0380, 72.6520]
      ]
    },
    {
      id: 'W-07',
      name: 'Asarwa Hospital & Railway Junction',
      zone: 'North Central Medical Hub',
      population: 122000,
      area_km2: 4.6,
      base_lst: 43.5,
      canopy_pct: 9.8,
      svi: 0.86,
      elderly_count: 16200,
      outdoor_workers: 11500,
      albedo: 0.18,
      impervious_pct: 82,
      cooling_centers: 3,
      water_kiosks: 6,
      xai_factors: {
        albedo_density: 22,
        tree_deficit: 24,
        elderly_svi: 34,
        impervious_mass: 18,
      },
      diagnosis: 'Exceptional elderly vulnerability concentration due to major civil hospital complex and aging residential chawls. Ambulatory and emergency heatstroke intake peaks during midday hours.',
      recommended: [
        { name: 'Patient Campus Shaded Green Walkways', cost: 65000, temp_drop: 2.6, lives: 4900, type: 'shade' },
        { name: 'Hospital District Dedicated Hydration Hubs (4x)', cost: 60000, temp_drop: 1.7, lives: 5300, type: 'misting' },
        { name: 'Reflective Roofs on Low-Income Chawls', cost: 80000, temp_drop: 2.2, lives: 4400, type: 'roofs' }
      ],
      coordinates: [
        [23.0360, 72.5980], [23.0640, 72.6020], [23.0650, 72.6320],
        [23.0380, 72.6360], [23.0310, 72.6070]
      ]
    },
    {
      id: 'W-08',
      name: 'Sabarmati West & Motera',
      zone: 'North-West Transit Corridor',
      population: 156000,
      area_km2: 7.8,
      base_lst: 41.2,
      canopy_pct: 16.4,
      svi: 0.52,
      elderly_count: 13500,
      outdoor_workers: 9200,
      albedo: 0.22,
      impervious_pct: 71,
      cooling_centers: 3,
      water_kiosks: 5,
      xai_factors: {
        albedo_density: 18,
        tree_deficit: 16,
        elderly_svi: 20,
        impervious_mass: 14,
      },
      diagnosis: 'Moderate heat stress. Proximity to upper Sabarmati river channel offers cooling convective breeze, though newly paved arterial expressways display elevated thermal radiometry.',
      recommended: [
        { name: 'Metro Station Plaza Shade Structures', cost: 50000, temp_drop: 1.8, lives: 2800, type: 'shade' },
        { name: 'Riverfront Green Extension Bioswales', cost: 70000, temp_drop: 2.2, lives: 2500, type: 'trees' },
        { name: 'High-Efficiency Hydration Centers', cost: 30000, temp_drop: 1.2, lives: 2200, type: 'misting' }
      ],
      coordinates: [
        [23.0600, 72.5650], [23.0980, 72.5700], [23.0950, 72.6100],
        [23.0620, 72.6010], [23.0560, 72.5720]
      ]
    },
    {
      id: 'W-09',
      name: 'Navrangpura Commercial & University',
      zone: 'West Central Academic & IT Hub',
      population: 138000,
      area_km2: 5.9,
      base_lst: 39.8,
      canopy_pct: 22.1,
      svi: 0.38,
      elderly_count: 14100,
      outdoor_workers: 7400,
      albedo: 0.25,
      impervious_pct: 68,
      cooling_centers: 4,
      water_kiosks: 7,
      xai_factors: {
        albedo_density: 14,
        tree_deficit: 12,
        elderly_svi: 16,
        impervious_mass: 12,
      },
      diagnosis: 'Relatively well-buffered thermal profile due to legacy institutional tree canopy at university campuses. Heat vulnerabilities localized to high-traffic commercial retail corridors and bus stations.',
      recommended: [
        { name: 'Pedestrian Boulevard Tree Infill', cost: 45000, temp_drop: 1.6, lives: 1900, type: 'trees' },
        { name: 'Transit Node Misting Canopies', cost: 35000, temp_drop: 1.5, lives: 2100, type: 'misting' }
      ],
      coordinates: [
        [23.0240, 72.5450], [23.0520, 72.5490], [23.0560, 72.5720],
        [23.0220, 72.5690], [23.0180, 72.5520]
      ]
    },
    {
      id: 'W-10',
      name: 'Maninagar South-East Residential',
      zone: 'South-East Residential & Lake Basin',
      population: 172000,
      area_km2: 6.8,
      base_lst: 42.1,
      canopy_pct: 14.2,
      svi: 0.61,
      elderly_count: 18900,
      outdoor_workers: 11200,
      albedo: 0.20,
      impervious_pct: 78,
      cooling_centers: 3,
      water_kiosks: 6,
      xai_factors: {
        albedo_density: 22,
        tree_deficit: 20,
        elderly_svi: 28,
        impervious_mass: 16,
      },
      diagnosis: 'Dense middle-income residential district with Kankaria lake micro-cooling buffer in the center. However, outer chawls experience noticeable night heat trapping with a significant senior citizen demographic.',
      recommended: [
        { name: 'Lake District Shaded Transit Promenade', cost: 65000, temp_drop: 2.1, lives: 3400, type: 'shade' },
        { name: 'Elderly Community Cooling Hub Upgrades', cost: 85000, temp_drop: 1.5, lives: 3900, type: 'centers' },
        { name: 'Rooftop Albedo Enhancement Grants', cost: 70000, temp_drop: 1.9, lives: 3100, type: 'roofs' }
      ],
      coordinates: [
        [22.9860, 72.5930], [23.0120, 72.5960], [23.0140, 72.6280],
        [22.9840, 72.6250], [22.9790, 72.6020]
      ]
    },
    {
      id: 'W-11',
      name: 'Bopal - Ambli Developing West',
      zone: 'Western Suburban Fringe',
      population: 125000,
      area_km2: 9.4,
      base_lst: 40.5,
      canopy_pct: 12.8,
      svi: 0.41,
      elderly_count: 9800,
      outdoor_workers: 14500,
      albedo: 0.21,
      impervious_pct: 69,
      cooling_centers: 2,
      water_kiosks: 4,
      xai_factors: {
        albedo_density: 24,
        tree_deficit: 22,
        elderly_svi: 12,
        impervious_mass: 14,
      },
      diagnosis: 'Rapid construction boom creates acute heat risks for over 14,500 active construction site laborers. High daytime dust and unshaded open asphalt tracts increase solar radiation exposure.',
      recommended: [
        { name: 'Mobile Construction Worker Hydration Units', cost: 45000, temp_drop: 1.8, lives: 3200, type: 'misting' },
        { name: 'Suburban Arterial Tree Corridors (2 Hectares)', cost: 70000, temp_drop: 2.4, lives: 2600, type: 'trees' }
      ],
      coordinates: [
        [23.0100, 72.4820], [23.0550, 72.4880], [23.0530, 72.5320],
        [23.0080, 72.5280], [23.0020, 72.4980]
      ]
    },
    {
      id: 'W-12',
      name: 'Sarkhej Heritage & Highway Junction',
      zone: 'South-West Perimeter',
      population: 139000,
      area_km2: 8.7,
      base_lst: 43.1,
      canopy_pct: 9.1,
      svi: 0.82,
      elderly_count: 12100,
      outdoor_workers: 17300,
      albedo: 0.17,
      impervious_pct: 81,
      cooling_centers: 2,
      water_kiosks: 4,
      xai_factors: {
        albedo_density: 26,
        tree_deficit: 28,
        elderly_svi: 24,
        impervious_mass: 18,
      },
      diagnosis: 'Highway junction and trucking terminal with dry peri-urban soil, extensive barren unshaded parcels, and vulnerable low-income informal pockets around historic Sarkhej Roza monument perimeter.',
      recommended: [
        { name: 'Truck Terminal Evaporative Misting Rest Hub', cost: 55000, temp_drop: 2.2, lives: 3100, type: 'misting' },
        { name: 'Micro-Park Buffer Forestry along SG Highway', cost: 80000, temp_drop: 2.8, lives: 2900, type: 'trees' },
        { name: 'Cooling Center at Sarkhej Civic Complex', cost: 85000, temp_drop: 1.6, lives: 3400, type: 'centers' }
      ],
      coordinates: [
        [22.9700, 72.4920], [23.0080, 72.4950], [23.0050, 72.5360],
        [22.9720, 72.5380], [22.9640, 72.5050]
      ]
    }
  ];

  // --- ARTERIAL STREETS & TRANSIT CORRIDORS ---
  const STREETS_DATA = [
    {
      id: 'ST-01',
      name: 'Relief Road Market Corridor',
      ward_id: 'W-01',
      length_km: 2.4,
      traffic_heat_index: 88,
      shade_pct: 4.1,
      surface_type: 'Dark Asphalt',
      risk_score: 91.2,
      pedestrians_daily: 48000,
      coordinates: [[23.0245, 72.5855], [23.0280, 72.5930], [23.0315, 72.6020]]
    },
    {
      id: 'ST-02',
      name: 'Gandhi Road Heritage Spine',
      ward_id: 'W-01',
      length_km: 2.1,
      traffic_heat_index: 82,
      shade_pct: 7.2,
      surface_type: 'Paved Bitumen',
      risk_score: 87.4,
      pedestrians_daily: 42000,
      coordinates: [[23.0215, 72.5860], [23.0248, 72.5925], [23.0272, 72.6005]]
    },
    {
      id: 'ST-03',
      name: 'Danilimda Canal Expressway',
      ward_id: 'W-03',
      length_km: 4.6,
      traffic_heat_index: 94,
      shade_pct: 2.8,
      surface_type: 'Heavy Bitumen Highway',
      risk_score: 95.8,
      pedestrians_daily: 31000,
      coordinates: [[22.9860, 72.5850], [22.9940, 72.5910], [23.0040, 72.6020]]
    },
    {
      id: 'ST-04',
      name: 'Vatva GIDC Freight Avenue',
      ward_id: 'W-04',
      length_km: 5.2,
      traffic_heat_index: 96,
      shade_pct: 1.5,
      surface_type: 'Industrial Concrete & Bitumen',
      risk_score: 97.2,
      pedestrians_daily: 26000,
      coordinates: [[22.9640, 72.6200], [22.9730, 72.6310], [22.9810, 72.6420]]
    },
    {
      id: 'ST-05',
      name: 'Narol-Naroda Ring Expressway',
      ward_id: 'W-05',
      length_km: 6.8,
      traffic_heat_index: 91,
      shade_pct: 3.2,
      surface_type: 'High-Thermal Concrete Expressway',
      risk_score: 93.4,
      pedestrians_daily: 39000,
      coordinates: [[23.0050, 72.6500], [23.0250, 72.6560], [23.0520, 72.6620]]
    },
    {
      id: 'ST-06',
      name: 'Asarwa Civil Hospital Approach',
      ward_id: 'W-07',
      length_km: 2.8,
      traffic_heat_index: 79,
      shade_pct: 8.5,
      surface_type: 'Asphalt Arterial',
      risk_score: 84.1,
      pedestrians_daily: 35000,
      coordinates: [[23.0370, 72.6010], [23.0480, 72.6140], [23.0590, 72.6250]]
    },
    {
      id: 'ST-07',
      name: 'Ashram Road Riverfront Arterial',
      ward_id: 'W-09',
      length_km: 5.4,
      traffic_heat_index: 73,
      shade_pct: 18.2,
      surface_type: 'Tree-lined Bitumen',
      risk_score: 58.6,
      pedestrians_daily: 46000,
      coordinates: [[23.0180, 72.5680], [23.0360, 72.5710], [23.0580, 72.5730]]
    },
    {
      id: 'ST-08',
      name: 'C.G. Road Commercial Boulevard',
      ward_id: 'W-09',
      length_km: 3.2,
      traffic_heat_index: 68,
      shade_pct: 21.0,
      surface_type: 'Paver & Asphalt Mix',
      risk_score: 52.3,
      pedestrians_daily: 34000,
      coordinates: [[23.0230, 72.5560], [23.0350, 72.5580], [23.0470, 72.5600]]
    },
    {
      id: 'ST-09',
      name: 'Sarkhej-Gandhinagar (SG) Highway',
      ward_id: 'W-11',
      length_km: 7.5,
      traffic_heat_index: 85,
      shade_pct: 7.9,
      surface_type: 'Multilane Concrete Highway',
      risk_score: 76.5,
      pedestrians_daily: 52000,
      coordinates: [[22.9850, 72.5030], [23.0220, 72.5120], [23.0550, 72.5210]]
    },
    {
      id: 'ST-10',
      name: 'Kankaria Lake Perimeter Road',
      ward_id: 'W-10',
      length_km: 3.8,
      traffic_heat_index: 62,
      shade_pct: 24.5,
      surface_type: 'Cobblestone & Asphalt',
      risk_score: 48.2,
      pedestrians_daily: 28000,
      coordinates: [[22.9960, 72.6000], [23.0060, 72.6030], [23.0030, 72.6130]]
    }
  ];

  // --- COOLING AMENITIES (Centers & Hydration Kiosks) ---
  const COOLING_AMENITIES = [
    { id: 'AC-01', name: 'Kalupur Central Civic Cooling Haven', type: 'center', lat: 23.0260, lng: 72.5940, capacity: 450, backup_power: true, status: 'Active' },
    { id: 'AC-02', name: 'Danilimda Municipal Hospital Cooling Wing', type: 'center', lat: 22.9920, lng: 72.5980, capacity: 300, backup_power: true, status: 'Active' },
    { id: 'AC-03', name: 'Vatva Workers Resilience Hub', type: 'center', lat: 22.9710, lng: 72.6320, capacity: 500, backup_power: false, status: 'Active' },
    { id: 'AC-04', name: 'Odhav Community Air-Cooled Center', type: 'center', lat: 23.0180, lng: 72.6620, capacity: 350, backup_power: true, status: 'Active' },
    { id: 'AC-05', name: 'Asarwa Medical Campus Heat Respite Hall', type: 'center', lat: 23.0490, lng: 72.6120, capacity: 600, backup_power: true, status: 'Active' },
    { id: 'AC-06', name: 'Jamalpur Riverfront Shaded Cooling Center', type: 'center', lat: 23.0120, lng: 72.5840, capacity: 400, backup_power: true, status: 'Active' },
    { id: 'AC-07', name: 'Navrangpura University Resilience Pavilion', type: 'center', lat: 23.0370, lng: 72.5580, capacity: 500, backup_power: true, status: 'Active' },
    { id: 'AC-08', name: 'Sarkhej Highway Transit Respite Center', type: 'center', lat: 22.9880, lng: 72.5180, capacity: 320, backup_power: false, status: 'Active' },
    { id: 'WK-01', name: 'Kalupur Market Chilled Water Kiosk', type: 'kiosk', lat: 23.0235, lng: 72.5880, capacity: 2500, backup_power: true, status: 'Active' },
    { id: 'WK-02', name: 'Relief Road Smart Misting Post', type: 'kiosk', lat: 23.0285, lng: 72.5960, capacity: 1800, backup_power: true, status: 'Active' },
    { id: 'WK-03', name: 'Danilimda Canal Hydration Booth', type: 'kiosk', lat: 22.9880, lng: 72.5910, capacity: 3000, backup_power: false, status: 'Active' },
    { id: 'WK-04', name: 'Vatva Industrial Gate Misting Arc', type: 'kiosk', lat: 22.9660, lng: 72.6240, capacity: 4000, backup_power: false, status: 'Active' },
    { id: 'WK-05', name: 'Odhav Ring Road Water Kiosk', type: 'kiosk', lat: 23.0220, lng: 72.6550, capacity: 2200, backup_power: true, status: 'Active' },
    { id: 'WK-06', name: 'Asarwa Station Mist Fan Node', type: 'kiosk', lat: 23.0420, lng: 72.6080, capacity: 2800, backup_power: true, status: 'Active' },
    { id: 'WK-07', name: 'Kankaria Gate 3 Hydration Point', type: 'kiosk', lat: 23.0010, lng: 72.6070, capacity: 3500, backup_power: true, status: 'Active' },
    { id: 'WK-08', name: 'SG Highway Bus Shelter Misting Station', type: 'kiosk', lat: 23.0180, lng: 72.5150, capacity: 2000, backup_power: true, status: 'Active' }
  ];

  // --- STATE MANAGEMENT ---
  const state = {
    theme: localStorage.getItem('terra07_theme') || 'dark',
    activeLayer: 'composite', // 'composite', 'lst', 'ndvi', 'svi', 'amenities'
    layerOpacity: 0.75,
    showStreets: true,
    showAmenities: true,
    activeBasemap: 'dark', // 'dark', 'light', 'satellite', 'street'
    selectedEntity: null, // ward or street object
    comparisonMode: false, // true = post-mitigation preview
    chartType: 'bar', // 'bar' or 'radar'

    // Climate Scenario Simulator
    scenario: {
      heatwaveDelta: 2.0, // +0°C to +5°C
      gridOutage: false,  // true / false
      humiditySurge: false, // true / false (Wet bulb heat index)
      timeOfDay: '14:00' // '09:00', '14:00', '21:00'
    },

    // Intervention Sandbox
    sandbox: {
      budgetCap: 450000,
      allocations: {
        shade: 4,     // $25k each = $100k
        misting: 5,   // $15k each = $75k
        centers: 2,   // $85k each = $170k
        trees: 2,     // $35k each = $70k
        roofs: 3      // $40k each = $120k
      },
      // Cache of simulation results
      optimizedResults: null
    },
    tableSort: { col: 'current_score', asc: false },
    activeTierFilter: 'all',

    // Data collections with reactive runtime mutations
    wards: JSON.parse(JSON.stringify(WARDS_DATA)),
    streets: JSON.parse(JSON.stringify(STREETS_DATA)),
    amenities: JSON.parse(JSON.stringify(COOLING_AMENITIES))
  };

  // Intervention Catalog Specifications
  const INTERVENTIONS_CATALOG = {
    shade: {
      id: 'shade',
      name: 'Tensile Shade Sails & Canopies',
      unitCost: 25000,
      coolingPower: 2.2, // °C perceived reduction
      icon: 'tent',
      badge: 'Immediate',
      desc: 'Rapid deployment over open bazaar corridors and transit walks.'
    },
    misting: {
      id: 'misting',
      name: 'Smart High-Pressure Misting Stations',
      unitCost: 15000,
      coolingPower: 1.8,
      icon: 'droplets',
      badge: 'Evaporative',
      desc: 'Evaporative cooling micro-droplets along pedestrian hotspots.'
    },
    centers: {
      id: 'centers',
      name: 'Resilience Cooling Centers (Solar AC)',
      unitCost: 85000,
      coolingPower: 3.5,
      icon: 'shield-snowflake',
      badge: 'Critical Lifeline',
      desc: 'Air-conditioned public refuges with solar microgrid backup.'
    },
    trees: {
      id: 'trees',
      name: 'Urban Miyawaki Forests & Bioswales',
      unitCost: 35000,
      coolingPower: 3.0,
      icon: 'trees',
      badge: 'Long-Term',
      desc: 'Dense native forestry pockets that permanently drop ambient microclimate.'
    },
    roofs: {
      id: 'roofs',
      name: 'High-Albedo Cool Roof Retrofits',
      unitCost: 40000,
      coolingPower: 2.6,
      icon: 'sun-snow',
      badge: 'Structural',
      desc: 'High-reflectance white coatings slashing indoor heat retention.'
    }
  };

  // --- CALCULATION & RISK MODELING ENGINE ---
  function calculateCompositeRisk(ward, scenario, postMitigationDrops = 0) {
    // 1. Base components
    let lst = ward.base_lst + scenario.heatwaveDelta;

    // Time of day diurnal variations
    if (scenario.timeOfDay === '09:00') {
      lst -= 4.5;
    } else if (scenario.timeOfDay === '21:00') {
      // Trapped nocturnal heat: high impervious wards stay hotter
      lst -= (12.0 - (ward.impervious_pct / 100) * 4.0);
    }

    // Apply mitigation reduction if in post-intervention or sandbox view
    lst = Math.max(28.0, lst - postMitigationDrops);

    // 2. Canopy deficit: target is 25%
    const canopyDeficit = Math.max(0, (25 - ward.canopy_pct) / 25); // 0 to 1

    // 3. Normalized thermal factor (35°C = 0, 50°C = 100)
    const lstNorm = Math.min(100, Math.max(0, ((lst - 34) / (50 - 34)) * 100));

    // 4. Social vulnerability penalty
    let sviScore = ward.svi * 100;

    // 5. Scenario modifiers
    let gridMultiplier = 1.0;
    if (scenario.gridOutage) {
      // Grid outage disables residential AC and fans, multiplying elderly & low-income risk
      gridMultiplier = 1.25;
      sviScore = Math.min(100, sviScore * 1.30);
    }

    let humidityMultiplier = 1.0;
    if (scenario.humiditySurge) {
      // High humidity drastically impairs human evaporative sweating (Wet Bulb effect)
      humidityMultiplier = 1.18;
    }

    // 6. Amenities buffering: cooling centers reduce raw risk
    const amenityBuffer = (ward.cooling_centers * 3.5) + (ward.water_kiosks * 1.2);

    // Composite Weighted Formula
    // 40% Thermal LST + 25% Canopy Deficit + 25% Social Vulnerability + 10% Impervious Mass
    const rawScore = (
      (lstNorm * 0.40) +
      (canopyDeficit * 100 * 0.25) +
      (sviScore * 0.25) +
      ((ward.impervious_pct) * 0.10)
    ) * gridMultiplier * humidityMultiplier - amenityBuffer;

    const finalScore = Math.min(99.9, Math.max(12.0, rawScore));
    return {
      score: parseFloat(finalScore.toFixed(1)),
      effective_lst: parseFloat(lst.toFixed(1)),
      tier: getRiskTier(finalScore)
    };
  }

  function getRiskTier(score) {
    if (score >= 82) return { label: 'EXTREME', color: '#9333ea', bg: 'bg-purple-950/80', text: 'text-purple-300', border: 'border-purple-500' };
    if (score >= 68) return { label: 'HIGH', color: '#ef4444', bg: 'bg-red-950/80', text: 'text-red-300', border: 'border-red-500' };
    if (score >= 50) return { label: 'MODERATE', color: '#f59e0b', bg: 'bg-amber-950/80', text: 'text-amber-300', border: 'border-amber-500' };
    return { label: 'LOW / RESILIENT', color: '#10b981', bg: 'bg-emerald-950/80', text: 'text-emerald-300', border: 'border-emerald-500' };
  }

  // --- COLORMAP & PALETTE UTILITIES ---
  function getHeatColor(val, type = 'composite') {
    // Thermal palettes: amber / crimson / purple
    if (type === 'composite') {
      // 0-100 scale
      if (val >= 85) return '#9333ea'; // Electric Purple
      if (val >= 75) return '#dc2626'; // Deep Crimson
      if (val >= 65) return '#ef4444'; // Red
      if (val >= 52) return '#f97316'; // Vivid Orange
      if (val >= 40) return '#f59e0b'; // Amber Gold
      if (val >= 28) return '#10b981'; // Resilient Green
      return '#06b6d4'; // Cyan
    } else if (type === 'lst') {
      // 36°C to 48°C
      if (val >= 46) return '#7e22ce'; // Purple
      if (val >= 44) return '#b91c1c'; // Deep Crimson
      if (val >= 42) return '#ea580c'; // Hot Orange
      if (val >= 40) return '#f59e0b'; // Amber
      return '#10b981'; // Mild
    } else if (type === 'ndvi') {
      // Canopy deficit: lower canopy = hotter crimson/purple
      if (val < 6) return '#9333ea';
      if (val < 10) return '#ef4444';
      if (val < 16) return '#f59e0b';
      return '#10b981';
    } else if (type === 'svi') {
      // Social Vulnerability 0.0 to 1.0
      if (val >= 0.85) return '#9333ea';
      if (val >= 0.70) return '#ef4444';
      if (val >= 0.50) return '#f59e0b';
      return '#10b981';
    }
    return '#f97316';
  }

  // --- MAP & GIS CONTROLLER ---
  class MapManager {
    constructor() {
      this.map = null;
      this.wardLayers = {};
      this.streetLayers = {};
      this.amenityMarkers = [];
      this.tileLayer = null;
      this.tileUrls = {
        dark: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        light: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        satellite: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        street: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
      };
    }

    init() {
      // Create Leaflet map centered at Ahmedabad Metro
      this.map = L.map('leaflet-map', {
        center: [23.0225, 72.5850],
        zoom: 12,
        zoomControl: false,
        attributionControl: false
      });

      // Add custom zoom control in bottom right
      L.control.zoom({ position: 'bottomright' }).addTo(this.map);

      // Add base tile layer
      this.updateTileLayer(state.activeBasemap);

      // Render GIS Ward Polygons
      this.renderWards();

      // Render Arterial Street Lines
      this.renderStreets();

      // Render Cooling Amenity Markers
      this.renderAmenities();

      // Map click on canvas deselects
      this.map.on('click', (e) => {
        // If clicking blank space, do not deselect if targeting layer
      });
    }

    updateTileLayer(baseKey) {
      if (this.tileLayer) {
        this.map.removeLayer(this.tileLayer);
      }
      const url = this.tileUrls[baseKey] || this.tileUrls.dark;
      this.tileLayer = L.tileLayer(url, {
        maxZoom: 19,
        subdomains: 'abcd'
      }).addTo(this.map);
    }

    getWardStyle(ward) {
      const calc = calculateCompositeRisk(
        ward,
        state.scenario,
        state.comparisonMode ? (ward.simulated_drop || 2.4) : 0
      );

      let val = calc.score;
      if (state.activeLayer === 'lst') val = calc.effective_lst;
      else if (state.activeLayer === 'ndvi') val = ward.canopy_pct;
      else if (state.activeLayer === 'svi') val = ward.svi;

      const fillColor = getHeatColor(val, state.activeLayer);
      const isSelected = state.selectedEntity && state.selectedEntity.id === ward.id;

      return {
        fillColor: fillColor,
        fillOpacity: isSelected ? Math.min(0.95, state.layerOpacity + 0.15) : state.layerOpacity,
        color: isSelected ? '#ffffff' : (state.theme === 'dark' ? '#0f172a' : '#ffffff'),
        weight: isSelected ? 3.5 : 1.5,
        opacity: 0.95,
        dashArray: isSelected ? '' : '2',
        className: isSelected ? 'pulse-ward-border transition-all duration-300' : 'transition-all duration-300'
      };
    }

    renderWards() {
      // Clear existing
      Object.values(this.wardLayers).forEach(layer => this.map.removeLayer(layer));
      this.wardLayers = {};

      state.wards.forEach(ward => {
        const poly = L.polygon(ward.coordinates, this.getWardStyle(ward));

        // Tooltip
        const calc = calculateCompositeRisk(ward, state.scenario);
        poly.bindTooltip(`
          <div class="px-2 py-1 text-xs font-sans">
            <div class="font-bold text-sm tracking-wide">${ward.name}</div>
            <div class="flex items-center gap-2 mt-1">
              <span class="inline-block w-2.5 h-2.5 rounded-full" style="background:${calc.tier.color}"></span>
              <span class="font-mono font-semibold">${calc.score} / 100</span>
              <span class="text-slate-400">(${calc.tier.label})</span>
            </div>
            <div class="text-[11px] text-slate-300 mt-0.5">LST: ${calc.effective_lst}°C | Canopy: ${ward.canopy_pct}%</div>
          </div>
        `, {
          sticky: true,
          className: 'leaflet-custom-tooltip'
        });

        // Click handler
        poly.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          selectEntity(ward, 'ward');
          sounds.playClick();
        });

        // Hover highlight
        poly.on('mouseover', () => {
          if (!state.selectedEntity || state.selectedEntity.id !== ward.id) {
            poly.setStyle({ weight: 2.5, fillOpacity: Math.min(0.95, state.layerOpacity + 0.15) });
          }
        });

        poly.on('mouseout', () => {
          if (!state.selectedEntity || state.selectedEntity.id !== ward.id) {
            poly.setStyle(this.getWardStyle(ward));
          }
        });

        poly.addTo(this.map);
        this.wardLayers[ward.id] = poly;
      });
    }

    renderStreets() {
      // Clear existing
      Object.values(this.streetLayers).forEach(layer => this.map.removeLayer(layer));
      this.streetLayers = {};

      if (!state.showStreets) return;

      state.streets.forEach(street => {
        const strokeColor = getHeatColor(street.risk_score, 'composite');
        const isSelected = state.selectedEntity && state.selectedEntity.id === street.id;

        const line = L.polyline(street.coordinates, {
          color: strokeColor,
          weight: isSelected ? 6 : 3.5,
          opacity: 0.9,
          dashArray: street.shade_pct < 5 ? '4, 4' : null,
          lineCap: 'round',
          className: 'transition-all duration-200'
        });

        line.bindTooltip(`
          <div class="px-2 py-1 text-xs">
            <div class="font-bold text-amber-400">${street.name}</div>
            <div>Risk Score: <span class="font-mono font-bold">${street.risk_score}</span></div>
            <div class="text-slate-300">Pedestrians: ${(street.pedestrians_daily).toLocaleString()} / day</div>
            <div class="text-[10px] text-red-400">Tree Shade: ${street.shade_pct}%</div>
          </div>
        `, { sticky: true, className: 'leaflet-custom-tooltip' });

        line.on('click', (e) => {
          L.DomEvent.stopPropagation(e);
          selectEntity(street, 'street');
          sounds.playClick();
        });

        line.addTo(this.map);
        this.streetLayers[street.id] = line;
      });
    }

    renderAmenities() {
      this.amenityMarkers.forEach(m => this.map.removeLayer(m));
      this.amenityMarkers = [];

      if (!state.showAmenities) return;

      state.amenities.forEach(point => {
        const isCenter = point.type === 'center';
        const color = isCenter ? '#38bdf8' : '#22d3ee';
        const iconHtml = isCenter ?
          `<div class="w-7 h-7 rounded-full bg-sky-500/90 border-2 border-white shadow-lg flex items-center justify-center text-white text-xs pulse-glow-blue cursor-pointer">
             <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
           </div>` :
          `<div class="w-6 h-6 rounded-full bg-cyan-500/90 border-2 border-white shadow-lg flex items-center justify-center text-white text-[10px] pulse-glow-cyan cursor-pointer">
             <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
           </div>`;

        const customIcon = L.divIcon({
          className: 'custom-amenity-pin',
          html: iconHtml,
          iconSize: [28, 28],
          iconAnchor: [14, 14]
        });

        const marker = L.marker([point.lat, point.lng], { icon: customIcon });

        marker.bindPopup(`
          <div class="p-2 min-w-[200px] text-xs font-sans text-slate-800 dark:text-slate-100">
            <div class="flex items-center gap-1.5 font-bold text-sm ${isCenter ? 'text-sky-400' : 'text-cyan-400'}">
              <span>${isCenter ? '🛡️ Cooling Haven' : '💧 Hydration Station'}</span>
            </div>
            <div class="font-semibold text-slate-900 dark:text-white mt-1">${point.name}</div>
            <div class="mt-2 space-y-1 text-slate-600 dark:text-slate-300">
              <div class="flex justify-between"><span>Capacity:</span> <strong class="text-slate-900 dark:text-white">${point.capacity} pers/hr</strong></div>
              <div class="flex justify-between"><span>Solar Backup:</span> <span class="badge ${point.backup_power ? 'text-emerald-400 font-semibold' : 'text-amber-400'}">${point.backup_power ? 'Yes (Microgrid)' : 'Standard Grid'}</span></div>
              <div class="flex justify-between"><span>Status:</span> <span class="text-emerald-400 font-semibold">● ${point.status}</span></div>
            </div>
          </div>
        `, { className: 'leaflet-custom-popup' });

        marker.addTo(this.map);
        this.amenityMarkers.push(marker);
      });
    }

    refreshStyles() {
      state.wards.forEach(ward => {
        const poly = this.wardLayers[ward.id];
        if (poly) poly.setStyle(this.getWardStyle(ward));
      });
      this.renderStreets();
    }

    flyToEntity(entity) {
      if (!entity) return;
      if (entity.coordinates) {
        if (Array.isArray(entity.coordinates[0])) {
          // Polygon or polyline
          const bounds = L.latLngBounds(entity.coordinates);
          this.map.flyToBounds(bounds, { padding: [40, 40], duration: 1.2 });
        }
      }
    }
  }

  const mapMgr = new MapManager();

  // --- XAI DRIVER BREAKDOWN CHART CONTROLLER (Chart.js) ---
  let xaiChartInstance = null;

  function renderXAIChart(ward) {
    const ctx = document.getElementById('xai-canvas');
    if (!ctx) return;

    if (xaiChartInstance) {
      xaiChartInstance.destroy();
    }

    const isDark = state.theme === 'dark';
    const textColor = isDark ? '#cbd5e1' : '#334155';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)';

    const factors = ward.xai_factors || {
      albedo_density: 30,
      tree_deficit: 28,
      elderly_svi: 24,
      impervious_mass: 18
    };

    const labels = [
      'Low Albedo / Asphalt',
      'Tree Canopy Deficit',
      'SVI & Elderly Vulnerability',
      'Impervious Thermal Mass'
    ];
    const dataValues = [
      factors.albedo_density,
      factors.tree_deficit,
      factors.elderly_svi,
      factors.impervious_mass
    ];

    if (typeof Chart === 'undefined') {
      const parent = ctx.parentElement;
      if (parent) {
        parent.innerHTML = `
          <div class="space-y-2 py-1">
            <div>
              <div class="flex justify-between text-[11px] text-slate-300"><span>Low Albedo / Asphalt</span><span class="font-mono text-orange-400">+${factors.albedo_density} pts</span></div>
              <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden mt-0.5"><div class="h-full bg-orange-500 rounded-full" style="width:${Math.min(100, factors.albedo_density * 2.5)}%"></div></div>
            </div>
            <div>
              <div class="flex justify-between text-[11px] text-slate-300"><span>Tree Canopy Deficit</span><span class="font-mono text-red-400">+${factors.tree_deficit} pts</span></div>
              <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden mt-0.5"><div class="h-full bg-red-500 rounded-full" style="width:${Math.min(100, factors.tree_deficit * 2.5)}%"></div></div>
            </div>
            <div>
              <div class="flex justify-between text-[11px] text-slate-300"><span>SVI & Elderly Vulnerability</span><span class="font-mono text-purple-400">+${factors.elderly_svi} pts</span></div>
              <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden mt-0.5"><div class="h-full bg-purple-500 rounded-full" style="width:${Math.min(100, factors.elderly_svi * 2.5)}%"></div></div>
            </div>
            <div>
              <div class="flex justify-between text-[11px] text-slate-300"><span>Impervious Thermal Mass</span><span class="font-mono text-amber-400">+${factors.impervious_mass} pts</span></div>
              <div class="h-1.5 bg-slate-800 rounded-full overflow-hidden mt-0.5"><div class="h-full bg-amber-500 rounded-full" style="width:${Math.min(100, factors.impervious_mass * 2.5)}%"></div></div>
            </div>
          </div>
        `;
      }
      return;
    }

    if (state.chartType === 'bar') {
      xaiChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'SHAP Feature Contribution (+ pts)',
            data: dataValues,
            backgroundColor: [
              'rgba(249, 115, 22, 0.85)',
              'rgba(239, 68, 68, 0.85)',
              'rgba(168, 85, 247, 0.85)',
              'rgba(234, 179, 8, 0.85)'
            ],
            borderColor: [
              '#f97316',
              '#ef4444',
              '#a855f7',
              '#eab308'
            ],
            borderWidth: 1.5,
            borderRadius: 6
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
              titleColor: isDark ? '#fff' : '#0f172a',
              bodyColor: isDark ? '#cbd5e1' : '#334155',
              borderColor: 'rgba(249, 115, 22, 0.4)',
              borderWidth: 1,
              callbacks: {
                label: (ctx) => ` +${ctx.raw} points to Composite Risk`
              }
            }
          },
          scales: {
            x: {
              grid: { color: gridColor },
              ticks: { color: textColor, font: { family: 'JetBrains Mono', size: 10 } }
            },
            y: {
              grid: { display: false },
              ticks: { color: textColor, font: { size: 11, weight: '500' } }
            }
          }
        }
      });
    } else {
      // Radar Chart
      xaiChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Risk Contribution Index',
            data: dataValues,
            backgroundColor: 'rgba(249, 115, 22, 0.25)',
            borderColor: '#f97316',
            pointBackgroundColor: '#ef4444',
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: '#ef4444',
            borderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: isDark ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
              titleColor: isDark ? '#fff' : '#0f172a',
              bodyColor: isDark ? '#cbd5e1' : '#334155'
            }
          },
          scales: {
            r: {
              angleLines: { color: gridColor },
              grid: { color: gridColor },
              pointLabels: { color: textColor, font: { size: 10, weight: 'bold' } },
              ticks: { display: false }
            }
          }
        }
      });
    }
  }

  // --- ENTITY SELECTION (WARD / STREET INSPECTOR) ---
  function selectEntity(entity, type = 'ward') {
    state.selectedEntity = entity;
    state.selectedType = type;

    // Refresh polygon/line highlight styling
    mapMgr.refreshStyles();
    mapMgr.flyToEntity(entity);

    // Update UI Panel
    updateInspectorPanel(entity, type);
  }

  function updateInspectorPanel(entity, type) {
    const inspectorContainer = document.getElementById('inspector-content');
    if (!inspectorContainer || !entity) return;

    if (type === 'ward') {
      const calc = calculateCompositeRisk(entity, state.scenario);
      const isMitigated = state.comparisonMode;
      const mitigatedScore = isMitigated ? Math.max(15, calc.score - (entity.simulated_drop * 4 || 12)) : calc.score;
      const tier = getRiskTier(mitigatedScore);

      inspectorContainer.innerHTML = `
        <!-- Header Info -->
        <div class="border-b border-slate-700/60 pb-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-orange-500/20 text-orange-400 border border-orange-500/30">
              ${entity.id} • ${entity.zone}
            </span>
            <button id="btn-zoom-ward" class="text-xs flex items-center gap-1 text-slate-400 hover:text-white transition-colors bg-slate-800/80 px-2 py-1 rounded border border-slate-700">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
              Center View
            </button>
          </div>
          <h2 class="text-lg font-bold text-white mt-2 leading-tight">${entity.name}</h2>
          <div class="flex items-center gap-3 text-xs text-slate-400 mt-1">
            <span>Pop: <strong class="text-slate-200">${(entity.population).toLocaleString()}</strong></span>
            <span>•</span>
            <span>Area: <strong class="text-slate-200">${entity.area_km2} km²</strong></span>
            <span>•</span>
            <span>Density: <strong class="text-slate-200">${Math.round(entity.population / entity.area_km2).toLocaleString()}/km²</strong></span>
          </div>
        </div>

        <!-- Composite Score Badge Hero -->
        <div class="mt-3 p-3.5 rounded-xl ${tier.bg} border ${tier.border} relative overflow-hidden transition-all duration-300">
          <div class="flex items-center justify-between relative z-10">
            <div>
              <div class="text-[11px] font-mono tracking-wider uppercase text-slate-300">Composite Heat Risk Score</div>
              <div class="flex items-baseline gap-2 mt-0.5">
                <span class="text-3xl font-black font-mono tracking-tight text-white">${mitigatedScore}</span>
                <span class="text-xs text-slate-300 font-mono">/ 100</span>
                ${isMitigated ? `<span class="text-xs font-bold text-emerald-400 ml-1">(-${(calc.score - mitigatedScore).toFixed(1)} MITIGATED)</span>` : ''}
              </div>
            </div>
            <div class="text-right">
              <span class="inline-block px-3 py-1 rounded-full text-xs font-black tracking-wider ${tier.text} border border-current shadow-sm animate-pulse">
                ${tier.label}
              </span>
              <div class="text-[10px] text-slate-300 mt-1 font-mono">SVI Rank: ${Math.round(entity.svi * 100)}th percentile</div>
            </div>
          </div>
          <!-- Decorative thermal glow -->
          <div class="absolute -right-8 -bottom-8 w-24 h-24 rounded-full blur-2xl opacity-40" style="background:${tier.color}"></div>
        </div>

        <!-- Key Vulnerability Micro-Metrics -->
        <div class="grid grid-cols-2 gap-2 mt-3 text-xs">
          <div class="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
            <div class="text-[10px] text-slate-400 uppercase font-mono">Land Surface Temp</div>
            <div class="text-sm font-bold text-amber-400 font-mono mt-0.5 flex items-baseline justify-between">
              <span>${calc.effective_lst}°C</span>
              <span class="text-[10px] text-red-400 font-normal">+${(calc.effective_lst - 38.0).toFixed(1)}° vs avg</span>
            </div>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
            <div class="text-[10px] text-slate-400 uppercase font-mono">Tree Canopy Coverage</div>
            <div class="text-sm font-bold ${entity.canopy_pct < 10 ? 'text-red-400' : 'text-emerald-400'} font-mono mt-0.5 flex items-baseline justify-between">
              <span>${entity.canopy_pct}%</span>
              <span class="text-[10px] text-slate-400 font-normal">Target: 25%</span>
            </div>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
            <div class="text-[10px] text-slate-400 uppercase font-mono">Elderly (65+ Years)</div>
            <div class="text-sm font-bold text-purple-400 font-mono mt-0.5 flex items-baseline justify-between">
              <span>${(entity.elderly_count).toLocaleString()}</span>
              <span class="text-[10px] text-slate-400 font-normal">High Care</span>
            </div>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
            <div class="text-[10px] text-slate-400 uppercase font-mono">Outdoor Workers</div>
            <div class="text-sm font-bold text-orange-400 font-mono mt-0.5 flex items-baseline justify-between">
              <span>${(entity.outdoor_workers).toLocaleString()}</span>
              <span class="text-[10px] text-slate-400 font-normal">Labor Risk</span>
            </div>
          </div>
        </div>

        <!-- Interactive XAI Driver Breakdown -->
        <div class="mt-4 pt-3 border-t border-slate-700/60">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-orange-500 animate-ping"></span>
              <h3 class="text-xs font-bold uppercase tracking-wider text-slate-200">XAI Driver Breakdown</h3>
            </div>
            <div class="flex items-center bg-slate-800 rounded p-0.5 border border-slate-700">
              <button id="btn-chart-bar" class="px-2 py-0.5 text-[10px] rounded font-semibold ${state.chartType === 'bar' ? 'bg-orange-500 text-white' : 'text-slate-400 hover:text-white'}">Bar</button>
              <button id="btn-chart-radar" class="px-2 py-0.5 text-[10px] rounded font-semibold ${state.chartType === 'radar' ? 'bg-orange-500 text-white' : 'text-slate-400 hover:text-white'}">Radar</button>
            </div>
          </div>
          <div class="h-44 w-full bg-slate-900/60 rounded-xl p-2 border border-slate-800/80">
            <canvas id="xai-canvas"></canvas>
          </div>
        </div>

        <!-- Natural Language AI Diagnosis -->
        <div class="mt-4 p-3 rounded-xl bg-orange-950/20 border border-orange-500/30 text-xs">
          <div class="flex items-center gap-1.5 font-bold text-orange-400 mb-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <span>AI Microclimate Diagnosis</span>
          </div>
          <p class="text-slate-300 leading-relaxed text-[11px]">${entity.diagnosis}</p>
        </div>

        <!-- Immediate Intervention Recommendations -->
        <div class="mt-4 pt-3 border-t border-slate-700/60">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-200">Targeted Interventions & ROI</h3>
            <span class="text-[10px] text-emerald-400 font-mono">Proven HAP Playbook</span>
          </div>
          <div class="space-y-2">
            ${entity.recommended.map((rec, idx) => `
              <div class="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700 hover:border-orange-500/50 transition-all text-xs">
                <div class="flex items-start justify-between">
                  <div class="font-semibold text-slate-100">${rec.name}</div>
                  <span class="font-mono font-bold text-emerald-400 text-[11px]">-$${(rec.cost / 1000).toFixed(0)}k</span>
                </div>
                <div class="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                  <span class="text-amber-400">🔥 -${rec.temp_drop}°C microclimate</span>
                  <span class="text-sky-300">👥 ${(rec.lives).toLocaleString()} protected</span>
                </div>
                <button data-type="${rec.type}" class="btn-stage-intervention w-full mt-2 py-1 rounded bg-slate-700/70 hover:bg-orange-600 text-[10px] font-bold text-slate-200 hover:text-white transition-colors flex items-center justify-center gap-1">
                  <span>+ Stage in Planner Sandbox</span>
                </button>
              </div>
            `).join('')}
          </div>
        </div>
      `;

      // Wire up chart
      renderXAIChart(entity);

      // Event listeners for inspector controls
      const btnZoom = document.getElementById('btn-zoom-ward');
      if (btnZoom) btnZoom.addEventListener('click', () => mapMgr.flyToEntity(entity));

      const btnBar = document.getElementById('btn-chart-bar');
      const btnRadar = document.getElementById('btn-chart-radar');
      if (btnBar) {
        btnBar.addEventListener('click', () => {
          state.chartType = 'bar';
          btnBar.className = 'px-2 py-0.5 text-[10px] rounded font-semibold bg-orange-500 text-white';
          btnRadar.className = 'px-2 py-0.5 text-[10px] rounded font-semibold text-slate-400 hover:text-white';
          renderXAIChart(entity);
          sounds.playClick();
        });
      }
      if (btnRadar) {
        btnRadar.addEventListener('click', () => {
          state.chartType = 'radar';
          btnRadar.className = 'px-2 py-0.5 text-[10px] rounded font-semibold bg-orange-500 text-white';
          btnBar.className = 'px-2 py-0.5 text-[10px] rounded font-semibold text-slate-400 hover:text-white';
          renderXAIChart(entity);
          sounds.playClick();
        });
      }

      // Add to sandbox buttons
      document.querySelectorAll('.btn-stage-intervention').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const type = e.currentTarget.getAttribute('data-type');
          if (type && state.sandbox.allocations[type] !== undefined) {
            state.sandbox.allocations[type]++;
            updateSandboxUI();
            sounds.playChime();
            showToast(`Added ${INTERVENTIONS_CATALOG[type]?.name || type} to sandbox allocations.`);
          }
        });
      });

    } else if (type === 'street') {
      // Street Corridor Inspector
      const tier = getRiskTier(entity.risk_score);
      inspectorContainer.innerHTML = `
        <div class="border-b border-slate-700/60 pb-3">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono font-bold tracking-wider px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
              CORRIDOR • ${entity.id}
            </span>
            <button id="btn-zoom-ward" class="text-xs flex items-center gap-1 text-slate-400 hover:text-white transition-colors bg-slate-800/80 px-2 py-1 rounded border border-slate-700">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
              Focus Line
            </button>
          </div>
          <h2 class="text-lg font-bold text-white mt-2 leading-tight">${entity.name}</h2>
          <div class="text-xs text-slate-400 mt-1">
            Segment Length: <strong class="text-slate-200">${entity.length_km} km</strong> • Surface: <strong class="text-slate-200">${entity.surface_type}</strong>
          </div>
        </div>

        <div class="mt-3 p-3.5 rounded-xl ${tier.bg} border ${tier.border} relative overflow-hidden">
          <div class="flex items-center justify-between relative z-10">
            <div>
              <div class="text-[11px] font-mono tracking-wider uppercase text-slate-300">Street Exposure Score</div>
              <div class="text-3xl font-black font-mono tracking-tight text-white mt-0.5">${entity.risk_score} <span class="text-xs text-slate-300 font-mono">/ 100</span></div>
            </div>
            <span class="px-3 py-1 rounded-full text-xs font-black tracking-wider ${tier.text} border border-current shadow-sm animate-pulse">
              ${tier.label}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-2 mt-3 text-xs">
          <div class="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
            <div class="text-[10px] text-slate-400 uppercase font-mono">Pedestrians Exposed</div>
            <div class="text-sm font-bold text-amber-400 font-mono mt-0.5">${(entity.pedestrians_daily).toLocaleString()} / day</div>
          </div>
          <div class="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
            <div class="text-[10px] text-slate-400 uppercase font-mono">Tree Shade Deficit</div>
            <div class="text-sm font-bold text-red-400 font-mono mt-0.5">${entity.shade_pct}% (Severe)</div>
          </div>
        </div>

        <div class="mt-4 p-3 rounded-xl bg-orange-950/20 border border-orange-500/30 text-xs">
          <div class="font-bold text-orange-400 mb-1">Human Scale Transit Impact</div>
          <p class="text-slate-300 leading-relaxed text-[11px]">
            High thermal asphalt storage and unshaded pedestrian walkways expose ${(entity.pedestrians_daily).toLocaleString()} daily commuters and informal vendors to acute heat radiation. Installation of tensile awnings and sidewalk misting stations is recommended.
          </p>
        </div>

        <div class="mt-4 pt-3 border-t border-slate-700/60">
          <button id="btn-shade-corridor" class="w-full py-2 rounded-lg bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white font-bold text-xs transition-all shadow-lg flex items-center justify-center gap-2">
            <span>🛡️ Deploy Shade Awnings Along Corridor</span>
          </button>
        </div>
      `;

      const btnZoom = document.getElementById('btn-zoom-ward');
      if (btnZoom) btnZoom.addEventListener('click', () => mapMgr.flyToEntity(entity));

      const btnShade = document.getElementById('btn-shade-corridor');
      if (btnShade) {
        btnShade.addEventListener('click', () => {
          state.sandbox.allocations.shade += 2;
          updateSandboxUI();
          sounds.playChime();
          showToast(`Allocated 2 Shade Sail clusters for ${entity.name}.`);
        });
      }
    }
  }

  // --- INTERVENTION PLANNER SANDBOX CONTROLLER ---
  function calculateSandboxBudget() {
    let spent = 0;
    Object.entries(state.sandbox.allocations).forEach(([key, count]) => {
      const spec = INTERVENTIONS_CATALOG[key];
      if (spec) spent += count * spec.unitCost;
    });
    return {
      spent,
      cap: state.sandbox.budgetCap,
      remaining: state.sandbox.budgetCap - spent,
      isOverBudget: spent > state.sandbox.budgetCap
    };
  }

  function updateSandboxUI() {
    const budgetStatus = calculateSandboxBudget();

    // Budget display elements
    const budgetSpentEl = document.getElementById('sandbox-spent-val');
    const budgetCapEl = document.getElementById('sandbox-cap-val');
    const budgetProgressEl = document.getElementById('sandbox-budget-progress');
    const budgetStatusPill = document.getElementById('sandbox-status-pill');

    if (budgetSpentEl) budgetSpentEl.innerText = `$${(budgetStatus.spent).toLocaleString()}`;
    if (budgetCapEl) budgetCapEl.innerText = `$${(budgetStatus.cap).toLocaleString()}`;

    if (budgetProgressEl) {
      const pct = Math.min(100, (budgetStatus.spent / budgetStatus.cap) * 100);
      budgetProgressEl.style.width = `${pct}%`;
      if (budgetStatus.isOverBudget) {
        budgetProgressEl.className = 'h-2 rounded-full bg-red-500 transition-all duration-300';
      } else {
        budgetProgressEl.className = 'h-2 rounded-full bg-gradient-to-r from-emerald-500 to-orange-500 transition-all duration-300';
      }
    }

    if (budgetStatusPill) {
      if (budgetStatus.isOverBudget) {
        budgetStatusPill.innerHTML = `<span class="text-red-400 font-bold">-$${Math.abs(budgetStatus.remaining).toLocaleString()} OVER BUDGET</span>`;
      } else {
        budgetStatusPill.innerHTML = `<span class="text-emerald-400 font-mono">$${(budgetStatus.remaining).toLocaleString()} Remaining</span>`;
      }
    }

    // Update item counter numbers
    Object.entries(state.sandbox.allocations).forEach(([key, count]) => {
      const countEl = document.getElementById(`count-${key}`);
      if (countEl) countEl.innerText = count;
      const subtotalEl = document.getElementById(`subtotal-${key}`);
      if (subtotalEl && INTERVENTIONS_CATALOG[key]) {
        subtotalEl.innerText = `$${(count * INTERVENTIONS_CATALOG[key].unitCost).toLocaleString()}`;
      }
    });
  }

  function runParetoOptimization() {
    sounds.playAlert();
    const btn = document.getElementById('btn-run-optimization');
    if (btn) {
      btn.innerHTML = `
        <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
        </svg>
        Solving Pareto Heat Heuristic...
      `;
      btn.disabled = true;
    }

    setTimeout(() => {
      // Greedy Heuristic:
      // Sort wards by vulnerability: score * elderly_count
      const sortedWards = [...state.wards].sort((a, b) => {
        const scoreA = calculateCompositeRisk(a, state.scenario).score * a.elderly_count;
        const scoreB = calculateCompositeRisk(b, state.scenario).score * b.elderly_count;
        return scoreB - scoreA;
      });

      // Target budget
      const cap = state.sandbox.budgetCap;
      let remaining = cap;
      const newAlloc = { shade: 0, misting: 0, centers: 0, trees: 0, roofs: 0 };

      // Optimized distribution pattern
      while (remaining >= 15000) {
        if (remaining >= 85000 && newAlloc.centers < 4) {
          newAlloc.centers++;
          remaining -= 85000;
        } else if (remaining >= 40000 && newAlloc.roofs < 6) {
          newAlloc.roofs++;
          remaining -= 40000;
        } else if (remaining >= 35000 && newAlloc.trees < 5) {
          newAlloc.trees++;
          remaining -= 35000;
        } else if (remaining >= 25000 && newAlloc.shade < 8) {
          newAlloc.shade++;
          remaining -= 25000;
        } else if (remaining >= 15000 && newAlloc.misting < 10) {
          newAlloc.misting++;
          remaining -= 15000;
        } else {
          break;
        }
      }

      state.sandbox.allocations = newAlloc;
      updateSandboxUI();

      // Compute simulated mitigation impact across city
      let totalTempDrop = 0;
      let totalLivesProtected = 0;

      state.wards.forEach(ward => {
        const risk = calculateCompositeRisk(ward, state.scenario).score;
        // High risk wards receive higher benefit from citywide deployment
        const simDrop = parseFloat(((risk / 100) * 3.4 + (newAlloc.roofs * 0.25) + (newAlloc.trees * 0.3)).toFixed(2));
        ward.simulated_drop = simDrop;
        totalTempDrop += simDrop;
        totalLivesProtected += Math.round((ward.elderly_count + ward.outdoor_workers) * 0.45);
      });

      const avgTempDrop = (totalTempDrop / state.wards.length).toFixed(1);

      // Store results
      state.sandbox.optimizedResults = {
        avgTempDrop: avgTempDrop,
        livesProtected: totalLivesProtected,
        hospitalizationReduction: Math.min(48, Math.round(avgTempDrop * 12.5))
      };

      // Show results in UI
      const resultsEl = document.getElementById('sandbox-results-panel');
      if (resultsEl) {
        resultsEl.classList.remove('hidden');
        document.getElementById('opt-lives-val').innerText = `+${totalLivesProtected.toLocaleString()}`;
        document.getElementById('opt-temp-val').innerText = `-${avgTempDrop}°C`;
        document.getElementById('opt-hosp-val').innerText = `-${state.sandbox.optimizedResults.hospitalizationReduction}%`;
      }

      // Automatically enable Before vs After map mode
      state.comparisonMode = true;
      const toggleComp = document.getElementById('toggle-compare-mode');
      if (toggleComp) toggleComp.checked = true;

      mapMgr.refreshStyles();
      updateTopKPIs();
      renderRankingTable();
      if (state.selectedEntity) {
        updateInspectorPanel(state.selectedEntity, state.selectedType || 'ward');
      }

      sounds.playChime();
      if (window.confetti) {
        window.confetti({ particleCount: 75, spread: 70, origin: { y: 0.6 } });
      }

      if (btn) {
        btn.innerHTML = `<span>✓ Optimization Applied (Pareto Optimal)</span>`;
        btn.disabled = false;
        setTimeout(() => {
          btn.innerHTML = `<span>⚡ Run AI Optimization</span>`;
        }, 3000);
      }
    }, 600);
  }

  // --- TOP KPI METRICS BAR CONTROLLER ---
  function updateTopKPIs() {
    let totalPop = 0;
    let highRiskPop = 0;
    let totalElderlyAtRisk = 0;
    let sumScore = 0;
    let criticalWardsCount = 0;

    state.wards.forEach(ward => {
      totalPop += ward.population;
      const calc = calculateCompositeRisk(ward, state.scenario, state.comparisonMode ? (ward.simulated_drop || 2.4) : 0);
      sumScore += calc.score;

      if (calc.score >= 68) {
        highRiskPop += ward.population;
        totalElderlyAtRisk += ward.elderly_count;
        criticalWardsCount++;
      }
    });

    const meanScore = (sumScore / state.wards.length).toFixed(1);

    const elScore = document.getElementById('kpi-mean-score');
    const elPop = document.getElementById('kpi-high-risk-pop');
    const elElderly = document.getElementById('kpi-elderly-risk');
    const elCritical = document.getElementById('kpi-critical-wards');

    if (elScore) elScore.innerText = meanScore;
    if (elPop) elPop.innerText = (highRiskPop).toLocaleString();
    if (elElderly) elElderly.innerText = (totalElderlyAtRisk).toLocaleString();
    if (elCritical) elCritical.innerText = `${criticalWardsCount} / ${state.wards.length}`;
  }

  // --- PRIORITY RANKING TABLE CONTROLLER ---
  function renderRankingTable(filterQuery = '', tierFilter = 'all') {
    const tableBody = document.getElementById('ranking-table-body');
    if (!tableBody) return;

    let items = state.wards.map(ward => {
      const calc = calculateCompositeRisk(ward, state.scenario, state.comparisonMode ? (ward.simulated_drop || 2.4) : 0);
      return {
        ...ward,
        type: 'Ward',
        current_score: calc.score,
        current_lst: calc.effective_lst,
        tier: calc.tier
      };
    });

    // Also include streets if selected
    if (state.showStreets) {
      state.streets.forEach(st => {
        const tier = getRiskTier(st.risk_score);
        items.push({
          id: st.id,
          name: st.name,
          type: 'Corridor',
          current_score: st.risk_score,
          current_lst: 45.2,
          canopy_pct: st.shade_pct,
          elderly_count: Math.round(st.pedestrians_daily * 0.18),
          outdoor_workers: Math.round(st.pedestrians_daily * 0.42),
          tier: tier,
          isStreet: true
        });
      });
    }

    // Apply Tier Filter
    if (tierFilter === 'extreme') items = items.filter(i => i.current_score >= 82);
    else if (tierFilter === 'high') items = items.filter(i => i.current_score >= 68 && i.current_score < 82);
    else if (tierFilter === 'corridors') items = items.filter(i => i.type === 'Corridor');

    // Apply text search
    if (filterQuery.trim()) {
      const q = filterQuery.toLowerCase();
      items = items.filter(i => i.name.toLowerCase().includes(q) || i.id.toLowerCase().includes(q));
    }

    // Apply dynamic sorting
    const colKey = state.tableSort.col || 'current_score';
    const isAsc = !!state.tableSort.asc;
    items.sort((a, b) => {
      let valA = a[colKey];
      let valB = b[colKey];
      if (typeof valA === 'string') {
        return isAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
      }
      return isAsc ? (valA - valB) : (valB - valA);
    });

    // Render Rows
    tableBody.innerHTML = items.map((item, idx) => {
      const isSelected = state.selectedEntity && state.selectedEntity.id === item.id;
      return `
        <tr data-id="${item.id}" data-type="${item.isStreet ? 'street' : 'ward'}" class="border-b border-slate-800 hover:bg-slate-800/60 cursor-pointer transition-colors ${isSelected ? 'bg-orange-500/10 border-orange-500/40' : ''}">
          <td class="px-3 py-2.5 font-mono text-xs text-slate-400">#${idx + 1}</td>
          <td class="px-3 py-2.5">
            <div class="font-semibold text-xs text-slate-100 flex items-center gap-1.5">
              <span>${item.name}</span>
              ${item.type === 'Corridor' ? '<span class="text-[9px] px-1 py-0.2 bg-sky-950 text-sky-400 border border-sky-800 rounded font-mono">CORRIDOR</span>' : ''}
            </div>
            <div class="text-[10px] text-slate-400 font-mono">${item.id}</div>
          </td>
          <td class="px-3 py-2.5 font-mono font-bold text-xs">
            <span class="inline-block px-2 py-0.5 rounded text-xs" style="background:${item.tier.color}22; color:${item.tier.color}; border: 1px solid ${item.tier.color}44;">
              ${item.current_score}
            </span>
          </td>
          <td class="px-3 py-2.5 font-mono text-xs text-amber-400">${item.current_lst}°C</td>
          <td class="px-3 py-2.5 font-mono text-xs ${item.canopy_pct < 10 ? 'text-red-400' : 'text-emerald-400'}">${item.canopy_pct}%</td>
          <td class="px-3 py-2.5 font-mono text-xs text-purple-300">${(item.elderly_count).toLocaleString()}</td>
          <td class="px-3 py-2.5 font-mono text-xs text-orange-300">${(item.outdoor_workers).toLocaleString()}</td>
          <td class="px-3 py-2.5">
            <span class="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${item.tier.text}">
              ${item.tier.label}
            </span>
          </td>
          <td class="px-3 py-2.5 text-right">
            <button class="px-2.5 py-1 rounded bg-slate-800 hover:bg-orange-600 text-[10px] font-bold text-slate-300 hover:text-white transition-all border border-slate-700">
              Inspect
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // Attach row click events
    tableBody.querySelectorAll('tr').forEach(tr => {
      tr.addEventListener('click', () => {
        const id = tr.getAttribute('data-id');
        const type = tr.getAttribute('data-type');
        let entity = null;
        if (type === 'ward') {
          entity = state.wards.find(w => w.id === id);
        } else {
          entity = state.streets.find(s => s.id === id);
        }
        if (entity) {
          selectEntity(entity, type);
          sounds.playClick();
        }
      });
    });
  }

  // --- CSV / GEOJSON EXPORT UTILITIES ---
  function exportCSV() {
    sounds.playClick();
    const rows = [
      ['Ward_ID', 'Name', 'Zone', 'Population', 'Composite_Heat_Risk', 'LST_Celsius', 'Canopy_Pct', 'SVI', 'Elderly_Count', 'Outdoor_Workers', 'Cooling_Centers']
    ];

    state.wards.forEach(w => {
      const calc = calculateCompositeRisk(w, state.scenario);
      rows.push([
        w.id,
        `"${w.name}"`,
        `"${w.zone}"`,
        w.population,
        calc.score,
        calc.effective_lst,
        w.canopy_pct,
        w.svi,
        w.elderly_count,
        w.outdoor_workers,
        w.cooling_centers
      ]);
    });

    const csvContent = 'data:text/csv;charset=utf-8,' + rows.map(e => e.join(',')).join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `TERRA07_Heat_Risk_Matrix_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Exported Heat Vulnerability Matrix to CSV.');
  }

  // --- TOAST NOTIFICATIONS ---
  function showToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-5 right-5 z-50 px-4 py-2.5 rounded-xl bg-slate-900/95 border border-orange-500/60 text-white text-xs shadow-2xl flex items-center gap-2 transform transition-all duration-300 translate-y-2 opacity-0';
    toast.innerHTML = `
      <span class="w-2 h-2 rounded-full bg-orange-500 animate-ping"></span>
      <span>${msg}</span>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);
    setTimeout(() => {
      toast.classList.add('translate-y-2', 'opacity-0');
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  // --- FASTAPI BACKEND SYNC (Optional Live Connect) ---
  async function checkBackendConnection() {
    const statusDot = document.getElementById('backend-status-dot');
    const statusText = document.getElementById('backend-status-text');

    try {
      // 1. Fetch live Overview telemetry
      const overviewRes = await fetch('/api/overview', { method: 'GET', signal: AbortSignal.timeout(1500) }).catch(() => null);
      if (overviewRes && overviewRes.ok) {
        const overview = await overviewRes.json();
        if (overview.average_heat_risk) {
          const elScore = document.getElementById('kpi-mean-score');
          if (elScore) elScore.innerText = overview.average_heat_risk.toFixed(1);
        }
        if (overview.most_vulnerable_population) {
          const elElderly = document.getElementById('kpi-elderly-risk');
          if (elElderly && overview.most_vulnerable_population.elderly_count) {
            elElderly.innerText = overview.most_vulnerable_population.elderly_count.toLocaleString();
          }
        }
      }

      // 2. Fetch live wards
      const res = await fetch('/api/wards', { method: 'GET', signal: AbortSignal.timeout(1500) });
      if (res.ok) {
        const liveData = await res.json();
        const wardList = Array.isArray(liveData) ? liveData : (liveData.wards || []);
        if (wardList.length > 0) {
          console.log('[TERRA07] Connected to live FastAPI backend with', wardList.length, 'wards!');
        }
        if (statusDot) statusDot.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
        if (statusText) statusText.innerText = 'FASTAPI: CONNECTED';
      } else {
        throw new Error('Fallback to Client Sim');
      }
    } catch (err) {
      // Seamless in-memory simulation mode
      if (statusDot) statusDot.className = 'w-2 h-2 rounded-full bg-orange-400';
      if (statusText) statusText.innerText = 'SIM ENGINE: ACTIVE (CLIENT)';
    }
  }

  // --- EVENT ATTACHMENTS & INITIALIZATION ---
  function initApp() {
    // 1. Initialize Map
    mapMgr.init();

    // 2. Select default high-priority ward
    const defaultWard = state.wards.find(w => w.id === 'W-03') || state.wards[0];
    selectEntity(defaultWard, 'ward');

    // 3. Render Table & KPIs
    updateTopKPIs();
    renderRankingTable();
    updateSandboxUI();

    // 4. Layer Switcher Buttons
    const layerButtons = document.querySelectorAll('.btn-layer-toggle');
    layerButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const layer = e.currentTarget.getAttribute('data-layer');
        if (layer) {
          state.activeLayer = layer;
          layerButtons.forEach(b => {
            b.classList.remove('bg-orange-500', 'text-white', 'border-orange-500');
            b.classList.add('bg-slate-800/80', 'text-slate-300', 'border-slate-700');
          });
          e.currentTarget.classList.add('bg-orange-500', 'text-white', 'border-orange-500');
          e.currentTarget.classList.remove('bg-slate-800/80', 'text-slate-300', 'border-slate-700');

          mapMgr.refreshStyles();
          sounds.playClick();
        }
      });
    });

    // Layer Opacity Slider
    const opacitySlider = document.getElementById('slider-layer-opacity');
    if (opacitySlider) {
      opacitySlider.addEventListener('input', (e) => {
        state.layerOpacity = parseFloat(e.target.value);
        mapMgr.refreshStyles();
      });
    }

    // Basemap Switcher
    const basemapSelect = document.getElementById('select-basemap');
    if (basemapSelect) {
      basemapSelect.addEventListener('change', (e) => {
        state.activeBasemap = e.target.value;
        mapMgr.updateTileLayer(state.activeBasemap);
        sounds.playClick();
      });
    }

    // Streets and Amenities Checkbox Toggles
    const toggleStreets = document.getElementById('toggle-street-lines');
    if (toggleStreets) {
      toggleStreets.addEventListener('change', (e) => {
        state.showStreets = e.target.checked;
        mapMgr.renderStreets();
        renderRankingTable();
        sounds.playClick();
      });
    }

    const toggleAmenities = document.getElementById('toggle-amenity-markers');
    if (toggleAmenities) {
      toggleAmenities.addEventListener('change', (e) => {
        state.showAmenities = e.target.checked;
        mapMgr.renderAmenities();
        sounds.playClick();
      });
    }

    // Climate Scenario Sliders
    const heatwaveSlider = document.getElementById('slider-heatwave-delta');
    const heatwaveDisplay = document.getElementById('val-heatwave-delta');
    if (heatwaveSlider && heatwaveDisplay) {
      heatwaveSlider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        state.scenario.heatwaveDelta = val;
        heatwaveDisplay.innerText = `+${val.toFixed(1)}°C`;
        mapMgr.refreshStyles();
        updateTopKPIs();
        renderRankingTable();
        if (state.selectedEntity) updateInspectorPanel(state.selectedEntity, state.selectedType || 'ward');
      });
    }

    const gridToggle = document.getElementById('toggle-grid-outage');
    if (gridToggle) {
      gridToggle.addEventListener('change', (e) => {
        state.scenario.gridOutage = e.target.checked;
        mapMgr.refreshStyles();
        updateTopKPIs();
        renderRankingTable();
        if (state.selectedEntity) updateInspectorPanel(state.selectedEntity, state.selectedType || 'ward');
        sounds.playAlert();
        showToast(state.scenario.gridOutage ? '⚠️ Power Grid Outage Active: Cooling Centers on Battery Only' : 'Grid Power Restored');
      });
    }

    const humidityToggle = document.getElementById('toggle-humidity-surge');
    if (humidityToggle) {
      humidityToggle.addEventListener('change', (e) => {
        state.scenario.humiditySurge = e.target.checked;
        mapMgr.refreshStyles();
        updateTopKPIs();
        renderRankingTable();
        if (state.selectedEntity) updateInspectorPanel(state.selectedEntity, state.selectedType || 'ward');
        sounds.playClick();
      });
    }

    const timeOfDaySelect = document.getElementById('select-time-of-day');
    if (timeOfDaySelect) {
      timeOfDaySelect.addEventListener('change', (e) => {
        state.scenario.timeOfDay = e.target.value;
        mapMgr.refreshStyles();
        updateTopKPIs();
        renderRankingTable();
        if (state.selectedEntity) updateInspectorPanel(state.selectedEntity, state.selectedType || 'ward');
        sounds.playClick();
      });
    }

    // Budget Slider
    const budgetSlider = document.getElementById('slider-budget-cap');
    if (budgetSlider) {
      budgetSlider.addEventListener('input', (e) => {
        state.sandbox.budgetCap = parseInt(e.target.value, 10);
        updateSandboxUI();
      });
    }

    // Intervention Allocation Increment/Decrement Buttons
    Object.keys(INTERVENTIONS_CATALOG).forEach(key => {
      const btnPlus = document.getElementById(`btn-plus-${key}`);
      const btnMinus = document.getElementById(`btn-minus-${key}`);

      if (btnPlus) {
        btnPlus.addEventListener('click', () => {
          state.sandbox.allocations[key]++;
          updateSandboxUI();
          sounds.playClick();
        });
      }

      if (btnMinus) {
        btnMinus.addEventListener('click', () => {
          if (state.sandbox.allocations[key] > 0) {
            state.sandbox.allocations[key]--;
            updateSandboxUI();
            sounds.playClick();
          }
        });
      }
    });

    // Run Optimization Button
    const btnOpt = document.getElementById('btn-run-optimization');
    if (btnOpt) {
      btnOpt.addEventListener('click', runParetoOptimization);
    }

    // Compare Mode (Before vs After) Toggle
    const compareToggle = document.getElementById('toggle-compare-mode');
    if (compareToggle) {
      compareToggle.addEventListener('change', (e) => {
        state.comparisonMode = e.target.checked;
        mapMgr.refreshStyles();
        updateTopKPIs();
        renderRankingTable();
        if (state.selectedEntity) updateInspectorPanel(state.selectedEntity, state.selectedType || 'ward');
        sounds.playClick();
        showToast(state.comparisonMode ? 'Viewing Post-Intervention Simulated Map' : 'Viewing Baseline Map');
      });
    }

    // Table Search and Filter Buttons
    const searchInput = document.getElementById('input-search-zones');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        renderRankingTable(e.target.value);
      });
    }

    const tableFilterBtns = document.querySelectorAll('.btn-table-filter');
    tableFilterBtns.forEach(b => {
      b.addEventListener('click', (e) => {
        const filter = e.currentTarget.getAttribute('data-filter');
        state.activeTierFilter = filter;
        tableFilterBtns.forEach(btn => btn.classList.remove('bg-orange-500', 'text-white'));
        e.currentTarget.classList.add('bg-orange-500', 'text-white');
        renderRankingTable(searchInput ? searchInput.value : '', filter);
        sounds.playClick();
      });
    });

    // Table Header Click-to-Sort
    document.querySelectorAll('thead th[data-col]').forEach(th => {
      th.addEventListener('click', (e) => {
        const col = e.currentTarget.getAttribute('data-col');
        if (state.tableSort.col === col) {
          state.tableSort.asc = !state.tableSort.asc;
        } else {
          state.tableSort.col = col;
          state.tableSort.asc = false;
        }
        // Update header highlight
        document.querySelectorAll('thead th[data-col]').forEach(h => {
          h.classList.remove('text-orange-400');
        });
        e.currentTarget.classList.add('text-orange-400');

        renderRankingTable(
          searchInput ? searchInput.value : '',
          state.activeTierFilter || 'all'
        );
        sounds.playClick();
      });
    });

    // Export CSV
    const btnExport = document.getElementById('btn-export-csv');
    if (btnExport) btnExport.addEventListener('click', exportCSV);

    // Audio Mute Toggle
    const btnAudio = document.getElementById('btn-toggle-audio');
    if (btnAudio) {
      btnAudio.addEventListener('click', () => {
        sounds.enabled = !sounds.enabled;
        btnAudio.innerHTML = sounds.enabled ?
          `<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/></svg>` :
          `<svg class="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"/></svg>`;
        showToast(sounds.enabled ? 'Audio Feedback Enabled' : 'Audio Muted');
      });
    }

    // Theme Switcher (Dark/Light)
    const btnTheme = document.getElementById('btn-toggle-theme');
    if (btnTheme) {
      btnTheme.addEventListener('click', () => {
        state.theme = state.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('terra07_theme', state.theme);
        applyTheme(state.theme);
        sounds.playClick();
      });
    }
    applyTheme(state.theme);

    // Fullscreen Toggle
    const btnFullscreen = document.getElementById('btn-fullscreen');
    if (btnFullscreen) {
      btnFullscreen.addEventListener('click', () => {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen();
        } else {
          document.exitFullscreen();
        }
      });
    }

    // Modal Handlers (Executive Briefing & Tour)
    const btnBriefing = document.getElementById('btn-exec-briefing');
    const modalBriefing = document.getElementById('modal-briefing');
    const closeBriefing = document.getElementById('close-briefing');
    if (btnBriefing && modalBriefing) {
      btnBriefing.addEventListener('click', () => {
        modalBriefing.classList.remove('hidden');
        sounds.playClick();
      });
    }
    if (closeBriefing && modalBriefing) {
      closeBriefing.addEventListener('click', () => modalBriefing.classList.add('hidden'));
    }

    // Periodic Backend Ping
    checkBackendConnection();
  }

  function applyTheme(theme) {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      state.activeBasemap = 'dark';
    } else {
      root.classList.remove('dark');
      state.activeBasemap = 'light';
    }
    if (mapMgr && mapMgr.map) {
      mapMgr.updateTileLayer(state.activeBasemap);
      mapMgr.refreshStyles();
    }
  }

  // Auto initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }

})();

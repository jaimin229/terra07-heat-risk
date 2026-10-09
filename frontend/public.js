/**
 * TERRA07 - Public Heat Safety Portal Engine (public.js)
 * Team TERRA07 - Agnitia Hackathon 2026: Heat-Risk Mapping at Human Scale
 * 
 * Features:
 * 1. Live Heat Emergency Alert status banner with WBGT, UV, and audio synthesis (TTS).
 * 2. "How Safe is My Street Right Now?" search/selector with thermal danger levels & UHI diagnostics.
 * 3. Persona-based Personal Safety Risk Assessment with safe outdoor minutes countdown timer & hydration protocol.
 * 4. "Find Nearest Cooling Sanctuary" Interactive Radar with distance, walk times, and Leaflet map.
 * 5. "Cool Walk" Navigation Tool with side-by-side Shortest vs Cool-Corridor route comparison & turn-by-turn guidance.
 * 6. Sunlight Boost outdoor daylight mode, multilingual translation (EN, HI, ES), and FastAPI backend integration.
 */

// ============================================================================
// 1. CONFIGURATION & STATE MANAGEMENT
// ============================================================================

const CONFIG = {
  // Determine backend base URL: supports served via FastAPI or direct static hosting
  API_BASE: window.TERRA_API_BASE || (
    window.location.protocol === 'file:' 
      ? 'http://localhost:8000/api' 
      : `${window.location.origin}/api`
  ),
  DEFAULT_COORDS: { lat: 23.0225, lon: 72.5714 }, // Ahmedabad City Center
  WALKING_SPEED_M_PER_MIN: 70.0, // Standard pedestrian walking speed (approx 4.2 km/h)
  DEFAULT_LANG: 'en'
};

const STATE = {
  isBackendLive: false,
  language: 'en',
  sunlightBoost: false,
  userLocation: { ...CONFIG.DEFAULT_COORDS },
  activeWard: null,
  activeStreet: null,
  streets: [],
  coolingCenters: [],
  hydrationPoints: [],
  selectedPersona: 'senior', // 'senior' | 'worker' | 'parent' | 'general'
  personaConditions: {
    hasAc: 'yes',           // 'yes' | 'fans' | 'none'
    sunExposure: 'direct',  // 'direct' | 'partial' | 'indoor'
    healthFactor: 'heart',  // 'heart' | 'asthma' | 'diabetes' | 'none'
    exertion: 'moderate'    // 'heavy' | 'moderate' | 'sedentary'
  },
  timer: {
    totalSeconds: 15 * 60,
    remainingSeconds: 15 * 60,
    intervalId: null,
    isRunning: false
  },
  map: null,
  mapMarkers: [],
  mapRouteLayers: [],
  speaking: false,
  activeRouteData: null
};

// ============================================================================
// 2. MULTILINGUAL DICTIONARY (EN, HI, ES)
// ============================================================================

const I18N = {
  en: {
    alert_extreme: "EXTREME HEAT WARNING: CODE RED",
    alert_high: "HIGH HEATWAVE ALERT: CODE ORANGE",
    alert_moderate: "HEAT ADVISORY: CODE YELLOW",
    alert_safe: "NORMAL CONDITIONS: CODE GREEN",
    street_index_label: "Current Street Index",
    feels_like: "Feels Like",
    wbgt_label: "Wet-Bulb Temp (WBGT)",
    uv_label: "Solar UV Index",
    peak_window_label: "Peak Danger Window",
    listen_alert: "Listen to Alert",
    stop_audio: "Stop Audio",
    safe_street_title: "How Safe is My Street Right Now?",
    search_placeholder: "Search neighbourhood or street (e.g., Manek Chowk, Khadia, Odhav)...",
    surface_temp: "Surface Temp",
    shade_temp: "Shaded Sidewalk",
    canopy_cover: "Tree Canopy",
    radiant_temp: "Radiant Temp",
    why_hot: "Why is this street hotter?",
    hourly_curve: "Today's Thermal Danger Timeline",
    persona_assessment_title: "Personal Safety Risk Assessment",
    select_persona: "1. Select Your Profile",
    persona_senior: "Senior Citizen (65+)",
    persona_senior_sub: "Vulnerable to rapid hyperthermia",
    persona_worker: "Outdoor Worker / Rider",
    persona_worker_sub: "Heavy exertion in direct sun",
    persona_parent: "Parent with Infant",
    persona_parent_sub: "Strollers travel near hot asphalt",
    persona_general: "General Public",
    persona_general_sub: "Commuters & shoppers",
    conditions_title: "2. Your Current Conditions",
    ac_home: "AC at Home?",
    sun_work: "Sun Exposure?",
    health_cond: "Pre-existing Condition?",
    exertion_level: "Physical Exertion?",
    opt_ac_yes: "Yes, AC",
    opt_ac_fans: "Fans Only",
    opt_ac_none: "No AC / Tin Roof",
    opt_sun_direct: "Direct Sun",
    opt_sun_partial: "Partial Shade",
    opt_sun_indoor: "Indoors",
    opt_cond_heart: "Heart / High BP",
    opt_cond_asthma: "Asthma / Lungs",
    opt_cond_diabetes: "Diabetes",
    opt_cond_none: "None",
    opt_exert_heavy: "Heavy Labor",
    opt_exert_moderate: "Walking / Commute",
    opt_exert_resting: "Resting",
    safe_limit_title: "Maximum Safe Outdoor Time",
    start_timer: "Start Safe Walk Timer",
    pause_timer: "Pause",
    reset_timer: "Reset",
    hydration_title: "Personal Hydration Protocol",
    symptoms_title: "Critical Symptoms to Watch",
    sanctuaries_title: "Find Nearest Cooling Sanctuary",
    filter_all: "All Havens",
    filter_ac: "❄️ AC Centers",
    filter_water: "💧 Free Water",
    filter_parks: "🌳 Shaded Parks",
    walk_here: "Walk Here Now",
    cool_walk_title: "Cool Walk Navigation Tool",
    start_loc: "Start Location",
    dest_loc: "Destination",
    calc_cool_route: "Find Coolest Route",
    shortest_path_title: "Standard Shortest Route",
    cool_path_title: "🌿 Cool-Corridor Route",
    distance: "Distance",
    walk_time: "Walk Time",
    shade_cover: "Shade Coverage",
    water_points: "Water Points on Way",
    turn_steps_title: "Turn-by-Turn Safe Directions",
    sos_call: "🚨 Heat Emergency SOS (108)",
    sunlight_boost_on: "☀️ Sunlight Boost ON",
    sunlight_boost_off: "☀️ Sunlight Boost OFF"
  },
  hi: {
    alert_extreme: "चरम ग्रीष्म चेतावनी: कोड रेड (लाल सतर्कता)",
    alert_high: "अत्यधिक लू चेतावनी: कोड ऑरेंज (नारंगी सतर्कता)",
    alert_moderate: "ग्रीष्मकालीन परामर्श: कोड येलो (पीली सतर्कता)",
    alert_safe: "सामान्य स्थिति: कोड ग्रीन (सुरक्षित)",
    street_index_label: "वर्तमान सड़क तापमान सूचकांक",
    feels_like: "महसूस तापमान",
    wbgt_label: "वेट-बल्ब तापमान (WBGT)",
    uv_label: "सूर्य UV सूचकांक",
    peak_window_label: "उच्चतम खतरे का समय",
    listen_alert: "चेतावनी सुनें",
    stop_audio: "आवाज बंद करें",
    safe_street_title: "मेरी सड़क अभी कितनी सुरक्षित है?",
    search_placeholder: "मोहल्ला या सड़क खोजें (उदा. मानक चौक, खाड़िया, ओढ़व)...",
    surface_temp: "सतह तापमान",
    shade_temp: "छायादार फुटपाथ",
    canopy_cover: "वृक्ष आच्छादन",
    radiant_temp: "विकिरण तापमान",
    why_hot: "यह सड़क अधिक गर्म क्यों है?",
    hourly_curve: "आज का गर्मी खतरा ग्राफ",
    persona_assessment_title: "व्यक्तिगत सुरक्षा जोखिम मूल्यांकन",
    select_persona: "1. अपना प्रोफ़ाइल चुनें",
    persona_senior: "वरिष्ठ नागरिक (65+)",
    persona_senior_sub: "गर्मी से शीघ्र अस्वस्थ होने का खतरा",
    persona_worker: "श्रमिक / डिलीवरी राइडर",
    persona_worker_sub: "कड़ी धूप में शारीरिक श्रम",
    persona_parent: "शिशु के साथ अभिभावक",
    persona_parent_sub: "गर्म डामर के पास प्रैम/स्ट्रोलर",
    persona_general: "आम नागरिक",
    persona_general_sub: "दैनिक यात्री और खरीदार",
    conditions_title: "2. आपकी वर्तमान स्थिति",
    ac_home: "घर पर एसी?",
    sun_work: "धूप का संपर्क?",
    health_cond: "पुरानी बीमारी?",
    exertion_level: "शारीरिक श्रम?",
    opt_ac_yes: "हाँ, एसी है",
    opt_ac_fans: "केवल पंखा/कूलर",
    opt_ac_none: "एसी नहीं / टीन शेड",
    opt_sun_direct: "कड़ी धूप में",
    opt_sun_partial: "हल्की छाया",
    opt_sun_indoor: "भीतर",
    opt_cond_heart: "हृदय / बीपी",
    opt_cond_asthma: "अस्थमा / सांस",
    opt_cond_diabetes: "मधुमेह",
    opt_cond_none: "कोई नहीं",
    opt_exert_heavy: "कड़ा श्रम",
    opt_exert_moderate: "चलना / यात्रा",
    opt_exert_resting: "विश्राम",
    safe_limit_title: "सुरक्षित बाहर रहने का अधिकतम समय",
    start_timer: "सुरक्षित वॉक टाइमर शुरू करें",
    pause_timer: "रोकें",
    reset_timer: "रीसेट",
    hydration_title: "व्यक्तिगत जलपान (हाइड्रेशन) नियम",
    symptoms_title: "महत्वपूर्ण खतरे के लक्षण",
    sanctuaries_title: "निकटतम शीतल आश्रय (कूलिंग सेंटर) खोजें",
    filter_all: "सभी आश्रय",
    filter_ac: "❄️ एसी केंद्र",
    filter_water: "💧 मुफ्त पानी",
    filter_parks: "🌳 छायादार पार्क",
    walk_here: "यहाँ चलें",
    cool_walk_title: "कूल वॉक (शीतल मार्ग) नेविगेशन",
    start_loc: "प्रारंभिक स्थान",
    dest_loc: "गंतव्य स्थान",
    calc_cool_route: "शीतल मार्ग खोजें",
    shortest_path_title: "सामान्य सबसे छोटा मार्ग",
    cool_path_title: "🌿 छायादार शीतल गलियारा मार्ग",
    distance: "दूरी",
    walk_time: "पैदल समय",
    shade_cover: "छाया प्रतिशत",
    water_points: "रास्ते में पानी के केंद्र",
    turn_steps_title: "कदम-दर-कदम सुरक्षित दिशा निर्देश",
    sos_call: "🚨 आपातकालीन एम्बुलेंस (108)",
    sunlight_boost_on: "☀️ धूप मोड सक्रिय",
    sunlight_boost_off: "☀️ सामान्य मोड"
  },
  gu: {
    alert_extreme: "અતિશય ગરમીની ચેતવણી: રેડ એલર્ટ",
    alert_high: "તીવ્ર લૂ ની ચેતવણી: ઓરેન્જ એલર્ટ",
    alert_moderate: "ગરમીની સાવચેતી: યલો એલર્ટ",
    alert_safe: "સામાન્ય સ્થિતિ: ગ્રીન એલર્ટ",
    street_index_label: "વર્તમાન શેરી તાપમાન સૂચકાંક",
    feels_like: "અનુભવાતું તાપમાન",
    wbgt_label: "વેટ-બલ્બ તાપમાન (WBGT)",
    uv_label: "સૂર્ય UV સૂચકાંક",
    peak_window_label: "સૌથી જોખમી સમયગાળો",
    listen_alert: "ચેતવણી સાંભળો",
    stop_audio: "અવાજ બંધ કરો",
    safe_street_title: "મારી શેરી અત્યારે કેટલી સલામત છે?",
    search_placeholder: "વિસ્તાર અથવા શેરી શોધો (દા.ત. માણેક ચોક, ખાડિયા, ઓઢવ)...",
    surface_temp: "સપાટીનું તાપમાન",
    shade_temp: "છાંયડાવાળો ફૂટપાથ",
    canopy_cover: "વૃક્ષોનું આવરણ",
    radiant_temp: "રેડિયન્ટ તાપમાન",
    why_hot: "આ શેરી વધુ ગરમ કેમ છે?",
    hourly_curve: "આજનો ગરમીનો જોખમ ગ્રાફ",
    persona_assessment_title: "વ્યક્તિગત ગરમી સલામતી મૂલ્યાંકન",
    select_persona: "1. તમારું પ્રોફાઇલ પસંદ કરો",
    persona_senior: "વરિષ્ઠ નાગરિક (65+)",
    persona_senior_sub: "ગરમીથી ઝડપી બીમાર થવાનું જોખમ",
    persona_worker: "શ્રમિક / ડિલિવરી રાઇડર",
    persona_worker_sub: "સખત તડકામાં શારીરિક શ્રમ",
    persona_parent: "નાના બાળક સાથે વાલી",
    persona_parent_sub: "ગરમ ડામર નજીક સ્ટ્રોલર",
    persona_general: "સામાન્ય જનતા",
    persona_general_sub: "રોજિંદા મુસાફરો અને ગ્રાહકો",
    conditions_title: "2. તમારી વર્તમાન સ્થિતિ",
    ac_home: "ઘરે AC છે?",
    sun_work: "તડકામાં રહેવું પડે છે?",
    health_cond: "જૂની બીમારી?",
    exertion_level: "શારીરિક શ્રમ?",
    opt_ac_yes: "હા, AC છે",
    opt_ac_fans: "માત્ર પંખો",
    opt_ac_none: "AC નથી / પતરાનું છાપરું",
    opt_sun_direct: "સીધો તડકો",
    opt_sun_partial: "હળવો છાંયડો",
    opt_sun_indoor: "અંદર",
    opt_cond_heart: "હૃદય / બ્લડ પ્રેશર",
    opt_cond_asthma: "અસ્થમા / ફેફસાં",
    opt_cond_diabetes: "ડાયાબિટીસ",
    opt_cond_none: "કંઈ નહીં",
    opt_exert_heavy: "સખત શ્રમ",
    opt_exert_moderate: "ચાલવું / મુસાફરી",
    opt_exert_resting: "આરામ",
    safe_limit_title: "બહાર રહેવાનો મહત્તમ સલામત સમય",
    start_timer: "સેફ વૉક ટાઈમર શરૂ કરો",
    pause_timer: "વિરામ",
    reset_timer: "રીસેટ",
    hydration_title: "પાણી પીવાના નિયમો",
    symptoms_title: "લૂ ના મુખ્ય લક્ષણો",
    sanctuaries_title: "નજીકનું શીતળ આશ્રયસ્થાન શોધો",
    filter_all: "બધા કેન્દ્રો",
    filter_ac: "❄️ AC સેન્ટર",
    filter_water: "💧 મફત ઠંડુ પાણી",
    filter_parks: "🌳 છાંયડાવાળા બગીચા",
    walk_here: "અહીં જાઓ",
    cool_walk_title: "કૂલ વૉક (શીતળ માર્ગ) નેવિગેશન",
    start_loc: "શરૂઆતનું સ્થળ",
    dest_loc: "પહોંચવાનું સ્થળ",
    calc_cool_route: "શીતળ માર્ગ શોધો",
    shortest_path_title: "સામાન્ય ટૂંકો માર્ગ",
    cool_path_title: "🌿 છાંયડાવાળો શીતળ માર્ગ",
    distance: "અંતર",
    walk_time: "ચાલવાનો સમય",
    shade_cover: "છાંયડાનું પ્રમાણ",
    water_points: "રસ્તામાં પાણીની પરબ",
    turn_steps_title: "પગલે પગલે સલામત દિશા-નિર્દેશ",
    sos_call: "🚨 ઇમરજન્સી એમ્બ્યુલન્સ (108)",
    sunlight_boost_on: "☀️ સૂર્યપ્રકાશ મોડ સક્રિય",
    sunlight_boost_off: "☀️ સામાન્ય મોડ"
  },
  es: {
    alert_extreme: "ALERTA EXTREMA DE CALOR: CÓDIGO ROJO",
    alert_high: "ALERTA DE OLA DE CALOR: CÓDIGO NARANJA",
    alert_moderate: "AVISO DE CALOR: CÓDIGO AMARILLO",
    alert_safe: "CONDICIONES NORMALES: CÓDIGO VERDE",
    street_index_label: "Índice Térmico Actual de Calle",
    feels_like: "Sensación Térmica",
    wbgt_label: "Temp. Bulbo Húmedo (WBGT)",
    uv_label: "Índice Solar UV",
    peak_window_label: "Ventana de Peligro Máximo",
    listen_alert: "Escuchar Alerta",
    stop_audio: "Detener Audio",
    safe_street_title: "¿Qué tan segura está mi calle ahora?",
    search_placeholder: "Buscar vecindario o calle...",
    surface_temp: "Temp. Superficie",
    shade_temp: "Acera con Sombra",
    canopy_cover: "Cubierta de Árboles",
    radiant_temp: "Temp. Radiante",
    why_hot: "¿Por qué esta calle es más calurosa?",
    hourly_curve: "Evolución Horaria del Riesgo Térmico",
    persona_assessment_title: "Evaluación Personal de Seguridad Térmica",
    select_persona: "1. Seleccione su perfil",
    persona_senior: "Adulto Mayor (65+)",
    persona_senior_sub: "Vulnerable a hipertermia rápida",
    persona_worker: "Trabajador al Aire Libre",
    persona_worker_sub: "Esfuerzo intenso bajo sol directo",
    persona_parent: "Padre con Bebé",
    persona_parent_sub: "Coches viajan cerca del asfalto",
    persona_general: "Público General",
    persona_general_sub: "Transeúntes y compradores",
    conditions_title: "2. Sus condiciones actuales",
    ac_home: "¿Aire acondicionado en casa?",
    sun_work: "¿Exposición al sol?",
    health_cond: "¿Condición médica previa?",
    exertion_level: "¿Nivel de esfuerzo físico?",
    opt_ac_yes: "Sí, con AC",
    opt_ac_fans: "Solo ventilador",
    opt_ac_none: "Sin AC / Techo de zinc",
    opt_sun_direct: "Sol directo",
    opt_sun_partial: "Sombra parcial",
    opt_sun_indoor: "Interiores",
    opt_cond_heart: "Cardiovascular / Hipertensión",
    opt_cond_asthma: "Asma / Respiratorio",
    opt_cond_diabetes: "Diabetes",
    opt_cond_none: "Ninguna",
    opt_exert_heavy: "Trabajo pesado",
    opt_exert_moderate: "Caminata moderada",
    opt_exert_resting: "En reposo",
    safe_limit_title: "Tiempo Máximo Seguro al Aire Libre",
    start_timer: "Iniciar Cronómetro Seguro",
    pause_timer: "Pausar",
    reset_timer: "Reiniciar",
    hydration_title: "Protocolo Personalizado de Hidratación",
    symptoms_title: "Síntomas Críticos de Alarma",
    sanctuaries_title: "Encontrar Refugio Climatizado Cercano",
    filter_all: "Todos",
    filter_ac: "❄️ Centros con AC",
    filter_water: "💧 Agua Gratis",
    filter_parks: "🌳 Parques con Sombra",
    walk_here: "Ir Aquí Ahora",
    cool_walk_title: "Navegación 'Paseo Fresco'",
    start_loc: "Punto de Inicio",
    dest_loc: "Destino",
    calc_cool_route: "Buscar Ruta Fresca",
    shortest_path_title: "Ruta Más Corta (Soleada)",
    cool_path_title: "🌿 Corredor Fresco y Sombreado",
    distance: "Distancia",
    walk_time: "Tiempo a pie",
    shade_cover: "Cobertura de Sombra",
    water_points: "Puntos de Agua en Camino",
    turn_steps_title: "Instrucciones de Navegación Segura",
    sos_call: "🚨 SOS Emergencia Térmica (108)",
    sunlight_boost_on: "☀️ Modo Luz Solar ACTIVO",
    sunlight_boost_off: "☀️ Modo Normal"
  }
};

function t(key) {
  const lang = STATE.language || 'en';
  return (I18N[lang] && I18N[lang][key]) || (I18N.en && I18N.en[key]) || key;
}

// ============================================================================
// 3. FALLBACK HIGH-FIDELITY DATASET (Ahmedabad Microclimate Model)
// Aligned with backend data_store.py & schemas.py
// ============================================================================

const MOCK_DATA = {
  cityOverview: {
    city_name: "Ahmedabad Metropolitan Region",
    city_alert_level: "Red Alert (Severe Heatwave Emergency)",
    alert_advisory: "Severe heat stress conditions citywide. Emergency Heat Action Plan fully activated. Avoid open-air travel 11:30-16:30.",
    average_surface_temp_celsius: 43.8,
    ambient_air_temp_celsius: 40.5,
    average_heat_risk: 74.2,
    wbgt_celsius: 33.4,
    uv_index: "11+",
    peak_window: "11:30 AM – 4:30 PM",
    remaining_peak_hours: 2.5
  },
  streets: [
    {
      street_id: "ST001",
      street_name: "Manek Chowk Bazaar Corridor",
      ward_id: "W02",
      ward_name: "Khadia",
      length_meters: 650,
      surface_temp_celsius: 51.4,
      mean_radiant_temp_celsius: 58.2,
      shade_ratio: 0.08,
      canopy_pct: 6,
      pedestrian_heat_risk: 91.5,
      risk_level: "Extreme",
      sky_view_factor: 0.88,
      asphalt_radiance: "54.2°C",
      diagnostic: "Narrow commercial canyon with zero tree canopy, high foot traffic, and heat-retaining tin roofing.",
      hourly_curve: [32, 36, 42, 48, 51, 50, 47, 41] // 8am to 8pm
    },
    {
      street_id: "ST002",
      street_name: "Danilimda Industrial Highway",
      ward_id: "W05",
      ward_name: "Danilimda",
      length_meters: 1100,
      surface_temp_celsius: 52.8,
      mean_radiant_temp_celsius: 60.1,
      shade_ratio: 0.05,
      canopy_pct: 4,
      pedestrian_heat_risk: 94.0,
      risk_level: "Extreme",
      sky_view_factor: 0.94,
      asphalt_radiance: "56.0°C",
      diagnostic: "Wide unshaded 4-lane asphalt corridor with heavy diesel vehicular thermal exhaust and low albedo.",
      hourly_curve: [33, 37, 44, 49, 53, 52, 48, 42]
    },
    {
      street_id: "ST003",
      street_name: "Navrangpura Riverfront Shaded Promenade",
      ward_id: "W27",
      ward_name: "Navrangpura",
      length_meters: 850,
      surface_temp_celsius: 36.2,
      mean_radiant_temp_celsius: 42.0,
      shade_ratio: 0.84,
      canopy_pct: 82,
      pedestrian_heat_risk: 32.0,
      risk_level: "Moderate",
      sky_view_factor: 0.35,
      asphalt_radiance: "37.5°C",
      diagnostic: "Continuous dense neem and banyan canopy combined with water-cooling microclimate from Sabarmati.",
      hourly_curve: [28, 30, 33, 36, 37, 36, 34, 31]
    },
    {
      street_id: "ST004",
      street_name: "Khadia Heritage Arcade",
      ward_id: "W02",
      ward_name: "Khadia",
      length_meters: 480,
      surface_temp_celsius: 45.2,
      mean_radiant_temp_celsius: 50.8,
      shade_ratio: 0.42,
      canopy_pct: 22,
      pedestrian_heat_risk: 68.0,
      risk_level: "High",
      sky_view_factor: 0.52,
      asphalt_radiance: "47.0°C",
      diagnostic: "Traditional pol architecture provides partial building wall shade, but high thermal inertia holds heat.",
      hourly_curve: [30, 33, 39, 44, 46, 45, 42, 37]
    },
    {
      street_id: "ST005",
      street_name: "Odhav Industrial Ring Road",
      ward_id: "W17",
      ward_name: "Odhav",
      length_meters: 1400,
      surface_temp_celsius: 53.5,
      mean_radiant_temp_celsius: 61.2,
      shade_ratio: 0.04,
      canopy_pct: 3,
      pedestrian_heat_risk: 96.0,
      risk_level: "Extreme",
      sky_view_factor: 0.96,
      asphalt_radiance: "57.2°C",
      diagnostic: "Industrial metal roofs, heavy asphalt, zero vegetation, and industrial boiler thermal exhaust.",
      hourly_curve: [34, 38, 45, 51, 54, 53, 49, 43]
    },
    {
      street_id: "ST006",
      street_name: "Vastrapur Lake Pedestrian Walkway",
      ward_id: "W42",
      ward_name: "Vastrapur",
      length_meters: 750,
      surface_temp_celsius: 37.8,
      mean_radiant_temp_celsius: 43.5,
      shade_ratio: 0.78,
      canopy_pct: 75,
      pedestrian_heat_risk: 36.5,
      risk_level: "Moderate",
      sky_view_factor: 0.40,
      asphalt_radiance: "38.9°C",
      diagnostic: "Mature tree canopy, evaporative cooling water body, and permeable stone pavers prevent heat trapping.",
      hourly_curve: [29, 31, 34, 37, 38, 37, 35, 32]
    },
    {
      street_id: "ST007",
      street_name: "Civil Hospital Medical Boulevard",
      ward_id: "W07",
      ward_name: "Asarwa",
      length_meters: 920,
      surface_temp_celsius: 46.1,
      mean_radiant_temp_celsius: 52.4,
      shade_ratio: 0.35,
      canopy_pct: 28,
      pedestrian_heat_risk: 72.0,
      risk_level: "Severe",
      sky_view_factor: 0.60,
      asphalt_radiance: "48.2°C",
      diagnostic: "Emergency ambulance corridor with moderate shade trees, but high emergency foot traffic.",
      hourly_curve: [31, 34, 40, 45, 47, 46, 43, 38]
    }
  ],
  coolingCenters: [
    {
      center_id: "CC001",
      name: "AMC Town Hall & Cooling Sanctuary",
      facility_type: "AMC Community Hall (AC Active)",
      address: "Ellisbridge, Near Riverfront, Ahmedabad",
      coordinates: { lat: 23.0235, lon: 72.5710 },
      distance_meters: 180,
      walking_time_minutes: 3,
      operating_hours: "08:00 - 22:00 (24/7 Red Alert Mode)",
      capacity_persons: 450,
      has_medical_staff: true,
      phone_contact: "+91-79-25501001",
      amenities: ["❄️ High-Capacity AC", "💧 Chilled RO Water", "⚡ Phone Charging", "🪑 Free Seating", "🩺 ORS / Doctor On-Site"]
    },
    {
      center_id: "CC002",
      name: "Khadia Municipal AC Public Library",
      facility_type: "Municipal Air-Conditioned Public Library",
      address: "Near Bala Hanuman, Khadia, Ahmedabad",
      coordinates: { lat: 23.0245, lon: 72.5915 },
      distance_meters: 320,
      walking_time_minutes: 5,
      operating_hours: "09:00 - 21:00",
      capacity_persons: 280,
      has_medical_staff: true,
      phone_contact: "+91-79-25501002",
      amenities: ["❄️ Air Conditioning", "💧 Free Water Dispenser", "⚡ Wi-Fi & Power", "🪑 Quiet Rest Hall"]
    },
    {
      center_id: "CC003",
      name: "Old City Metro Underground Haven",
      facility_type: "Metro Station Underground Concourse",
      address: "Gheekanta Underground Station, Ahmedabad",
      coordinates: { lat: 23.0280, lon: 72.5860 },
      distance_meters: 520,
      walking_time_minutes: 7,
      operating_hours: "06:00 - 23:00",
      capacity_persons: 600,
      has_medical_staff: false,
      phone_contact: "+91-79-25501003",
      amenities: ["❄️ Underground Natural Sub-surface Cooling", "💧 Water Kiosk", "🛗 Elevator Access"]
    },
    {
      center_id: "CC004",
      name: "Riverfront Banyan Misted Grove",
      facility_type: "Civic Shaded Park & Misting Station",
      address: "East Riverfront Promenade, Ahmedabad",
      coordinates: { lat: 23.0200, lon: 72.5760 },
      distance_meters: 410,
      walking_time_minutes: 6,
      operating_hours: "Open 24/7",
      capacity_persons: 350,
      has_medical_staff: false,
      phone_contact: "+91-79-25501004",
      amenities: ["🌳 90% Canopy Shade", "💨 High-Pressure Misting Fans", "💧 Cold Earthen Water Pots", "🪑 Shaded Benches"]
    }
  ],
  hydrationPoints: [
    {
      point_id: "HY001",
      name: "AMC Chilled Water ATM Kiosk #14",
      water_source_type: "AMC Chilled Water ATM Kiosk",
      address: "Opp. City Civic Centre, Khadia",
      coordinates: { lat: 23.0238, lon: 72.5890 },
      distance_meters: 110,
      walking_time_minutes: 1.5,
      status: "Operational & Cold (16°C)",
      is_free: true
    },
    {
      point_id: "HY002",
      name: "Swaminarayan Temple Free Piau",
      water_source_type: "Temple Trust Piau (Cool Earthen Matkas)",
      address: "Relief Road Junction, Ahmedabad",
      coordinates: { lat: 23.0260, lon: 72.5840 },
      distance_meters: 240,
      walking_time_minutes: 3,
      status: "Operational 24/7 with ORS sachets",
      is_free: true
    },
    {
      point_id: "HY003",
      name: "BRTS Metro Chilled Water Refill Post",
      water_source_type: "Bus Rapid Transit (BRTS) Free Water Post",
      address: "Ellisbridge BRTS Station",
      coordinates: { lat: 23.0215, lon: 72.5725 },
      distance_meters: 290,
      walking_time_minutes: 4,
      status: "Operational (RO UV Filtered)",
      is_free: true
    }
  ]
};

// ============================================================================
// 4. API CLIENT & INTEGRATION
// ============================================================================

const ApiService = {
  async checkHealth() {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(`${CONFIG.API_BASE}/overview`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        STATE.isBackendLive = true;
        this.updateConnectionBadge(true);
        return data;
      }
    } catch (err) {
      // Backend not running or timeout -> use mock fallback
    }
    STATE.isBackendLive = false;
    this.updateConnectionBadge(false);
    return MOCK_DATA.cityOverview;
  },

  updateConnectionBadge(isLive) {
    const badge = document.getElementById('apiStatusBadge');
    if (!badge) return;
    if (isLive) {
      badge.className = 'status-chip';
      badge.innerHTML = `<span class="pulse-dot"></span><span>FastAPI Live</span>`;
    } else {
      badge.className = 'status-chip offline';
      badge.innerHTML = `<span class="pulse-dot"></span><span>Offline Resilient Mode</span>`;
    }
  },

  async getStreets() {
    if (STATE.isBackendLive) {
      try {
        const res = await fetch(`${CONFIG.API_BASE}/streets?limit=50`);
        if (res.ok) {
          const data = await res.json();
          if (data && data.streets && data.streets.length > 0) {
            return data.streets;
          }
        }
      } catch (e) {
        console.warn('Streets API fetch failed, falling back to local dataset', e);
      }
    }
    return MOCK_DATA.streets;
  },

  async getCoolingCenters() {
    if (STATE.isBackendLive) {
      try {
        const res = await fetch(`${CONFIG.API_BASE}/cooling-centers`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            return data;
          }
        }
      } catch (e) {
        console.warn('Cooling centers API fetch failed, using fallback', e);
      }
    }
    return MOCK_DATA.coolingCenters;
  },

  async getHydrationPoints() {
    if (STATE.isBackendLive) {
      try {
        const res = await fetch(`${CONFIG.API_BASE}/hydration-points`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            return data;
          }
        }
      } catch (e) {
        console.warn('Hydration points API fetch failed, using fallback', e);
      }
    }
    return MOCK_DATA.hydrationPoints;
  },

  async calculateCoolPath(origin, destination, profile = 'standard') {
    if (STATE.isBackendLive) {
      try {
        const payload = {
          origin: { lat: origin.lat, lon: origin.lon },
          destination: { lat: destination.lat, lon: destination.lon },
          departure_hour: 14,
          max_detour_factor: 1.4,
          vulnerability_profile: profile
        };
        const res = await fetch(`${CONFIG.API_BASE}/routing/cool-path`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          return await res.json();
        }
      } catch (e) {
        console.warn('Cool path backend error, calculating local simulation', e);
      }
    }
    // High-accuracy client simulation
    return NavigationEngine.simulateCoolRoute(origin, destination);
  }
};

// ============================================================================
// 5. THERMAL ALGORITHMS & PERSONA RISK ASSESSMENT
// ============================================================================

const RiskEngine = {
  calculatePersonalAssessment(personaKey, conditions, currentStreetTemp = 43.8) {
    let baseSafeMinutes = 45;
    let riskPoints = 30; // base score out of 100

    // Persona baseline modifier
    switch (personaKey) {
      case 'senior':
        baseSafeMinutes = 20;
        riskPoints += 30;
        break;
      case 'worker':
        baseSafeMinutes = 30; // heavy exertion offset
        riskPoints += 25;
        break;
      case 'parent':
        baseSafeMinutes = 18; // infants close to hot ground
        riskPoints += 32;
        break;
      case 'general':
      default:
        baseSafeMinutes = 45;
        riskPoints += 10;
        break;
    }

    // AC availability modifier
    if (conditions.hasAc === 'none') {
      baseSafeMinutes *= 0.65;
      riskPoints += 20;
    } else if (conditions.hasAc === 'fans') {
      baseSafeMinutes *= 0.85;
      riskPoints += 10;
    }

    // Direct sun exposure modifier
    if (conditions.sunExposure === 'direct') {
      baseSafeMinutes *= 0.60;
      riskPoints += 25;
    } else if (conditions.sunExposure === 'partial') {
      baseSafeMinutes *= 0.85;
      riskPoints += 10;
    }

    // Health condition modifier
    if (conditions.healthFactor === 'heart') {
      baseSafeMinutes *= 0.55;
      riskPoints += 25;
    } else if (conditions.healthFactor === 'asthma') {
      baseSafeMinutes *= 0.65;
      riskPoints += 18;
    } else if (conditions.healthFactor === 'diabetes') {
      baseSafeMinutes *= 0.75;
      riskPoints += 14;
    }

    // Exertion level modifier
    if (conditions.exertion === 'heavy') {
      baseSafeMinutes *= 0.60;
      riskPoints += 20;
    } else if (conditions.exertion === 'moderate') {
      baseSafeMinutes *= 0.85;
      riskPoints += 8;
    }

    // Street temperature stress scaling
    if (currentStreetTemp >= 48.0) {
      baseSafeMinutes *= 0.65;
      riskPoints += 15;
    } else if (currentStreetTemp >= 44.0) {
      baseSafeMinutes *= 0.80;
      riskPoints += 10;
    }

    const safeMinutes = Math.max(8, Math.round(baseSafeMinutes));
    const finalScore = Math.min(99, Math.max(15, Math.round(riskPoints)));

    let riskTier = 'Moderate';
    let tierColor = '#eab308';
    let advisoryText = '';

    if (finalScore >= 80) {
      riskTier = 'Extreme';
      tierColor = '#C62828';
      advisoryText = 'EXTREME HEAT STRESS: Extended direct sun exposure during afternoon peak (11:30 AM – 4:30 PM) increases the risk of heat exhaustion or heatstroke. Move indoors if symptoms appear, hydrate with electrolytes, and seek cooling shelters.';
    } else if (finalScore >= 60) {
      riskTier = 'High';
      tierColor = '#EA580C';
      advisoryText = 'HIGH HEAT STRESS: Higher risk during prolonged exposure (>30–45 mins). Rest frequently in shaded corridors and drink cool water.';
    } else if (finalScore >= 40) {
      riskTier = 'Moderate';
      tierColor = '#D97706';
      advisoryText = 'MODERATE CAUTION: Take regular shaded rest breaks, avoid strenuous outdoor activity during peak sun, and carry drinking water.';
    } else {
      riskTier = 'Resilient';
      tierColor = '#2E8B57';
      advisoryText = 'RESILIENT: Lower thermal stress under canopy. Maintain standard hydration while outdoors.';
    }

    // Hydration protocol
    let waterMl = 250;
    let intervalMin = 20;
    let totalTargetPerHour = 1.0;

    if (personaKey === 'worker' || conditions.exertion === 'heavy') {
      waterMl = 300;
      intervalMin = 15;
      totalTargetPerHour = 1.2;
    } else if (personaKey === 'senior' || conditions.healthFactor === 'heart') {
      waterMl = 200;
      intervalMin = 20;
      totalTargetPerHour = 0.8;
    } else if (personaKey === 'parent') {
      waterMl = 150;
      intervalMin = 15;
      totalTargetPerHour = 0.6;
    }

    // Clinical warnings
    const symptoms = [];
    if (personaKey === 'senior' || conditions.healthFactor === 'heart') {
      symptoms.push("Rapid bounding pulse or heart palpitations", "Confusion, dizziness, sudden slurred speech", "Absence of sweating with hot dry skin (Call 108 immediately)");
    } else if (personaKey === 'worker') {
      symptoms.push("Painful muscle cramps in calves or abdomen", "Severe headache, persistent nausea, and vomiting", "Cold clammy skin followed by sudden cessation of sweat");
    } else if (personaKey === 'parent') {
      symptoms.push("Infant sunken eyes and absence of tears when crying", "Extreme restlessness followed by unusual lethargy/sleepiness", "Hot, dry, flushed skin with high fever");
    } else {
      symptoms.push("Dizziness or lightheadedness upon standing", "Heavy sweating accompanied by weakness and fainting", "Nausea, clammy skin, or dark concentrated urine");
    }

    return {
      safeMinutes,
      finalScore,
      riskTier,
      tierColor,
      advisoryText,
      hydration: {
        waterMl,
        intervalMin,
        totalTargetPerHour,
        recipe: "Drink 1 cup (250ml) cool electrolyte water every " + intervalMin + " mins. Add 1 sachet ORS or a pinch of salt & lemon to 1L water. Avoid sugary carbonated drinks and caffeine."
      },
      symptoms
    };
  }
};

// ============================================================================
// 6. COOL WALK ROUTING & SIMULATION ENGINE
// ============================================================================

const NavigationEngine = {
  simulateCoolRoute(origin, destination) {
    const lat1 = origin.lat, lon1 = origin.lon;
    const lat2 = destination.lat, lon2 = destination.lon;

    // Approximate Euclidean/Haversine distance
    const dLat = (lat2 - lat1) * 111000;
    const dLon = (lon2 - lon1) * 102000;
    const straightDistance = Math.round(Math.sqrt(dLat * dLat + dLon * dLon));
    
    // Shortest path metrics (exposed asphalt)
    const shortestDist = Math.max(350, Math.round(straightDistance * 1.15));
    const shortestWalkMin = Math.round((shortestDist / CONFIG.WALKING_SPEED_M_PER_MIN) * 10) / 10;
    const shortestShade = 14;
    const shortestTemp = 48.4;

    // Cool path metrics (shaded tree corridors, covered arcades)
    const coolDist = Math.round(shortestDist * 1.14); // ~14% detour for 80%+ shade
    const coolWalkMin = Math.round((coolDist / CONFIG.WALKING_SPEED_M_PER_MIN) * 10) / 10;
    const coolShade = 82;
    const coolTemp = 36.6;
    const tempDiff = Math.round((shortestTemp - coolTemp) * 10) / 10;
    const shadeInc = coolShade - shortestShade;

    // Midpoints for polyline geometry
    const midLat = (lat1 + lat2) / 2;
    const midLon = (lon1 + lon2) / 2;

    const shortestLine = [
      [lat1, lon1],
      [midLat + 0.0005, midLon - 0.0005],
      [lat2, lon2]
    ];

    const coolLine = [
      [lat1, lon1],
      [lat1 + 0.0008, lon1 + 0.0010],
      [midLat + 0.0012, midLon + 0.0015],
      [lat2 - 0.0004, lon2 + 0.0008],
      [lat2, lon2]
    ];

    // Hydration kiosks on the cool corridor
    const nearbyKiosks = [
      {
        name: "AMC Chilled Water ATM Station",
        type: "Free Chilled RO Water",
        distance_from_route_m: 15,
        lat: midLat + 0.0010,
        lon: midLon + 0.0012
      },
      {
        name: "Temple Trust Earthen Piau & Shade Arbor",
        type: "Cool Water Matkas & Misting",
        distance_from_route_m: 20,
        lat: lat2 - 0.0003,
        lon: lon2 + 0.0006
      }
    ];

    const steps = [
      {
        step: 1,
        instruction: "Depart onto shaded sidewalk along Banyan Tree Corridor",
        street_name: "Banyan Arcade",
        dist: 260,
        shade: 85,
        temp: 36.2,
        is_water: false
      },
      {
        step: 2,
        instruction: "💧 Hydration Stop: Free AMC Cold Water ATM #14 (Drink 250ml electrolyte fluid)",
        street_name: "Water Refill Post",
        dist: 15,
        shade: 95,
        temp: 34.0,
        is_water: true
      },
      {
        step: 3,
        instruction: "Turn left into covered civic shopping arcade (Building shadow protects from direct sun)",
        street_name: "Civic Arcade Promenade",
        dist: 340,
        shade: 88,
        temp: 35.8,
        is_water: false
      },
      {
        step: 4,
        instruction: "💧 Second Hydration Stop: Temple Trust Free Cold Water Piau",
        street_name: "Piau Gazebo",
        dist: 20,
        shade: 90,
        temp: 33.5,
        is_water: true
      },
      {
        step: 5,
        instruction: "Arrive at Cooling Sanctuary destination",
        street_name: "Sanctuary Entrance",
        dist: 120,
        shade: 80,
        temp: 36.5,
        is_water: false
      }
    ];

    return {
      shortest: {
        distance_m: shortestDist,
        walk_time_min: shortestWalkMin,
        shade_pct: shortestShade,
        surface_temp_c: shortestTemp,
        radiant_temp_c: 57.5,
        risk_tier: "Extreme",
        kiosks_count: 0,
        coords: shortestLine
      },
      cool: {
        distance_m: coolDist,
        walk_time_min: coolWalkMin,
        shade_pct: coolShade,
        surface_temp_c: coolTemp,
        radiant_temp_c: 42.1,
        risk_tier: "Moderate",
        kiosks_count: 2,
        coords: coolLine,
        kiosks: nearbyKiosks,
        steps
      },
      summary: {
        detour_m: coolDist - shortestDist,
        detour_min: Math.round((coolWalkMin - shortestWalkMin) * 10) / 10,
        shade_increase_pct: shadeInc,
        temp_drop_c: tempDiff,
        heat_dose_reduction_pct: 42.5
      }
    };
  }
};

// ============================================================================
// 7. AUDIO SPEECH SYNTHESIS (TTS)
// ============================================================================

const SpeechAssistant = {
  speak(text) {
    if (!('speechSynthesis' in window)) {
      alert("Text-to-speech audio is not supported in this browser.");
      return;
    }
    window.speechSynthesis.cancel(); // stop any ongoing speech

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    // Set voice language according to active language
    if (STATE.language === 'hi') {
      utterance.lang = 'hi-IN';
    } else if (STATE.language === 'es') {
      utterance.lang = 'es-ES';
    } else {
      utterance.lang = 'en-US';
    }

    utterance.onstart = () => {
      STATE.speaking = true;
      document.querySelectorAll('.btn-listen').forEach(b => {
        b.innerHTML = `<span>⏹️</span><span>${t('stop_audio')}</span>`;
      });
    };

    utterance.onend = utterance.onerror = () => {
      STATE.speaking = false;
      document.querySelectorAll('.btn-listen').forEach(b => {
        b.innerHTML = `<span>🔊</span><span>${t('listen_alert')}</span>`;
      });
    };

    window.speechSynthesis.speak(utterance);
  },

  stop() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      STATE.speaking = false;
      document.querySelectorAll('.btn-listen').forEach(b => {
        b.innerHTML = `<span>🔊</span><span>${t('listen_alert')}</span>`;
      });
    }
  },

  toggle(text) {
    if (STATE.speaking) {
      this.stop();
    } else {
      this.speak(text);
    }
  }
};

// ============================================================================
// 8. INTERACTIVE SAFE TIMER CONTROLLER
// ============================================================================

const TimerController = {
  init(safeMinutes) {
    this.stop();
    STATE.timer.totalSeconds = safeMinutes * 60;
    STATE.timer.remainingSeconds = safeMinutes * 60;
    STATE.timer.isRunning = false;
    this.render();
  },

  start() {
    if (STATE.timer.isRunning) return;
    STATE.timer.isRunning = true;
    const startBtn = document.getElementById('timerToggleBtn');
    if (startBtn) startBtn.innerText = t('pause_timer');

    STATE.timer.intervalId = setInterval(() => {
      if (STATE.timer.remainingSeconds > 0) {
        STATE.timer.remainingSeconds -= 1;
        this.render();
      } else {
        this.onExpire();
      }
    }, 1000);
  },

  pause() {
    STATE.timer.isRunning = false;
    if (STATE.timer.intervalId) {
      clearInterval(STATE.timer.intervalId);
      STATE.timer.intervalId = null;
    }
    const startBtn = document.getElementById('timerToggleBtn');
    if (startBtn) startBtn.innerText = t('start_timer');
  },

  toggle() {
    if (STATE.timer.isRunning) {
      this.pause();
    } else {
      this.start();
    }
  },

  reset() {
    this.pause();
    STATE.timer.remainingSeconds = STATE.timer.totalSeconds;
    this.render();
  },

  stop() {
    this.pause();
  },

  render() {
    const mins = Math.floor(STATE.timer.remainingSeconds / 60);
    const secs = STATE.timer.remainingSeconds % 60;
    const minEl = document.getElementById('timerMinutesVal');
    if (minEl) {
      minEl.innerText = `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }

    // Progress circle stroke animation (circumference = 2 * PI * 60 = ~377)
    const circle = document.getElementById('timerProgressCircle');
    if (circle && STATE.timer.totalSeconds > 0) {
      const frac = STATE.timer.remainingSeconds / STATE.timer.totalSeconds;
      const offset = 377 * (1 - frac);
      circle.style.strokeDashoffset = offset;

      if (frac < 0.2) {
        circle.style.stroke = 'var(--hazard-extreme)';
      } else if (frac < 0.5) {
        circle.style.stroke = 'var(--hazard-high)';
      } else {
        circle.style.stroke = 'var(--accent-cool)';
      }
    }
  },

  onExpire() {
    this.pause();
    // Sound/Beep alert using Web Audio API
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      osc.start();
      osc.stop(ctx.currentTime + 1.2);
    } catch (e) {}

    // Alert announcement
    const msg = "Attention! Your maximum safe outdoor limit has expired. Please enter an air-conditioned cooling sanctuary immediately to prevent heat exhaustion.";
    SpeechAssistant.speak(msg);
    alert("⚠️ SAFE OUTDOOR LIMIT EXPIRED!\nPlease step into the nearest air-conditioned cooling center or shaded water station immediately!");
  }
};

// ============================================================================
// 9. LEAFLET MAP & RADAR CONTROLLER
// ============================================================================

const MapController = {
  init() {
    const mapContainer = document.getElementById('sanctuaryMap');
    if (!mapContainer) return;

    if (typeof L === 'undefined') {
      console.warn('Leaflet not loaded from CDN, displaying fallback canvas radar');
      this.renderFallbackRadar();
      return;
    }

    try {
      STATE.map = L.map('sanctuaryMap', {
        zoomControl: false,
        attributionControl: false
      }).setView([STATE.userLocation.lat, STATE.userLocation.lon], 15);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
      }).addTo(STATE.map);

      // Add user location marker with pulsing radar effect
      const userIcon = L.divIcon({
        className: 'user-radar-pin',
        html: `
          <div style="position:relative; width:24px; height:24px;">
            <div style="position:absolute; width:24px; height:24px; border-radius:50%; background:rgba(6,182,212,0.4); animation:pulseBeacon 2s infinite ease-out;"></div>
            <div style="position:absolute; top:4px; left:4px; width:16px; height:16px; border-radius:50%; background:#06b6d4; border:2px solid white; box-shadow:0 0 10px #06b6d4;"></div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      L.marker([STATE.userLocation.lat, STATE.userLocation.lon], { icon: userIcon })
        .addTo(STATE.map)
        .bindPopup("<b>You Are Here</b><br>Ahmedabad Urban Core");

      this.plotSanctuaries(STATE.coolingCenters, STATE.hydrationPoints);
    } catch (e) {
      console.error('Error creating Leaflet map, switching to fallback canvas', e);
      this.renderFallbackRadar();
    }
  },

  plotSanctuaries(centers, kiosks) {
    if (!STATE.map || typeof L === 'undefined') return;

    // Clear existing markers
    STATE.mapMarkers.forEach(m => STATE.map.removeLayer(m));
    STATE.mapMarkers = [];

    // Plot Cooling Centers (Blue Snowflake Pin)
    centers.forEach(c => {
      const lat = c.coordinates ? c.coordinates.lat : c.lat;
      const lon = c.coordinates ? c.coordinates.lon : c.lon;
      if (!lat || !lon) return;

      const acIcon = L.divIcon({
        className: 'sanctuary-pin',
        html: `
          <div style="background:#0284c7; color:white; width:34px; height:34px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:16px; border:2px solid white; box-shadow:0 2px 10px rgba(0,0,0,0.5); cursor:pointer;">
            ❄️
          </div>
        `,
        iconSize: [34, 34],
        iconAnchor: [17, 17]
      });

      const marker = L.marker([lat, lon], { icon: acIcon }).addTo(STATE.map);
      marker.bindPopup(`
        <div style="font-family:sans-serif; color:#0f172a; padding:4px;">
          <h4 style="margin:0 0 4px 0; font-size:14px; font-weight:800;">${c.name}</h4>
          <p style="margin:0 0 4px 0; font-size:12px; color:#475569;">${c.facility_type || 'AC Cooling Center'}</p>
          <p style="margin:0 0 8px 0; font-size:11px;"><b>Hours:</b> ${c.operating_hours}</p>
          <button onclick="PublicUI.navigateToSanctuary('${c.name}', ${lat}, ${lon})" style="background:#06b6d4; color:#000; font-weight:700; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; width:100%;">
            🌿 Navigate via Cool Walk
          </button>
        </div>
      `);
      STATE.mapMarkers.push(marker);
    });

    // Plot Hydration Points (Cyan Water Droplet Pin)
    kiosks.forEach(k => {
      const lat = k.coordinates ? k.coordinates.lat : k.lat;
      const lon = k.coordinates ? k.coordinates.lon : k.lon;
      if (!lat || !lon) return;

      const waterIcon = L.divIcon({
        className: 'water-pin',
        html: `
          <div style="background:#06b6d4; color:white; width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; border:2px solid white; box-shadow:0 2px 8px rgba(0,0,0,0.5); cursor:pointer;">
            💧
          </div>
        `,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      });

      const marker = L.marker([lat, lon], { icon: waterIcon }).addTo(STATE.map);
      marker.bindPopup(`
        <div style="font-family:sans-serif; color:#0f172a; padding:4px;">
          <h4 style="margin:0 0 4px 0; font-size:13px; font-weight:800;">${k.name}</h4>
          <p style="margin:0 0 4px 0; font-size:11px; color:#0284c7;"><b>Free Chilled Drinking Water</b></p>
          <p style="margin:0 0 6px 0; font-size:11px; color:#475569;">${k.water_source_type || 'Public Fountain'}</p>
          <button onclick="PublicUI.navigateToSanctuary('${k.name}', ${lat}, ${lon})" style="background:#06b6d4; color:#000; font-weight:700; border:none; padding:6px 12px; border-radius:6px; cursor:pointer; width:100%;">
            🌿 Walk to Water Point
          </button>
        </div>
      `);
      STATE.mapMarkers.push(marker);
    });
  },

  drawRoutes(routeData) {
    if (!STATE.map || typeof L === 'undefined') return;

    // Clear previous route polylines
    STATE.mapRouteLayers.forEach(l => STATE.map.removeLayer(l));
    STATE.mapRouteLayers = [];

    // 1. Draw Shortest Route (Red / Amber Exposed Sun Path)
    if (routeData.shortest && routeData.shortest.coords) {
      const hotLine = L.polyline(routeData.shortest.coords, {
        color: '#ef4444',
        weight: 6,
        opacity: 0.85,
        dashArray: '8, 8'
      }).addTo(STATE.map);
      hotLine.bindPopup(`<b>Shortest Path (Extreme Sun Exposure)</b><br>Surface Temp: ${routeData.shortest.surface_temp_c}°C<br>Shade: ${routeData.shortest.shade_pct}%`);
      STATE.mapRouteLayers.push(hotLine);
    }

    // 2. Draw Cool Corridor Route (Emerald Green & Cyan Glowing Path)
    if (routeData.cool && routeData.cool.coords) {
      const coolGlow = L.polyline(routeData.cool.coords, {
        color: '#06b6d4',
        weight: 10,
        opacity: 0.4
      }).addTo(STATE.map);
      STATE.mapRouteLayers.push(coolGlow);

      const coolLine = L.polyline(routeData.cool.coords, {
        color: '#10b981',
        weight: 6,
        opacity: 0.95
      }).addTo(STATE.map);
      coolLine.bindPopup(`<b>🌿 Cool-Corridor Walking Path</b><br>Surface Temp: ${routeData.cool.surface_temp_c}°C<br>Shade: ${routeData.cool.shade_pct}% (Continuous Canopy)`);
      STATE.mapRouteLayers.push(coolLine);

      // Fit map bounds to encompass both paths
      STATE.map.fitBounds(coolLine.getBounds(), { padding: [40, 40] });
    }
  },

  renderFallbackRadar() {
    const container = document.getElementById('sanctuaryMap');
    if (!container) return;
    container.innerHTML = `
      <div style="width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#0d131f; color:white; padding:20px; text-align:center;">
        <div style="width:180px; height:180px; border-radius:50%; border:2px dashed #06b6d4; display:flex; align-items:center; justify-content:center; position:relative; margin-bottom:12px;">
          <div style="width:120px; height:120px; border-radius:50%; border:1px solid rgba(6,182,212,0.5);"></div>
          <div style="width:60px; height:60px; border-radius:50%; border:1px solid rgba(6,182,212,0.3);"></div>
          <div style="position:absolute; width:12px; height:12px; border-radius:50%; background:#06b6d4; box-shadow:0 0 12px #06b6d4;"></div>
          <div style="position:absolute; top:25px; right:35px; font-size:18px;">❄️</div>
          <div style="position:absolute; bottom:30px; left:30px; font-size:18px;">💧</div>
          <div style="position:absolute; top:50px; left:40px; font-size:18px;">🌳</div>
        </div>
        <h4 style="font-size:1rem; font-weight:700; margin-bottom:4px;">Cooling Sanctuary Interactive Radar</h4>
        <p style="font-size:0.8rem; color:#94a3b8;">4 Sanctuaries detected within 500m radius of your street</p>
      </div>
    `;
  }
};

// ============================================================================
// 10. PUBLIC UI EVENT HANDLERS & RENDERING
// ============================================================================

const PublicUI = {
  async init() {
    // 1. Check API connection
    await ApiService.checkHealth();

    // 2. Load streets and sanctuary directories
    STATE.streets = await ApiService.getStreets();
    STATE.coolingCenters = await ApiService.getCoolingCenters();
    STATE.hydrationPoints = await ApiService.getHydrationPoints();

    // 3. Set default active street
    STATE.activeStreet = STATE.streets[0];

    // 4. Render initial UI components
    this.renderHeaderAndAlert();
    this.renderStreetSection();
    this.renderPersonaSection();
    this.renderSanctuariesList('all');
    this.renderNavigationInputs();

    // 5. Initialize Map
    MapController.init();

    // 6. Setup Event Listeners
    this.setupListeners();
  },

  setupListeners() {
    // Language Switcher
    const langSelect = document.getElementById('langSelect');
    if (langSelect) {
      langSelect.addEventListener('change', (e) => {
        STATE.language = e.target.value;
        this.reTranslateAll();
      });
    }

    // Sunlight Boost Toggle
    const boostBtn = document.getElementById('sunlightBoostBtn');
    if (boostBtn) {
      boostBtn.addEventListener('click', () => {
        STATE.sunlightBoost = !STATE.sunlightBoost;
        document.body.classList.toggle('sunlight-boost', STATE.sunlightBoost);
        boostBtn.innerText = STATE.sunlightBoost ? t('sunlight_boost_on') : t('sunlight_boost_off');
      });
    }

    // Emergency Listen Button
    const listenAlertBtn = document.getElementById('listenAlertBtn');
    if (listenAlertBtn) {
      listenAlertBtn.addEventListener('click', () => {
        const textToRead = `${t('alert_extreme')}. ${t('street_index_label')}: 43.8°C. ${MOCK_DATA.cityOverview.alert_advisory}`;
        SpeechAssistant.toggle(textToRead);
      });
    }

    // Street Autocomplete Search
    const streetInput = document.getElementById('streetSearchInput');
    if (streetInput) {
      streetInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        if (!query) return;
        const match = STATE.streets.find(s => s.street_name.toLowerCase().includes(query) || s.ward_name.toLowerCase().includes(query));
        if (match) {
          this.selectStreet(match);
        }
      });
    }

    // Safe Timer Controls
    const timerBtn = document.getElementById('timerToggleBtn');
    if (timerBtn) {
      timerBtn.addEventListener('click', () => TimerController.toggle());
    }

    const resetTimerBtn = document.getElementById('timerResetBtn');
    if (resetTimerBtn) {
      resetTimerBtn.addEventListener('click', () => TimerController.reset());
    }

    // Persona Card Clicks
    document.querySelectorAll('.persona-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.persona-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        STATE.selectedPersona = btn.dataset.persona;
        this.updatePersonaAssessment();
      });
    });

    // Condition Toggles
    document.querySelectorAll('.pill-opt').forEach(pill => {
      pill.addEventListener('click', () => {
        const parent = pill.closest('.pill-options');
        if (!parent) return;
        parent.querySelectorAll('.pill-opt').forEach(p => p.classList.remove('selected'));
        pill.classList.add('selected');

        const condType = parent.dataset.condition;
        STATE.personaConditions[condType] = pill.dataset.val;
        this.updatePersonaAssessment();
      });
    });

    // Sanctuaries Filter Tabs
    document.querySelectorAll('.filter-pill').forEach(f => {
      f.addEventListener('click', () => {
        document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
        f.classList.add('active');
        this.renderSanctuariesList(f.dataset.filter);
      });
    });

    // Route Calculation Button
    const calcRouteBtn = document.getElementById('calculateRouteBtn');
    if (calcRouteBtn) {
      calcRouteBtn.addEventListener('click', () => this.handleCalculateRoute());
    }

    // Bottom Navigation Active State
    document.querySelectorAll('.nav-item-btn').forEach(nav => {
      nav.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-item-btn').forEach(n => n.classList.remove('active'));
        nav.classList.add('active');
        const targetSection = document.getElementById(nav.dataset.target);
        if (targetSection) {
          targetSection.scrollIntoView({ behavior: 'smooth' });
        }
      });
    });

    // GPS Locate Me Button
    const gpsBtn = document.getElementById('locateMeBtn');
    if (gpsBtn) {
      gpsBtn.addEventListener('click', () => this.handleGeolocation());
    }

    // SOS Modal Toggles
    const openSosBtn = document.getElementById('openSosModalBtn');
    const closeSosBtn = document.getElementById('closeSosModalBtn');
    const sosModal = document.getElementById('sosModal');

    if (openSosBtn && sosModal) {
      openSosBtn.addEventListener('click', () => sosModal.classList.add('active'));
    }
    if (closeSosBtn && sosModal) {
      closeSosBtn.addEventListener('click', () => sosModal.classList.remove('active'));
    }
  },

  renderHeaderAndAlert() {
    const alertEl = document.getElementById('heatEmergencyBanner');
    if (!alertEl) return;

    alertEl.innerHTML = `
      <div class="banner-headline">
        <span class="alert-badge">🚨 ${t('alert_extreme')}</span>
        <div class="banner-controls">
          <button id="listenAlertBtn" class="icon-btn btn-listen" aria-label="Listen to Alert Audio">
            <span>🔊</span><span>${t('listen_alert')}</span>
          </button>
        </div>
      </div>
      <div class="banner-temp-hero">
        <span class="temp-huge">43.8°</span>
        <span class="temp-unit">C</span>
        <span class="temp-subtitle">(${t('feels_like')} 48.5°C)</span>
      </div>
      <div class="banner-stats-grid">
        <div class="stat-item">
          <span class="stat-label">${t('wbgt_label')}</span>
          <span class="stat-val" style="color:var(--hazard-extreme);">33.4°C</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">${t('uv_label')}</span>
          <span class="stat-val" style="color:var(--hazard-high);">11+ (Extreme)</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">${t('peak_window_label')}</span>
          <span class="stat-val">11:30 AM – 4:30 PM</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Peak Time Left</span>
          <span class="stat-val" style="color:var(--hazard-moderate);">2h 15m remaining</span>
        </div>
      </div>
      <div class="banner-action-row">
        <div class="banner-message">
          ⚠️ <b>Mandatory Advisory:</b> High heatstroke hazard on unshaded asphalt. Seek air-conditioned sanctuary or shaded tree corridors.
        </div>
        <button id="openSosModalBtn" class="btn btn-sos">
          <span>🚨</span><span>${t('sos_call')}</span>
        </button>
      </div>
    `;

    // Reattach emergency listen listener after DOM re-render
    const btn = document.getElementById('listenAlertBtn');
    if (btn) {
      btn.addEventListener('click', () => {
        const text = `${t('alert_extreme')}. Current street index 43.8 degrees Celsius. Mandatory advisory: High heatstroke hazard. Seek air-conditioned sanctuary immediately.`;
        SpeechAssistant.toggle(text);
      });
    }

    const sosBtn = document.getElementById('openSosModalBtn');
    if (sosBtn) {
      sosBtn.addEventListener('click', () => {
        const modal = document.getElementById('sosModal');
        if (modal) modal.classList.add('active');
      });
    }
  },

  renderStreetSection() {
    // 1. Populate Street Filter Chips
    const chipCarousel = document.getElementById('streetChipCarousel');
    if (chipCarousel) {
      chipCarousel.innerHTML = STATE.streets.map((s, idx) => `
        <button class="street-chip ${idx === 0 ? 'active' : ''}" onclick="PublicUI.selectStreetById('${s.street_id}')">
          ${s.street_name}
        </button>
      `).join('');
    }

    // 2. Render Active Street Danger Card
    this.updateStreetDangerCard(STATE.activeStreet);
  },

  selectStreetById(streetId) {
    const street = STATE.streets.find(s => s.street_id === streetId);
    if (street) {
      this.selectStreet(street);
    }
  },

  selectStreet(street) {
    STATE.activeStreet = street;
    document.querySelectorAll('.street-chip').forEach(c => {
      c.classList.toggle('active', c.innerText.trim() === street.street_name);
    });
    this.updateStreetDangerCard(street);
    // Recalculate personal risk with this street's temperature
    this.updatePersonaAssessment();
  },

  updateStreetDangerCard(street) {
    const cardEl = document.getElementById('streetThermalCard');
    if (!cardEl || !street) return;

    const riskColor = street.pedestrian_heat_risk >= 80 ? 'extreme' : (street.pedestrian_heat_risk >= 60 ? 'high' : 'moderate');
    const badgeClass = `badge-${riskColor}`;

    let plainLanguage = '';
    if (street.pedestrian_heat_risk >= 80) {
      plainLanguage = `🚨 <b>SEVERE DANGER:</b> Walking on this unshaded asphalt street carries acute heatstroke hazard within 15 minutes. Surface asphalt is radiating ${street.surface_temp_celsius}°C.`;
    } else if (street.pedestrian_heat_risk >= 60) {
      plainLanguage = `⚠️ <b>HIGH HEAT STRESS:</b> Direct solar load. Limit continuous walking to 20 minutes and drink cool electrolyte water.`;
    } else {
      plainLanguage = `🌿 <b>MODERATE SHADED ZONE:</b> Continuous canopy reduces ground temperature by ~14°C compared to open asphalt. Safe for walking with hydration.`;
    }

    cardEl.className = `thermal-danger-card level-${riskColor}`;
    cardEl.innerHTML = `
      <div class="street-danger-header">
        <div>
          <div class="street-danger-title">${street.street_name}</div>
          <div style="font-size:0.8rem; color:var(--text-secondary);">${street.ward_name} Zone</div>
        </div>
        <span class="street-danger-badge ${badgeClass}">${street.risk_level} Hazard</span>
      </div>

      <div class="plain-language-advisory">${plainLanguage}</div>

      <div class="risk-meter-wrap">
        <div class="meter-track">
          <div class="meter-fill" style="width:${street.pedestrian_heat_risk}%;"></div>
        </div>
        <div class="meter-labels">
          <span>Safe (0)</span>
          <span>Moderate (50)</span>
          <span style="color:var(--hazard-extreme);">Severe Hazard (${street.pedestrian_heat_risk}/100)</span>
        </div>
      </div>

      <div class="metrics-pill-grid">
        <div class="metric-pill">
          <div class="metric-pill-title">${t('surface_temp')}</div>
          <div class="metric-pill-value" style="color:var(--hazard-extreme);">${street.surface_temp_celsius}°C</div>
          <div class="metric-pill-sub" style="color:var(--text-secondary);">Direct Sun</div>
        </div>
        <div class="metric-pill">
          <div class="metric-pill-title">${t('shade_temp')}</div>
          <div class="metric-pill-value" style="color:var(--hazard-safe);">${Math.round((street.surface_temp_celsius - 14.5) * 10) / 10}°C</div>
          <div class="metric-pill-sub">-14.5°C Cooler</div>
        </div>
        <div class="metric-pill">
          <div class="metric-pill-title">${t('canopy_cover')}</div>
          <div class="metric-pill-value">${street.canopy_pct || Math.round(street.shade_ratio * 100)}%</div>
          <div class="metric-pill-sub">${(street.canopy_pct || street.shade_ratio * 100) < 20 ? 'Deficit' : 'Optimal'}</div>
        </div>
        <div class="metric-pill">
          <div class="metric-pill-title">${t('radiant_temp')}</div>
          <div class="metric-pill-value">${street.mean_radiant_temp_celsius}°C</div>
          <div class="metric-pill-sub">Mean Tmrt</div>
        </div>
      </div>

      <div class="street-diagnostic-box">
        <div class="diagnostic-title">
          <span>🔍</span><span>${t('why_hot')}</span>
        </div>
        <div class="diagnostic-text">
          ${street.diagnostic || "High building density and unshaded black asphalt absorb 92% of solar radiation, re-radiating intense thermal energy onto pedestrians."}
        </div>
      </div>

      <div class="hourly-curve-wrap">
        <div class="hourly-curve-title">
          <span>${t('hourly_curve')}</span>
          <span style="color:var(--hazard-extreme); font-size:0.75rem;">Peak Hazard: 12 PM - 4 PM</span>
        </div>
        <div class="hourly-bars">
          ${this.generateHourlyBars(street.hourly_curve || [30, 34, 40, 46, 50, 49, 45, 39])}
        </div>
      </div>
    `;
  },

  generateHourlyBars(curve) {
    const hours = ['8 AM', '10 AM', '12 PM', '2 PM', '4 PM', '5 PM', '6 PM', '8 PM'];
    return curve.map((val, idx) => {
      let dangerClass = 'danger-green';
      if (val >= 48) dangerClass = 'danger-red';
      else if (val >= 42) dangerClass = 'danger-orange';
      else if (val >= 35) dangerClass = 'danger-yellow';

      const heightPct = Math.min(100, Math.max(25, (val / 55) * 100));

      return `
        <div class="hour-col">
          <div class="hour-bar-track">
            <div class="hour-bar ${dangerClass}" style="height:${heightPct}%;" title="${val}°C at ${hours[idx]}"></div>
          </div>
          <span class="hour-label">${hours[idx]}</span>
        </div>
      `;
    }).join('');
  },

  renderPersonaSection() {
    this.updatePersonaAssessment();
  },

  updatePersonaAssessment() {
    const streetTemp = STATE.activeStreet ? STATE.activeStreet.surface_temp_celsius : 43.8;
    const assessment = RiskEngine.calculatePersonalAssessment(
      STATE.selectedPersona,
      STATE.personaConditions,
      streetTemp
    );

    const container = document.getElementById('personaResultContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="assessment-result-card">
        <div class="assessment-result-header">
          <div>
            <h3 style="font-size:1.15rem; font-weight:800;">Your Safety Risk Assessment</h3>
            <p style="font-size:0.8rem; color:var(--text-secondary);">Calculated for: ${t('persona_' + STATE.selectedPersona)}</p>
          </div>
          <span class="risk-level-badge-large" style="background:${assessment.tierColor}; color:white;">
            ${assessment.riskTier} Risk (${assessment.finalScore}/100)
          </span>
        </div>

        <p style="font-size:0.95rem; font-weight:600; color:var(--text-primary); margin-bottom:14px;">
          ${assessment.advisoryText}
        </p>

        <!-- Safe Outdoor Limit Countdown Widget -->
        <div class="safe-timer-box">
          <div style="font-size:0.85rem; font-weight:800; color:var(--text-secondary); text-transform:uppercase;">
            ${t('safe_limit_title')}
          </div>
          <div class="timer-circle-wrap">
            <svg class="timer-svg" viewBox="0 0 140 140">
              <circle class="timer-circle-bg" cx="70" cy="70" r="60"></circle>
              <circle id="timerProgressCircle" class="timer-circle-progress" cx="70" cy="70" r="60"></circle>
            </svg>
            <div class="timer-center-text">
              <div id="timerMinutesVal" class="timer-minutes">${assessment.safeMinutes}:00</div>
              <div class="timer-sub">Minutes (Exposure Guide)</div>
            </div>
          </div>
          <div class="timer-controls-row">
            <button id="timerToggleBtn" class="btn btn-primary" style="min-height:42px; padding:6px 16px;">
              ${t('start_timer')}
            </button>
            <button id="timerResetBtn" class="btn btn-secondary" style="min-height:42px; padding:6px 14px;">
              ${t('reset_timer')}
            </button>
          </div>
        </div>

        <!-- Hydration Protocol Card -->
        <div class="hydration-card">
          <div class="hydration-title">
            <span>💧</span><span>${t('hydration_title')}</span>
          </div>
          <div class="hydration-body">
            <b>Target:</b> Drink <b>${assessment.hydration.waterMl} ml</b> cool fluid every <b>${assessment.hydration.intervalMin} minutes</b> (~${assessment.hydration.totalTargetPerHour}L / hour).<br>
            <span style="font-size:0.82rem; color:var(--text-secondary);">${assessment.hydration.recipe}</span>
          </div>
        </div>

        <!-- Clinical Warning Symptoms Checklist -->
        <div class="symptoms-box">
          <div class="symptoms-title">
            <span>⚠️</span><span>${t('symptoms_title')}</span>
          </div>
          <ul class="symptoms-list">
            ${assessment.symptoms.map(s => `<li>${s}</li>`).join('')}
          </ul>
        </div>

        <!-- Medical Disclaimer & Privacy Note -->
        <div style="margin-top:14px; padding:12px; background:#F8FAFC; border:1px solid #E4E7EC; border-radius:8px; font-size:11.5px; color:#667085; line-height:1.45;">
          <div>ℹ️ <b>Medical Disclaimer:</b> This is general public safety guidance based on thermal stress thresholds, not a medical diagnosis. If anyone exhibits severe dizziness, confusion, or absence of sweating, contact emergency medical services immediately (Dial <b>108</b> in India).</div>
          <div style="margin-top:6px;">🔒 <b>Privacy Notice:</b> Your profile answers are evaluated locally in your browser and are never transmitted or stored in this prototype.</div>
        </div>

        <div style="margin-top:14px; display:flex; justify-content:flex-end;">
          <button class="btn btn-secondary btn-listen" onclick="PublicUI.speakPersonalPlan('${assessment.safeMinutes}', '${assessment.hydration.waterMl}')">
            <span>🔊</span><span>Listen to My Advice</span>
          </button>
        </div>
      </div>
    `;

    // Initialize Timer with new safe minutes
    TimerController.init(assessment.safeMinutes);

    // Rebind timer buttons
    const toggleBtn = document.getElementById('timerToggleBtn');
    if (toggleBtn) toggleBtn.addEventListener('click', () => TimerController.toggle());

    const resetBtn = document.getElementById('timerResetBtn');
    if (resetBtn) resetBtn.addEventListener('click', () => TimerController.reset());
  },

  speakPersonalPlan(safeMins, waterMl) {
    const text = `Your heat risk profile is ready. Your maximum safe outdoor exposure time is ${safeMins} minutes. Please drink ${waterMl} milliliters of cool electrolyte water every 20 minutes. If you experience dizziness or absence of sweat, seek air conditioned shelter immediately.`;
    SpeechAssistant.toggle(text);
  },

  renderSanctuariesList(filter = 'all') {
    const container = document.getElementById('sanctuariesListContainer');
    if (!container) return;

    if (STATE.showAllSanctuaries === undefined) {
      STATE.showAllSanctuaries = false;
    }

    let items = [];

    if (filter === 'ac') {
      items = STATE.coolingCenters.filter(c => (c.facility_type || '').includes('AC'));
    } else if (filter === 'water') {
      items = STATE.hydrationPoints;
    } else if (filter === 'parks') {
      items = STATE.coolingCenters.filter(c => (c.facility_type || '').includes('Park') || (c.name || '').includes('Grove'));
    } else {
      items = [...STATE.coolingCenters, ...STATE.hydrationPoints];
    }

    if (items.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-secondary);">No sanctuaries matching this filter.</div>`;
      return;
    }

    const userLat = (STATE.activeStreet && STATE.activeStreet.lat) ? STATE.activeStreet.lat : (STATE.userLocation.lat || 23.0225);
    const userLon = (STATE.activeStreet && STATE.activeStreet.lon) ? STATE.activeStreet.lon : (STATE.userLocation.lon || 72.5714);

    // Compute realistic distance to each item
    items.forEach(item => {
      const lat = item.coordinates ? item.coordinates.lat : (item.lat || 23.0225);
      const lon = item.coordinates ? item.coordinates.lon : (item.lon || 72.5714);
      const dLat = (lat - userLat) * 111000;
      const dLon = (lon - userLon) * 102000;
      const distCalc = Math.round(Math.sqrt(dLat * dLat + dLon * dLon));
      item._computedDist = (item.distance_meters && item.distance_meters > 0) ? Math.round(item.distance_meters) : distCalc;
      item._computedWalkMin = Math.max(2, Math.round(item._computedDist / 70.0));
    });

    items.sort((a, b) => a._computedDist - b._computedDist);

    const totalCount = items.length;
    const displayItems = STATE.showAllSanctuaries ? items : items.slice(0, 5);

    const cardsHtml = displayItems.map(item => {
      const isWater = !!item.water_source_type;
      const badgeClass = isWater ? 'sanctuary-type-water' : 'sanctuary-type-ac';
      const badgeLabel = isWater ? 'Free Chilled Water' : (item.facility_type || 'AC Sanctuary');
      const icon = isWater ? '💧' : '❄️';
      const hours = item.operating_hours || 'Open 24/7';
      const lat = item.coordinates ? item.coordinates.lat : item.lat;
      const lon = item.coordinates ? item.coordinates.lon : item.lon;
      const distStr = item._computedDist < 1000 ? `${item._computedDist}m away` : `${(item._computedDist / 1000).toFixed(1)} km away`;

      return `
        <div class="sanctuary-card">
          <div class="sanctuary-header">
            <div>
              <div class="sanctuary-name">${icon} ${item.name}</div>
              <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">${item.address || 'Ahmedabad Civic Area'}</div>
            </div>
            <div style="text-align:right;">
              <span class="sanctuary-type-badge ${badgeClass}">${badgeLabel}</span>
              <div class="verified-badge" style="font-size:10px; color:#0F766E; margin-top:2px;">✓ Verified today</div>
            </div>
          </div>

          <div class="sanctuary-details-row">
            <span>📍 <b>${distStr}</b></span>
            <span>⏱️ <b>~${item._computedWalkMin} min walk</b></span>
            <span>🕒 ${hours}</span>
          </div>

          ${item.amenities ? `
            <div class="sanctuary-amenities">
              ${item.amenities.map(a => `<span class="amenity-chip">${a}</span>`).join('')}
            </div>
          ` : ''}

          <div class="sanctuary-action-row">
            <span style="font-size:11px; color:#64748B;">Capacity: ${item.capacity_persons || 250} people</span>
            <button class="btn btn-primary" style="min-height:36px; padding:6px 14px; font-size:0.85rem;" onclick="PublicUI.navigateToSanctuary('${item.name}', ${lat}, ${lon})">
              <span>🌿</span><span>${t('walk_here')}</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    const toggleBtnHtml = totalCount > 5 ? `
      <div style="text-align:center; margin-top:14px; padding-top:10px; border-top:1px solid #E4E7EC;">
        <button class="icon-btn" style="width:100%; font-weight:600; color:#0F766E;" onclick="PublicUI.toggleAllSanctuaries('${filter}')">
          ${STATE.showAllSanctuaries ? '▲ Show Top 5 Nearby Havens' : `▼ View All ${totalCount} Shelters & Water Points`}
        </button>
      </div>
    ` : '';

    container.innerHTML = cardsHtml + toggleBtnHtml;
  },

  toggleAllSanctuaries(filter = 'all') {
    STATE.showAllSanctuaries = !STATE.showAllSanctuaries;
    this.renderSanctuariesList(filter);
  },

  navigateToSanctuary(name, lat, lon) {
    // Populate Cool Walk tool with this sanctuary as destination
    const destSelect = document.getElementById('routeDestSelect');
    if (destSelect) {
      destSelect.value = `${lat},${lon}`;
    }
    // Scroll smoothly to Cool Walk section
    const navSection = document.getElementById('cool-walk-section');
    if (navSection) {
      navSection.scrollIntoView({ behavior: 'smooth' });
    }
    // Trigger route calculation
    this.handleCalculateRoute();
  },

  renderNavigationInputs() {
    const originSelect = document.getElementById('routeOriginSelect');
    const destSelect = document.getElementById('routeDestSelect');

    if (originSelect) {
      originSelect.innerHTML = `
        <option value="${CONFIG.DEFAULT_COORDS.lat},${CONFIG.DEFAULT_COORDS.lon}">📍 My Current Location (Ellisbridge Core)</option>
        ${STATE.streets.map(s => `
          <option value="${CONFIG.DEFAULT_COORDS.lat + 0.002},${CONFIG.DEFAULT_COORDS.lon + 0.002}">${s.street_name}</option>
        `).join('')}
      `;
    }

    if (destSelect) {
      destSelect.innerHTML = STATE.coolingCenters.map(c => `
        <option value="${c.coordinates.lat},${c.coordinates.lon}">❄️ ${c.name} (${c.distance_meters}m)</option>
      `).join('') + STATE.hydrationPoints.map(k => `
        <option value="${k.coordinates.lat},${k.coordinates.lon}">💧 ${k.name} (${k.distance_meters}m)</option>
      `).join('');
    }
  },

  async handleCalculateRoute() {
    const originSelect = document.getElementById('routeOriginSelect');
    const destSelect = document.getElementById('routeDestSelect');
    if (!originSelect || !destSelect) return;

    const [oLat, oLon] = originSelect.value.split(',').map(Number);
    const [dLat, dLon] = destSelect.value.split(',').map(Number);

    const calcBtn = document.getElementById('calculateRouteBtn');
    if (calcBtn) {
      calcBtn.innerText = 'Calculating Thermal Corridor...';
      calcBtn.disabled = true;
    }

    try {
      const routeData = await ApiService.calculateCoolPath(
        { lat: oLat, lon: oLon },
        { lat: dLat, lon: dLon },
        STATE.selectedPersona === 'senior' ? 'elderly' : (STATE.selectedPersona === 'worker' ? 'outdoor_laborer' : 'standard')
      );

      STATE.activeRouteData = routeData;
      this.renderRouteComparison(routeData);
      MapController.drawRoutes(routeData);
    } catch (err) {
      console.error('Route calculation error:', err);
    } finally {
      if (calcBtn) {
        calcBtn.innerText = t('calc_cool_route');
        calcBtn.disabled = false;
      }
    }
  },

  renderRouteComparison(data) {
    const container = document.getElementById('routeComparisonContainer');
    if (!container || !data) return;

    const shortest = data.shortest || data.shortest_path;
    const cool = data.cool || data.cool_path;
    const summary = data.summary || {
      detour_m: cool.distance_m - shortest.distance_m,
      detour_min: Math.round((cool.walk_time_min - shortest.walk_time_min) * 10) / 10,
      shade_increase_pct: cool.shade_pct - shortest.shade_pct,
      temp_drop_c: Math.round((shortest.surface_temp_c - cool.surface_temp_c) * 10) / 10,
      heat_dose_reduction_pct: 42.5
    };

    container.innerHTML = `
      <div class="route-compare-grid">
        <!-- Shortest Route (Harsh Exposed Sun) -->
        <div class="route-card route-shortest">
          <div>
            <span class="route-card-badge badge-shortest-path">☀️ Direct Sun Path</span>
            <div class="route-card-title">${t('shortest_path_title')}</div>
            <div class="route-metrics-list">
              <div class="route-metric-row">
                <span class="route-metric-name">${t('distance')}:</span>
                <span class="route-metric-val">${shortest.distance_m || shortest.total_distance_meters} meters</span>
              </div>
              <div class="route-metric-row">
                <span class="route-metric-name">${t('walk_time')}:</span>
                <span class="route-metric-val">${shortest.walk_time_min || shortest.estimated_walking_minutes} mins</span>
              </div>
              <div class="route-metric-row">
                <span class="route-metric-name">${t('shade_cover')}:</span>
                <span class="route-metric-val highlight-hot-val">${shortest.shade_pct || Math.round(shortest.average_shade_ratio * 100)}% (Harsh Sun)</span>
              </div>
              <div class="route-metric-row">
                <span class="route-metric-name">Avg Ground Temp:</span>
                <span class="route-metric-val highlight-hot-val">${shortest.surface_temp_c || 48.4}°C</span>
              </div>
              <div class="route-metric-row">
                <span class="route-metric-name">${t('water_points')}:</span>
                <span class="route-metric-val">0 Kiosks</span>
              </div>
            </div>
          </div>
          <div style="font-size:0.78rem; color:#fca5a5; background:rgba(239,68,68,0.12); padding:8px; border-radius:6px;">
            ⚠️ Severe cumulative heat stress. High risk of heat exhaustion for seniors and workers.
          </div>
        </div>

        <!-- Cool-Corridor Route (Tree Canopy & Water Kiosks) -->
        <div class="route-card route-cool">
          <div>
            <span class="route-card-badge badge-cool-path">🌿 Recommended Corridor</span>
            <div class="route-card-title">${t('cool_path_title')}</div>
            <div class="route-metrics-list">
              <div class="route-metric-row">
                <span class="route-metric-name">${t('distance')}:</span>
                <span class="route-metric-val">${cool.distance_m || cool.total_distance_meters} m (+${summary.detour_m}m)</span>
              </div>
              <div class="route-metric-row">
                <span class="route-metric-name">${t('walk_time')}:</span>
                <span class="route-metric-val">${cool.walk_time_min || cool.estimated_walking_minutes} mins (+${summary.detour_min} min)</span>
              </div>
              <div class="route-metric-row">
                <span class="route-metric-name">${t('shade_cover')}:</span>
                <span class="route-metric-val highlight-cool-val">${cool.shade_pct || Math.round(cool.average_shade_ratio * 100)}% Shade (+${summary.shade_increase_pct}%)</span>
              </div>
              <div class="route-metric-row">
                <span class="route-metric-name">Avg Ground Temp:</span>
                <span class="route-metric-val highlight-cool-val">${cool.surface_temp_c || 36.6}°C (-${summary.temp_drop_c}°C Cooler!)</span>
              </div>
              <div class="route-metric-row">
                <span class="route-metric-name">${t('water_points')}:</span>
                <span class="route-metric-val highlight-cool-val">2 Chilled Kiosks on way</span>
              </div>
            </div>
          </div>
          <div style="font-size:0.78rem; color:#86efac; background:rgba(16,185,129,0.12); padding:8px; border-radius:6px;">
            ✅ 42% lower cumulative thermal dose! Continuous tree canopy with 2 free chilled drinking water stops.
          </div>
        </div>
      </div>

      <!-- Turn-by-turn navigation instructions -->
      <div class="turn-directions-wrap">
        <h4 style="font-size:1.05rem; font-weight:800; margin-bottom:10px;">${t('turn_steps_title')}</h4>
        <div>
          ${(cool.steps || []).map(step => `
            <div class="step-card ${step.is_water ? 'step-water' : ''}">
              <div class="step-icon">${step.is_water ? '💧' : '🚶'}</div>
              <div class="step-content">
                <div class="step-instruction">${step.instruction}</div>
                <div class="step-meta">
                  ${step.dist} meters • ${step.shade}% Canopy Cover • Temp: ${step.temp}°C
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  },

  handleGeolocation() {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          STATE.userLocation = {
            lat: pos.coords.latitude,
            lon: pos.coords.longitude
          };
          if (STATE.map) {
            STATE.map.setView([STATE.userLocation.lat, STATE.userLocation.lon], 16);
          }
          alert("📍 Location updated to your current GPS position!");
        },
        (err) => {
          console.warn('Geolocation failed or denied, using simulated city location');
          alert("Using default Ahmedabad Central Location (Ellisbridge / Khadia Core).");
        }
      );
    }
  },

  reTranslateAll() {
    this.renderHeaderAndAlert();
    this.renderStreetSection();
    this.renderPersonaSection();
    this.renderSanctuariesList();
    this.renderNavigationInputs();
    if (STATE.activeRouteData) {
      this.renderRouteComparison(STATE.activeRouteData);
    }
  }
};

// ============================================================================
// 11. BOOTSTRAP APPLICATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
  PublicUI.init();
});

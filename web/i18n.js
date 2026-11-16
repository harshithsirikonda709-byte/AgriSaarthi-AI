/* ==========================================================================
   AgriSaarthi AI — Centralized i18n Architecture (web/js/i18n.js)
   Trilingual support for Telugu (te - default), English (en), and Hindi (hi).
   Provides clean translation dictionaries, phrase lookup, DOM translation,
   language persistence, and farmer profile synchronization.
   ========================================================================== */

(function () {
  'use strict';

  const I18N_STORAGE_KEY = 'agrisaarthi_lang';
  const DEFAULT_LANG = 'te';

  // Master translation dictionary by category and key
  const I18N_DICTIONARY = {
    app: {
      title: {
        te: 'AgriSaarthi AI <span class="telugu-name">(అగ్రిసారథి)</span>',
        en: 'AgriSaarthi AI <span class="telugu-name">(Farmer Assistant)</span>',
        hi: 'AgriSaarthi AI <span class="telugu-name">(अग्रिसारथी)</span>',
      },
      page_title: {
        te: 'AgriSaarthi AI — రైతు నేస్తం (Farmer Decision Assistant)',
        en: 'AgriSaarthi AI — Farmer Decision Assistant',
        hi: 'AgriSaarthi AI — किसान निर्णय सहायक (AgriSaarthi)',
      },
      subtitle: {
        te: 'రైతు నిర్ణయ సహాయకుడు • స్మార్ట్ వ్యవసాయ వేదిక',
        en: 'Farmer Decision Assistant • Smart Agriculture Platform',
        hi: 'किसान निर्णय सहायक • स्मार्ट कृषि निर्णय मंच',
      },
    },
    nav: {
      home: {
        te: 'హోమ్ (Home)',
        en: 'Home',
        hi: 'होम (Home)',
      },
      dashboard: {
        te: 'డాష్‌బోర్డ్ (Dashboard)',
        en: 'Dashboard',
        hi: 'डैशबोर्ड (Dashboard)',
      },
      advisory: {
        te: 'పంట సలహా (Crop Advisory)',
        en: 'Crop Advisory',
        hi: 'फसल सलाह (Crop Advisory)',
      },
      health: {
        te: 'పంట ఆరోగ్యం (Crop Health)',
        en: 'Crop Health',
        hi: 'फसल स्वास्थ्य (Crop Health)',
      },
      weather: {
        te: 'వాతావరణం (Weather & Alerts)',
        en: 'Weather & Alerts',
        hi: 'मौसम और चेतावनियाँ (Weather)',
      },
      voice: {
        te: 'AI వాయిస్ సహాయకుడు (Voice AI)',
        en: 'Voice AI Assistant',
        hi: 'AI वॉयस सहायक (Voice AI)',
      },
      profile: {
        te: 'నా ప్రొఫైల్ (Profile)',
        en: 'My Profile',
        hi: 'मेरी प्रोफ़ाइल (Profile)',
      },
      login: {
        te: 'లాగిన్ (Login)',
        en: 'Login',
        hi: 'लॉगिन (Login)',
      },
      register: {
        te: 'రైతు నమోదు (Register)',
        en: 'Register',
        hi: 'किसान पंजीकरण (Register)',
      },
      logout: {
        te: 'లాగ్ అవుట్ (Logout)',
        en: 'Logout',
        hi: 'लॉग आउट (Logout)',
      },
      home_short: {
        te: 'హోమ్',
        en: 'Home',
        hi: 'होम',
      },
      advisory_short: {
        te: 'పంట సలహా',
        en: 'Find Crop',
        hi: 'फसल सलाह',
      },
      health_short: {
        te: 'పంట ఆరోగ్యం',
        en: 'Crop Health',
        hi: 'फसल स्वास्थ्य',
      },
      weather_short: {
        te: 'వాతావరణం',
        en: 'Weather',
        hi: 'मौसम',
      },
      voice_short: {
        te: 'వాయిస్ AI',
        en: 'Voice AI',
        hi: 'वॉयस AI',
      },
    },
    hub: {
      pill_advisory: {
        te: '<span></span> <strong>పంట సలహాదారు:</strong> 11 ICAR/CACP పంటలు',
        en: '<span></span> <strong>Crop Advisory:</strong> 11 ICAR/CACP Crops',
        hi: '<span></span> <strong>फसल सलाहकार:</strong> 11 ICAR/CACP फसलें',
      },
      pill_health: {
        te: '<span></span> <strong>పంట రక్షణ:</strong> లక్షణాలు & నివారణ',
        en: '<span></span> <strong>Crop Health:</strong> Verified Symptoms & Cultural Steps',
        hi: '<span></span> <strong>फसल सुरक्षा:</strong> वैज्ञानिक लक्षण व जैविक रोकथाम',
      },
      pill_weather: {
        te: '<span></span> <strong>వాతావరణం:</strong> వాస్తవ వాతావరణ నివేదిక',
        en: '<span></span> <strong>Live Weather:</strong> Real-Time Meteorological Feed',
        hi: '<span></span> <strong>मौसम अपडेट:</strong> वास्तविक मौसम जानकारी',
      },
      voice_ready: {
        te: 'వాయిస్ సిద్ధంగా ఉంది',
        en: 'Voice Ready',
        hi: 'वॉयस तैयार है',
      },
      voice_listening: {
        te: 'వింటున్నాను...',
        en: 'Listening...',
        hi: 'सुन रहा हूँ...',
      },
      voice_processing: {
        te: '⏳ ప్రాసెసింగ్...',
        en: '⏳ Processing...',
        hi: '⏳ प्रक्रिया जारी...',
      },
      voice_speaking: {
        te: 'మాట్లాడుతున్నాను...',
        en: 'Speaking...',
        hi: 'बोल रहा हूँ...',
      },
      voice_paused: {
        te: '⏸ పాజ్ చేయబడింది',
        en: '⏸ Paused',
        hi: '⏸ ठहरा हुआ है',
      },
    },
    home: {
      hero_title: {
        te: 'అగ్రిసారథి AI — భారతీయ రైతుల కోసం స్మార్ట్ వ్యవసాయ నిర్ణయ వేదిక',
        en: 'AgriSaarthi AI — Smart Agricultural Decision Platform for Indian Farmers',
        hi: 'अग्रिसारथी AI — भारतीय किसानों के लिए स्मार्ट कृषि निर्णय मंच',
      },
      hero_desc: {
        te: 'ICAR మరియు CACP (MSP 2024–2025) ప్రామాణిక గణాంకాల ఆధారంగా మీ నేల, నీటి వసతి, సీజన్ మరియు బడ్జెట్‌కు తగిన పంట సిఫార్సులు, పంట తెగుళ్ల రోగనిర్ధారణ, వాస్తవ వాతావరణ సమాచారం మరియు బహుభాషా వాయిస్ అసిస్టెంట్.',
        en: 'Autonomous agricultural decision support grounded in ICAR & CACP standards. Get climate-resilient crop recommendations, disease diagnostics, real-time weather alerts, and multilingual voice assistance.',
        hi: 'ICAR और CACP (MSP 2024-2025) मानकों पर आधारित: अपनी मिट्टी, पानी, मौसम और बजट के अनुसार फसल सिफारिशें, कीट व रोग निदान, वास्तविक मौसम अपडेट और बहुभाषी वॉयस सहायक।',
      },
      btn_reg: {
        te: 'కొత్త రైతు నమోదు (Register Free)',
        en: 'Register Free',
        hi: 'नया किसान पंजीकरण (मुफ़्त)',
      },
      btn_login: {
        te: 'రైతు లాగిన్ (Farmer Login)',
        en: 'Farmer Login',
        hi: 'किसान लॉगिन (Login)',
      },
      btn_try_voice: {
        te: 'AI వాయిస్ సహాయకుడిని ప్రయత్నించండి (Try Voice AI)',
        en: 'Try Voice AI Assistant',
        hi: 'AI वॉयस सहायक आज़माएं (Try Voice)',
      },
      btn_dashboard: {
        te: 'నా రైతు డాష్‌బోర్డ్‌కు వెళ్ళండి (Open My Dashboard)',
        en: 'Open Farmer Dashboard',
        hi: 'किसान डैशबोर्ड खोलें',
      },
      card_advisory_title: {
        te: 'శాస్త్రీయ పంట సిఫార్సు',
        en: 'Scientific Crop Recommendations',
        hi: 'वैज्ञानिक फसल सिफारिश',
      },
      card_advisory_desc: {
        te: 'నేల రకం, నీటి లభ్యత, బడ్జెట్ మరియు పంట కాలం ఆధారంగా గరిష్ట లాభదాయక పంటల ఎంపిక.',
        en: 'Evaluate profitability, suitability score, and budget limits for 11 major crops.',
        hi: 'मिट्टी के प्रकार, जल उपलब्धता, बजट और मौसम के आधार पर सर्वाधिक लाभदायक फसलों का चयन।',
      },
      card_health_title: {
        te: 'పంట తెగుళ్ల నిర్ధారణ',
        en: 'Crop Health & Diagnostics',
        hi: 'फसल रोग व कीट निदान',
      },
      card_health_desc: {
        te: 'ఆకులు పసుపుబారడం, ముడత, పురుగుల లక్షణాలను గుర్తించి తక్షణ సురక్షిత చర్యలు పొందండి.',
        en: 'Identify yellowing, leaf curls, and pest attacks with ICAR-verified safe cultural steps.',
        hi: 'पत्तियों का पीलापन, मरोड़िया रोग व कीट प्रकोप की पहचान और तत्काल सुरक्षित जैविक उपाय।',
      },
      card_weather_title: {
        te: 'వాస్తవ వాతావరణం & రక్షణ',
        en: 'Live Weather & Protection',
        hi: 'वास्तविक मौसम व फसल सुरक्षा',
      },
      card_weather_desc: {
        te: 'ఓపెన్-మెటియో ఆధారిత వర్షపాతం, ఉష్ణోగ్రత, గాలి వేగం మరియు 3 రోజుల వ్యవసాయ సూచనలు.',
        en: 'Real-time rainfall, temperature, wind speed, and 3-day agricultural advisories.',
        hi: 'वास्तविक तापमान, वर्षा संभावना, हवा की गति और 3-दिवसीय कृषि कार्य सलाह।',
      },
      card_voice_title: {
        te: 'బహుభాషా వాయిస్ సహాయకుడు',
        en: 'Trilingual Voice Assistant',
        hi: 'त्रिभाषी वॉयस सहायक',
      },
      card_voice_desc: {
        te: 'తెలుగు, హిందీ మరియు ఇంగ్లీష్‌లో మాట్లాడి వ్యవసాయ సలహాలను వినండి.',
        en: 'Speak naturally in Telugu, Hindi, or English to receive synthesized audio advice.',
        hi: 'तेलुगु, हिंदी और अंग्रेजी में अपनी भाषा में बोलकर कृषि सलाह और समाधान सुनें।',
      },
      standards_title: {
        te: 'వ్యవసాయ శాస్త్రీయ ప్రమాణాలు (Agricultural Standards)',
        en: 'Agricultural Science Standards',
        hi: 'कृषि वैज्ञानिक मानक (Agricultural Standards)',
      },
      standards_desc: {
        te: 'అగ్రిసారథి ఎటువంటి నకిలీ లేదా ఊహాజనిత డేటాను ఉపయోగించదు. భారత ప్రభుత్వం CACP నిర్దేశించిన కనీస మద్దతు ధరలు (MSP 2024–2025) మరియు ICAR వ్యవసాయ పద్ధతుల ప్రకారం మాత్రమే సలహాలు ఇవ్వబడతాయి.',
        en: 'AgriSaarthi AI operates with zero hallucinated figures. Recommendations are calculated strictly against Commission for Agricultural Costs and Prices (CACP) benchmarks, Minimum Support Prices (MSP 2024–2025), and Indian Council of Agricultural Research (ICAR) packages of practices.',
        hi: 'अग्रिसारथी AI किसी भी काल्पनिक आंकड़े का उपयोग नहीं करता है। सभी सलाह कृषि लागत एवं मूल्य आयोग (CACP) के आधिकारिक मानकों, न्यूनतम समर्थन मूल्य (MSP 2024–2025) और भारतीय कृषि अनुसंधान परिषद (ICAR) के नियमों के अनुसार ही दी जाती हैं।',
      },
    },
    dashboard: {
      welcome: {
        te: 'నమస్కారం రైతు సోదరులారా!',
        en: 'Welcome, Respected Farmer!',
        hi: 'नमस्ते किसान बंधु!',
      },
      default_location: {
        te: 'ప్రాంతం వివరాలు (Location Details)',
        en: 'Location Details',
        hi: 'स्थान विवरण (Location Details)',
      },
      my_farm_btn: {
        te: 'నా పొలం ప్రొఫైల్ (My Farm Profile)',
        en: 'My Farm Profile',
        hi: 'मेरी खेत प्रोफ़ाइल (Farm Profile)',
      },
      quick_actions: {
        te: 'తక్షణ సేవలు (Quick Actions)',
        en: 'Quick Actions',
        hi: 'त्वरित सेवाएँ (Quick Actions)',
      },
      qa_advisory_title: {
        te: 'పంట సలహా (Crop Advisory)',
        en: 'Crop Advisory',
        hi: 'फसल सलाह (Crop Advisory)',
      },
      qa_advisory_desc: {
        te: 'మీ నేల, నీరు & బడ్జెట్‌కు తగిన లాభదాయక పంటలు',
        en: 'Crops suited to your soil, water availability and budget',
        hi: 'आपकी मिट्टी, पानी व बजट के अनुसार लाभदायक फसलें',
      },
      qa_health_title: {
        te: 'పంట ఆరోగ్యం (Crop Health)',
        en: 'Crop Health',
        hi: 'फसल स्वास्थ्य (Crop Health)',
      },
      qa_health_desc: {
        te: 'ఆకు మచ్చలు, పసుపుబారడం & పురుగుల నిర్ధారణ',
        en: 'Diagnose leaf spots, yellowing, and pest attacks',
        hi: 'पत्तियों के धब्बे, पीलापन और कीटों की पहचान',
      },
      qa_weather_title: {
        te: 'వాతావరణం & హెచ్చరికలు',
        en: 'Weather & Alerts',
        hi: 'मौसम और चेतावनियाँ',
      },
      qa_weather_desc: {
        te: 'వాస్తవ వర్షపాతం, గాలి వేగం & 3-రోజుల సూచన',
        en: 'Live rainfall, temperature, and 3-day forecast',
        hi: 'वास्तविक वर्षा, हवा की गति व 3-दिवसीय मौसम अनुमान',
      },
      qa_voice_title: {
        te: 'AI వాయిస్ సహాయకుడు',
        en: 'AI Voice Assistant',
        hi: 'AI वॉयस सहायक',
      },
      qa_voice_desc: {
        te: 'తెలుగు, హిందీ లేదా ఇంగ్లీష్‌లో మాట్లాడి సమాధానం వినండి',
        en: 'Speak in Telugu, Hindi, or English and listen to answers',
        hi: 'हिंदी, तेलुगु या अंग्रेजी में बोलें और समाधान सुनें',
      },
      regional_weather: {
        te: 'ప్రాంతీయ వాతావరణం (Real-Time Weather)',
        en: 'Regional Weather (Real-Time)',
        hi: 'क्षेत्रीय मौसम (वास्तविक समय)',
      },
      view_full_details: {
        te: 'పూర్తి వివరాలు →',
        en: 'Full Details →',
        hi: 'पूरा विवरण →',
      },
      weather_loading: {
        te: '⏳ వాతావరణ సమాచారం లోడ్ అవుతోంది...',
        en: '⏳ Loading live weather data...',
        hi: '⏳ मौसम की जानकारी लोड हो रही है...',
      },
      weather_alerts: {
        te: 'అధికారిక వాతావరణ హెచ్చరికలు (Weather Alerts)',
        en: 'Official Weather Alerts',
        hi: 'आधिकारिक मौसम चेतावनियाँ',
      },
      alerts_loading: {
        te: '⏳ హెచ్చరికల స్థితి లోడ్ అవుతోంది...',
        en: '⏳ Loading alert status...',
        hi: '⏳ चेतावनी की स्थिति लोड हो रही है...',
      },
      my_farm_summary: {
        te: 'నా పొలం వివరాలు (My Farm Summary)',
        en: 'My Farm Holding Summary',
        hi: 'मेरे खेत का विवरण (Farm Summary)',
      },
      recent_history: {
        te: 'ఇటీవలి సలహా చరిత్ర (Recent Advisory History)',
        en: 'Recent Advisory History',
        hi: 'हालिया सलाह इतिहास (Recent History)',
      },
      no_history: {
        te: 'ఇంకా ఎటువంటి సలహా చరిత్ర లేదు.',
        en: 'No advisory history recorded yet.',
        hi: 'अभी तक कोई सलाह इतिहास दर्ज नहीं है।',
      },
      schemes_title: {
        te: 'ప్రభుత్వ పథకాలు & రైతు ప్రయోజనాలు (Government Schemes)',
        en: 'Government Schemes & Farmer Benefits',
        hi: 'सरकारी योजनाएं व किसान लाभ (Government Schemes)',
      },
      schemes_sub: {
        te: 'భారత ప్రభుత్వ మరియు రాష్ట్ర వ్యవసాయ సంక్షేమ పథకాల సమాచారం:',
        en: 'Key Government of India & State Agricultural Welfare Schemes:',
        hi: 'भारत सरकार एवं राज्य की प्रमुख किसान कल्याणकारी योजनाएं:',
      },
      scheme_pmkisan: {
        te: '<strong>పీఎం-కిసాన్ (PM-KISAN):</strong> అర్హులైన రైతులకు ఏడాదికి ₹6,000 ప్రత్యక్ష ఆర్థిక సాయం (3 విడతల్లో ₹2,000 చొప్పున బ్యాంక్ ఖాతాలో జమ).',
        en: '<strong>PM-KISAN:</strong> ₹6,000 per year direct income support to eligible farmer families in three 4-monthly installments of ₹2,000.',
        hi: '<strong>पीएम-किसान (PM-KISAN):</strong> पात्र किसान परिवारों को ₹6,000 प्रति वर्ष सीधी आय सहायता (₹2,000 की 3 किस्तों में बैंक खाते में)।',
      },
      scheme_pmfby: {
        te: '<strong>పీఎం ఫసల్ బీమా యోజన (PMFBY):</strong> ప్రకృతి వైపరీత్యాలు, తెగుళ్లు మరియు వర్షాభావ పరిస్థితుల్లో పంట నష్ట పరిహార బీమా రక్షణ.',
        en: '<strong>PM Fasal Bima Yojana (PMFBY):</strong> Comprehensive crop loss insurance against non-preventable natural risks (Kharif 2%, Rabi 1.5% premium).',
        hi: '<strong>प्रधानमंत्री फसल बीमा योजना (PMFBY):</strong> प्राकृतिक आपदाओं, सूखा, बाढ़ और कीट प्रकोप से फसल क्षति पर व्यापक सुरक्षा बीमा (खरीफ 2%, रबी 1.5%)।',
      },
      scheme_soil: {
        te: '<strong>సాయిల్ హెల్త్ కార్డ్ (Soil Health Card):</strong> భూసార పరీక్ష ఆధారంగా సరైన మోతాదులో ఎరువుల వాడకం & నేల సారం పెంపుదల.',
        en: '<strong>Soil Health Card:</strong> Scientific soil nutrient status and customized dosage recommendations to reduce chemical costs.',
        hi: '<strong>मृदा स्वास्थ्य कार्ड (Soil Health Card):</strong> खेत की मिट्टी जांच के आधार पर पोषक तत्वों की स्थिति और संतुलित उर्वरक प्रयोग।',
      },
      scheme_kcc: {
        te: '<strong>కిసాన్ క్రెడిట్ కార్డ్ (KCC):</strong> సాగు పెట్టుబడి కోసం 4% రాయితీ వడ్డీ రేటుతో సకాలంలో సులభ బ్యాంక్ రుణాలు.',
        en: '<strong>Kisan Credit Card (KCC):</strong> Concessional agricultural short-term credit at 4% effective interest rate with prompt repayment.',
        hi: '<strong>किसान क्रेडिट कार्ड (KCC):</strong> समय पर आसान कृषि ऋण 4% रियायती ब्याज दर पर (समय पर चुकाने पर 3% अतिरिक्त छूट)।',
      },
    },
    auth: {
      login_heading: {
        te: 'రైతు లాగిన్ (Farmer Login)',
        en: 'Farmer Login',
        hi: 'किसान लॉगिन (Farmer Login)',
      },
      login_sub: {
        te: 'మీ రిజిస్టర్డ్ యూజర్‌నేమ్, మొబైల్ లేదా ఈమెయిల్ మరియు పాస్‌వర్డ్‌తో లాగిన్ అవ్వండి.',
        en: 'Log in with your registered mobile number, username, or email address.',
        hi: 'अपने पंजीकृत मोबाइल नंबर, यूजरनेम या ईमेल और पासवर्ड से लॉगिन करें।',
      },
      login_id_label: {
        te: 'మొబైల్ నంబర్ / యూజర్‌నేమ్ / ఈమెయిల్ *',
        en: 'Mobile Number / Username / Email *',
        hi: 'मोबाइल नंबर / यूजरनेम / ईमेल *',
      },
      login_id_placeholder: {
        te: 'ఉదా: 9876543210 లేదా ramarao_farmer',
        en: 'e.g. 9876543210 or ramarao_farmer',
        hi: 'उदा: 9876543210 या ramarao_farmer',
      },
      login_pwd_label: {
        te: 'పాస్‌వర్డ్ (Password) *',
        en: 'Password *',
        hi: 'पासवर्ड (Password) *',
      },
      btn_login_submit: {
        te: 'లాగిన్ అవ్వండి (Login to Portal)',
        en: 'Log In to Portal',
        hi: 'पोर्टल में लॉगिन करें',
      },
      no_account: {
        te: 'ఇంకా ఖాతా లేదా? (New to AgriSaarthi?)',
        en: 'New to AgriSaarthi?',
        hi: 'क्या नया खाता बनाना चाहते हैं?',
      },
      link_register: {
        te: 'ఇక్కడ నమోదు చేసుకోండి (Register Free)',
        en: 'Register Free Here',
        hi: 'यहाँ मुफ़्त पंजीकरण करें',
      },
      reg_heading: {
        te: 'కొత్త రైతు ఖాతా నమోదు (Farmer Registration)',
        en: 'New Farmer Registration',
        hi: 'नया किसान खाता पंजीकरण (Registration)',
      },
      reg_sub: {
        te: 'ఖాతా సృష్టించండి — వ్యక్తిగతీకరించిన పంట సిఫార్సులు, వాతావరణ హెచ్చరికలు ఉచితంగా పొందండి.',
        en: 'Create your account for personalized crop recommendations and farm analytics.',
        hi: 'खाता बनाएं — व्यक्तिगत फसल सिफारिशें और सटीक मौसम अपडेट मुफ़्त प्राप्त करें।',
      },
      reg_fullname_label: {
        te: 'పూర్తి పేరు (Full Name) *',
        en: 'Full Name *',
        hi: 'पूरा नाम (Full Name) *',
      },
      reg_fullname_ph: {
        te: 'ఉదా: రామారావు / Ramarao',
        en: 'e.g. Ramarao Patel',
        hi: 'उदा: रामाराव पटेल',
      },
      reg_email_label: {
        te: 'ఈమెయిల్ చిరునామా (Email Address)',
        en: 'Email Address',
        hi: 'ईमेल पता (Email Address)',
      },
      reg_email_ph: {
        te: 'ఉదా: farmer@example.com',
        en: 'e.g. farmer@example.com',
        hi: 'उदा: farmer@example.com',
      },
      reg_phone_label: {
        te: 'ఫోన్ నంబర్ - 10 అంకెలు (10-Digit Phone Number)',
        en: '10-Digit Mobile Phone Number',
        hi: '10-अंकीय मोबाइल फोन नंबर',
      },
      reg_phone_ph: {
        te: 'ఉదా: 9876543210',
        en: 'e.g. 9876543210',
        hi: 'उदा: 9876543210',
      },
      reg_id_label: {
        te: 'యూజర్‌నేమ్ లేదా మొబైల్ ఐడెంటిఫైయర్ *',
        en: 'Username or Mobile Identifier *',
        hi: 'यूजरनेम या मोबाइल पहचानकर्ता *',
      },
      reg_id_ph: {
        te: 'ఉదా: 9876543210 లేదా ramarao_farmer',
        en: 'e.g. 9876543210 or ramarao_farmer',
        hi: 'उदा: 9876543210 या ramarao_farmer',
      },
      reg_pwd_label: {
        te: 'పాస్‌వర్డ్ (కనీసం 6 అక్షరాలు / Min 6 chars) *',
        en: 'Password (Min 6 chars) *',
        hi: 'पासवर्ड (न्यूनतम 6 अक्षर) *',
      },
      reg_cpwd_label: {
        te: 'పాస్‌వర్డ్ నిర్ధారణ (Confirm Password) *',
        en: 'Confirm Password *',
        hi: 'पासवर्ड की पुष्टि करें (Confirm Password) *',
      },
      reg_lang_label: {
        te: 'ప్రాధాన్య భాష (Preferred Language)',
        en: 'Preferred Language',
        hi: 'पसंदीदा भाषा (Preferred Language)',
      },
      btn_reg_submit: {
        te: 'ఖాతా సృష్టించి కొనసాగండి (Register & Continue)',
        en: 'Register & Continue',
        hi: 'खाता बनाएं और आगे बढ़ें (Register)',
      },
      already_account: {
        te: 'ఇప్పటికే ఖాతా ఉందా? (Already registered?)',
        en: 'Already registered?',
        hi: 'क्या पहले से खाता है?',
      },
      link_login: {
        te: 'ఇక్కడ లాగిన్ అవ్వండి (Login Here)',
        en: 'Login Here',
        hi: 'यहाँ लॉगिन करें',
      },

      login_or: {
        te: 'లేదా (OR)',
        en: 'OR',
        hi: 'या (OR)',
      },
      LOGIN_OR: {
        te: 'లేదా (OR)',
        en: 'OR',
        hi: 'या (OR)',
      },
      login_google: {
        te: 'Google తో కొనసాగించండి (Continue with Google)',
        en: 'Continue with Google',
        hi: 'Google से जारी रखें (Continue with Google)',
      },
      login_coming_soon: {
        te: 'త్వరలో అందుబాటులోకి',
        en: 'Coming soon',
        hi: 'जल्द आ रहा है',
      },
      forgot_password: {
        te: 'పాస్‌వర్డ్ మర్చిపోయారా? (Forgot Password?)',
        en: 'Forgot Password?',
        hi: 'पासवर्ड भूल गए? (Forgot Password?)',
      },
      btn_send_otp: {
        te: 'OTP పంపండి (Send OTP)',
        en: 'Send Verification OTP',
        hi: 'ओटीपी भेजें (Send OTP)',
      },
      btn_verify_otp: {
        te: 'ధృవీకరించి లాగిన్ అవ్వండి (Verify & Log In)',
        en: 'Verify OTP & Log In',
        hi: 'सत्यापित करें और लॉगिन करें',
      },
      otp_enter_label: {
        te: '6-అంకెల OTP నమోదు చేయండి (Enter 6-Digit OTP)',
        en: 'Enter 6-Digit Verification OTP',
        hi: '6-अंकीय ओटीपी दर्ज करें',
      },
      otp_sent_to: {
        te: 'ఓటీపీ పంపబడింది:',
        en: 'OTP sent to:',
        hi: 'ओटीपी भेजा गया:',
      },
      otp_resend: {
        te: 'మళ్ళీ పంపండి (Resend OTP)',
        en: 'Resend OTP',
        hi: 'ओटीपी पुनः भेजें (Resend OTP)',
      },
      otp_back_to_login: {
        te: '← సాధారణ లాగిన్‌కు తిరిగి వెళ్ళండి (Back to Password Login)',
        en: '← Back to Password Login',
        hi: '← पासवर्ड लॉगिन पर वापस जाएं',
      },
      change_password_title: {
        te: 'కొత్త పాస్‌వర్డ్ మార్చండి (Change Password)',
        en: 'Set New Password',
        hi: 'नया पासवर्ड सेट करें (Change Password)',
      },
      change_password_desc: {
        te: 'మీ ఖాతా భద్రత కోసం కొత్త పాస్‌వర్డ్‌ను సెట్ చేసుకోండి.',
        en: 'Please set a secure new password for your farmer account.',
        hi: 'अपने खाते की सुरक्षा के लिए एक नया सुरक्षित पासवर्ड सेट करें।',
      },
      new_password_label: {
        te: 'కొత్త పాస్‌వర్డ్ (New Password) *',
        en: 'New Password (Min 6 chars) *',
        hi: 'नया पासवर्ड (कम से कम 6 अक्षर) *',
      },
      confirm_new_password_label: {
        te: 'కొత్త పాస్‌వర్డ్ నిర్ధారణ (Confirm New Password) *',
        en: 'Confirm New Password *',
        hi: 'नए पासवर्ड की पुष्टि करें *',
      },
      btn_save_password: {
        te: 'కొత్త పాస్‌వర్డ్ సేవ్ చేయండి (Save New Password)',
        en: 'Save New Password',
        hi: 'नया पासवर्ड सुरक्षित करें',
      },
      password_changed_success: {
        te: 'పాస్‌వర్డ్ విజయవంతంగా మార్చబడింది! (Password updated successfully)',
        en: 'Password updated successfully! Your account is secured.',
        hi: 'पासवर्ड सफलतापूर्वक बदल दिया गया है!',
      },
      otp_login_title: {
        te: 'ఓటీపీని ధృవీకరించి లాగిన్ అవ్వండి (Verify OTP to Log In)',
        en: 'Verify OTP to Log In',
        hi: 'ओटीपी सत्यापित करके लॉगिन करें (Verify OTP to Log In)',
      },
      otp_step2_heading: {
        te: 'ఓటీపీని ధృవీకరించండి (Verify OTP to Log In)',
        en: 'Verify OTP to Log In',
        hi: 'ओटीपी सत्यापित करें (Verify OTP to Log In)',
      },
      otp_logged_in_notice: {
        te: 'మీరు OTP ద్వారా లాగిన్ అయ్యారు. దయచేసి మీ ఖాతా పాస్‌వర్డ్‌ను అప్‌డేట్ చేయండి.',
        en: 'You logged in via OTP. Please update your account password.',
        hi: 'आप OTP द्वारा लॉगिन हुए हैं। कृपया अपना खाता पासवर्ड अपडेट करें।',
      },
      password_updated_banner_title: {
        te: 'పాస్‌వర్డ్ విజయవంతంగా అప్‌డేట్ చేయబడింది!',
        en: 'Password Updated Successfully!',
        hi: 'पासवर्ड सफलतापूर्वक अपडेट हो गया!',
      },
      password_updated_banner_desc: {
        te: 'పాస్‌వర్డ్ విజయవంతంగా అప్‌డేట్ చేయబడింది! మీరు ఇప్పుడు మీ కొత్త పాస్‌వర్డ్‌తో లాగిన్ అవ్వవచ్చు.',
        en: 'Password updated successfully! You can now log in using your new password.',
        hi: 'पासवर्ड सफलतापूर्वक अपडेट हो गया! अब आप अपने नए पासवर्ड से लॉगिन कर सकते हैं।',
      },
      otp_set_password_hint: {
        te: 'తదుపరి సులభమైన లాగిన్ కోసం దయచేసి ఇప్పుడు మీ శాశ్వత పాస్‌వర్డ్‌ను సెట్ చేసుకోండి.',
        en: 'Please set your permanent password now for effortless future logins.',
        hi: 'भविष्य में आसान लॉगिन के लिए कृपया अभी अपना पासवर्ड सेट करें।',
      },
      btn_set_password_now: {
        te: 'మీ పాస్‌వర్డ్‌ను అప్‌డేట్ చేయండి (Update Your Password)',
        en: 'Update Your Password',
        hi: 'अपना पासवर्ड अपडेट करें (Update Your Password)',
      },
      google_choose_account: {
        te: 'Google ఖాతాను ఎంచుకోండి (Choose Google Account)',
        en: 'Choose Google Account',
        hi: 'Google खाता चुनें',
      },
      google_choose_sub: {
        te: 'అగ్రిసారథి AI తో కొనసాగించడానికి మీ ఖాతాను ఎంచుకోండి',
        en: 'Select an account to continue to AgriSaarthi AI',
        hi: 'एग्रीसारथी एआई से जुड़ने के लिए अपना खाता चुनें',
      },
      google_name_label: {
        te: 'పూర్తి పేరు (Your Name):',
        en: 'Full Name:',
        hi: 'पूरा नाम:',
      },
      google_email_label: {
        te: 'Google ఈమెయిల్ (Gmail Address):',
        en: 'Google Email (Gmail):',
        hi: 'गूगल ईमेल पता:',
      },
      otp_step1_desc: {
        te: 'మీ రిజిస్టర్డ్ మొబైల్ లేదా ఈమెయిల్‌ను నమోదు చేయండి. మేము తక్షణమే 6-అంకెల OTP ని పంపుతాము.',
        en: 'Enter your registered mobile number, username, or email. We will send an instant 6-digit verification OTP.',
        hi: 'अपना पंजीकृत मोबाइल नंबर, यूजरनेम या ईमेल दर्ज करें। हम तुरंत 6 अंकों का ओटीपी भेजेंगे।',
      },
      otp_sms_title: {
        te: '[SMS డెమో నోటిఫికేషన్]',
        en: '[SMS Demo Notification]',
        hi: '[SMS डेमो सूचना]',
      },
      otp_sms_demo: {
        te: 'మీ ధృవీకరణ OTP:',
        en: 'Your verification OTP is:',
        hi: 'आपका सत्यापन ओटीपी:',
      },
      otp_validity_note: {
        te: '(10 నిమిషాల చెల్లుబాటు)',
        en: '(10 min validity)',
        hi: '(10 मिनट वैधता)',
      },
      google_use_another: {
        te: 'వేరే Google ఖాతాను ఉపయోగించండి (Use another account)',
        en: 'Use another Google account',
        hi: 'दूसरे Google खाते का उपयोग करें',
      },
      google_continue: {
        te: 'Google తో కొనసాగించండి (Sign in with Google)',
        en: 'Sign in with Google',
        hi: 'Google के साथ जारी रखें',
      },
      btn_cancel: {
        te: 'రద్దు (Cancel)',
        en: 'Cancel',
        hi: 'रद्द करें (Cancel)',
      },

    },
    advisory: {
      heading: {
        te: 'శాస్త్రీయ పంట సిఫార్సు (ICAR/CACP Crop Advisory)',
        en: 'Scientific Crop Recommendations (ICAR/CACP Advisory)',
        hi: 'वैज्ञानिक फसल सिफारिश (ICAR/CACP फसल सलाह)',
      },
      subheading: {
        te: 'మీ పొలం వివరాలను నమోదు చేసి అనుకూలత స్కోరు, పెట్టుబడి మరియు నికర లాభం అంచనాలను పొందండి.',
        en: 'Input farm holding parameters to compute suitability scores, estimated costs, and net returns.',
        hi: 'अपने खेत का विवरण दर्ज करें और उपयुक्तता स्कोर, अनुमानित लागत व शुद्ध लाभ गणना प्राप्त करें।',
      },
      ask_voice_btn: {
        te: 'వాయిస్ ద్వారా అడగండి (Ask via Voice)',
        en: 'Ask via Voice Assistant',
        hi: 'बोलकर पूछें (Ask via Voice)',
      },
      chip_ts_kharif: {
        te: 'తెలంగాణ నల్ల రేగడి - ఖరీఫ్ (Warangal Kharif)',
        en: 'Telangana Black Soil - Kharif (Warangal Kharif)',
        hi: 'तेलंगाना काली मिट्टी - खरीफ (Warangal Kharif)',
      },
      chip_ap_rabi: {
        te: 'ఆంధ్రప్రదేశ్ ఎర్ర నేల - రబీ (Guntur Rabi)',
        en: 'Andhra Pradesh Red Soil - Rabi (Guntur Rabi)',
        hi: 'आंध्र प्रदेश लाल मिट्टी - रबी (Guntur Rabi)',
      },
      chip_pb_rabi: {
        te: 'పంజాబ్ ఒండ్రు నేల - గోధుమ (Punjab Wheat)',
        en: 'Punjab Alluvial Soil - Wheat (Punjab Rabi)',
        hi: 'पंजाब जलोढ़ मिट्टी - गेहूं (Punjab Rabi)',
      },
      lbl_state: {
        te: 'రాష్ట్రం (State) *',
        en: 'State *',
        hi: 'राज्य (State) *',
      },
      lbl_district: {
        te: 'జిల్లా (District)',
        en: 'District',
        hi: 'जिला (District)',
      },
      ph_district: {
        te: 'ఉదా: Warangal, Guntur, Karimnagar',
        en: 'e.g. Warangal, Guntur, Karnal',
        hi: 'उदा: वारंगल, गुंटूर, करनाल',
      },
      lbl_acres: {
        te: 'భూమి విస్తీర్ణం - ఎకరాల్లో (Land Size in Acres) *',
        en: 'Land Size in Acres *',
        hi: 'भूमि का रकबा - एकड़ में (Land Size) *',
      },
      lbl_soil: {
        te: 'నేల రకం (Soil Type) *',
        en: 'Soil Type *',
        hi: 'मिट्टी का प्रकार (Soil Type) *',
      },
      lbl_water: {
        te: 'నీటి వసతి (Water Availability) *',
        en: 'Water Availability *',
        hi: 'जल उपलब्धता / सिंचाई सुविधा *',
      },
      lbl_season: {
        te: 'సాగు సీజన్ (Season) *',
        en: 'Cropping Season *',
        hi: 'फसल का मौसम (Season) *',
      },
      lbl_budget: {
        te: 'మొత్తం పెట్టుబడి బడ్జెట్ ₹ (Total Budget in INR) *',
        en: 'Total Budget in INR *',
        hi: 'कुल निवेश बजट ₹ (INR) *',
      },
      lbl_risk: {
        te: 'రిస్క్ స్థాయి (Risk Tolerance)',
        en: 'Risk Tolerance',
        hi: 'जोखिम स्तर (Risk Tolerance)',
      },
      btn_calculate: {
        te: 'అనుకూల పంటలను విశ్లేషించండి (Calculate Crop Recommendations)',
        en: 'Calculate Crop Recommendations',
        hi: 'अनुकूल फसलों का विश्लेषण करें (Calculate)',
      },
      mode_wizard: {
        te: '✨ దశలవారీ ఎంపిక (5-Step Wizard)',
        en: '✨ 5-Step Guided Wizard',
        hi: '✨ 5-चरणीय मार्गदर्शन',
      },
      mode_form: {
        te: '📝 పూర్తి ఫారమ్ (All-in-One Form)',
        en: '📝 All-in-One Form',
        hi: '📝 संपूर्ण फ़ॉर्म',
      },
      btn_listen_advice: {
        te: '🔊 పంట సలహాను వినండి',
        en: '🔊 Listen to Crop Recommendations',
        hi: '🔊 फसल सलाह सुनें',
      },
      step1_title: {
        te: 'దశ 1: మీ పొలం ఎక్కడ ఉంది?',
        en: 'Step 1: Where is your farm located?',
        hi: 'चरण 1: आपका खेत कहाँ है?',
      },
      step2_title: {
        te: 'దశ 2: మీ పొలం నేల రకం ఏమిటి?',
        en: 'Step 2: What is your soil type?',
        hi: 'चरण 2: आपके खेत की मिट्टी कैसी है?',
      },
      step3_title: {
        te: 'దశ 3: సాగు విస్తీర్ణం ఎంత (ఎకరాలు)?',
        en: 'Step 3: How many acres of land?',
        hi: 'चरण 3: खेती का रकबा कितना है (एकड़)?',
      },
      step4_title: {
        te: 'దశ 4: నీటి వసతి ఎలా ఉంది?',
        en: 'Step 4: Water availability for irrigation?',
        hi: 'चरण 4: सिंचाई के पानी की सुविधा?',
      },
      step5_title: {
        te: 'దశ 5: ఏ కాలంలో సాగు చేయదలిచారు?',
        en: 'Step 5: Which cropping season?',
        hi: 'चरण 5: किस मौसम में फसल बोना चाहते हैं?',
      },
      btn_find_crops: {
        te: '🔍 నా పొలానికి అనుకూల పంటలను చూపించండి',
        en: '🔍 Show Recommended Crops for My Farm',
        hi: '🔍 मेरे खेत के लिए उपयुक्त फसलें दिखाएं',
      },
    },
    health: {
      heading: {
        te: 'పంట ఆరోగ్యం & రోగనిర్ధారణ (Crop Health & Diagnostics)',
        en: 'Crop Health & Disease Diagnostics',
        hi: 'फसल स्वास्थ्य एवं रोग निदान (Crop Health)',
      },
      subheading: {
        te: 'ICAR & వ్యవసాయ విశ్వవిద్యాలయాల ధృవీకరించిన లక్షణాల ఆధారంగా పంట సమస్యలను గుర్తించండి.',
        en: 'Identify crop disorders and insect pests based on ICAR & State Agricultural University verified symptoms.',
        hi: 'ICAR और कृषि विश्वविद्यालयों द्वारा प्रमाणित लक्षणों के आधार पर फसल रोगों और कीटों की पहचान करें।',
      },
      btn_voice_symptoms: {
        te: 'వాయిస్ ద్వారా లక్షణాలు చెప్పండి',
        en: 'Describe Symptoms via Voice',
        hi: 'बोलकर लक्षण बताएं (Voice)',
      },
      chip_paddy: {
        te: 'వరి ఆకులు పసుపుబారడం (Paddy Yellowing)',
        en: 'Paddy Yellowing',
        hi: 'धान की पत्तियों का पीलापन (Paddy Yellowing)',
      },
      chip_cotton: {
        te: 'పత్తి ఆకు ఎర్రబడటం & ముడత (Cotton Reddening)',
        en: 'Cotton Leaf Reddening & Curl',
        hi: 'कपास की पत्तियां लाल होना व मरोड़िया',
      },
      chip_chilli: {
        te: 'మిరప ఆకు ముడత (Chilli Leaf Curl)',
        en: 'Chilli Leaf Curl',
        hi: 'मिर्च का पत्ता मरोड़ रोग (Chilli Leaf Curl)',
      },
      chip_wheat: {
        te: 'గోధుమ పసుపు చారలు (Wheat Rust/Yellowing)',
        en: 'Wheat Yellow Rust',
        hi: 'गेहूं का पीला रतुआ (Wheat Rust)',
      },
      chip_maize: {
        te: 'మొక్కజొన్న కత్తెర పురుగు (Fall Armyworm)',
        en: 'Maize Fall Armyworm',
        hi: 'मक्का का फाल आर्मीवर्म कीट (Fall Armyworm)',
      },
      lbl_crop: {
        te: 'పంట పేరు (Crop Name) *',
        en: 'Crop Name *',
        hi: 'फसल का नाम (Crop Name) *',
      },
      lbl_symptom: {
        te: 'కనిపిస్తున్న లక్షణం (Observed Symptom) *',
        en: 'Observed Symptom *',
        hi: 'दिखाई दे रहा लक्षण (Observed Symptom) *',
      },
      ph_symptom: {
        te: 'ఉదా: ఆకులు పసుపు రంగులోకి మారుతున్నాయి / yellow leaves',
        en: 'e.g. leaves turning yellow from bottom, drying tips',
        hi: 'उदा: निचली पत्तियां पीली पड़ रही हैं, सूख रही हैं',
      },
      lbl_notes: {
        te: 'పొలం పరిశీలన వివరాలు - ఐచ్ఛికం (Field Observations)',
        en: 'Field Observations: Crop age, top vs bottom leaves, water condition',
        hi: 'खेत निरीक्षण विवरण - ऐच्छिक (फसल उम्र, पत्तियों की स्थिति, जलभराव)',
      },
      ph_notes: {
        te: 'ఉదా: పంట వయస్సు 25 రోజులు, కింది పాత ఆకులపై ముందుగా కనిపించింది, నీరు నిలిచి ఉంది',
        en: 'e.g. crop age 25 days, noticed on older lower leaves first, waterlogged field',
        hi: 'उदा: फसल 25 दिन की है, पहले निचली पत्तियों पर दिखा, खेत में पानी भरा है',
      },
      btn_analyze: {
        te: 'లక్షణాలను విశ్లేషించండి (Analyze Crop Symptom)',
        en: 'Analyze Crop Symptom',
        hi: 'लक्षणों का विश्लेषण करें (Analyze)',
      },
      diagnostic_questions: {
        te: '❓ రోగనిర్ధారణ ప్రశ్నలు (గరిష్టంగా 3)',
        en: '❓ Diagnostic Questions (Max 3)',
        hi: '❓ रोग निदान सत्यापन प्रश्न (अधिकतम 3)',
      },
      verified_causes: {
        te: '🔍 శాస్త్రీయ ఆధారాల ప్రకారం సాధ్యమైన కారణాలు',
        en: '🔍 Verified Causes & Evidence',
        hi: '🔍 प्रमाणित संभावित कारण व साक्ष्य',
      },
      safe_cultural_steps: {
        te: '🛡️ సురక్షిత తక్షణ చర్యలు',
        en: '🛡️ Safe Cultural Next Steps',
        hi: '🛡️ सुरक्षित जैविक व सांस्कृतिक कदम',
      },
      uncertainty_notice: {
        te: '⚠️ అనిశ్చితి & తప్పనిసరి నిపుణుల తనిఖీ',
        en: '⚠️ Advisory Notice & Uncertainty',
        hi: '⚠️ सलाह सूचना व अनिश्चितता',
      },
      icar_reference: {
        te: '📚 ధృవీకరించబడిన వ్యవసాయ మూలం (ICAR)',
        en: '📚 Verified ICAR Reference',
        hi: '📚 प्रमाणित आईसीएआर संदर्भ (ICAR)',
      },
      photo_box_title: {
        te: '📸 పంట ఆకు ఫోటో తీయండి లేదా అప్‌లోడ్ చేయండి',
        en: '📸 Take or Upload Crop Leaf Photo',
        hi: '📸 फसल की पत्ती की तस्वीर लें या अपलोड करें',
      },
      btn_take_photo: {
        te: '📸 ఫోటో తీయండి / అప్‌లోడ్ చేయండి',
        en: '📸 Take Photo / Upload',
        hi: '📸 फोटो खींचें / अपलोड करें',
      },
      photo_attached: {
        te: 'ఆకు ఫోటో జతచేయబడింది',
        en: 'Leaf Photo Attached',
        hi: 'पत्ती का फोटो संलग्न है',
      },
      photo_remove: {
        te: 'తొలగించండి',
        en: 'Remove',
        hi: 'हटाएं',
      },
      btn_listen_diag: {
        te: '🔊 రోగనిర్ధారణ సమాధానం వినండి',
        en: '🔊 Listen to Diagnosis',
        hi: '🔊 निदान व उपाय सुनें',
      },
      severity_mild: {
        te: '🟢 సాధారణ సమస్య — సకాలంలో నివారణ సాధ్యం',
        en: '🟢 Mild — Preventable with standard cultural steps',
        hi: '🟢 सामान्य समस्या — समय पर जैविक उपचार संभव',
      },
      severity_moderate: {
        te: '🟡 జాగ్రత్త అవసరం — వెంటనే నివారణ చర్యలు తీసుకోండి',
        en: '🟡 Moderate — Timely cultural action recommended',
        hi: '🟡 सावधानी आवश्यक — तत्काल उपचार करें',
      },
      severity_severe: {
        te: '🔴 తీవ్రమైన సమస్య — తక్షణ చర్యలు మరియు నిపుణుల సలహా అవసరం',
        en: '🔴 Severe — Immediate action and expert confirmation needed',
        hi: '🔴 गंभीर समस्या — तत्काल कदम व कृषि अधिकारी से संपर्क करें',
      },
    },
    weather: {
      heading: {
        te: 'వాతావరణం & వ్యవసాయ హెచ్చరికలు (Weather & Alerts)',
        en: 'Weather Forecast & Agricultural Advisories',
        hi: 'मौसम पूर्वानुमान एवं कृषि चेतावनियाँ (Weather & Alerts)',
      },
      subheading: {
        te: 'వాస్తవ వాతావరణ డేటా (Open-Meteo WMO) మరియు పంట రక్షణ జాగ్రత్తలు. నకిలీ హెచ్చరికలు చూపబడవు.',
        en: 'Real-time meteorological feed (Open-Meteo WMO) and verified precautions. Zero fabricated data.',
        hi: 'वास्तविक मौसम डेटा (Open-Meteo WMO) और फसल सुरक्षा सावधानियां। कोई फर्जी चेतावनी नहीं।',
      },
      lbl_state: {
        te: 'రాష్ట్రం (State)',
        en: 'State',
        hi: 'राज्य (State)',
      },
      lbl_district: {
        te: 'జిల్లా (District)',
        en: 'District',
        hi: 'जिला (District)',
      },
      ph_district: {
        te: 'ఉదా: Warangal, Guntur, Visakhapatnam, Karimnagar',
        en: 'e.g. Warangal, Guntur, Karnal, Nagpur',
        hi: 'उदा: वारंगल, गुंटूर, करनाल, नागपुर',
      },
      btn_check: {
        te: 'వాతావరణం చూడండి (Check Live Weather)',
        en: 'Check Live Weather',
        hi: 'ताज़ा मौसम देखें (Live Weather)',
      },
      btn_listen: {
        te: '🔊 ఈరోజు వాతావరణ నివేదిక వినండి',
        en: '🔊 Listen to Weather Report',
        hi: '🔊 मौसम रिपोर्ट सुनें',
      },
      farmer_tip_title: {
        te: '🌾 ఈరోజు రైతు వ్యవసాయ సూచన',
        en: "🌾 Today's Practical Farm Advice",
        hi: '🌾 आज की किसान कृषि सलाह',
      },
    },
    voice: {
      type_or_speak_title: {
        te: 'టైప్ చేయండి లేదా మాట్లాడండి (Type or Speak)',
        en: 'Type or Speak to Fill',
        hi: 'टाइप करें या बोलकर भरें (Type or Speak)',
      },
      type_or_speak_desc: {
        te: 'ఫీల్డ్ పక్కన ఉన్న బటన్ నొక్కండి లేదా గైడెడ్ వాయిస్ అసిస్టెంట్ ద్వారా ఫారమ్ నింపండి.',
        en: 'Tap beside any field, or use the guided voice assistant to complete the entire form.',
        hi: 'किसी भी फ़ील्ड के पास दबाएं या निर्देशित वాయిस से पूरा फ़ॉर्म भरें।',
      },
      btn_voice_fill_page: {
        te: 'వాయిస్ ద్వారా నింపండి',
        en: 'Fill Form by Voice',
        hi: 'बोलकर फ़ॉर्म भरें',
      },
      fab_title: {
        te: 'అగ్రిసారథి వాయిస్ అసిస్టెంట్ (AgriSaarthi Voice)',
        en: 'AgriSaarthi Voice Assistant',
        hi: 'एग्रीसारथी वॉयस सहायक (Voice Assistant)',
      },
      drawer_title: {
        te: 'AI వాయిస్ సహాయకుడు',
        en: 'Voice AI Assistant',
        hi: 'AI वॉयस सहायक',
      },
      tab_guided: {
        te: 'ఫారమ్ నింపండి',
        en: 'Guided Form Fill',
        hi: 'फ़ॉर्म भरें',
      },
      tab_commands: {
        te: 'ఆదేశాలు & AI',
        en: 'Ask & Commands',
        hi: 'आदेश व AI',
      },
      guided_page_label: {
        te: 'ప్రస్తుత పేజీ:',
        en: 'Current Page:',
        hi: 'वर्तमान पृष्ठ:',
      },
      current_page_label: {
        te: 'ప్రస్తుత పేజీ:',
        en: 'Current Page:',
        hi: 'वर्तमान पृष्ठ:',
      },
      guided_start_btn: {
        te: '▶ వాయిస్ ద్వారా ఫారమ్ నింపండి',
        en: '▶ Start Guided Voice Filling',
        hi: '▶ बोलकर फ़ॉर्म भरना शुरू करें',
      },
      guided_repeat_btn: {
        te: '🔁 ప్రాంప్ట్ పునరావృతం',
        en: '🔁 Repeat Prompt',
        hi: '🔁 पुनः पूछें',
      },
      guided_skip_btn: {
        te: '⏭ దాటవేయండి',
        en: '⏭ Skip Field',
        hi: '⏭ छोड़ें',
      },
      guided_stop_btn: {
        te: '⏹ ఆపండి',
        en: '⏹ Stop',
        hi: '⏹ रोकें',
      },
      close_title: {
        te: 'వాయిస్ సహాయకుడిని మూసివేయండి',
        en: 'Close Voice Assistant',
        hi: 'वॉयस सहायक बंद करें',
      },
      close_aria: {
        te: 'వాయిస్ సహాయకుడిని మూసివేయండి',
        en: 'Close Voice Assistant',
        hi: 'वॉयस सहायक बंद करें',
      },
      tap_to_speak: {
        te: 'నొక్కి మాట్లాడండి',
        en: 'Tap to Speak',
        hi: 'बोलने के लिए दबाएं',
      },
      you_said: {
        te: 'మీరు అన్నది:',
        en: 'You said:',
        hi: 'आपने कहा:',
      },
      assistant_reply: {
        te: 'అగ్రిసారథి సమాధానం:',
        en: 'AgriSaarthi Reply:',
        hi: 'अग्रिसारथी उत्तर:',
      },
      heard_label: {
        te: 'విన్న మాట:',
        en: 'Heard:',
        hi: 'सुनी गई बात:',
      },
      btn_listen: {
        te: '🔊 వినండి',
        en: '🔊 Listen',
        hi: '🔊 सुनें',
      },
      repeat_btn: {
        te: '🔁 ప్రాంప్ట్ పునరావృతం',
        en: '🔁 Repeat Prompt',
        hi: '🔁 पुनः पूछें',
      },
      chip_dashboard: {
        te: 'రైతు డాష్‌బోర్డ్',
        en: 'Farmer Dashboard',
        hi: 'किसान डैशबोर्ड',
      },
      chip_advisory: {
        te: 'పంట సలహా',
        en: 'Crop Advisory',
        hi: 'फसल सलाह',
      },
      chip_weather: {
        te: 'వాతావరణం',
        en: 'Weather',
        hi: 'मौसम',
      },
      chip_health: {
        te: 'పంట ఆరోగ్యం',
        en: 'Crop Health',
        hi: 'फसल स्वास्थ्य',
      },
      chip_pest: {
        te: 'చీడపీడల నివారణ',
        en: 'Pest Control',
        hi: 'कीट नियंत्रण',
      },
      commands_desc: {
        te: 'మాట్లాడండి — ఏదైనా పేజీకి వెళ్లండి లేదా వ్యవసాయ ప్రశ్న అడగండి.',
        en: 'Speak naturally — navigate to any page or ask any farming question.',
        hi: 'बोलें — किसी भी पेज पर जाएं या खेती से जुड़ा कोई भी प्रश्न पूछें।',
      },
      status_idle: {
        te: 'సిద్ధంగా ఉంది',
        en: 'Ready',
        hi: 'तैयार',
      },
      status_listening: {
        te: 'వింటోంది...',
        en: 'Listening...',
        hi: 'सुन रहे हैं...',
      },
      status_processing: {
        te: 'విశ్లేషిస్తోంది...',
        en: 'Processing...',
        hi: 'प्रोसेस कर रहे हैं...',
      },
      welcome_bubble: {
        te: '<strong>నమస్కారం రైతు సోదరులారా! నేను అగ్రిసారథి AI (AgriSaarthi AI)</strong>... మీ పంట సాగు, నేల ఆరోగ్యం, చీడపీడల నివారణ మరియు వాతావరణ సమాచారం గురించి మీ సొంత భాషలో నన్ను అడగండి.',
        en: '<strong>Welcome farmers! I am AgriSaarthi AI</strong>... Ask me in your own language about crop advisory, crop health, pest diagnosis, and local weather forecasts.',
        hi: '<strong>नमस्कार किसान भाइयों! मैं एग्रीसारथी AI (AgriSaarthi AI) हूँ</strong>... फसल सलाह, कीट रोग निदान और मौसम की जानकारी के लिए अपनी भाषा में मुझसे पूछें।',
      },
      tab_advisory: {
        te: 'పంట సిఫార్సు (Crop Advisory)',
        en: 'Crop Recommendations',
        hi: 'फसल सिफारिश (Crop Advisory)',
      },
      tab_problems: {
        te: 'పంట సమస్య & రోగనిర్ధారణ (Crop Health)',
        en: 'Crop Problem & Diagnostics',
        hi: 'फसल समस्या व रोग निदान (Crop Health)',
      },
      lbl_voice_lang: {
        te: 'వాయిస్ భాష (Voice Language):',
        en: 'Voice Language:',
        hi: 'बोलने व सुनने की भाषा:',
      },
      btn_listen: {
        te: 'వినండి (Listen)',
        en: 'Listen',
        hi: 'सुनें (Listen)',
      },
      btn_pause: {
        te: '⏸ పాజ్ (Pause)',
        en: '⏸ Pause',
        hi: '⏸ ठहराएं (Pause)',
      },
      btn_resume: {
        te: '▶ కొనసాగించండి (Resume)',
        en: '▶ Resume',
        hi: '▶ जारी रखें (Resume)',
      },
      btn_replay: {
        te: 'మళ్ళీ (Replay)',
        en: 'Replay',
        hi: 'पुनः सुनें (Replay)',
      },
      btn_stop: {
        te: '⏹ ఆపు (Stop)',
        en: '⏹ Stop',
        hi: '⏹ रोकें (Stop)',
      },
      speaking_msg: {
        te: 'అసిస్టెంట్ మాట్లాడుతున్నారు...',
        en: 'Assistant is speaking...',
        hi: 'सहायक बोल रहा है...',
      },
      listening_msg: {
        te: 'రైతు గళం వింటున్నాను... మాట్లాడండి',
        en: 'Listening to your voice... Speak naturally',
        hi: 'आपकी आवाज़ सुन रहा हूँ... बोलिए',
      },
      processing_msg: {
        te: '⏳ మాటలను అక్షరాలుగా మారుస్తున్నాము...',
        en: '⏳ Processing speech...',
        hi: '⏳ आवाज़ को टेक्स्ट में बदला जा रहा है...',
      },
      input_ph: {
        te: 'మీ వ్యవసాయ వివరాలు మాట్లాడండి లేదా టైప్ చేయండి...',
        en: 'Speak or type your crop symptom or farm details...',
        hi: 'अपनी फसल का लक्षण या खेत का विवरण बोलें या लिखें...',
      },
      send_btn_title: {
        te: 'పంపండి (Send)',
        en: 'Send Message',
        hi: 'भेजें (Send)',
      },
      mic_btn_title: {
        te: 'మైక్రోఫోన్ ద్వారా మాట్లాడండి (Speak via Microphone)',
        en: 'Speak via Microphone',
        hi: 'माइक द्वारा बोलें (Speak via Mic)',
      },
      notice_cacp: {
        te: '<strong>CACP & ICAR ప్రామాణిక నివేదికలు మరియు MSP 2024–2025 ఆధారితం.</strong> లైవ్ వాతావరణం/మండి స్క్రాపింగ్ లేదు (శాస్త్రీయ అంచనాలు మాత్రమే).',
        en: '<strong>Grounded in official CACP & ICAR research guidelines and MSP 2024–2025 benchmarks.</strong> No fabricated data or web scraping.',
        hi: '<strong>CACP व ICAR वैज्ञानिक दिशा-निर्देशों एवं न्यूनतम समर्थन मूल्य (MSP 2024–2025) पर आधारित।</strong> कोई मनगढ़ंत डेटा नहीं।',
      },
      notice_browser: {
        te: 'ℹ గమనిక: బ్రౌజర్ Web Speech API ఆధారంగా తెలుగు (te-IN), హిందీ (hi-IN) & English (en-IN) వాయిస్ రికగ్నిషన్ సపోర్ట్ ఉంది (Chrome/Edge సిఫార్సు). మాట్లాడిన తర్వాత టెక్స్ట్ ఎడిట్ చేసి పంపవచ్చు.',
        en: 'ℹ Note: Uses browser Web Speech API with Telugu (te-IN), Hindi (hi-IN) & English (en-IN) recognition (Chrome/Edge recommended). You can edit transcript before sending.',
        hi: 'ℹ सूचना: ब्राउज़र Web Speech API आधारित तेलुगु (te-IN), हिंदी (hi-IN) और अंग्रेजी (en-IN) वॉयस पहचान समर्थित है (Chrome/Edge अनुशंसित)। बोलने के बाद टेक्स्ट संशोधित कर सकते हैं।',
      },
    },
    profile: {
      onboarding_title: {
        te: '<strong>స్వాగతం! మీ రైతు ఖాతా సిద్ధంగా ఉంది.</strong><br>వ్యక్తిగతీకరించిన పంట సిఫార్సులు మరియు మీ జిల్లా వాతావరణం కోసం కింది వ్యవసాయ వివరాలను పూర్తి చేయండి. (ఐచ్ఛిక ఫీల్డ్‌లను ఇప్పుడే దాటవేసి నేరుగా డాష్‌బోర్డ్‌కు వెళ్ళవచ్చు).',
        en: '<strong>Welcome! Your farmer account is ready.</strong><br>Complete your farm holding details below for customized crop recommendations and local weather forecasts. (Optional fields can be skipped).',
        hi: '<strong>स्वागत है! आपका किसान खाता तैयार है।</strong><br>सटीक फसल सिफारिशों और स्थानीय मौसम के लिए नीचे दिए गए खेत के विवरण भरें। (ऐच्छिक फ़ील्ड अभी छोड़कर सीधे डैशबोर्ड जा सकते हैं)।',
      },
      heading: {
        te: 'రైతు & వ్యవసాయ భూమి ప్రొఫైల్ (Farmer & Farm Profile)',
        en: 'Farmer & Farm Holding Profile',
        hi: 'किसान एवं कृषि भूमि प्रोफ़ाइल (Farm Profile)',
      },
      subheading: {
        te: 'మీ ప్రాంతం, నేల రకం, నీటి వసతి మరియు బడ్జెట్ వివరాలను ఎప్పుడైనా మార్చుకోవచ్చు.',
        en: 'Update your location, soil type, water availability, and budget parameters anytime.',
        hi: 'अपने क्षेत्र, मिट्टी के प्रकार, सिंचाई सुविधा और मौसमी बजट का विवरण कभी भी अपडेट करें।',
      },
      skip_btn: {
        te: '⏭ ఇప్పుడే దాటవేయండి → డాష్‌బోర్డ్ (Skip for Now)',
        en: '⏭ Skip for Now → Dashboard',
        hi: '⏭ अभी छोड़ें → डैशबोर्ड',
      },
      lbl_fullname: {
        te: 'పూర్తి పేరు (Full Name) *',
        en: 'Full Name *',
        hi: 'पूरा नाम (Full Name) *',
      },
      lbl_email: {
        te: 'ఈమెయిల్ చిరునామా (Email Address)',
        en: 'Email Address',
        hi: 'ईमेल पता (Email Address)',
      },
      lbl_phone: {
        te: 'ఫోన్ నంబర్ - 10 అంకెలు (10-Digit Phone Number)',
        en: '10-Digit Phone Number',
        hi: '10-अंकीय फोन नंबर',
      },
      lbl_state: {
        te: 'రాష్ట్రం (State)',
        en: 'State',
        hi: 'राज्य (State)',
      },
      lbl_district: {
        te: 'జిల్లా (District)',
        en: 'District',
        hi: 'जिला (District)',
      },
      lbl_mandal: {
        te: 'మండలం (Mandal)',
        en: 'Mandal / Tehsil',
        hi: 'मंडल / तहसील (Mandal/Tehsil)',
      },
      ph_mandal: {
        te: 'ఉదా: పరకాల (Parkal)',
        en: 'e.g. Parkal, Karnal',
        hi: 'उदा: परकाल, करनाल',
      },
      lbl_village: {
        te: 'గ్రామం (Village)',
        en: 'Village',
        hi: 'गांव (Village)',
      },
      ph_village: {
        te: 'ఉదా: ధర్మారం (Dharmaram)',
        en: 'e.g. Dharmaram',
        hi: 'उदा: धर्माराम',
      },
      lbl_acres: {
        te: 'భూమి విస్తీర్ణం - ఎకరాలు (Land Size in Acres)',
        en: 'Land Size in Acres',
        hi: 'भूमि का रकबा - एकड़ (Land Size)',
      },
      lbl_soil: {
        te: 'ప్రధాన నేల రకం (Dominant Soil Type)',
        en: 'Dominant Soil Type',
        hi: 'मुख्य मिट्टी का प्रकार (Soil Type)',
      },
      lbl_water: {
        te: 'నీటి వసతి (Water Availability)',
        en: 'Water Availability',
        hi: 'सिंचाई / जल उपलब्धता (Water)',
      },
      lbl_season: {
        te: 'ప్రస్తుత సాగు సీజన్ (Target Season)',
        en: 'Target Cropping Season',
        hi: 'लक्षित फसल का मौसम (Target Season)',
      },
      lbl_budget: {
        te: 'సీజన్ పెట్టుబడి బడ్జెట్ ₹ (Planned Budget in INR)',
        en: 'Planned Budget in INR',
        hi: 'मौसमी निवेश बजट ₹ (Budget in INR)',
      },
      lbl_risk: {
        te: 'రిస్క్ ప్రాధాన్యత (Risk Preference)',
        en: 'Risk Preference',
        hi: 'जोखिम प्राथमिकता (Risk Preference)',
      },
      lbl_crops: {
        te: 'సాధారణంగా పండించే పంటలు (Primary Crops Grown - Optional)',
        en: 'Primary Crops Grown (Optional)',
        hi: 'सामान्यतः उगाई जाने वाली फसलें (ऐच्छिक)',
      },
      btn_save: {
        te: 'ప్రొఫైల్ సేవ్ చేయండి (Save Farm Profile)',
        en: 'Save Farm Profile',
        hi: 'प्रोफ़ाइल सहेजें (Save Profile)',
      },
      btn_cancel: {
        te: 'రద్దు చేయండి (Cancel)',
        en: 'Cancel',
        hi: 'रद्द करें (Cancel)',
      },
      btn_back_dash: {
        te: 'డాష్‌బోర్డ్‌కు వెళ్ళండి (Back to Dashboard)',
        en: 'Back to Dashboard',
        hi: 'डैशबोर्ड पर जाएं',
      },
    },
  };

  // Dynamic phrase dictionary for programmatic phrases in portal.js
  const PHRASE_DICTIONARY = {
    'voice.tap_to_speak': { en: 'Tap to Speak', te: 'నొక్కి మాట్లాడండి', hi: 'बोलने के लिए दबाएं' },
    'voice.you_said': { en: 'You said:', te: 'మీరు అన్నది:', hi: 'आपने कहा:' },
    'voice.assistant_reply': { en: 'AgriSaarthi Reply:', te: 'అగ్రిసారథి సమాధానం:', hi: 'अग्रिसारथी उत्तर:' },
    'voice.heard_label': { en: 'Heard:', te: 'విన్న మాట:', hi: 'सुनी गई बात:' },
    'voice.btn_listen': { en: '🔊 Listen', te: '🔊 వినండి', hi: '🔊 सुनें' },
    'voice.repeat_btn': { en: '🔁 Repeat Prompt', te: '🔁 ప్రాంప్ట్ పునరావృతం', hi: '🔁 पुनः पूछें' },
    'voice.chip_dashboard': { en: 'Farmer Dashboard', te: 'రైతు డాష్‌బోర్డ్', hi: 'किसान डैशबोर्ड' },
    'voice.chip_advisory': { en: 'Crop Advisory', te: 'పంట సలహా', hi: 'फसल सलाह' },
    'voice.chip_weather': { en: 'Weather', te: 'వాతావరణం', hi: 'मौसम' },
    'voice.chip_health': { en: 'Crop Health', te: 'పంట ఆరోగ్యం', hi: 'फसल स्वास्थ्य' },
    'voice.chip_pest': { en: 'Pest Control', te: 'చీడపీడల నివారణ', hi: 'कीट नियंत्रण' },
    'voice.drawer_title': { en: 'Voice AI Assistant', te: 'AI వాయిస్ సహాయకుడు', hi: 'AI वॉयस सहायक' },
    'voice.tab_guided': { en: 'Guided Form Fill', te: 'ఫారమ్ నింపండి', hi: 'फ़ॉर्म भरें' },
    'voice.tab_commands': { en: 'Ask & Commands', te: 'ఆదేశాలు & AI', hi: 'आदेश व AI' },
    'voice.guided_page_label': { en: 'Current Page:', te: 'ప్రస్తుత పేజీ:', hi: 'वर्तमान पृष्ठ:' },
    'voice.current_page_label': { en: 'Current Page:', te: 'ప్రస్తుత పేజీ:', hi: 'वर्तमान पृष्ठ:' },
    'voice.guided_start_btn': { en: '▶ Start Guided Voice Filling', te: '▶ వాయిస్ ద్వారా ఫారమ్ నింపండి', hi: '▶ बोलकर फ़ॉर्म भरना शुरू करें' },
    'voice.guided_repeat_btn': { en: '🔁 Repeat Prompt', te: '🔁 ప్రాంప్ట్ పునరావృతం', hi: '🔁 पुनः पूछें' },
    'voice.guided_skip_btn': { en: '⏭ Skip Field', te: '⏭ దాటవేయండి', hi: '⏭ छोड़ें' },
    'voice.guided_stop_btn': { en: '⏹ Stop', te: '⏹ ఆపండి', hi: '⏹ रोकें' },
    'voice.close_title': { en: 'Close Voice Assistant', te: 'వాయిస్ సహాయకుడిని మూసివేయండి', hi: 'वॉयस सहायक बंद करें' },
    'voice.close_aria': { en: 'Close Voice Assistant', te: 'వాయిస్ సహాయకుడిని మూసివేయండి', hi: 'वॉयस सहायक बंद करें' },
    'Current Page:': { en: 'Current Page:', te: 'ప్రస్తుత పేజీ:', hi: 'वर्तमान पृष्ठ:' },
    'ప్రస్తుత పేజీ:': { en: 'Current Page:', te: 'ప్రస్తుత పేజీ:', hi: 'वर्तमान पृष्ठ:' },
    'Farmer Profile': { en: 'Farmer Profile', te: 'రైతు ప్రొఫైల్', hi: 'किसान प्रोफ़ाइल' },
    'రైతు ప్రొఫైల్': { en: 'Farmer Profile', te: 'రైతు ప్రొఫైల్', hi: 'किसान प्रोफ़ाइल' },
    'app.badge': { en: '(Farmer Assistant)', te: '(రైతు సహాయకుడు)', hi: '(किसान सहायक)' },
    'app.title': { en: 'AgriSaarthi AI (Farmer Assistant)', te: 'AgriSaarthi AI (రైతు సహాయకుడు)', hi: 'AgriSaarthi AI (किसान सहायक)' },
    'auth.otp_step1_desc': { en: 'Enter your registered mobile number, username, or email. We will send an instant 6-digit verification OTP.', te: 'మీ రిజిస్టర్డ్ మొబైల్ లేదా ఈమెయిల్‌ను నమోదు చేయండి. మేము తక్షణమే 6-అంకెల OTP ని పంపుతాము.', hi: 'अपना पंजीकृत मोबाइल नंबर, यूजरनेम या ईमेल दर्ज करें। हम तुरंत 6 अंकों का ओटीपी भेजेंगे।' },
    'auth.btn_send_otp': { en: 'Send Verification OTP', te: 'OTP పంపండి (Send OTP)', hi: 'ओटीपी भेजें (Send OTP)' },
    'auth.otp_resend': { en: 'Resend OTP', te: 'మళ్ళీ పంపండి (Resend OTP)', hi: 'ओटीपी पुनः भेजें (Resend OTP)' },
    'auth.btn_verify_otp': { en: 'Verify OTP & Log In', te: 'ధృవీకరించి లాగిన్ అవ్వండి (Verify & Log In)', hi: 'सत्यापित करें और लॉगिन करें' },
    'మీ ధృవీకరణ OTP:': { en: 'Your verification OTP is:', te: 'మీ ధృవీకరణ OTP:', hi: 'आपका सत्यापन ओटीपी:' },
    'auth.otp_logged_in_notice': { en: 'You logged in via OTP. Please update your account password.', te: 'మీరు OTP ద్వారా లాగిన్ అయ్యారు. దయచేసి మీ ఖాతా పాస్‌వర్డ్‌ను అప్‌డేట్ చేయండి.', hi: 'आप OTP द्वारा लॉगिन हुए हैं। कृपया अपना खाता पासवर्ड अपडेट करें।' },
    'auth.btn_set_password_now': { en: 'Update Your Password', te: 'మీ పాస్‌వర్డ్‌ను అప్‌డేట్ చేయండి (Update Your Password)', hi: 'अपना पासवर्ड अपडेट करें' },
    'auth.password_updated_banner_title': { en: 'Password Updated Successfully!', te: 'పాస్‌వర్డ్ విజయవంతంగా అప్‌డేట్ చేయబడింది!', hi: 'पासवर्ड सफलतापूर्वक अपडेट हो गया!' },
    'auth.password_updated_banner_desc': { en: 'Password updated successfully! You can now log in using your new password.', te: 'పాస్‌వర్డ్ విజయవంతంగా అప్‌డేట్ చేయబడింది! మీరు ఇప్పుడు మీ కొత్త పాస్‌వర్డ్‌తో లాగిన్ అవ్వవచ్చు.', hi: 'पासवर्ड सफलतापूर्वक अपडेट हो गया! अब आप अपने नए पासवर्ड से लॉगिन कर सकते हैं।' },
    'auth.otp_login_title': { en: 'Verify OTP to Log In', te: 'ఓటీపీని ధృవీకరించి లాగిన్ అవ్వండి (Verify OTP to Log In)', hi: 'ओटीपी सत्यापित करके लॉगिन करें' },
    'auth.otp_step2_heading': { en: 'Verify OTP to Log In', te: 'ఓటీపీని ధృవీకరించండి (Verify OTP to Log In)', hi: 'ओटीपी सत्यापित करें' },
    'auth.otp_logged_in_notice': { en: 'You logged in via OTP. Please update your account password.', te: 'మీరు OTP ద్వారా లాగిన్ అయ్యారు. దయచేసి మీ ఖాతా పాస్‌వర్డ్‌ను అప్‌డేట్ చేయండి.', hi: 'आप OTP द्वारा लॉगिन हुए हैं। कृपया अपना खाता पासवर्ड अपडेट करें।' },
    'auth.btn_set_password_now': { en: 'Update Your Password', te: 'మీ పాస్‌వర్డ్‌ను అప్‌డేట్ చేయండి (Update Your Password)', hi: 'अपना पासवर्ड अपडेट करें' },
    'auth.password_updated_banner_title': { en: 'Password Updated Successfully!', te: 'పాస్‌వర్డ్ విజయవంతంగా అప్‌డేట్ చేయబడింది!', hi: 'पासवर्ड सफलतापूर्वक अपडेट हो गया!' },
    'auth.password_updated_banner_desc': { en: 'Password updated successfully! You can now log in using your new password.', te: 'పాస్‌వర్డ్ విజయవంతంగా అప్‌డేట్ చేయబడింది! మీరు ఇప్పుడు మీ కొత్త పాస్‌వర్డ్‌తో లాగిన్ అవ్వవచ్చు.', hi: 'पासवर्ड सफलतापूर्वक अपडेट हो गया! अब आप अपने नए पासवर्ड से लॉगिन कर सकते हैं।' },
    'voice.type_or_speak_title': { en: 'Type or Speak to Fill', te: 'టైప్ చేయండి లేదా మాట్లాడండి (Type or Speak)', hi: 'टाइप करें या बोलकर भरें (Type or Speak)' },
    'voice.type_or_speak_desc': { en: 'Tap beside any field, or use the guided voice assistant to complete the entire form.', te: 'ఫీల్డ్ పక్కన ఉన్న బటన్ నొక్కండి లేదా గైడెడ్ వాయిస్ అసిస్టెంట్ ద్వారా ఫారమ్ నింపండి.', hi: 'किसी भी फ़ील्ड के पास दबाएं या निर्देशित वాయిस से पूरा फ़ॉर्म भरें।' },
    'voice.btn_voice_fill_page': { en: 'Fill Form by Voice', te: 'వాయిస్ ద్వారా నింపండి', hi: 'बोलकर फ़ॉर्म भरें' },
    'voice.fab_title': { en: 'AgriSaarthi Voice Assistant', te: 'అగ్రిసారథి వాయిస్ అసిస్టెంట్', hi: 'एग्रीसारथी वॉयस सहायक' },
    'voice.commands_desc': { en: 'Speak naturally — navigate to any page or ask any farming question.', te: 'మాట్లాడండి — ఏదైనా పేజీకి వెళ్లండి లేదా వ్యవసాయ ప్రశ్న అడగండి.', hi: 'बोलें — किसी भी पेज पर जाएं या खेती से जुड़ा प्रश्न पूछें।' },
    'voice.status_idle': { en: 'Ready', te: 'సిద్ధంగా ఉంది', hi: 'तैयार' },
    'voice.status_listening': { en: 'Listening...', te: 'వింటోంది...', hi: 'सुन रहे हैं...' },
    'voice.status_processing': { en: 'Processing...', te: 'విశ్లేషిస్తోంది...', hi: 'प्रोसेस कर रहे हैं...' },
    'వాయిస్ ద్వారా చెప్పండి': { en: 'Speak for this field', te: 'వాయిస్ ద్వారా చెప్పండి', hi: 'बोलकर दर्ज करें' },
    'నమోదు చేయబడింది': { en: 'Recorded', te: 'నమోదు చేయబడింది', hi: 'दर्ज किया गया' },
    'దాటవేయబడింది': { en: 'Skipped', te: 'దాటవేయబడింది', hi: 'छोड़ दिया गया' },
    'దయచేసి మళ్ళీ చెప్పండి.': { en: 'Please say again.', te: 'దయచేసి మళ్ళీ చెప్పండి.', hi: 'कृपया पुनः बताएं।' },
    'ఫారమ్ పూర్తి చేయబడింది!': { en: 'Form completed!', te: 'ఫారమ్ పూర్తి చేయబడింది!', hi: 'फ़ॉर्म पूर्ण हो गया!' },
    'profile.btn_cancel': { en: 'Cancel', te: 'రద్దు చేయండి (Cancel)', hi: 'रद्द करें (Cancel)' },
    'btn_cancel': { en: 'Cancel', te: 'రద్దు చేయండి (Cancel)', hi: 'रद्द करें (Cancel)' },
    'Cancel': { en: 'Cancel', te: 'రద్దు చేయండి', hi: 'रद्द करें' },
    'time_now': { en: 'Just now', te: 'ఇప్పుడే', hi: 'अभी' },
    'wiz_step1_name': { en: 'Personal', te: 'వ్యక్తిగతం', hi: 'व्यक्तिगत' },
    'wiz_step2_name': { en: 'Location', te: 'ప్రాంతం', hi: 'स्थान' },
    'wiz_step3_name': { en: 'Land', te: 'భూమి', hi: 'भूमि' },
    'wiz_step4_name': { en: 'Soil', te: 'నేల', hi: 'मिट्टी' },
    'wiz_step5_name': { en: 'Crops & Water', te: 'సాగు & నీరు', hi: 'फसल व पानी' },
    'wiz_step6_name': { en: 'Privacy', te: 'గోప్యత', hi: 'गोपनीयता' },
    'wiz_btn_back': { en: '⬅ Back', te: '⬅ వెనుకకు', hi: '⬅ पीछे' },
    'wiz_btn_next': { en: 'Next Step', te: 'తదుపరి దశ', hi: 'अगला चरण' },
    'wiz_btn_save': { en: 'Complete Profile', te: 'ప్రొఫైల్ పూర్తి చేయండి', hi: 'प्रोफ़ाइल पूर्ण करें' },
    'login_or': { en: 'OR', te: 'లేదా (OR)', hi: 'या (OR)' },
    'LOGIN_OR': { en: 'OR', te: 'లేదా (OR)', hi: 'या (OR)' },
    'login_google': { en: 'Continue with Google', te: 'Google తో కొనసాగించండి (Continue with Google)', hi: 'Google से जारी रखें (Continue with Google)' },
    'login_coming_soon': { en: 'Coming soon', te: 'త్వరలో అందుబాటులోకి', hi: 'जल्द आ रहा है' },
    'forgot_password': { en: 'Forgot Password?', te: 'పాస్‌వర్డ్ మర్చిపోయారా? (Forgot Password?)', hi: 'पासवर्ड भूल गए? (Forgot Password?)' },
    // Buttons & Actions
    'వ్యవసాయ ప్రొఫైల్ పూర్తి చేయండి': { en: 'Complete Farm Profile', hi: 'खेत प्रोफ़ाइल पूरी करें' },
    'నా పొలానికి పంట సిఫార్సు పొందండి': { en: 'Get Crop Advisory for My Farm', hi: 'अपने खेत के लिए फसल सलाह प्राप्त करें' },
    'వివరాలు మార్చండి': { en: 'Edit Farm Profile', hi: 'विवरण संपादित करें' },
    'మళ్ళీ ప్రయత్నించండి': { en: 'Retry Request', hi: 'पुनः प्रयास करें' },
    'సేవ్ చేస్తున్నాము...': { en: 'Saving...', hi: 'सहेज रहे हैं...' },
    'విశ్లేషిస్తున్నాము...': { en: 'Analyzing...', hi: 'विश्लेषण कर रहे हैं...' },

    // Metrics & Labels
    'రాష్ట్రం / జిల్లా': { en: 'State / District', hi: 'राज्य / जिला' },
    'భూమి విస్తీర్ణం': { en: 'Land Holding', hi: 'भूमि का रकबा' },
    'ఎకరాలు': { en: 'Acres', hi: 'एकड़' },
    'acres': { en: 'acres', hi: 'एकड़' },
    'నేల & నీటి వసతి': { en: 'Soil & Water', hi: 'मिट्टी और पानी' },
    'సీజన్ & బడ్జెట్': { en: 'Season & Budget', hi: 'मौसम और बजट' },
    'ఉష్ణోగ్రత': { en: 'Temperature', hi: 'तापमान' },
    'వాతావరణ స్థితి': { en: 'Condition', hi: 'मौसम स्थिति' },
    'వాతావరణం': { en: 'Condition', hi: 'मौसम' },
    'గాలిలో తేమ': { en: 'Humidity', hi: 'हवा में नमी' },
    'Relative Humidity': { en: 'Relative Humidity', hi: 'सापेक्ष आर्द्रता' },
    'గాలి వేగం': { en: 'Wind Speed', hi: 'हवा की गति' },
    'గాలి వేగం & వర్షం': { en: 'Wind & Precipitation', hi: 'हवा की गति व वर्षा' },
    'వర్షపాతం': { en: 'Precipitation', hi: 'वर्षा' },
    'గరిష్ట / కనిష్ట': { en: 'Max / Min', hi: 'अधिकतम / न्यूनतम' },
    'గరిష్ట గాలి వేగం': { en: 'Max Wind Speed', hi: 'अधिकतम हवा गति' },
    'ప్రస్తుత వాతావరణం': { en: 'Current Conditions', hi: 'वर्तमान मौसम' },
    'వాస్తవ డేటా (Live)': { en: 'Live WMO Feed', hi: 'लाइव मौसम डेटा' },

    // Advisory Cards
    'ప్రధాన సిఫార్సు (Primary)': { en: 'Primary Recommendation', hi: 'मुख्य अनुशंसित फसल' },
    'ప్రత్యామ్నాయ పంట (Alternative/Hedge)': { en: 'Diversified Alternative', hi: 'विविधीकृत वैकल्पिक फसल' },
    'అనుకూలత స్కోరు': { en: 'Suitability Score', hi: 'उपयुक्तता स्कोर' },
    'Suitability': { en: 'Suitability', hi: 'उपयुक्तता' },
    'ఎకరానికి ఖర్చు (CACP)': { en: 'Est. Cost / Acre (CACP)', hi: 'अनुमानित लागत / एकड़ (CACP)' },
    'Est. Cost / Acre': { en: 'Est. Cost / Acre', hi: 'अनुमानित लागत / एकड़' },
    'మొత్తం ఖర్చు & బడ్జెట్ స్థితి': { en: 'Total Cost & Feasibility', hi: 'कुल लागत व बजट स्थिति' },
    'Total Cost & Feasibility': { en: 'Total Cost & Feasibility', hi: 'कुल लागत व व्यवहार्यता' },
    'ఆశించే దిగుబడి / ఎకరానికి': { en: 'Expected Yield / Acre', hi: 'अपेक्षित पैदावार / एकड़' },
    'Expected Yield / Acre': { en: 'Expected Yield / Acre', hi: 'अपेक्षित पैदावार / एकड़' },
    'అంచనా నికర లాభం / ఎకరానికి': { en: 'Est. Net Profit / Acre', hi: 'अनुमानित शुद्ध लाभ / एकड़' },
    'Est. Net Profit / Acre': { en: 'Est. Net Profit / Acre', hi: 'अनुमानित शुद्ध लाभ / एकड़' },
    'సాగు సూచన:': { en: 'Agronomic Note:', hi: 'कृषि सलाह:' },
    'ప్రధాన ప్రయోజనాలు (Key Strengths)': { en: 'Key Strengths', hi: 'प्रमुख लाभ व विशेषताएं' },
    'Key Strengths': { en: 'Key Strengths', hi: 'प्रमुख लाभ व विशेषताएं' },
    'ముఖ్య జాగ్రత్తలు & రిస్కులు (Risk Factors)': { en: 'Risk Factors', hi: 'जोखिम कारक व सावधानियां' },
    'Risk Factors': { en: 'Risk Factors', hi: 'जोखिम कारक व सावधानियां' },
    'బడ్జెట్ & పొలం విశ్లేషణ (Budget Summary)': { en: 'Farm Holding & Budget Analysis', hi: 'खेत जोत एवं बजट विश्लेषण' },
    'Farm Holding & Budget Analysis': { en: 'Farm Holding & Budget Analysis', hi: 'खेत जोत एवं बजट विश्लेषण' },
    'మొత్తం బడ్జెట్': { en: 'Total Budget', hi: 'कुल बजट' },
    'విస్తీర్ణం': { en: 'Land Size', hi: 'रकबा' },
    'ఎకరానికి కేటాయింపు': { en: 'Per Acre Allocation', hi: 'प्रति एकड़ आवंटन' },
    '4-దశల నిర్ణయ ప్రక్రియ (4-Step Engine Reasoning)': { en: '4-Step Decision Engine Reasoning', hi: '4-चरणीय निर्णय इंजन तर्क' },
    'ICAR/CACP పరిమితులు & సలహాలు (Advisory & Limitations)': { en: 'ICAR/CACP Limitations & Advisory', hi: 'ICAR/CACP सीमाएँ एवं सलाह' },
    'ఈ పరిస్థితులకు సరిపోయే ప్రధాన పంటలు కనుగొనబడలేదు.': { en: 'No primary crops matched under given constraints.', hi: 'दिए गए मापदंडों के तहत कोई मुख्य फसल मेल नहीं खाती।' },

    // Health Cards
    'లక్షణ ఆధారాలు': { en: 'Field Evidence', hi: 'खेत में लक्षण साक्ष्य' },
    'Field Evidence': { en: 'Field Evidence', hi: 'खेत में लक्षण साक्ष्य' },
    'గుర్తించే కీలక తేడా': { en: 'Distinguishing Clue', hi: 'विशिष्ट पहचान सूत्र' },
    'Distinguishing Clue': { en: 'Distinguishing Clue', hi: 'विशिष्ट पहचान सूत्र' },
    'రోగనిర్ధారణ ధృవీకరణ ప్రశ్నలు (గరిష్టంగా 3)': { en: 'Diagnostic Verification Questions (Max 3)', hi: 'रोग निदान सत्यापन प्रश्न (अधिकतम 3)' },
    'శాస్త్రీయ ఆధారాల ప్రకారం సాధ్యమైన కారణాలు (Possible Causes)': { en: 'Verified Possible Causes & Field Clues', hi: 'प्रमाणित संभावित कारण व संकेत' },
    'సురక్షిత తక్షణ చర్యలు (రసాయనేతర & యాజమాన్య పద్ధతులు)': { en: 'Safe Non-Chemical & Cultural Next Steps', hi: 'सुरक्षित गैर-रासायनिक व जैविक कदम' },
    'అనిశ్చితి & నిపుణుల తనిఖీ హెచ్చరిక': { en: 'Uncertainty & Expert Inspection Notice', hi: 'अनिश्चितता व विशेषज्ञ निरीक्षण चेतावनी' },
    'ధృవీకరించబడిన ICAR / వ్యవసాయ విశ్వవిద్యాలయ మూలం': { en: 'Verified ICAR / Agricultural University Reference', hi: 'प्रमाणित ICAR / कृषि विश्वविद्यालय संदर्भ' },

    // Weather Warnings & Alerts
    '3-రోజుల వాతావరణ అంచనా (3-Day Agricultural Forecast)': { en: '3-Day Agricultural Forecast', hi: '3-दिवसीय कृषि मौसम पूर्वानुमान' },
    'అధికారిక వాతావరణ & తుఫాను హెచ్చరికల స్థితి (Official Alerts Status)': { en: 'Official Weather & Cyclone Alerts Status', hi: 'आधिकारिक मौसम एवं चक्रवात चेतावनी स्थिति' },
    'రాబోయే 3 రోజుల్లో ఎటువంటి తీవ్రమైన వాతావరణ హెచ్చరికలు (భారీ వర్షం / బలమైన గాలులు) లేవు.': {
      en: 'No severe meteorological threshold warnings (heavy rain or gale winds) in the 3-day forecast.',
      hi: 'अगले 3 दिनों में कोई गंभीर मौसम चेतावनी (भारी वर्षा या तेज आंधी) नहीं है।',
    },
    'వాతావరణ సమాచారం అందుబాటులో లేదు.': { en: 'Live weather data is unavailable.', hi: 'लाइव मौसम डेटा उपलब्ध नहीं है।' },
    'లైవ్ వాతావరణ డేటా అందుబాటులో లేదు': { en: 'Live Weather Feed Unavailable', hi: 'लाइव मौसम फ़ीड उपलब्ध नहीं है' },

    // Validation & Messages
    'పాస్‌వర్డ్ మరియు కన్ఫర్మ్ పాస్‌వర్డ్ సరిపోలలేదు.': { en: 'Password and Confirm Password do not match.', hi: 'पासवर्ड और कन्फर्म पासवर्ड मेल नहीं खाते हैं।' },
    'దయచేసి సరైన 10-అంకెల ఫోన్ నంబర్‌ను నమోదు చేయండి.': { en: 'Please enter a valid 10-digit phone number.', hi: 'कृपया एक मान्य 10-अंकीय फोन नंबर दर्ज करें।' },
    'నమోదు విఫలమైంది.': { en: 'Registration failed.', hi: 'पंजीकरण विफल रहा।' },
    'దయచేసి మొబైల్ నంబర్/యూజర్‌నేమ్ మరియు పాస్‌వర్డ్ నమోదు చేయండి.': { en: 'Please enter both mobile number/username and password.', hi: 'कृपया मोबाइल नंबर/यूजरनेम और पासवर्ड दोनों दर्ज करें।' },
    'లాగిన్ విజయవంతమైంది!': { en: 'Login successful!', hi: 'लॉगिन सफल रहा!' },
    'ప్రొఫైల్ విజయవంతంగా సేవ్ చేయబడింది!': { en: 'Farm Profile saved successfully!', hi: 'खेत प्रोफ़ाइल सफलतापूर्वक सहेजी गई!' },
    'రైతు డాష్‌బోర్డ్ మరియు ప్రొఫైల్ చూడటానికి దయచేసి లాగిన్ అవ్వండి.': { en: 'Please log in to access your Farmer Dashboard and Farm Profile.', hi: 'अपने किसान डैशबोर्ड और प्रोफ़ाइल के लिए कृपया लॉगिन करें।' },
    'మీ వ్యవసాయ భూమి వివరాలు ఇంకా పూర్తి కాలేదు. ఖచ్చితమైన పంట సిఫార్సుల కోసం మీ ప్రొఫైల్‌ను పూర్తి చేయండి.': {
      en: 'Your farm holding details have not been added yet. Complete your Farm Profile for one-click personalized crop recommendations.',
      hi: 'आपके खेत की जानकारी अभी पूरी नहीं हुई है। सटीक फसल सिफारिशों के लिए अपनी प्रोफ़ाइल पूरी करें।',
    },
    'వాస్తవ వాతావరణ డేటాను సేకరిస్తున్నాము...': { en: 'Fetching real-time meteorological feed...', hi: 'वास्तविक मौसम डेटा प्राप्त किया जा रहा है...' },
  };

  // Determine current language from storage or fallback
  let currentLanguage = (function () {
    try {
      const stored = localStorage.getItem(I18N_STORAGE_KEY);
      if (stored === 'te' || stored === 'en' || stored === 'hi') {
        return stored;
      }
    } catch (_) {}
    return DEFAULT_LANG;
  })();

  // Export to window
  window.currentLang = currentLanguage;

  /**
   * Universal translation helper `t(arg1, arg2, arg3)`.
   * Accepts:
   * 1. `t(category.key)`
   * 2. `t(teText, enText)`
   * 3. `t(teText, enText, hiText)`
   */
  function t(arg1, arg2, arg3) {
    const lang = window.currentLang || currentLanguage;

    // If arg1 is a dot-separated translation key, ALWAYS resolve via dictionary first
    if (typeof arg1 === 'string' && arg1.indexOf('.') !== -1) {
      const parts = arg1.split('.');
      if (parts.length >= 2) {
        let cur = I18N_DICTIONARY;
        for (let i = 0; i < parts.length; i++) {
          if (cur && typeof cur === 'object' && parts[i] in cur) {
            cur = cur[parts[i]];
          } else {
            cur = null;
            break;
          }
        }
        if (cur && typeof cur === 'object' && (cur.te || cur.en || cur.hi)) {
          return cur[lang] || cur[DEFAULT_LANG] || cur.en || cur.te || arg1;
        }
      }
      const cleanKey = arg1.trim();
      if (PHRASE_DICTIONARY[cleanKey] && PHRASE_DICTIONARY[cleanKey][lang]) {
        return PHRASE_DICTIONARY[cleanKey][lang];
      }
    }

    // Signature 3: t(te, en, hi)
    if (typeof arg3 !== 'undefined') {
      if (lang === 'hi') return arg3;
      if (lang === 'en') return arg2;
      return arg1;
    }

    // Signature 2: t(te, en)
    if (typeof arg2 !== 'undefined') {
      if (lang === 'en') return arg2;
      if (lang === 'hi') {
        // Look up phrase dictionary for Hindi translation
        const cleanTe = String(arg1 || '').trim();
        const cleanEn = String(arg2 || '').trim();
        if (PHRASE_DICTIONARY[cleanTe] && PHRASE_DICTIONARY[cleanTe].hi) {
          return PHRASE_DICTIONARY[cleanTe].hi;
        }
        if (PHRASE_DICTIONARY[cleanEn] && PHRASE_DICTIONARY[cleanEn].hi) {
          return PHRASE_DICTIONARY[cleanEn].hi;
        }
        // Fallback: if no direct match, return English rather than Telugu when in Hindi mode
        return arg2;
      }
      return arg1;
    }

    // Signature 1: t(dot.separated.key)
    if (typeof arg1 === 'string') {
      const parts = arg1.split('.');
      if (parts.length >= 2) {
        let cur = I18N_DICTIONARY;
        for (let i = 0; i < parts.length; i++) {
          if (cur && typeof cur === 'object' && parts[i] in cur) {
            cur = cur[parts[i]];
          } else {
            cur = null;
            break;
          }
        }
        if (cur && typeof cur === 'object' && (cur.te || cur.en || cur.hi)) {
          return cur[lang] || cur[DEFAULT_LANG] || arg1;
        }
      }
      // Check phrase dictionary directly
      const cleanKey = arg1.trim();
      if (PHRASE_DICTIONARY[cleanKey] && PHRASE_DICTIONARY[cleanKey][lang]) {
        return PHRASE_DICTIONARY[cleanKey][lang];
      }
    }

    return arg1;
  }

  /**
   * Apply translations across the entire document DOM without clearing inputs.
   */
  function applyTranslations(lang) {
    const targetLang = (lang === 'te' || lang === 'en' || lang === 'hi') ? lang : DEFAULT_LANG;
    currentLanguage = targetLang;
    window.currentLang = targetLang;

    // Update document HTML lang
    document.documentElement.lang = targetLang;

    // Update Page Title
    const titleObj = I18N_DICTIONARY.app.page_title;
    if (titleObj && titleObj[targetLang]) {
      document.title = titleObj[targetLang];
    }

    // Update all [data-i18n]
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      const key = el.getAttribute('data-i18n');
      const val = t(key);
      if (val && typeof val === 'string') {
        // Preserve HTML if it contains tags, or preserve SVG if element has icon + text span
        const textSpan = el.querySelector('span:not(.nav-icon):not(.btn-icon):not(.field-icon):not(.voice-hint-icon)');
        const svg = el.querySelector('svg');
        if (textSpan) {
          textSpan.textContent = val;
        } else if (svg) {
          let replaced = false;
          el.childNodes.forEach(function (node) {
            if (node.nodeType === 3 && node.nodeValue.trim().length > 0) {
              node.nodeValue = ' ' + val.replace(/<[^>]+>/g, '').trim();
              replaced = true;
            }
          });
          if (!replaced) {
            const span = document.createElement('span');
            span.textContent = val;
            el.appendChild(span);
          }
        } else if (val.indexOf('<') !== -1) {
          el.innerHTML = val;
        } else {
          el.textContent = val;
        }
      }
    });

    // Update [data-i18n-placeholder]
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      const key = el.getAttribute('data-i18n-placeholder');
      const val = t(key);
      if (val && typeof val === 'string') {
        el.placeholder = val;
      }
    });

    // Update [data-i18n-title]
    document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      const key = el.getAttribute('data-i18n-title');
      const val = t(key);
      if (val && typeof val === 'string') {
        el.title = val;
      }
    });

    // Update [data-i18n-aria]
    document.querySelectorAll('[data-i18n-aria]').forEach(function (el) {
      const key = el.getAttribute('data-i18n-aria');
      const val = t(key);
      if (val && typeof val === 'string') {
        el.setAttribute('aria-label', val);
      }
    });

    // Update dropdown option elements with [data-i18n-opt-te], [data-i18n-opt-en], [data-i18n-opt-hi]
    document.querySelectorAll('option[data-i18n-opt-te]').forEach(function (opt) {
      const teText = opt.getAttribute('data-i18n-opt-te');
      const enText = opt.getAttribute('data-i18n-opt-en');
      const hiText = opt.getAttribute('data-i18n-opt-hi');
      if (targetLang === 'hi' && hiText) {
        opt.textContent = hiText;
      } else if (targetLang === 'en' && enText) {
        opt.textContent = enText;
      } else if (teText) {
        opt.textContent = teText;
      }
    });

    // Update Header Language Selector Buttons
    const btnTe = document.getElementById('btn-lang-te');
    const btnEn = document.getElementById('btn-lang-en');
    const btnHi = document.getElementById('btn-lang-hi');
    if (btnTe) btnTe.classList.toggle('active', targetLang === 'te');
    if (btnEn) btnEn.classList.toggle('active', targetLang === 'en');
    if (btnHi) btnHi.classList.toggle('active', targetLang === 'hi');

    // Update Voice AI language select if present
    const voiceLangSelect = document.getElementById('voice-lang-select');
    if (voiceLangSelect) {
      const targetCode = targetLang === 'te' ? 'te-IN' : (targetLang === 'hi' ? 'hi-IN' : 'en-IN');
      if (voiceLangSelect.value !== targetCode) {
        voiceLangSelect.value = targetCode;
      }
    }

    // Persist to localStorage
    try {
      localStorage.setItem(I18N_STORAGE_KEY, targetLang);
    } catch (_) {}

    // Dispatch global event
    try {
      window.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang: targetLang } }));
    } catch (_) {}
  }

  /**
   * Set language globally and sync with backend farmer profile if logged in.
   */
  async function setLanguage(lang) {
    const targetLang = (lang === 'te' || lang === 'en' || lang === 'hi') ? lang : DEFAULT_LANG;
    applyTranslations(targetLang);

    if (window.AgriVoiceAssistant && typeof window.AgriVoiceAssistant.syncLanguage === 'function') {
      window.AgriVoiceAssistant.syncLanguage(targetLang);
    }

    // Sync with farmer profile setting if logged in
    const token = localStorage.getItem('agrisaarthi_session_token');
    if (token) {
      try {
        const apiBase = (window.AGRISAARTHI_CONFIG && window.AGRISAARTHI_CONFIG.API_BASE_URL)
          ? window.AGRISAARTHI_CONFIG.API_BASE_URL.replace(/\/$/, '')
          : '';
        await fetch(apiBase + '/api/farmer/profile', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token,
          },
          body: JSON.stringify({ preferred_language: targetLang }),
        });
      } catch (e) {
        // Silently preserve local preference on network error
      }
    }
  }

  // Expose on window
  window.i18n = {
    t: t,
    dictionary: I18N_DICTIONARY,
    phrases: PHRASE_DICTIONARY,
    applyTranslations: applyTranslations,
    setLanguage: setLanguage,
    getLanguage: function () { return currentLanguage; },
  };
  window.t = t;
  window.setLanguage = setLanguage;
  window.applyLanguage = applyTranslations;
  window.I18N = I18N_DICTIONARY;

  // Auto-apply stored language on DOM load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      applyTranslations(currentLanguage);
    });
  } else {
    applyTranslations(currentLanguage);
  }
})();

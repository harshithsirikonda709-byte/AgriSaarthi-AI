/* ==========================================================================
   AgriSaarthi AI — Complete Farmer Portal Application Controller (web/js/portal.js)
   Connects the 9 portal pages to real Python backend APIs, SQLite auth,
   AgriSaarthiEngine, CROP_DISORDER_DATABASE, Open-Meteo weather, and Voice AI.
   ========================================================================== */

(function () {
  const TOKEN_STORAGE_KEY = 'agrisaarthi_session_token';
  let authToken = localStorage.getItem(TOKEN_STORAGE_KEY) || '';
  let currentFarmer = null;
  let currentPage = 'home';
  let isFirstTimeOnboarding = false;

  function getApiUrl(path) {
    const cfg = window.AGRISAARTHI_CONFIG || {};
    const base = (cfg.API_BASE_URL || '').replace(/\/$/, '');
    return base + path;
  }

  function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) {
      headers['Authorization'] = 'Bearer ' + authToken;
    }
    return headers;
  }

  function t(teText, enText) {
    return (typeof currentLang !== 'undefined' && currentLang === 'en') ? enText : teText;
  }

  function showStatusAlert(elId, message, type) {
    const el = document.getElementById(elId);
    if (!el) return;
    if (!message) {
      el.className = 'status-alert';
      el.textContent = '';
      return;
    }
    el.className = 'status-alert show alert-' + (type || 'info');
    el.textContent = message;
  }

  // =========================================================================
  // Navigation & Route Protection
  // =========================================================================
  window.navigateTo = function (pageId, options) {
    const opts = options || {};
    const protectedPages = ['dashboard', 'profile'];

    if (protectedPages.includes(pageId) && ! currentFarmer) {
      navigateTo('login');
      showStatusAlert(
        'login-alert',
        t(
          '🔒 రైతు డాష్‌బోర్డ్ మరియు ప్రొఫైల్ చూడటానికి దయచేసి లాగిన్ అవ్వండి.',
          '🔒 Please log in to access your Farmer Dashboard and Farm Profile.'
        ),
        'info'
      );
      return;
    }

    currentPage = pageId;
    document.querySelectorAll('.portal-page').forEach(function (sec) {
      sec.classList.toggle('active', sec.id === 'page-' + pageId);
    });

    document.querySelectorAll('.nav-item-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-page') === pageId);
    });

    // Adjust body scroll mode: voice assistant uses internal scroll, other pages scroll naturally
    if (pageId === 'voice') {
      document.body.classList.remove('portal-body');
    } else {
      document.body.classList.add('portal-body');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    if (pageId === 'dashboard') {
      loadFarmerDashboard();
    } else if (pageId === 'advisory') {
      prefillAdvisoryForm();
    } else if (pageId === 'weather') {
      prefillWeatherFilters();
      loadWeatherPage();
    } else if (pageId === 'profile') {
      populateProfileForm(opts.onboarding === true);
    }
  };

  function updateAuthNavbar() {
    const guestBox = document.getElementById('nav-auth-guest');
    const userBox = document.getElementById('nav-auth-user');
    const userNameSpan = document.getElementById('nav-farmer-name');
    const navDashboardBtn = document.getElementById('nav-btn-dashboard');
    const navProfileBtn = document.getElementById('nav-btn-profile');
    const homeCtaAuth = document.getElementById('home-cta-authenticated');
    const homeCtaGuest = document.getElementById('home-cta-guest');

    if (currentFarmer) {
      if (guestBox) guestBox.style.display = 'none';
      if (userBox) userBox.style.display = 'flex';
      if (userNameSpan) userNameSpan.textContent = currentFarmer.full_name;
      if (navDashboardBtn) navDashboardBtn.style.display = 'inline-flex';
      if (navProfileBtn) navProfileBtn.style.display = 'inline-flex';
      if (homeCtaAuth) homeCtaAuth.style.display = 'inline-flex';
      if (homeCtaGuest) homeCtaGuest.style.display = 'none';
    } else {
      if (guestBox) guestBox.style.display = 'flex';
      if (userBox) userBox.style.display = 'none';
      if (navDashboardBtn) navDashboardBtn.style.display = 'none';
      if (navProfileBtn) navProfileBtn.style.display = 'none';
      if (homeCtaAuth) homeCtaAuth.style.display = 'none';
      if (homeCtaGuest) homeCtaGuest.style.display = 'inline-flex';
    }
  }

  // =========================================================================
  // Session Restoration, Registration, Login, Logout
  // =========================================================================
  async function restoreSession() {
    if (!authToken) {
      updateAuthNavbar();
      return;
    }
    try {
      const res = await fetch(getApiUrl('/api/farmer/profile'), {
        method: 'GET',
        headers: getAuthHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        currentFarmer = data.farmer;
        if (currentFarmer && currentFarmer.preferred_language && typeof setLanguage === 'function') {
          setLanguage(currentFarmer.preferred_language);
        }
      } else {
        authToken = '';
        currentFarmer = null;
        localStorage.removeItem(TOKEN_STORAGE_KEY);
      }
    } catch (e) {
      // Keep token on transient offline error, but guest state until verified
    }
    updateAuthNavbar();
  }

  window.handleRegisterSubmit = async function (ev) {
    if (ev) ev.preventDefault();
    showStatusAlert('register-alert', '');

    const fullName = (document.getElementById('reg-fullname').value || '').trim();
    const identifier = (document.getElementById('reg-identifier').value || '').trim();
    const password = document.getElementById('reg-password').value || '';
    const confirmPw = document.getElementById('reg-confirm-password').value || '';
    const prefLang = document.getElementById('reg-lang').value || 'te';
    const submitBtn = document.getElementById('reg-submit-btn');

    if (password !== confirmPw) {
      showStatusAlert(
        'register-alert',
        t('పాస్‌వర్డ్ మరియు కన్ఫర్మ్ పాస్‌వర్డ్ సరిపోలలేదు.', 'Password and Confirm Password do not match.'),
        'error'
      );
      return;
    }

    if (submitBtn) submitBtn.disabled = true;
    try {
      const res = await fetch(getApiUrl('/api/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName,
          identifier: identifier,
          password: password,
          preferred_language: prefLang
        })
      });
      const data = await res.json();
      if (!res.ok) {
        showStatusAlert('register-alert', data.error || t('నమోదు విఫలమైంది.', 'Registration failed.'), 'error');
        return;
      }

      authToken = data.token;
      currentFarmer = data.farmer;
      localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
      if (typeof setLanguage === 'function') {
        setLanguage(currentFarmer.preferred_language || 'te');
      }
      updateAuthNavbar();

      // Clear sensitive inputs
      document.getElementById('reg-password').value = '';
      document.getElementById('reg-confirm-password').value = '';

      // Direct to First-time Farm Profile setup (where optional fields can be skipped)
      navigateTo('profile', { onboarding: true });
    } catch (err) {
      showStatusAlert(
        'register-alert',
        t(
          'నెట్‌వర్క్ లోపం: సర్వర్‌కు కనెక్ట్ చేయలేకపోయాము. దయచేసి మళ్ళీ ప్రయత్నించండి.',
          'Network error: Unable to reach the server. Please check your connection and try again.'
        ),
        'error'
      );
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  };

  window.handleLoginSubmit = async function (ev) {
    if (ev) ev.preventDefault();
    showStatusAlert('login-alert', '');

    const identifier = (document.getElementById('login-identifier').value || '').trim();
    const password = document.getElementById('login-password').value || '';
    const submitBtn = document.getElementById('login-submit-btn');

    if (!identifier || !password) {
      showStatusAlert(
        'login-alert',
        t('దయచేసి మొబైల్ నంబర్/యూజర్‌నేమ్ మరియు పాస్‌వర్డ్ నమోదు చేయండి.', 'Please enter both mobile number/username and password.'),
        'error'
      );
      return;
    }

    if (submitBtn) submitBtn.disabled = true;
    try {
      const res = await fetch(getApiUrl('/api/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: identifier, password: password })
      });
      const data = await res.json();
      if (!res.ok) {
        showStatusAlert(
          'login-alert',
          data.error || t('తప్పు మొబైల్ నంబర్ లేదా పాస్‌వర్డ్.', 'Invalid mobile number/username or password.'),
          'error'
        );
        return;
      }

      authToken = data.token;
      currentFarmer = data.farmer;
      localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
      document.getElementById('login-password').value = '';

      if (currentFarmer.preferred_language && typeof setLanguage === 'function') {
        setLanguage(currentFarmer.preferred_language);
      }
      updateAuthNavbar();

      if (!currentFarmer.profile_completed) {
        navigateTo('profile', { onboarding: true });
      } else {
        navigateTo('dashboard');
      }
    } catch (err) {
      showStatusAlert(
        'login-alert',
        t(
          'నెట్‌వర్క్ లోపం: సర్వర్‌ను చేరుకోలేకపోయాము. సర్వర్ రన్ అవుతుందో లేదో సరిచూసుకోండి.',
          'Network error: Could not connect to AgriSaarthi server.'
        ),
        'error'
      );
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  };

  window.handleLogout = async function () {
    try {
      if (authToken) {
        await fetch(getApiUrl('/api/auth/logout'), {
          method: 'POST',
          headers: getAuthHeaders()
        });
      }
    } catch (_) {}
    authToken = '';
    currentFarmer = null;
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    updateAuthNavbar();
    navigateTo('home');
  };

  // =========================================================================
  // First-Time Farm Profile Setup & Profile Page
  // =========================================================================
  function populateProfileForm(onboardingMode) {
    isFirstTimeOnboarding = Boolean(onboardingMode);
    showStatusAlert('profile-alert', '');

    const banner = document.getElementById('onboarding-welcome-banner');
    const skipBtn = document.getElementById('profile-skip-btn');
    if (banner) {
      banner.style.display = isFirstTimeOnboarding ? 'block' : 'none';
    }
    if (skipBtn) {
      skipBtn.style.display = isFirstTimeOnboarding ? 'inline-flex' : 'none';
    }

    if (!currentFarmer) return;
    document.getElementById('prof-fullname').value = currentFarmer.full_name || '';
    document.getElementById('prof-state').value = currentFarmer.state || '';
    document.getElementById('prof-district').value = currentFarmer.district || '';
    document.getElementById('prof-village').value = currentFarmer.village || '';
    document.getElementById('prof-acres').value = currentFarmer.land_size_acres != null ? currentFarmer.land_size_acres : '';
    document.getElementById('prof-soil').value = currentFarmer.soil_type || '';
    document.getElementById('prof-water').value = currentFarmer.water_availability || '';
    document.getElementById('prof-season').value = currentFarmer.season || '';
    document.getElementById('prof-budget').value = currentFarmer.budget_inr != null ? currentFarmer.budget_inr : '';
    document.getElementById('prof-risk').value = currentFarmer.risk_tolerance || 'moderate';
    document.getElementById('prof-crops').value = currentFarmer.primary_crops_grown || '';
  }

  window.handleProfileSubmit = async function (ev) {
    if (ev) ev.preventDefault();
    showStatusAlert('profile-alert', '');

    const payload = {
      full_name: (document.getElementById('prof-fullname').value || '').trim(),
      state: (document.getElementById('prof-state').value || '').trim(),
      district: (document.getElementById('prof-district').value || '').trim(),
      village: (document.getElementById('prof-village').value || '').trim(),
      land_size_acres: document.getElementById('prof-acres').value,
      soil_type: document.getElementById('prof-soil').value,
      water_availability: document.getElementById('prof-water').value,
      season: document.getElementById('prof-season').value,
      budget_inr: document.getElementById('prof-budget').value,
      risk_tolerance: document.getElementById('prof-risk').value || 'moderate',
      primary_crops_grown: (document.getElementById('prof-crops').value || '').trim(),
      profile_completed: true
    };

    const saveBtn = document.getElementById('profile-save-btn');
    if (saveBtn) saveBtn.disabled = true;

    try {
      const res = await fetch(getApiUrl('/api/farmer/profile'), {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        showStatusAlert('profile-alert', data.error || t('ప్రొఫైల్ సేవ్ చేయడంలో లోపం.', 'Failed to update profile.'), 'error');
        return;
      }

      currentFarmer = data.farmer;
      updateAuthNavbar();
      showStatusAlert(
        'profile-alert',
        t('✅ మీ వ్యవసాయ ప్రొఫైల్ విజయవంతంగా సేవ్ చేయబడింది!', '✅ Your farm profile has been saved successfully!'),
        'success'
      );

      if (isFirstTimeOnboarding) {
        isFirstTimeOnboarding = false;
        navigateTo('dashboard');
      }
    } catch (err) {
      showStatusAlert(
        'profile-alert',
        t('నెట్‌వర్క్ లోపం: ప్రొఫైల్ సేవ్ చేయలేకపోయాము.', 'Network error while saving profile.'),
        'error'
      );
    } finally {
      if (saveBtn) saveBtn.disabled = false;
    }
  };

  window.skipOnboardingToDashboard = async function () {
    isFirstTimeOnboarding = false;
    try {
      const res = await fetch(getApiUrl('/api/farmer/profile'), {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ profile_completed: true })
      });
      if (res.ok) {
        const data = await res.json();
        currentFarmer = data.farmer;
      }
    } catch (_) {}
    navigateTo('dashboard');
  };

  // =========================================================================
  // Farmer Dashboard
  // =========================================================================
  async function loadFarmerDashboard() {
    if (!currentFarmer) return;

    const welcomeTitle = document.getElementById('dash-welcome-name');
    const welcomeSub = document.getElementById('dash-welcome-location');
    if (welcomeTitle) {
      welcomeTitle.textContent = t(
        `🌾 నమస్కారం, ${currentFarmer.full_name} గారు!`,
        `🌾 Welcome, ${currentFarmer.full_name}!`
      );
    }
    if (welcomeSub) {
      const locParts = [currentFarmer.village, currentFarmer.district, currentFarmer.state].filter(Boolean);
      welcomeSub.textContent = locParts.length
        ? `📍 ${locParts.join(', ')}`
        : t('📍 ప్రాంతం ఇంకా నమోదు చేయలేదు (ప్రొఫైల్‌లో జతచేయండి)', '📍 Location not set yet (Add in Farm Profile)');
    }

    renderMyFarmSummary(currentFarmer);

    const weatherBox = document.getElementById('dash-weather-content');
    const alertsBox = document.getElementById('dash-alerts-content');
    const historyBox = document.getElementById('dash-history-content');

    if (weatherBox) {
      weatherBox.innerHTML = `<p>${t('⏳ వాతావరణ సమాచారం లోడ్ అవుతోంది...', '⏳ Loading live weather data...')}</p>`;
    }

    try {
      const res = await fetch(getApiUrl('/api/farmer/dashboard'), {
        method: 'GET',
        headers: getAuthHeaders()
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      const data = await res.json();
      if (data.farmer) {
        currentFarmer = data.farmer;
        renderMyFarmSummary(currentFarmer);
      }
      renderDashboardWeatherAndAlerts(data.weather, weatherBox, alertsBox);
      renderDashboardHistory(data.history || [], historyBox);
    } catch (err) {
      if (weatherBox) {
        weatherBox.innerHTML = `<div class="status-alert show alert-warning">${t('వాతావరణ సమాచారం ప్రస్తుతం అందుబాటులో లేదు.', 'Weather service is currently unreachable.')}</div>`;
      }
    }
  }

  function renderMyFarmSummary(farmer) {
    const el = document.getElementById('dash-farm-summary');
    if (!el) return;

    if (!farmer.state && !farmer.land_size_acres && !farmer.soil_type) {
      el.innerHTML = `
        <p style="margin-bottom:12px;">${t(
          'మీ వ్యవసాయ భూమి వివరాలు ఇంకా పూర్తి కాలేదు. ఖచ్చితమైన పంట సిఫార్సుల కోసం మీ ప్రొఫైల్‌ను పూర్తి చేయండి.',
          'Your farm holding details have not been added yet. Complete your Farm Profile for one-click personalized crop recommendations.'
        )}</p>
        <button type="button" class="btn-secondary-agri" onclick="navigateTo('profile')">
          ✍️ ${t('వ్యవసాయ ప్రొఫైల్ పూర్తి చేయండి', 'Complete Farm Profile')}
        </button>
      `;
      return;
    }

    el.innerHTML = `
      <div class="metric-strip">
        <div class="metric-box">
          <div class="m-label">${t('రాష్ట్రం / జిల్లా', 'State / District')}</div>
          <div class="m-val">${escapeHtml((farmer.district ? farmer.district + ', ' : '') + (farmer.state || '—'))}</div>
        </div>
        <div class="metric-box">
          <div class="m-label">${t('భూమి విస్తీర్ణం', 'Land Holding')}</div>
          <div class="m-val">${farmer.land_size_acres ? farmer.land_size_acres + ' ' + t('ఎకరాలు', 'Acres') : '—'}</div>
        </div>
        <div class="metric-box">
          <div class="m-label">${t('నేల & నీటి వసతి', 'Soil & Water')}</div>
          <div class="m-val">${escapeHtml((farmer.soil_type || '—') + ' / ' + (farmer.water_availability || '—'))}</div>
        </div>
        <div class="metric-box">
          <div class="m-label">${t('సీజన్ & బడ్జెట్', 'Season & Budget')}</div>
          <div class="m-val">${escapeHtml((farmer.season || '—').toUpperCase())} ${farmer.budget_inr ? '• ₹' + Number(farmer.budget_inr).toLocaleString('en-IN') : ''}</div>
        </div>
      </div>
      <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:10px;">
        <button type="button" class="btn-primary-agri" onclick="navigateTo('advisory')">
          🌱 ${t('నా పొలానికి పంట సిఫార్సు పొందండి', 'Get Crop Advisory for My Farm')}
        </button>
        <button type="button" class="btn-secondary-agri" onclick="navigateTo('profile')">
          ✏️ ${t('వివరాలు మార్చండి', 'Edit Farm Profile')}
        </button>
      </div>
    `;
  }

  function renderDashboardWeatherAndAlerts(weather, weatherBox, alertsBox) {
    if (!weatherBox || !alertsBox) return;
    if (!weather || !weather.available || !weather.current) {
      const msg = weather ? (t(weather.message_te || weather.message, weather.message)) : t('వాతావరణ సమాచారం అందుబాటులో లేదు.', 'Live weather data is unavailable.');
      weatherBox.innerHTML = `
        <div class="status-alert show alert-info" style="margin-bottom:0;">
          <strong>ℹ️ ${t('వాతావరణ సమాచారం అందుబాటులో లేదు', 'Live Weather Unavailable')}:</strong><br>
          ${escapeHtml(msg)}
        </div>
      `;
      alertsBox.innerHTML = `
        <p>${t(
          'అధికారిక వాతావరణ హెచ్చరికల API ప్రస్తుతం కనెక్ట్ కాలేదు. నకిలీ హెచ్చరికలు చూపబడవు. ప్రభుత్వ IMD బులిటెన్ల కోసం mausam.imd.gov.in చూడండి.',
          'Official weather alert feed is not configured or offline. No fabricated alerts are shown. Check mausam.imd.gov.in for official IMD bulletins.'
        )}</p>
      `;
      return;
    }

    const c = weather.current;
    weatherBox.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
        <div>
          <strong style="font-size:16px; color:var(--forest-900);">📍 ${escapeHtml(weather.district)}, ${escapeHtml(weather.state)}</strong>
          <div style="font-size:12px; color:var(--text-muted);">${escapeHtml(weather.source)}</div>
        </div>
        <span class="badge-tag" style="background:#dcfce7; color:#166534;">🟢 ${t('వాస్తవ డేటా (Live)', 'Live WMO Feed')}</span>
      </div>
      <div class="metric-strip">
        <div class="metric-box">
          <div class="m-label">${t('ఉష్ణోగ్రత', 'Temperature')}</div>
          <div class="m-val">${c.temperature_c != null ? c.temperature_c + '°C' : '—'}</div>
        </div>
        <div class="metric-box">
          <div class="m-label">${t('వాతావరణ స్థితి', 'Condition')}</div>
          <div class="m-val">${escapeHtml(t(c.condition_te, c.condition_en))}</div>
        </div>
        <div class="metric-box">
          <div class="m-label">${t('గాలిలో తేమ', 'Humidity')}</div>
          <div class="m-val">${c.humidity_pct != null ? c.humidity_pct + '%' : '—'}</div>
        </div>
        <div class="metric-box">
          <div class="m-label">${t('గాలి వేగం', 'Wind Speed')}</div>
          <div class="m-val">${c.wind_speed_kmh != null ? c.wind_speed_kmh + ' km/h' : '—'}</div>
        </div>
      </div>
    `;

    const advs = weather.meteorological_advisories || [];
    let alertHtml = `
      <div style="font-size:12.5px; color:var(--text-muted); margin-bottom:10px;">
        ℹ️ ${escapeHtml(t(weather.official_alerts_status_te || weather.official_alerts_status, weather.official_alerts_status))}
      </div>
    `;
    if (advs.length === 0) {
      alertHtml += `
        <div class="status-alert show alert-success" style="margin-bottom:0;">
          ✅ ${t(
            'రాబోయే 3 రోజుల్లో Open-Meteo డేటా ప్రకారం తీవ్రమైన వర్షం (>50mm) లేదా తుఫాను గాలుల (>45 km/h) సూచనలు లేవు.',
            'No severe rainfall (>50mm) or high-wind (>45 km/h) threshold advisories observed in the 3-day Open-Meteo forecast.'
          )}
        </div>
      `;
    } else {
      alertHtml += advs.map(function (a) {
        return `
          <div class="card-warning" style="margin:8px 0;">
            <div class="card-header">⚠️ ${escapeHtml(t(a.title_te, a.title_en))}</div>
            <div style="font-size:13.5px;">${escapeHtml(t(a.action_te, a.action_en))}</div>
          </div>
        `;
      }).join('');
    }
    alertsBox.innerHTML = alertHtml;
  }

  function renderDashboardHistory(historyList, historyBox) {
    if (!historyBox) return;
    if (!historyList || historyList.length === 0) {
      historyBox.innerHTML = `
        <p>${t(
          'ఇంకా ఎటువంటి సలహా చరిత్ర లేదు. పంట సలహా లేదా పంట ఆరోగ్య విభాగాన్ని ఉపయోగించినప్పుడు ఇక్కడ కనిపిస్తాయి.',
          'No advisory consultations recorded yet. Run a Crop Advisory, Crop Health check, or Voice query to see your history here.'
        )}</p>
      `;
      return;
    }

    const typeLabels = {
      crop_advisory: t('🌱 పంట సిఫార్సు', '🌱 Crop Advisory'),
      crop_health: t('🔬 పంట ఆరోగ్యం', '🔬 Crop Health'),
      voice_chat: t('🎙️ వాయిస్ / చాట్', '🎙️ Voice / Chat')
    };

    historyBox.innerHTML = historyList.slice(0, 6).map(function (item) {
      const dt = item.created_at ? new Date(item.created_at).toLocaleString() : '';
      return `
        <div class="history-item">
          <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
            <span class="badge-tag" style="background:#dcfce7; color:#166534;">${typeLabels[item.advisory_type] || item.advisory_type}</span>
            <span style="font-size:11.5px; color:var(--text-light);">${escapeHtml(dt)}</span>
          </div>
          <div style="font-size:14px; font-weight:600; color:var(--text-main); margin-top:4px;">${escapeHtml(item.query_summary)}</div>
          <div style="font-size:13px; color:var(--text-muted);">${escapeHtml(item.result_summary)}</div>
        </div>
      `;
    }).join('');
  }

  // =========================================================================
  // Crop Advisory Page (Structured Engine Integration)
  // =========================================================================
  function prefillAdvisoryForm() {
    if (!currentFarmer) return;
    const setIfEmpty = function (id, val) {
      const el = document.getElementById(id);
      if (el && !el.value && val != null && val !== '') {
        el.value = val;
      }
    };
    setIfEmpty('adv-state', currentFarmer.state);
    setIfEmpty('adv-district', currentFarmer.district);
    setIfEmpty('adv-acres', currentFarmer.land_size_acres);
    setIfEmpty('adv-soil', currentFarmer.soil_type);
    setIfEmpty('adv-water', currentFarmer.water_availability);
    setIfEmpty('adv-season', currentFarmer.season);
    setIfEmpty('adv-budget', currentFarmer.budget_inr);
    setIfEmpty('adv-risk', currentFarmer.risk_tolerance);
  }

  window.handleAdvisorySubmit = async function (ev) {
    if (ev) ev.preventDefault();
    showStatusAlert('advisory-alert', '');
    const resultsContainer = document.getElementById('advisory-results-container');
    const submitBtn = document.getElementById('adv-submit-btn');

    const payload = {
      state: (document.getElementById('adv-state').value || '').trim(),
      district: (document.getElementById('adv-district').value || '').trim(),
      land_size_acres: parseFloat(document.getElementById('adv-acres').value || '0'),
      soil_type: document.getElementById('adv-soil').value,
      water_availability: document.getElementById('adv-water').value,
      season: document.getElementById('adv-season').value,
      budget_inr: parseFloat(document.getElementById('adv-budget').value || '0'),
      risk_tolerance: document.getElementById('adv-risk').value || 'moderate'
    };

    if (submitBtn) submitBtn.disabled = true;
    if (resultsContainer) {
      resultsContainer.innerHTML = `<div class="portal-card"><p>⏳ ${t('ICAR/CACP 4-దశల ఇంజిన్ ద్వారా మీ పొలానికి తగిన పంటలను లెక్కిస్తున్నాము...', 'Running 4-step ICAR/CACP agronomic & financial suitability engine...')}</p></div>`;
    }

    try {
      const res = await fetch(getApiUrl('/api/recommend'), {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok || !data.recommendation) {
        if (resultsContainer) resultsContainer.innerHTML = '';
        showStatusAlert('advisory-alert', data.error || t('సిఫార్సు లెక్కింపులో లోపం.', 'Invalid farm parameters.'), 'error');
        return;
      }

      renderAdvisoryResults(data.recommendation, resultsContainer);
    } catch (err) {
      if (resultsContainer) resultsContainer.innerHTML = '';
      showStatusAlert('advisory-alert', t('నెట్‌వర్క్ లోపం: సర్వర్‌ను చేరుకోలేకపోయాము.', 'Network error while fetching recommendations.'), 'error');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  };

  function renderAdvisoryResults(rec, container) {
    if (!container) return;
    const b = rec.budget_summary || {};
    const warningsHtml = (rec.warnings || []).map(function (w) {
      return `<div class="card-warning">⚠️ ${escapeHtml(w)}</div>`;
    }).join('');

    const renderCropCard = function (c, isPrimary) {
      const titleName = (typeof currentLang !== 'undefined' && currentLang === 'te' && c.name_te)
        ? `${c.name_te} — ${c.crop_name}`
        : `${c.crop_name} (${c.hindi_name})`;
      return `
        <div class="rec-crop-card">
          <div class="rec-crop-header">
            <div>
              <span class="badge-tag" style="background:${isPrimary ? '#dcfce7' : '#fef3c7'}; color:${isPrimary ? '#166534' : '#92400e'}; margin-bottom:4px;">
                ${isPrimary ? t('🌟 ప్రధాన సిఫార్సు (Primary)', '🌟 Primary Recommendation') : t('🛡️ ప్రత్యామ్నాయ పంట (Alternative/Hedge)', '🛡️ Diversified Alternative')}
              </span>
              <h4 style="font-size:18px; color:var(--forest-900); margin-top:4px;">🌾 ${escapeHtml(titleName)}</h4>
            </div>
            <div class="score-pill">${t('అనుకూలత స్కోరు', 'Suitability')}: ${c.suitability_score}/100</div>
          </div>
          <div class="metric-strip">
            <div class="metric-box">
              <div class="m-label">${t('ఎకరానికి ఖర్చు (CACP)', 'Est. Cost / Acre')}</div>
              <div class="m-val">₹${Number(c.estimated_cost_per_acre_inr).toLocaleString('en-IN')}</div>
            </div>
            <div class="metric-box">
              <div class="m-label">${t('మొత్తం ఖర్చు & బడ్జెట్ స్థితి', 'Total Cost & Feasibility')}</div>
              <div class="m-val">₹${Number(c.total_estimated_cost_inr).toLocaleString('en-IN')} (${escapeHtml(c.budget_feasibility)})</div>
            </div>
            <div class="metric-box">
              <div class="m-label">${t('ఆశించే దిగుబడి / ఎకరానికి', 'Expected Yield / Acre')}</div>
              <div class="m-val">${c.expected_yield_range_quintals_per_acre[0]}–${c.expected_yield_range_quintals_per_acre[1]} qtl</div>
            </div>
            <div class="metric-box">
              <div class="m-label">${t('అంచనా నికర లాభం / ఎకరానికి', 'Est. Net Profit / Acre')}</div>
              <div class="m-val" style="color:var(--forest-700);">₹${Number(c.estimated_net_profit_per_acre_inr).toLocaleString('en-IN')}</div>
            </div>
          </div>
          ${c.sowing_notes_te && currentLang === 'te' ? `<p style="font-size:13.5px; color:var(--forest-800); margin-bottom:8px;"><strong>🌱 సాగు సూచన:</strong> ${escapeHtml(c.sowing_notes_te)}</p>` : ''}
          <div class="grid-2" style="margin-top:8px;">
            <div class="card-reference" style="margin:0;">
              <div class="card-header">✅ ${t('ప్రధాన ప్రయోజనాలు (Key Strengths)', 'Key Strengths')}</div>
              <ul style="padding-left:18px; font-size:13.5px;">
                ${(c.key_strengths || []).map(s => `<li>${escapeHtml(s)}</li>`).join('')}
              </ul>
            </div>
            <div class="card-warning" style="margin:0;">
              <div class="card-header">⚠️ ${t('ముఖ్య జాగ్రత్తలు & రిస్కులు (Risk Factors)', 'Risk Factors')}</div>
              <ul style="padding-left:18px; font-size:13.5px;">
                ${(c.risk_factors || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}
              </ul>
            </div>
          </div>
        </div>
      `;
    };

    const primaryHtml = (rec.primary_recommendations || []).map(c => renderCropCard(c, true)).join('');
    const altHtml = (rec.alternative_recommendations || []).map(c => renderCropCard(c, false)).join('');
    const reasoningHtml = (rec.step_by_step_reasoning || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
    const limitsHtml = (rec.limitations_and_advisory || []).map(l => `<li>${escapeHtml(l)}</li>`).join('');

    container.innerHTML = `
      ${warningsHtml}
      <div class="portal-card card-green-accent" style="margin-bottom:18px;">
        <h3>💰 ${t('బడ్జెట్ & పొలం విశ్లేషణ (Budget Summary)', 'Farm Holding & Budget Analysis')}</h3>
        <p>${t('మొత్తం బడ్జెట్', 'Total Budget')}: <strong>₹${Number(b.total_budget_inr || 0).toLocaleString('en-IN')}</strong> •
           ${t('విస్తీర్ణం', 'Land Size')}: <strong>${b.land_size_acres || 0} ${t('ఎకరాలు', 'acres')}</strong> •
           ${t('ఎకరానికి కేటాయింపు', 'Per Acre Allocation')}: <strong>₹${Number(b.budget_per_acre_inr || 0).toLocaleString('en-IN')}/acre</strong>
           (${escapeHtml(b.status || '')})</p>
      </div>
      ${primaryHtml || `<div class="portal-card"><p>${t('ఈ పరిస్థితులకు సరిపోయే ప్రధాన పంటలు కనుగొనబడలేదు.', 'No primary crops matched.')}</p></div>`}
      ${altHtml}
      <div class="grid-2" style="margin-top:16px;">
        <div class="portal-card">
          <h3>🧭 ${t('4-దశల నిర్ణయ ప్రక్రియ (4-Step Engine Reasoning)', '4-Step Decision Engine Reasoning')}</h3>
          <ul style="padding-left:18px; font-size:13.5px; line-height:1.6; color:var(--text-muted);">${reasoningHtml}</ul>
        </div>
        <div class="portal-card">
          <h3>📚 ${t('ICAR/CACP పరిమితులు & సలహాలు (Advisory & Limitations)', 'ICAR/CACP Limitations & Advisory')}</h3>
          <ul style="padding-left:18px; font-size:13.5px; line-height:1.6; color:var(--text-muted);">${limitsHtml}</ul>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // Crop Health & Disease Page
  // =========================================================================
  window.fillCropHealthPreset = function (crop, symptom) {
    const cropEl = document.getElementById('health-crop');
    const symEl = document.getElementById('health-symptom');
    if (cropEl) cropEl.value = crop;
    if (symEl) symEl.value = symptom;
    handleCropHealthSubmit();
  };

  window.handleCropHealthSubmit = async function (ev) {
    if (ev) ev.preventDefault();
    showStatusAlert('health-alert', '');

    const crop = (document.getElementById('health-crop').value || '').trim();
    const symptom = (document.getElementById('health-symptom').value || '').trim();
    const fieldNotes = (document.getElementById('health-notes').value || '').trim();
    const outBox = document.getElementById('health-results-container');
    const btn = document.getElementById('health-submit-btn');

    if (!crop && !symptom) {
      showStatusAlert('health-alert', t('దయచేసి పంట పేరు మరియు కనిపిస్తున్న లక్షణాన్ని నమోదు చేయండి.', 'Please select a crop and describe the observed symptom.'), 'error');
      return;
    }

    if (btn) btn.disabled = true;
    if (outBox) {
      outBox.innerHTML = `<div class="portal-card"><p>⏳ ${t('ICAR/SAU పంట రక్షణ డేటాబేస్ నుండి విశ్లేషిస్తున్నాము...', 'Analyzing symptom against verified ICAR/SAU crop diagnostic database...')}</p></div>`;
    }

    try {
      const res = await fetch(getApiUrl('/api/crop-health'), {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          crop: crop,
          symptom: symptom,
          field_notes: fieldNotes,
          lang: typeof currentLang !== 'undefined' ? currentLang : 'te'
        })
      });
      const data = await res.json();
      if (!res.ok) {
        if (outBox) outBox.innerHTML = '';
        showStatusAlert('health-alert', data.error || 'Error diagnosing crop symptom.', 'error');
        return;
      }

      renderCropHealthResult(data, outBox);
    } catch (err) {
      if (outBox) outBox.innerHTML = '';
      showStatusAlert('health-alert', t('నెట్‌వర్క్ లోపం: సర్వర్‌ను చేరుకోలేకపోయాము.', 'Network error while running crop health check.'), 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  function renderCropHealthResult(data, container) {
    if (!container) return;
    if (!data.matched) {
      const formatted = typeof formatMarkdown === 'function' ? formatMarkdown(data.fallback_markdown || '') : escapeHtml(data.fallback_markdown || '');
      container.innerHTML = `<div class="portal-card">${formatted}</div>`;
      return;
    }

    const isTe = typeof currentLang !== 'undefined' && currentLang === 'te';
    const questions = isTe ? data.follow_up_questions_te : data.follow_up_questions_en;
    const actions = isTe ? data.safe_actions_te : data.safe_actions_en;
    const inspection = isTe ? data.required_inspection_te : data.required_inspection_en;
    const title = isTe ? data.symptom_name_te : data.symptom_name_en;

    const causesHtml = (data.possible_causes || []).map(function (c) {
      return `
        <div class="card-causes">
          <div class="card-header">🔬 ${escapeHtml(isTe ? c.name_te : c.name_en)} <span class="badge-tag">${escapeHtml(c.cause_type)}</span></div>
          <p style="font-size:13.5px; color:#3b0764; margin-bottom:4px;"><strong>${t('లక్షణ ఆధారాలు', 'Field Evidence')}:</strong> ${escapeHtml(isTe ? c.evidence_te : c.evidence_en)}</p>
          <p style="font-size:13px; color:#581c87;"><strong>${t('గుర్తించే కీలక తేడా', 'Distinguishing Clue')}:</strong> ${escapeHtml(isTe ? c.distinguishing_clues_te : c.distinguishing_clues_en)} (${escapeHtml(c.primary_stage)})</p>
        </div>
      `;
    }).join('');

    container.innerHTML = `
      <div class="portal-card">
        <h3>🌿 ${escapeHtml(data.crop_name)} — ${escapeHtml(title)}</h3>
        <div class="card-question">
          <div class="card-header">❓ ${t('రోగనిర్ధారణ ధృవీకరణ ప్రశ్నలు (గరిష్టంగా 3)', 'Diagnostic Verification Questions (Max 3)')}</div>
          <ol style="padding-left:20px; font-size:13.5px; line-height:1.6;">
            ${(questions || []).map(q => `<li>${escapeHtml(q)}</li>`).join('')}
          </ol>
          <p style="font-size:12.5px; margin-top:6px;"><em>💡 ${t('పై ప్రశ్నలకు మీ పొలం పరిశీలనలను పైన ఉన్న "పొలం పరిశీలన వివరాలు" బాక్స్‌లో రాసి మళ్ళీ నొక్కండి.', 'Enter your answers in the Field Observations box above to record a confirmed field consultation in your history.')}</em></p>
        </div>
        <h4 style="margin:14px 0 8px 0; color:var(--forest-900);">🔍 ${t('శాస్త్రీయ ఆధారాల ప్రకారం సాధ్యమైన కారణాలు (Possible Causes)', 'Verified Possible Causes & Field Clues')}</h4>
        ${causesHtml}
        <div class="card-actions">
          <div class="card-header">🛡️ ${t('సురక్షిత తక్షణ చర్యలు (రసాయనేతర & యాజమాన్య పద్ధతులు)', 'Safe Non-Chemical & Cultural Next Steps')}</div>
          <ul style="padding-left:18px; font-size:13.5px; line-height:1.6;">
            ${(actions || []).map(a => `<li>${escapeHtml(a)}</li>`).join('')}
          </ul>
        </div>
        <div class="card-warning">
          <div class="card-header">⚠️ ${t('అనిశ్చితి & నిపుణుల తనిఖీ హెచ్చరిక', 'Uncertainty & Expert Inspection Notice')}</div>
          <p style="font-size:13.5px; color:#92400e;">${escapeHtml(inspection)}</p>
        </div>
        <div class="card-reference">
          <div class="card-header">📚 ${t('ధృవీకరించబడిన ICAR / వ్యవసాయ విశ్వవిద్యాలయ మూలం', 'Verified ICAR / Agricultural University Reference')}</div>
          <p style="font-size:13.5px; color:#166534;"><strong>${escapeHtml(data.source_name)}</strong> — ${escapeHtml(data.source_reference)}</p>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // Weather and Alerts Page
  // =========================================================================
  function prefillWeatherFilters() {
    if (!currentFarmer) return;
    const stEl = document.getElementById('weather-state');
    const distEl = document.getElementById('weather-district');
    if (stEl && !stEl.value && currentFarmer.state) stEl.value = currentFarmer.state;
    if (distEl && !distEl.value && currentFarmer.district) distEl.value = currentFarmer.district;
  }

  window.loadWeatherPage = async function (ev) {
    if (ev) ev.preventDefault();
    const state = (document.getElementById('weather-state').value || '').trim();
    const district = (document.getElementById('weather-district').value || '').trim();
    const outBox = document.getElementById('weather-page-results');

    if (outBox) {
      outBox.innerHTML = `<div class="portal-card"><p>⏳ ${t('వాస్తవ వాతావరణ డేటాను సేకరిస్తున్నాము...', 'Fetching real-time meteorological feed...')}</p></div>`;
    }

    try {
      const qs = new URLSearchParams({ state: state, district: district }).toString();
      const res = await fetch(getApiUrl('/api/weather?' + qs), {
        method: 'GET',
        headers: getAuthHeaders()
      });
      const data = await res.json();
      renderWeatherPageData(data, outBox);
    } catch (err) {
      if (outBox) {
        outBox.innerHTML = `<div class="status-alert show alert-error">${t('వాతావరణ సర్వీస్‌కు కనెక్ట్ చేయలేకపోయాము. నకిలీ డేటా చూపబడదు.', 'Unable to connect to weather endpoint. No fabricated weather is displayed.')}</div>`;
      }
    }
  };

  function renderWeatherPageData(w, container) {
    if (!container) return;
    if (!w || !w.available || !w.current) {
      container.innerHTML = `
        <div class="portal-card">
          <div class="status-alert show alert-warning">
            <strong>⚠️ ${t('లైవ్ వాతావరణ డేటా అందుబాటులో లేదు', 'Live Weather Feed Unavailable')}</strong><br>
            ${escapeHtml(w ? t(w.message_te || w.message, w.message) : 'Service offline.')}
          </div>
          <p>${t(
            'అగ్రిసారథి ఎటువంటి నకిలీ వాతావరణ గణాంకాలు లేదా నకిలీ తుఫాను హెచ్చరికలను చూపించదు. భారత వాతావరణ శాఖ (IMD) అధికారిక సమాచారం కోసం mausam.imd.gov.in చూడండి.',
            'AgriSaarthi never displays fabricated weather readings, crop-loss statistics, or fake cyclone alerts. Please consult official India Meteorological Department bulletins at mausam.imd.gov.in.'
          )}</p>
        </div>
      `;
      return;
    }

    const c = w.current;
    const forecastCards = (w.daily_forecast || []).map(function (d) {
      return `
        <div class="portal-card">
          <h3>📅 ${escapeHtml(d.date)}</h3>
          <p style="font-weight:600; color:var(--forest-800); margin-bottom:8px;">${escapeHtml(t(d.condition_te, d.condition_en))}</p>
          <p>🌡️ ${t('గరిష్ట / కనిష్ట', 'Max / Min')}: <strong>${d.temp_max_c}°C / ${d.temp_min_c}°C</strong></p>
          <p>🌧️ ${t('వర్షపాతం', 'Precipitation')}: <strong>${d.precipitation_mm} mm</strong></p>
          <p>💨 ${t('గరిష్ట గాలి వేగం', 'Max Wind')}: <strong>${d.wind_max_kmh} km/h</strong></p>
        </div>
      `;
    }).join('');

    const advisories = w.meteorological_advisories || [];
    const advHtml = advisories.length
      ? advisories.map(a => `
          <div class="card-warning">
            <div class="card-header">⚠️ ${escapeHtml(t(a.title_te, a.title_en))}</div>
            <p>${escapeHtml(t(a.action_te, a.action_en))}</p>
          </div>
        `).join('')
      : `<div class="status-alert show alert-success" style="margin-bottom:0;">✅ ${t('రాబోయే 3 రోజుల్లో ఎటువంటి తీవ్రమైన వాతావరణ హెచ్చరికలు (భారీ వర్షం / బలమైన గాలులు) లేవు.', 'No severe meteorological threshold warnings (heavy rain or gale winds) in the 3-day forecast.')}</div>`;

    container.innerHTML = `
      <div class="portal-card card-green-accent" style="margin-bottom:18px;">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <h3>🌦️ ${escapeHtml(w.district)}, ${escapeHtml(w.state)} — ${t('ప్రస్తుత వాతావరణం', 'Current Conditions')}</h3>
          <span class="badge-tag" style="background:#dcfce7; color:#166534;">${escapeHtml(w.source)}</span>
        </div>
        ${w.location_note ? `<p style="font-size:12.5px; color:#b45309; margin-top:4px;">ℹ️ ${escapeHtml(w.location_note)}</p>` : ''}
        <div class="metric-strip">
          <div class="metric-box">
            <div class="m-label">${t('ఉష్ణోగ్రత', 'Temperature')}</div>
            <div class="m-val">${c.temperature_c}°C</div>
          </div>
          <div class="metric-box">
            <div class="m-label">${t('వాతావరణం', 'Condition')}</div>
            <div class="m-val">${escapeHtml(t(c.condition_te, c.condition_en))}</div>
          </div>
          <div class="metric-box">
            <div class="m-label">${t('గాలిలో తేమ', 'Relative Humidity')}</div>
            <div class="m-val">${c.humidity_pct}%</div>
          </div>
          <div class="metric-box">
            <div class="m-label">${t('గాలి వేగం & వర్షం', 'Wind & Precipitation')}</div>
            <div class="m-val">${c.wind_speed_kmh} km/h • ${c.precipitation_mm} mm</div>
          </div>
        </div>
      </div>

      <h3 style="margin-bottom:12px; color:var(--forest-900);">📆 ${t('3-రోజుల వాతావరణ అంచనా (3-Day Agricultural Forecast)', '3-Day Agricultural Forecast')}</h3>
      <div class="grid-3" style="margin-bottom:20px;">
        ${forecastCards}
      </div>

      <div class="portal-card">
        <h3>🚨 ${t('అధికారిక వాతావరణ & తుఫాను హెచ్చరికల స్థితి (Official Alerts Status)', 'Official Weather & Cyclone Alerts Status')}</h3>
        <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">
          ${escapeHtml(t(w.official_alerts_status_te || w.official_alerts_status, w.official_alerts_status))}
        </p>
        ${advHtml}
      </div>
    `;
  }

  // Initialize portal on DOM load
  window.addEventListener('DOMContentLoaded', async function () {
    document.body.classList.add('portal-body');
    await restoreSession();
    const pathName = (window.location.pathname || '/').replace(/^\/+|\/+$/g, '').toLowerCase();
    const validPages = ['home', 'login', 'register', 'dashboard', 'advisory', 'health', 'weather', 'voice', 'profile'];
    if (validPages.includes(pathName)) {
      navigateTo(pathName);
    }
  });
})();


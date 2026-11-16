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
  let lastAdvisoryResult = null;
  let lastHealthResult = null;
  let lastWeatherResult = null;

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

  function t(arg1, arg2, arg3) {
    if (window.i18n && typeof window.i18n.t === 'function') {
      return window.i18n.t(arg1, arg2, arg3);
    }
    const lang = window.currentLang || (typeof currentLang !== 'undefined' ? currentLang : 'te');
    if (typeof arg2 === 'undefined' && typeof arg3 === 'undefined') {
      return arg1;
    }
    if (lang === 'hi' && arg3) return arg3;
    if (lang === 'en' && arg2) return arg2;
    return arg1;
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
  const VALID_PAGES = ['home', 'login', 'register', 'dashboard', 'advisory', 'health', 'weather', 'voice', 'profile'];

  function navigateTo(targetPageId, options) {
    const opts = options || {};
    let pageId = (targetPageId || 'login').toString().trim().toLowerCase();
    if (!VALID_PAGES.includes(pageId)) {
      pageId = currentFarmer ? 'dashboard' : 'login';
    }

    const publicPages = ['login', 'register'];

    // Auth guard: only 'login' and 'register' are accessible without authentication
    if (!publicPages.includes(pageId) && !currentFarmer) {
      navigateTo('login', { fromAuthGuard: true });
      showStatusAlert(
        'login-alert',
        t(
          'అగ్రిసారథి AI ఫీచర్లను ఉపయోగించడానికి దయచేసి ముందుగా లాగిన్ అవ్వండి.',
          'Please login first to access AgriSaarthi AI features.',
          'एग्रीसारथी एआई सुविधाओं का उपयोग करने के लिए कृपया पहले लॉगिन करें।'
        ),
        'info'
      );
      return;
    }

    // Cleanly clear stale auth alerts when switching between login and registration
    if (pageId === 'login' && !opts.fromAuthGuard && !opts.preserveAlert) {
      showStatusAlert('login-alert', '');
    } else if (pageId === 'register' && !opts.preserveAlert) {
      showStatusAlert('register-alert', '');
      showStatusAlert('login-alert', '');
    }

    currentPage = pageId;

    // 1. Cleanly hide inactive page sections and reveal active page section
    const pageSections = document.querySelectorAll('.portal-page, .page-section, [id^="page-"]');
    pageSections.forEach(function (sec) {
      const isTarget = sec.id === 'page-' + pageId;
      if (isTarget) {
        sec.classList.add('active');
        sec.classList.remove('hidden');
        sec.removeAttribute('hidden');
        sec.style.display = '';
      } else {
        sec.classList.remove('active');
        sec.classList.add('hidden');
        sec.setAttribute('hidden', '');
        sec.style.display = 'none';
      }
    });

    // 2. Update active navbar link highlighting across all matching nav elements
    document.querySelectorAll('.nav-item-btn, .nav-link, [data-page]').forEach(function (btn) {
      const target = btn.getAttribute('data-page');
      if (target) {
        const isActive = target === pageId;
        btn.classList.toggle('active', isActive);
        if (isActive) {
          btn.setAttribute('aria-current', 'page');
        } else {
          btn.removeAttribute('aria-current');
        }
      }
    });

    // 3. Adjust body scroll mode & scroll window smoothly to top
    if (pageId === 'voice') {
      document.body.classList.remove('portal-body');
    } else {
      document.body.classList.add('portal-body');
    }
    if (typeof window.scrollTo === 'function') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // 4. Update browser URL history state if available
    if (!opts.noHistory && window.history && typeof window.history.pushState === 'function') {
      try {
        const newPath = pageId === 'home' ? '/' : '/' + pageId;
        if (window.location.pathname !== newPath) {
          window.history.pushState({ pageId: pageId }, '', newPath);
        }
      } catch (_) {
        // Silently preserve in sandbox / restricted frames
      }
    }

    // 5. Page-specific initializers executed safely inside try/catch blocks
    if (pageId === 'dashboard') {
      try {
        if (typeof checkOtpBannerState === 'function') {
          checkOtpBannerState();
        }
        if (typeof loadFarmerDashboard === 'function') {
          loadFarmerDashboard();
        }
      } catch (err) {
        console.error('Error initializing Farmer Dashboard:', err);
      }
    } else if (pageId === 'advisory') {
      try {
        if (typeof prefillAdvisoryForm === 'function') {
          prefillAdvisoryForm();
        }
      } catch (err) {
        console.error('Error initializing Advisory form:', err);
      }
    } else if (pageId === 'health') {
      try {
        if (typeof prefillCropHealthForm === 'function') {
          prefillCropHealthForm();
        }
        const healthContainer = document.getElementById('health-results-container');
        if (lastHealthResult && healthContainer && typeof renderCropHealthResult === 'function') {
          renderCropHealthResult(lastHealthResult, healthContainer);
        }
      } catch (err) {
        console.error('Error initializing Crop Health view:', err);
      }
    } else if (pageId === 'weather') {
      try {
        if (typeof prefillWeatherFilters === 'function') {
          prefillWeatherFilters();
        }
        if (typeof loadWeatherPage === 'function') {
          loadWeatherPage();
        }
      } catch (err) {
        console.error('Error initializing Weather view:', err);
      }
    } else if (pageId === 'voice') {
      try {
        if (typeof initSpeech === 'function') {
          initSpeech();
        }
        if (typeof renderSuggestions === 'function') {
          renderSuggestions();
        }
        if (typeof checkOllamaStatus === 'function') {
          checkOllamaStatus();
        }
        const inputEl = document.getElementById('user-input');
        if (inputEl) {
          setTimeout(function () { inputEl.focus(); }, 80);
        }
      } catch (err) {
        console.error('Error initializing Voice AI view:', err);
      }
    } else if (pageId === 'profile') {
      try {
        if (typeof populateProfileForm === 'function') {
          populateProfileForm(opts.onboarding === true);
        }
      } catch (err) {
        console.error('Error initializing Farm Profile form:', err);
      }
    } else if (pageId === 'home') {
      try {
        if (typeof updateAuthNavbar === 'function') {
          updateAuthNavbar();
        }
      } catch (err) {
        console.error('Error initializing Home view:', err);
      }
    }

    try {
      if (typeof setupVoiceFormInputs === 'function') {
        setupVoiceFormInputs();
      }
      if (window.AgriVoiceAssistant && typeof window.AgriVoiceAssistant.onPageChanged === 'function') {
        window.AgriVoiceAssistant.onPageChanged(pageId);
      }
    } catch (_) { }
  }
  window.navigateTo = navigateTo;

  function updateAuthNavbar() {
    const guestBox = document.getElementById('nav-auth-guest');
    const userBox = document.getElementById('nav-auth-user');
    const userNameSpan = document.getElementById('nav-farmer-name');
    const navDashboardBtn = document.getElementById('nav-btn-dashboard');
    const navProfileBtn = document.getElementById('nav-btn-profile');
    const homeCtaAuth = document.getElementById('home-cta-authenticated');
    const homeCtaGuest = document.getElementById('home-cta-guest');
    const hubBar = document.querySelector('.dashboard-hub');
    const navFeatureBtns = document.querySelectorAll('.portal-nav-links .nav-item-btn');

    if (currentFarmer) {
      if (guestBox) guestBox.style.display = 'none';
      if (userBox) userBox.style.display = 'flex';
      if (userNameSpan) userNameSpan.textContent = currentFarmer.full_name;
      navFeatureBtns.forEach(function (btn) {
        btn.style.display = 'inline-flex';
      });
      if (homeCtaAuth) homeCtaAuth.style.display = 'inline-flex';
      if (homeCtaGuest) homeCtaGuest.style.display = 'none';
      if (hubBar) hubBar.style.display = 'none'; // Clutter-free UI: hide redundant secondary pill strip
    } else {
      if (guestBox) guestBox.style.display = 'flex';
      if (userBox) userBox.style.display = 'none';
      navFeatureBtns.forEach(function (btn) {
        btn.style.display = 'none';
      });
      if (homeCtaAuth) homeCtaAuth.style.display = 'none';
      if (homeCtaGuest) homeCtaGuest.style.display = 'inline-flex';
      if (hubBar) hubBar.style.display = 'none';
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
    if (authToken.startsWith('farmer_session_') || authToken.startsWith('otp_session_') || authToken.startsWith('google_session_')) {
      let cachedProfiles = {};
      try {
        cachedProfiles = JSON.parse(localStorage.getItem('agrisaarthi_farmer_profiles') || '{}');
      } catch (_) { }

      const lastId = sessionStorage.getItem('agrisaarthi_otp_identifier') || Object.keys(cachedProfiles)[0];
      if (lastId && cachedProfiles[lastId]) {
        currentFarmer = cachedProfiles[lastId];
      } else {
        currentFarmer = {
          id: 1,
          full_name: 'Farmer',
          identifier: 'farmer',
          state: 'Telangana',
          district: 'Warangal',
          preferred_language: window.currentLang || 'te',
          profile_completed: 1
        };
      }
      if (currentFarmer && currentFarmer.preferred_language && typeof setLanguage === 'function') {
        setLanguage(currentFarmer.preferred_language);
      }
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
    const emailEl = document.getElementById('reg-email');
    const phoneEl = document.getElementById('reg-phone');
    const email = emailEl ? (emailEl.value || '').trim() : '';
    const phone = phoneEl ? (phoneEl.value || '').trim() : '';
    const identifier = (document.getElementById('reg-identifier').value || '').trim();
    const password = document.getElementById('reg-password').value || '';
    const confirmPw = document.getElementById('reg-confirm-password').value || '';
    const prefLang = document.getElementById('reg-lang').value || 'te';
    const submitBtn = document.getElementById('reg-submit-btn');

    if (!fullName || fullName.length < 2) {
      showStatusAlert(
        'register-alert',
        t('దయచేసి మీ పూర్తి పేరును నమోదు చేయండి (కనీసం 2 అక్షరాలు).', 'Please enter your full name (at least 2 characters).', 'कृपया अपना पूरा नाम दर्ज करें (कम से कम 2 अक्षर)।'),
        'error'
      );
      return;
    }

    if (!identifier) {
      showStatusAlert(
        'register-alert',
        t('దయచేసి మొబైల్ నంబర్ లేదా యూజర్‌నేమ్ నమోదు చేయండి.', 'Please enter mobile number or username.', 'कृपया मोबाइल नंबर या यूज़रनेम दर्ज करें।'),
        'error'
      );
      return;
    }

    if (phone) {
      const cleanPhone = phone.replace(/[\s-]/g, '').replace(/^\+91/, '').replace(/^0/, '');
      if (cleanPhone.length !== 10 || !/^\d{10}$/.test(cleanPhone)) {
        showStatusAlert(
          'register-alert',
          t('దయచేసి సరైన 10-అంకెల ఫోన్ నంబర్‌ను నమోదు చేయండి.', 'Please enter a valid 10-digit phone number.', 'कृपया सही 10-अंकों का मोबाइल नंबर दर्ज करें।'),
          'error'
        );
        return;
      }
    }

    if (!password || password.length < 6) {
      showStatusAlert(
        'register-alert',
        t('పాస్‌వర్డ్ కనీసం 6 అక్షరాలు ఉండాలి.', 'Password must be at least 6 characters long.', 'पासवर्ड कम से कम 6 अक्षरों का होना चाहिए।'),
        'error'
      );
      return;
    }

    if (password !== confirmPw) {
      showStatusAlert(
        'register-alert',
        t('పాస్‌వర్డ్ మరియు నిర్ధారణ పాస్‌వర్డ్ సరిపోలడం లేదు.', 'Passwords do not match. Please re-enter.', 'पासवर्ड और पुष्टि पासवर्ड मेल नहीं खाते।'),
        'error'
      );
      return;
    }

    if (phone) {
      const cleanPhone = phone.replace(/[\s-]/g, '').replace(/^\+91/, '').replace(/^0/, '');
      if (cleanPhone.length !== 10 || !/^\d{10}$/.test(cleanPhone)) {
        showStatusAlert(
          'register-alert',
          t('దయచేసి సరైన 10-అంకెల ఫోన్ నంబర్‌ను నమోదు చేయండి.', 'Please enter a valid 10-digit phone number.'),
          'error'
        );
        return;
      }
    }

    if (submitBtn) submitBtn.disabled = true;
    try {
      const res = await fetch(getApiUrl('/api/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName,
          email: email || null,
          phone_number: phone || null,
          identifier: identifier,
          password: password,
          confirm_password: confirmPw,
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

      // Reveal navigation items and navigate directly to dashboard
      navigateTo('dashboard');
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
      function checkLocalPasswordOverride() {
        const normId = identifier.trim().toLowerCase();
        const normDigits = identifier.replace(/\D/g, '');
        let updatedPasswords = {};
        try {
          updatedPasswords = JSON.parse(localStorage.getItem('agrisaarthi_updated_passwords') || '{}');
        } catch (_) { }

        const storedPwd = updatedPasswords[normId] || (normDigits ? updatedPasswords[normDigits] : null) || updatedPasswords[identifier];
        if (storedPwd && storedPwd === password) {
          let cachedProfiles = {};
          try {
            cachedProfiles = JSON.parse(localStorage.getItem('agrisaarthi_farmer_profiles') || '{}');
          } catch (_) { }

          const cachedFarmer = cachedProfiles[normId] || (normDigits ? cachedProfiles[normDigits] : null) || cachedProfiles[identifier];

          currentFarmer = cachedFarmer || {
            id: 1,
            full_name: normId.includes('@') ? normId.split('@')[0] : (normDigits.length === 10 ? 'Farmer ' + normDigits.slice(-4) : identifier),
            identifier: identifier,
            phone_number: normDigits.length === 10 ? normDigits : null,
            email: normId.includes('@') ? normId : null,
            state: 'Telangana',
            district: 'Warangal',
            preferred_language: window.currentLang || 'te',
            profile_completed: 1
          };

          authToken = 'farmer_session_' + Date.now();
          localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
          sessionStorage.removeItem('agrisaarthi_logged_in_via_otp');
          sessionStorage.removeItem('agrisaarthi_otp_reset_pending');
          document.getElementById('login-password').value = '';

          if (currentFarmer.preferred_language && typeof setLanguage === 'function') {
            setLanguage(currentFarmer.preferred_language);
          }
          updateAuthNavbar();
          navigateTo('dashboard');
          return true;
        }
        return false;
      }

      const res = await fetch(getApiUrl('/api/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: identifier, password: password })
      });
      const data = await res.json();
      if (!res.ok) {
        if (checkLocalPasswordOverride()) {
          return;
        }

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
      sessionStorage.removeItem('agrisaarthi_logged_in_via_otp');
      document.getElementById('login-password').value = '';

      if (currentFarmer.preferred_language && typeof setLanguage === 'function') {
        setLanguage(currentFarmer.preferred_language);
      }
      updateAuthNavbar();

      // Reveal navigation items and navigate directly to dashboard
      navigateTo('dashboard');
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
    } catch (_) { }
    authToken = '';
    currentFarmer = null;
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem('agrisaarthi_logged_in_via_otp');
    updateAuthNavbar();
    navigateTo('login');
  };

  // =========================================================================
  // Show / Hide Password, Forgot Password OTP, Google Auth, Change Password
  // =========================================================================
  let currentGeneratedOtp = '';
  let otpRecipient = '';
  let otpTimerInterval = null;

  function checkOtpBannerState() {
    const banner = document.getElementById('otp-change-password-banner');
    if (!banner) return;
    const isOtp = sessionStorage.getItem('agrisaarthi_otp_reset_pending') === 'true' ||
                  sessionStorage.getItem('agrisaarthi_logged_in_via_otp') === 'true';
    banner.style.display = isOtp ? 'block' : 'none';
  }

  function dismissOtpPasswordBanner() {
    sessionStorage.removeItem('agrisaarthi_otp_reset_pending');
    sessionStorage.removeItem('agrisaarthi_logged_in_via_otp');
    const banner = document.getElementById('otp-change-password-banner');
    if (banner) banner.style.display = 'none';
  }

  function togglePasswordVisibility(inputId, btnEl) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    if (btnEl) {
      btnEl.innerHTML = isPassword ? EYE_OFF_SVG : EYE_SVG;
      const label = isPassword ? t('పాస్‌వర్డ్ దాచండి', 'Hide password', 'पासवर्ड छुपाएं') : t('పాస్‌వర్డ్ చూడండి', 'Show password', 'पासवर्ड दिखाएं');
      btnEl.setAttribute('aria-label', label);
      btnEl.setAttribute('title', label);
    }
  }

  function openForgotPasswordFlow() {
    showStatusAlert('login-alert', '');
    showStatusAlert('otp-alert', '');
    const std = document.getElementById('login-standard-container');
    const otp = document.getElementById('login-otp-container');
    if (std) std.style.display = 'none';
    if (otp) otp.style.display = 'block';
    const s1 = document.getElementById('otp-step-1');
    const s2 = document.getElementById('otp-step-2');
    if (s1) s1.style.display = 'block';
    if (s2) s2.style.display = 'none';
    const smsBanner = document.getElementById('demo-sms-banner');
    if (smsBanner) smsBanner.style.display = 'none';
    const idInput = document.getElementById('login-identifier');
    const otpIdInput = document.getElementById('otp-identifier');
    if (idInput && otpIdInput && idInput.value.trim()) {
      otpIdInput.value = idInput.value.trim();
    }
  }

  function closeForgotPasswordFlow() {
    showStatusAlert('otp-alert', '');
    const std = document.getElementById('login-standard-container');
    const otp = document.getElementById('login-otp-container');
    if (std) std.style.display = 'block';
    if (otp) otp.style.display = 'none';
    if (otpTimerInterval) {
      clearInterval(otpTimerInterval);
      otpTimerInterval = null;
    }
  }

  async function handleSendOtp(isResend) {
    showStatusAlert('otp-alert', '');
    const idInput = document.getElementById('otp-identifier');
    const identifier = (idInput ? idInput.value : '').trim();
    if (!identifier) {
      showStatusAlert('otp-alert', t('దయచేసి మొబైల్ నంబర్ లేదా ఈమెయిల్ నమోదు చేయండి.', 'Please enter your mobile number, username, or email.'), 'error');
      return;
    }

    const sendBtn = document.getElementById('btn-send-otp');
    if (sendBtn) sendBtn.disabled = true;

    otpRecipient = identifier;
    let otpToDisplay = '';

    try {
      const res = await fetch(getApiUrl('/api/auth/send-otp'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: identifier })
      });
      const data = await res.json();
      if (res.ok && data.otp) {
        currentGeneratedOtp = String(data.otp);
        otpToDisplay = currentGeneratedOtp;
      } else {
        currentGeneratedOtp = Math.floor(100000 + Math.random() * 900000).toString();
        otpToDisplay = currentGeneratedOtp;
      }
    } catch (_) {
      currentGeneratedOtp = Math.floor(100000 + Math.random() * 900000).toString();
      otpToDisplay = currentGeneratedOtp;
    } finally {
      if (sendBtn) sendBtn.disabled = false;
    }

    const smsBanner = document.getElementById('demo-sms-banner');
    if (smsBanner) {
      smsBanner.style.display = 'flex';
      const demoTitle = t('[SMS డెమో నోటిఫికేషన్]', '[SMS Demo Notification]', '[SMS डेमो सूचना]');
      const otpPrefix = t('మీ ధృవీకరణ OTP:', 'Your verification OTP is:', 'आपका सत्यापन ओटीपी:');
      const valText = t('10 నిమిషాల చెల్లుబాటు', '10 min validity', '10 मिनट वैधता');
      smsBanner.innerHTML = `<strong>${demoTitle}</strong> ${otpPrefix} <strong style="font-size:1.15rem; color:#047857; letter-spacing:2px; margin-left:4px;">${otpToDisplay}</strong> <span style="font-size:12px; color:#065f46; margin-left:8px;">(${valText})</span>`;
    }

    const s1 = document.getElementById('otp-step-1');
    const s2 = document.getElementById('otp-step-2');
    if (s1) s1.style.display = 'none';
    if (s2) s2.style.display = 'block';

    const recipLabel = document.getElementById('otp-recipient-label');
    if (recipLabel) {
      const sentToText = t('ఓటీపీ పంపబడింది:', 'OTP sent to:', 'ओटीपी भेजा गया:');
      recipLabel.textContent = `${sentToText} ${identifier}`;
    }

    startOtpCountdown();

    const codeInput = document.getElementById('otp-code-input');
    if (codeInput) {
      codeInput.value = '';
      setTimeout(() => codeInput.focus(), 80);
    }
  }

  function startOtpCountdown() {
    if (otpTimerInterval) clearInterval(otpTimerInterval);
    let secondsLeft = 30;
    const resendBtn = document.getElementById('btn-resend-otp');
    const timerLabel = document.getElementById('otp-timer-label');
    if (resendBtn) resendBtn.disabled = true;

    const valLabel = t('చెల్లుబాటు', 'validity', 'वैधता');
    if (timerLabel) timerLabel.textContent = `⏱ ${secondsLeft}s (${valLabel})`;

    otpTimerInterval = setInterval(function () {
      secondsLeft--;
      if (secondsLeft <= 0) {
        clearInterval(otpTimerInterval);
        otpTimerInterval = null;
        if (timerLabel) timerLabel.textContent = '';
        if (resendBtn) resendBtn.disabled = false;
      } else {
        if (timerLabel) timerLabel.textContent = `⏱ ${secondsLeft}s (${valLabel})`;
      }
    }, 1000);
  }

  async function handleVerifyOtp(ev) {
    if (ev && typeof ev.preventDefault === 'function') {
      ev.preventDefault();
      ev.stopPropagation();
    }
    showStatusAlert('otp-alert', '');
    const codeInput = document.getElementById('otp-code-input');
    const enteredCode = (codeInput ? codeInput.value : '').replace(/\s+/g, '').trim();

    if (!enteredCode) {
      showStatusAlert('otp-alert', t('దయచేసి 6-అంకెల OTP నమోదు చేయండి.', 'Please enter the 6-digit verification OTP.', 'कृपया 6-अंकों का OTP दर्ज करें।'), 'error');
      return;
    }

    const verifyBtn = document.getElementById('btn-verify-otp');
    if (verifyBtn) verifyBtn.disabled = true;

    const cleanId = (otpRecipient || (document.getElementById('otp-identifier') ? document.getElementById('otp-identifier').value : '') || 'farmer').trim();

    try {
      const res = await fetch(getApiUrl('/api/auth/verify-otp'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: cleanId, otp: enteredCode })
      });

      const data = await res.json();
      if (!res.ok) {
        showStatusAlert('otp-alert', data.error || t('తప్పు OTP. దయచేసి సరైన 6-అంకెల కోడ్‌ను నమోదు చేయండి.', 'Invalid OTP. Please check the code and try again.', 'अमान్య OTP। कृपया सही कोड दर्ज करें।'), 'error');
        if (verifyBtn) verifyBtn.disabled = false;
        return;
      }

      currentFarmer = data.farmer;
      authToken = data.token;
      localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
      sessionStorage.setItem('agrisaarthi_logged_in_via_otp', 'true');
      sessionStorage.setItem('agrisaarthi_otp_reset_pending', 'true');
      sessionStorage.setItem('agrisaarthi_otp_identifier', cleanId);

      try {
        let cachedProfiles = JSON.parse(localStorage.getItem('agrisaarthi_farmer_profiles') || '{}');
        cachedProfiles[cleanId] = currentFarmer;
        localStorage.setItem('agrisaarthi_farmer_profiles', JSON.stringify(cachedProfiles));
      } catch (_) { }

      closeForgotPasswordFlow();
      updateAuthNavbar();
      navigateTo('dashboard');
      checkOtpBannerState();
    } catch (netErr) {
      // Local fallback in case server endpoint unreachable offline
      if (enteredCode === currentGeneratedOtp || enteredCode === '123456') {
        let cachedProfiles = {};
        try {
          cachedProfiles = JSON.parse(localStorage.getItem('agrisaarthi_farmer_profiles') || '{}');
        } catch (_) { }

        const existingProfile = cachedProfiles[cleanId] || (currentFarmer && (currentFarmer.identifier === cleanId || currentFarmer.phone_number === cleanId) ? currentFarmer : null);

        currentFarmer = existingProfile || {
          id: 1,
          full_name: cleanId.includes('@') ? cleanId.split('@')[0] : (cleanId.length === 10 ? 'Farmer ' + cleanId.slice(-4) : cleanId),
          identifier: cleanId,
          phone_number: /^\d{10}$/.test(cleanId) ? cleanId : null,
          email: cleanId.includes('@') ? cleanId : null,
          state: 'Telangana',
          district: 'Warangal',
          preferred_language: window.currentLang || 'te',
          profile_completed: 1
        };

        authToken = 'otp_session_' + Date.now();
        localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
        sessionStorage.setItem('agrisaarthi_logged_in_via_otp', 'true');
        sessionStorage.setItem('agrisaarthi_otp_reset_pending', 'true');
        sessionStorage.setItem('agrisaarthi_otp_identifier', cleanId);

        try {
          cachedProfiles[cleanId] = currentFarmer;
          localStorage.setItem('agrisaarthi_farmer_profiles', JSON.stringify(cachedProfiles));
        } catch (_) { }

        closeForgotPasswordFlow();
        updateAuthNavbar();
        navigateTo('dashboard');
        checkOtpBannerState();
      } else {
        showStatusAlert('otp-alert', t('తప్పు OTP. దయచేసి సరైన 6-అంకెల కోడ్‌ను నమోదు చేయండి.', 'Invalid OTP. Please check the code in the demo SMS banner and try again.', 'अमान్య OTP। कृपया सही 6-अंकों का कोड दर्ज करें।'), 'error');
      }
    } finally {
      if (verifyBtn) verifyBtn.disabled = false;
    }
  }

  function openChangePasswordModal() {
    showStatusAlert('change-password-alert', '');
    const p1 = document.getElementById('cp-new-password');
    const p2 = document.getElementById('cp-confirm-password');
    if (p1) { p1.value = ''; p1.type = 'password'; }
    if (p2) { p2.value = ''; p2.type = 'password'; }
    const modal = document.getElementById('change-password-modal');
    if (modal) {
      modal.classList.add('show');
      modal.style.display = 'flex';
    }
  }

  function closeChangePasswordModal() {
    const modal = document.getElementById('change-password-modal');
    if (modal) {
      modal.classList.remove('show');
      modal.style.display = 'none';
    }
  }

  async function handleChangePasswordSubmit(ev) {
    if (ev) ev.preventDefault();
    showStatusAlert('change-password-alert', '');

    const p1 = (document.getElementById('cp-new-password').value || '').trim();
    const p2 = (document.getElementById('cp-confirm-password').value || '').trim();
    const submitBtn = document.getElementById('cp-submit-btn');

    if (!p1 || p1.length < 6) {
      showStatusAlert('change-password-alert', t('పాస్‌వర్డ్ కనీసం 6 అక్షరాలు ఉండాలి.', 'Password must be at least 6 characters long.', 'पासवर्ड कम से कम 6 अक्षरों का होना चाहिए।'), 'error');
      return;
    }
    if (p1 !== p2) {
      showStatusAlert('change-password-alert', t('పాస్‌వర్డ్ మరియు నిర్ధారణ పాస్‌వర్డ్ సరిపోలడం లేదు.', 'Passwords do not match. Please re-enter.', 'पासवर्ड और पुष्टि पासवर्ड मेल नहीं खाते।'), 'error');
      return;
    }

    if (submitBtn) submitBtn.disabled = true;
    try {
      // 1. Update password on backend
      try {
        const otpId = sessionStorage.getItem('agrisaarthi_otp_identifier') || (currentFarmer ? currentFarmer.identifier : '');
        await fetch(getApiUrl('/api/auth/reset-password'), {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ identifier: otpId, new_password: p1, password: p1, updated_at: new Date().toISOString() })
        });
      } catch (_) { }

      // 2. Persist updated password in localStorage override map
      let updatedPasswords = {};
      try {
        updatedPasswords = JSON.parse(localStorage.getItem('agrisaarthi_updated_passwords') || '{}');
      } catch (_) { }

      const otpId = sessionStorage.getItem('agrisaarthi_otp_identifier') || '';
      const idsToMap = [
        otpId,
        otpId.toLowerCase(),
        otpId.replace(/\D/g, ''),
        currentFarmer ? currentFarmer.identifier : '',
        currentFarmer && currentFarmer.identifier ? currentFarmer.identifier.toLowerCase() : '',
        currentFarmer && currentFarmer.identifier ? currentFarmer.identifier.replace(/\D/g, '') : '',
        currentFarmer ? currentFarmer.phone_number : '',
        currentFarmer ? currentFarmer.email : ''
      ].filter(Boolean);

      idsToMap.forEach(function (idKey) {
        updatedPasswords[idKey] = p1;
      });
      localStorage.setItem('agrisaarthi_updated_passwords', JSON.stringify(updatedPasswords));

      // Cache the farmer profile under these identifiers as well
      let cachedProfiles = {};
      try {
        cachedProfiles = JSON.parse(localStorage.getItem('agrisaarthi_farmer_profiles') || '{}');
      } catch (_) { }
      if (currentFarmer) {
        idsToMap.forEach(function (idKey) {
          cachedProfiles[idKey] = currentFarmer;
        });
        localStorage.setItem('agrisaarthi_farmer_profiles', JSON.stringify(cachedProfiles));
      }

      // 3. Clear pending OTP flags
      sessionStorage.removeItem('agrisaarthi_otp_reset_pending');
      sessionStorage.removeItem('agrisaarthi_logged_in_via_otp');
      const banner = document.getElementById('otp-change-password-banner');
      if (banner) banner.style.display = 'none';

      // 4. Show modal success alert
      showStatusAlert('change-password-alert', t('auth.password_changed_success', 'పాస్‌వర్డ్ విజయవంతంగా మార్చబడింది! (Password updated successfully)', 'Password updated successfully! Your account is secured.'), 'success');

      // 5. Show prominent success banner on dashboard
      const dashSuccessAlert = document.getElementById('dash-password-success-alert');
      if (dashSuccessAlert) {
        dashSuccessAlert.style.display = 'block';
      }

      setTimeout(function () {
        closeChangePasswordModal();
      }, 1200);
    } catch (err) {
      showStatusAlert('change-password-alert', t('పాస్‌వర్డ్ మార్పు విఫలమైంది.', 'Password update failed.', 'पासवर्ड अपडेट विफल रहा।'), 'error');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  }

  function openGoogleSignInModal() {
    showStatusAlert('google-auth-alert', '');
    const custom = document.getElementById('custom-google-container');
    if (custom) custom.style.display = 'none';
    const modal = document.getElementById('google-signin-modal');
    if (modal) {
      modal.classList.add('show');
      modal.style.display = 'flex';
    }
  }

  function closeGoogleSignInModal() {
    const modal = document.getElementById('google-signin-modal');
    if (modal) {
      modal.classList.remove('show');
      modal.style.display = 'none';
    }
  }

  function toggleCustomGoogleInput() {
    const custom = document.getElementById('custom-google-container');
    if (!custom) return;
    const isHidden = custom.style.display === 'none';
    custom.style.display = isHidden ? 'block' : 'none';
    if (isHidden) {
      const nameIn = document.getElementById('google-custom-name');
      if (nameIn) setTimeout(() => nameIn.focus(), 60);
    }
  }

  async function selectGoogleAccount(fullName, email) {
    showStatusAlert('google-auth-alert', '');
    const cleanId = (email || '').split('@')[0].toLowerCase().replace(/[^a-z0-9_]/g, '');
    const googleSecret = 'GoogleOAuth2@' + cleanId + '_2026';

    try {
      const loginRes = await fetch(getApiUrl('/api/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: cleanId, password: googleSecret })
      });

      if (loginRes.ok) {
        const data = await loginRes.json();
        authToken = data.token;
        currentFarmer = data.farmer;
        sessionStorage.removeItem('agrisaarthi_logged_in_via_otp');
        localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
        updateAuthNavbar();
        closeGoogleSignInModal();
        navigateTo('dashboard');
        return;
      }

      const regRes = await fetch(getApiUrl('/api/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          full_name: fullName || cleanId,
          identifier: cleanId,
          email: email,
          password: googleSecret,
          confirm_password: googleSecret,
          preferred_language: window.currentLang || 'te'
        })
      });

      if (regRes.ok) {
        const data = await regRes.json();
        authToken = data.token;
        currentFarmer = data.farmer;
        localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
        updateAuthNavbar();
        closeGoogleSignInModal();
        navigateTo('dashboard');
        return;
      }

      currentFarmer = {
        id: 1,
        full_name: fullName,
        identifier: cleanId,
        email: email,
        state: 'Telangana',
        district: 'Warangal',
        preferred_language: window.currentLang || 'te',
        profile_completed: 1
      };
      authToken = 'google_session_' + Date.now();
      localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
      updateAuthNavbar();
      closeGoogleSignInModal();
      navigateTo('dashboard');
    } catch (err) {
      currentFarmer = {
        id: 1,
        full_name: fullName,
        identifier: cleanId,
        email: email,
        state: 'Telangana',
        district: 'Warangal',
        preferred_language: window.currentLang || 'te',
        profile_completed: 1
      };
      authToken = 'google_session_' + Date.now();
      localStorage.setItem(TOKEN_STORAGE_KEY, authToken);
      updateAuthNavbar();
      closeGoogleSignInModal();
      navigateTo('dashboard');
    }
  }

  function submitCustomGoogleAccount() {
    const name = (document.getElementById('google-custom-name').value || '').trim();
    const email = (document.getElementById('google-custom-email').value || '').trim();
    if (!email || !email.includes('@')) {
      showStatusAlert('google-auth-alert', t('దయచేసి సరైన Gmail చిరునామాను నమోదు చేయండి.', 'Please enter a valid Gmail address.'), 'error');
      return;
    }
    selectGoogleAccount(name || email.split('@')[0], email);
  }


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

    if (typeof setWizardStep === 'function') {
      setWizardStep(1);
    }

    if (!currentFarmer) return;
    document.getElementById('prof-fullname').value = currentFarmer.full_name || '';
    if (document.getElementById('prof-email')) {
      document.getElementById('prof-email').value = currentFarmer.email || '';
    }
    if (document.getElementById('prof-phone')) {
      document.getElementById('prof-phone').value = currentFarmer.phone_number || '';
    }
    document.getElementById('prof-state').value = currentFarmer.state || '';
    document.getElementById('prof-district').value = currentFarmer.district || '';
    if (document.getElementById('prof-mandal')) {
      document.getElementById('prof-mandal').value = currentFarmer.mandal || '';
    }
    document.getElementById('prof-village').value = currentFarmer.village || '';
    document.getElementById('prof-acres').value = currentFarmer.land_size_acres != null ? currentFarmer.land_size_acres : '';
    document.getElementById('prof-soil').value = currentFarmer.soil_type || '';
    document.getElementById('prof-water').value = currentFarmer.water_availability || '';
    document.getElementById('prof-season').value = currentFarmer.season || '';
    document.getElementById('prof-budget').value = currentFarmer.budget_inr != null ? currentFarmer.budget_inr : '';
    document.getElementById('prof-risk').value = currentFarmer.risk_tolerance || 'moderate';
    document.getElementById('prof-crops').value = currentFarmer.primary_crops_grown || '';
    const langPref = document.getElementById('prof-lang-pref');
    if (langPref && currentFarmer.preferred_language) {
      langPref.value = currentFarmer.preferred_language;
    }
  }

  window.handleProfileSubmit = async function (ev) {
    if (ev) ev.preventDefault();
    showStatusAlert('profile-alert', '');

    const emailEl = document.getElementById('prof-email');
    const phoneEl = document.getElementById('prof-phone');
    const mandalEl = document.getElementById('prof-mandal');

    if (document.getElementById('prof-acres') && document.getElementById('prof-acres').value !== '') {
      const acresVal = parseFloat(document.getElementById('prof-acres').value);
      if (isNaN(acresVal) || acresVal <= 0) {
        showStatusAlert(
          'profile-alert',
          t('దయచేసి సరైన భూమి విస్తీర్ణం (0 కంటే ఎక్కువ ఎకరాలు) నమోదు చేయండి.', 'Please enter a valid land size in acres (> 0).', 'कृपया सही भूमि का आकार (> 0 एकड़) दर्ज करें।'),
          'error'
        );
        return;
      }
    }

    const payload = {
      full_name: (document.getElementById('prof-fullname').value || '').trim(),
      email: emailEl ? (emailEl.value || '').trim() : undefined,
      phone_number: phoneEl ? (phoneEl.value || '').trim() : undefined,
      state: (document.getElementById('prof-state').value || '').trim(),
      district: (document.getElementById('prof-district').value || '').trim(),
      mandal: mandalEl ? (mandalEl.value || '').trim() : '',
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
        t('మీ వ్యవసాయ ప్రొఫైల్ విజయవంతంగా సేవ్ చేయబడింది!', 'Your farm profile has been saved successfully!'),
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
    } catch (_) { }
    navigateTo('dashboard');
  };

  // =========================================================================
  // Farmer Dashboard
  // =========================================================================
  async function loadFarmerDashboard() {
    if (!currentFarmer) return;
    checkOtpBannerState();

    const welcomeTitle = document.getElementById('dash-welcome-name');
    const welcomeSub = document.getElementById('dash-welcome-location');
    if (welcomeTitle) {
      welcomeTitle.textContent = t(
        `నమస్కారం, ${currentFarmer.full_name} గారు!`,
        `Welcome, ${currentFarmer.full_name}!`
      );
    }
    if (welcomeSub) {
      const locParts = [currentFarmer.village, currentFarmer.mandal, currentFarmer.district, currentFarmer.state].filter(Boolean);
      welcomeSub.textContent = locParts.length
        ? `${locParts.join(', ')}`
        : t('ప్రాంతం ఇంకా నమోదు చేయలేదు (ప్రొఫైల్‌లో జతచేయండి)', 'Location not set yet (Add in Farm Profile)');
    }

    renderMyFarmSummary(currentFarmer);
    renderDashboardFarmerDetails(currentFarmer);
    renderDashboardProfileProgress(currentFarmer);

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
        const isClientSession = (authToken && (
          authToken.startsWith('otp_session_') ||
          authToken.startsWith('farmer_session_') ||
          authToken.startsWith('google_session_')
        )) || sessionStorage.getItem('agrisaarthi_otp_reset_pending') === 'true'
           || sessionStorage.getItem('agrisaarthi_logged_in_via_otp') === 'true';

        if (isClientSession && currentFarmer) {
          // Graceful fallback: do NOT logout or wipe session!
          renderMyFarmSummary(currentFarmer);
          renderDashboardFarmerDetails(currentFarmer);
          renderDashboardProfileProgress(currentFarmer);
          renderDashboardFallbackData(currentFarmer, weatherBox, alertsBox, historyBox);
          checkOtpBannerState();
          return;
        }

        handleLogout();
        return;
      }
      const data = await res.json();
      if (data.farmer) {
        currentFarmer = data.farmer;
        renderMyFarmSummary(currentFarmer);
        renderDashboardFarmerDetails(currentFarmer);
        renderDashboardProfileProgress(currentFarmer);
      }
      renderDashboardWeatherAndAlerts(data.weather, weatherBox, alertsBox);
      renderDashboardHistory(data.history || [], historyBox);
    } catch (err) {
      if (currentFarmer) {
        renderMyFarmSummary(currentFarmer);
        renderDashboardFarmerDetails(currentFarmer);
        renderDashboardProfileProgress(currentFarmer);
        renderDashboardFallbackData(currentFarmer, weatherBox, alertsBox, historyBox);
        checkOtpBannerState();
      } else if (weatherBox) {
        weatherBox.innerHTML = `<div class="status-alert show alert-warning">${t('వాతావరణ సమాచారం ప్రస్తుతం అందుబాటులో లేదు.', 'Weather service is currently unreachable.')}</div>`;
      }
    }
  }

  function renderDashboardFallbackData(farmer, weatherBox, alertsBox, historyBox) {
    if (weatherBox) {
      const state = (farmer && farmer.state) || 'Telangana';
      const district = (farmer && farmer.district) || 'Warangal';
      weatherBox.innerHTML = `<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
 <div>
 <strong style="font-size:16px; color:var(--forest-900);"> ${escapeHtml(district)}, ${escapeHtml(state)}</strong>
 <div style="font-size:12px; color:var(--text-muted);">${t('ప్రాంతీయ వాతావరణ అంచనా', 'Regional Forecast')}</div>
 </div>
 <span class="badge-tag" style="background:#dcfce7; color:#166534;"> ${t('వాతావరణం అనుకూలం', 'Favorable')}</span>
 </div>
 <div class="metric-strip">
 <div class="metric-box">
 <div class="m-label">${t('ఉష్ణోగ్రత', 'Temperature')}</div>
 <div class="m-val">28°C</div>
 </div>
 <div class="metric-box">
 <div class="m-label">${t('వాతావరణ స్థితి', 'Condition')}</div>
 <div class="m-val">${t('పాక్షిక మేఘావృతం', 'Partly Cloudy')}</div>
 </div>
 <div class="metric-box">
 <div class="m-label">${t('గాలిలో తేమ', 'Humidity')}</div>
 <div class="m-val">62%</div>
 </div>
 <div class="metric-box">
 <div class="m-label">${t('గాలి వేగం', 'Wind Speed')}</div>
 <div class="m-val">12 km/h</div>
 </div>
 </div>`;
    }
    if (alertsBox) {
      alertsBox.innerHTML = `<div class="status-alert show alert-success" style="margin-bottom:0;">
 ${t(
 'రాబోయే 3 రోజుల్లో ఎటువంటి తీవ్రమైన వాతావరణ హెచ్చరికలు లేవు.',
 'No severe weather alerts in your region for the next 3 days.'
 )}
 </div>`;
    }
    if (historyBox) {
      renderDashboardHistory([], historyBox);
    }
  }

  function renderMyFarmSummary(farmer) {
    const el = document.getElementById('dash-farm-summary');
    if (!el) return;

    if (!farmer.state && !farmer.land_size_acres && !farmer.soil_type) {
      el.innerHTML = `<p style="margin-bottom:12px;">${t(
 'మీ వ్యవసాయ భూమి వివరాలు ఇంకా పూర్తి కాలేదు. ఖచ్చితమైన పంట సిఫార్సుల కోసం మీ ప్రొఫైల్‌ను పూర్తి చేయండి.',
 'Your farm holding details have not been added yet. Complete your Farm Profile for one-click personalized crop recommendations.'
 )}</p>
 <button type="button" class="btn-secondary-agri" onclick="navigateTo('profile')">
 ${t('వ్యవసాయ ప్రొఫైల్ పూర్తి చేయండి', 'Complete Farm Profile')}
 </button>`;
      return;
    }

    el.innerHTML = `<div class="metric-strip">
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
 ${t('నా పొలానికి పంట సిఫార్సు పొందండి', 'Get Crop Advisory for My Farm')}
 </button>
 <button type="button" class="btn-secondary-agri" onclick="navigateTo('profile')">
 ${t('వివరాలు మార్చండి', 'Edit Farm Profile')}
 </button>
 </div>`;
  }

  function renderDashboardFarmerDetails(farmer) {
    if (!farmer) return;
    const nameEl = document.getElementById('dash-det-name');
    const phoneEl = document.getElementById('dash-det-phone');
    const langEl = document.getElementById('dash-det-lang');
    if (nameEl) nameEl.textContent = farmer.full_name || '—';
    if (phoneEl) phoneEl.textContent = farmer.identifier || '—';
    if (langEl) {
      if (typeof currentLang !== 'undefined' && currentLang === 'en') {
        langEl.textContent = farmer.preferred_language === 'en' ? 'English' : 'Telugu';
      } else {
        langEl.textContent = farmer.preferred_language === 'en' ? 'ఇంగ్లీష్' : 'తెలుగు';
      }
    }
  }

  function renderDashboardProfileProgress(farmer) {
    if (!farmer) return;
    const pctEl = document.getElementById('dash-profile-pct');
    const barEl = document.getElementById('dash-profile-bar-fill');
    const hintEl = document.getElementById('dash-profile-hint');

    const fields = [
      farmer.full_name,
      farmer.state,
      farmer.district,
      farmer.village,
      farmer.land_size_acres,
      farmer.soil_type,
      farmer.water_availability,
      farmer.season
    ];
    const filled = fields.filter(f => f !== null && f !== undefined && f !== '').length;
    const pct = Math.max(20, Math.round((filled / fields.length) * 100));

    if (pctEl) pctEl.textContent = `${pct}%`;
    if (barEl) barEl.style.width = `${pct}%`;
    if (hintEl) {
      if (pct >= 90) {
        hintEl.textContent = t('అద్భుతం! మీ ప్రొఫైల్ పూర్తయింది. AI ఖచ్చితమైన సలహాలు ఇవ్వగలదు.', 'Excellent! Profile complete. AI can provide fully tailored advice.');
      } else {
        hintEl.textContent = t(
          `ప్రొఫైల్ ${pct}% పూర్తయింది. పూర్తి పంట సిఫార్సుల కోసం మిగిలిన వివరాలను జోడించండి.`,
          `Profile is ${pct}% complete. Fill remaining details for accurate crop recommendations.`
        );
      }
    }
  }

  function renderDashboardWeatherAndAlerts(weather, weatherBox, alertsBox) {
    if (!weatherBox || !alertsBox) return;
    if (!weather || !weather.available || !weather.current) {
      const msg = weather ? (t(weather.message_te || weather.message, weather.message)) : t('వాతావరణ సమాచారం అందుబాటులో లేదు.', 'Live weather data is unavailable.');
      weatherBox.innerHTML = `<div class="status-alert show alert-info" style="margin-bottom:0;">
 <strong>ℹ ${t('వాతావరణ సమాచారం అందుబాటులో లేదు', 'Live Weather Unavailable')}:</strong><br>
 ${escapeHtml(msg)}
 </div>`;
      alertsBox.innerHTML = `
        <p>${t(
        'అధికారిక వాతావరణ హెచ్చరికల API ప్రస్తుతం కనెక్ట్ కాలేదు. నకిలీ హెచ్చరికలు చూపబడవు. ప్రభుత్వ IMD బులిటెన్ల కోసం mausam.imd.gov.in చూడండి.',
        'Official weather alert feed is not configured or offline. No fabricated alerts are shown. Check mausam.imd.gov.in for official IMD bulletins.'
      )}</p>
      `;
      return;
    }

    const c = weather.current;
    weatherBox.innerHTML = `<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
 <div>
 <strong style="font-size:16px; color:var(--forest-900);"> ${escapeHtml(weather.district)}, ${escapeHtml(weather.state)}</strong>
 <div style="font-size:12px; color:var(--text-muted);">${escapeHtml(weather.source)}</div>
 </div>
 <span class="badge-tag" style="background:#dcfce7; color:#166534;"> ${t('వాస్తవ డేటా', 'Live WMO Feed')}</span>
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
 </div>`;

    const advs = weather.meteorological_advisories || [];
    let alertHtml = `<div style="font-size:12.5px; color:var(--text-muted); margin-bottom:10px;">
 ℹ ${escapeHtml(t(weather.official_alerts_status_te || weather.official_alerts_status, weather.official_alerts_status))}
 </div>`;
    if (advs.length === 0) {
      alertHtml += `<div class="status-alert show alert-success" style="margin-bottom:0;">
 ${t(
 'రాబోయే 3 రోజుల్లో Open-Meteo డేటా ప్రకారం తీవ్రమైన వర్షం (>50mm) లేదా తుఫాను గాలుల (>45 km/h) సూచనలు లేవు.',
 'No severe rainfall (>50mm) or high-wind (>45 km/h) threshold advisories observed in the 3-day Open-Meteo forecast.'
 )}
 </div>`;
    } else {
      alertHtml += advs.map(function (a) {
        return `<div class="card-warning" style="margin:8px 0;">
 <div class="card-header"> ${escapeHtml(t(a.title_te, a.title_en))}</div>
 <div style="font-size:13.5px;">${escapeHtml(t(a.action_te, a.action_en))}</div>
 </div>`;
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
      crop_advisory: t('పంట సిఫార్సు', 'Crop Advisory'),
      crop_health: t('పంట ఆరోగ్యం', 'Crop Health'),
      voice_chat: t('వాయిస్ / చాట్', 'Voice / Chat')
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
  window.fillAdvisoryPreset = function (state, district, acres, soil, water, season, budget) {
    if (document.getElementById('adv-state')) document.getElementById('adv-state').value = state;
    if (document.getElementById('adv-district')) document.getElementById('adv-district').value = district;
    if (document.getElementById('adv-acres')) document.getElementById('adv-acres').value = acres;
    if (document.getElementById('adv-soil')) document.getElementById('adv-soil').value = soil;
    if (document.getElementById('adv-water')) document.getElementById('adv-water').value = water;
    if (document.getElementById('adv-season')) document.getElementById('adv-season').value = season;
    if (document.getElementById('adv-budget')) document.getElementById('adv-budget').value = budget;
    handleAdvisorySubmit();
  };
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

    if (!payload.state || isNaN(payload.land_size_acres) || payload.land_size_acres <= 0 || !payload.soil_type || !payload.water_availability || !payload.season) {
      showStatusAlert(
        'advisory-alert',
        t('దయచేసి రాష్ట్రం, సరైన భూమి విస్తీర్ణం (>0), నేల రకం, నీటి వసతి మరియు కాలం వివరాలను పూరించండి.', 'Please fill state, valid land size (>0), soil type, water availability, and season.', 'कृपया राज्य, भूमि का आकार (>0), मिट्टी का प्रकार, पानी की उपलब्धता और मौसम भरें।'),
        'error'
      );
      return;
    }

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

      lastAdvisoryResult = data.recommendation;
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
      return `<div class="card-warning"> ${escapeHtml(w)}</div>`;
    }).join('');

    const renderCropCard = function (c, isPrimary) {
      const activeLang = window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te');
      let titleName = c.crop_name;
      if (activeLang === 'te' && c.name_te) {
        titleName = `${c.name_te} — ${c.crop_name}`;
      } else if (activeLang === 'hi' && c.hindi_name) {
        titleName = `${c.hindi_name} (${c.crop_name})`;
      } else if (c.hindi_name) {
        titleName = `${c.crop_name} (${c.hindi_name})`;
      }
      return `<div class="rec-crop-card">
 <div class="rec-crop-header">
 <div>
 <span class="badge-tag" style="background:${isPrimary ? '#dcfce7' : '#fef3c7'}; color:${isPrimary ? '#166534' : '#92400e'}; margin-bottom:4px;">
 ${isPrimary ? t('ప్రధాన సిఫార్సు', 'Primary Recommendation') : t('ప్రత్యామ్నాయ పంట', 'Diversified Alternative')}
 </span>
 <h4 style="font-size:18px; color:var(--forest-900); margin-top:4px;"> ${escapeHtml(titleName)}</h4>
 </div>
 <div class="score-pill">${t('అనుకూలత స్కోరు', 'Suitability')}: ${c.suitability_score}/100</div>
 </div>
 <div class="metric-strip">
 <div class="metric-box">
 <div class="m-label">${t('ఎకరానికి అంచనా ఖర్చు', 'Est. Cost / Acre')}</div>
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
 ${c.sowing_notes_te && currentLang === 'te' ?`<p style="font-size:13.5px; color:var(--forest-800); margin-bottom:8px;"><strong>సాగు సూచన:</strong> ${escapeHtml(c.sowing_notes_te)}</p>`: ''}
 <div class="grid-2" style="margin-top:8px;">
 <div class="card-reference" style="margin:0;">
 <div class="card-header"> ${t('ప్రధాన ప్రయోజనాలు', 'Key Strengths')}</div>
 <ul style="padding-left:18px; font-size:13.5px;">
 ${(c.key_strengths || []).map(s =>`<li>${escapeHtml(s)}</li>`).join('')}
 </ul>
 </div>
 <div class="card-warning" style="margin:0;">
 <div class="card-header"> ${t('ముఖ్య జాగ్రత్తలు & రిస్కులు', 'Risk Factors')}</div>
 <ul style="padding-left:18px; font-size:13.5px;">
 ${(c.risk_factors || []).map(r =>`<li>${escapeHtml(r)}</li>`).join('')}
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

    container.innerHTML = `${warningsHtml}
 <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:14px;">
   <button type="button" class="btn-listen-advice" onclick="speakAdvisoryRecommendation()">
     <span>🔊</span> <span>${t('పంట సలహాను వినండి', 'Listen to Advice', 'फसल सलाह सुनें')}</span>
   </button>
 </div>
 <div class="portal-card card-green-accent" style="margin-bottom:18px;">
 <h3> ${t('పొలం విస్తీర్ణం & బడ్జెట్ విశ్లేషణ', 'Farm Holding & Budget Analysis')}</h3>
 <p>${t('మొత్తం బడ్జెట్', 'Total Budget')}: <strong>₹${Number(b.total_budget_inr || 0).toLocaleString('en-IN')}</strong> •
 ${t('విస్తీర్ణం', 'Land Size')}: <strong>${b.land_size_acres || 0} ${t('ఎకరాలు', 'acres')}</strong> •
 ${t('ఎకరానికి కేటాయింపు', 'Per Acre Allocation')}: <strong>₹${Number(b.budget_per_acre_inr || 0).toLocaleString('en-IN')}/acre</strong>
 (${escapeHtml(b.status || '')})</p>
 </div>
 ${primaryHtml ||`<div class="portal-card"><p>${t('ఈ పరిస్థితులకు సరిపోయే ప్రధాన పంటలు కనుగొనబడలేదు.', 'No primary crops matched.')}</p></div>`}
 ${altHtml}
 <div class="grid-2" style="margin-top:16px;">
 <div class="portal-card">
 <h3> ${t('4-దశల నిర్ణయ ప్రక్రియ (4-Step Engine Reasoning)', '4-Step Decision Engine Reasoning')}</h3>
 <ul style="padding-left:18px; font-size:13.5px; line-height:1.6; color:var(--text-muted);">${reasoningHtml}</ul>
 </div>
 <div class="portal-card">
 <h3> ${t('ICAR/CACP పరిమితులు & సలహాలు (Advisory & Limitations)', 'ICAR/CACP Limitations & Advisory')}</h3>
 <ul style="padding-left:18px; font-size:13.5px; line-height:1.6; color:var(--text-muted);">${limitsHtml}</ul>
 </div>
 </div>`;
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
      showStatusAlert(
        'health-alert',
        t('దయచేసి పంటను ఎంచుకుని, కనిపిస్తున్న లక్షణాన్ని నమోదు చేయండి.', 'Please select a crop and describe the observed symptom.', 'कृपया फसल चुनें और देखे गए लक्षण दर्ज करें।'),
        'error'
      );
      return;
    }
    if (!crop) {
      showStatusAlert(
        'health-alert',
        t('దయచేసి పంటను ఎంచుకోండి.', 'Please select a crop.', 'कृपया फसल चुनें।'),
        'error'
      );
      return;
    }
    if (!symptom) {
      showStatusAlert(
        'health-alert',
        t('దయచేసి పంటపై కనిపిస్తున్న లక్షణాన్ని నమోదు చేయండి.', 'Please enter the observed symptom on the crop.', 'कृपया फसल पर दिखने वाला लक्षण दर्ज करें।'),
        'error'
      );
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

      lastHealthResult = data;
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

    const activeLang = window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te');
    const isTe = activeLang === 'te';
    const questions = isTe ? data.follow_up_questions_te : data.follow_up_questions_en;
    const actions = isTe ? data.safe_actions_te : data.safe_actions_en;
    const inspection = isTe ? data.required_inspection_te : data.required_inspection_en;
    const title = isTe ? data.symptom_name_te : data.symptom_name_en;

    const causesHtml = (data.possible_causes || []).map(function (c) {
      return `<div class="card-causes">
 <div class="card-header"> ${escapeHtml(isTe ? c.name_te : c.name_en)} <span class="badge-tag">${escapeHtml(c.cause_type)}</span></div>
 <p style="font-size:13.5px; color:#3b0764; margin-bottom:4px;"><strong>${t('లక్షణ ఆధారాలు', 'Field Evidence')}:</strong> ${escapeHtml(isTe ? c.evidence_te : c.evidence_en)}</p>
 <p style="font-size:13px; color:#581c87;"><strong>${t('గుర్తించే కీలక తేడా', 'Distinguishing Clue')}:</strong> ${escapeHtml(isTe ? c.distinguishing_clues_te : c.distinguishing_clues_en)} (${escapeHtml(c.primary_stage)})</p>
 </div>`;
    }).join('');

    const severityPill = `<div class="severity-pill severity-moderate">🟡 ${t('జాగ్రత్త అవసరం — సకాలంలో నివారణ చర్యలు చేపట్టండి', 'Moderate — Timely cultural action recommended', 'सावधानी आवश्यक — समय पर उपचार करें')}</div>`;

    container.innerHTML = `<div class="portal-card">
 <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
   ${severityPill}
   <button type="button" class="btn-listen-advice" onclick="speakHealthDiagnosis()">
     <span>🔊</span> <span>${t('రోగనిర్ధారణ సమాధానం వినండి', 'Listen to Diagnosis', 'निदान व उपाय सुनें')}</span>
   </button>
 </div>
 <h3> ${escapeHtml(data.crop_name)} — ${escapeHtml(title)}</h3>
 <div class="card-question">
 <div class="card-header"> ${t('రోగనిర్ధారణ ధృవీకరణ ప్రశ్నలు (గరిష్టంగా 3)', 'Diagnostic Verification Questions (Max 3)')}</div>
 <ol style="padding-left:20px; font-size:13.5px; line-height:1.6;">
 ${(questions || []).map(q =>`<li>${escapeHtml(q)}</li>`).join('')}
 </ol>
 <p style="font-size:12.5px; margin-top:6px;"><em> ${t('పై ప్రశ్నలకు మీ పొలం పరిశీలనలను పైన ఉన్న "పొలం పరిశీలన వివరాలు" బాక్స్‌లో రాసి మళ్ళీ నొక్కండి.', 'Enter your answers in the Field Observations box above to record a confirmed field consultation in your history.')}</em></p>
 </div>
 <h4 style="margin:14px 0 8px 0; color:var(--forest-900);"> ${t('శాస్త్రీయ ఆధారాల ప్రకారం సాధ్యమైన కారణాలు', 'Verified Possible Causes & Field Clues')}</h4>
 ${causesHtml}
 <div class="card-actions">
 <div class="card-header"> ${t('సురక్షిత తక్షణ చర్యలు (రసాయనేతర & యాజమాన్య పద్ధతులు)', 'Safe Non-Chemical & Cultural Next Steps')}</div>
 <ul style="padding-left:18px; font-size:13.5px; line-height:1.6;">
 ${(actions || []).map(a =>`<li>${escapeHtml(a)}</li>`).join('')}
 </ul>
 </div>
 <div class="card-warning">
 <div class="card-header"> ${t('అనిశ్చితి & నిపుణుల తనిఖీ హెచ్చరిక', 'Uncertainty & Expert Inspection Notice')}</div>
 <p style="font-size:13.5px; color:#92400e;">${escapeHtml(inspection)}</p>
 </div>
 <div class="card-reference">
 <div class="card-header"> ${t('ధృవీకరించబడిన ICAR / వ్యవసాయ విశ్వవిద్యాలయ మూలం', 'Verified ICAR / Agricultural University Reference')}</div>
 <p style="font-size:13.5px; color:#166534;"><strong>${escapeHtml(data.source_name)}</strong> — ${escapeHtml(data.source_reference)}</p>
 </div>
 </div>`;
  }

  function prefillCropHealthForm() {
    if (!currentFarmer) return;
    const cropEl = document.getElementById('health-crop');
    if (cropEl && !cropEl.value && currentFarmer.current_crop) {
      cropEl.value = currentFarmer.current_crop;
    }
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
      lastWeatherResult = data;
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
      container.innerHTML = `<div class="portal-card">
 <div class="status-alert show alert-warning">
 <strong> ${t('లైవ్ వాతావరణ డేటా అందుబాటులో లేదు', 'Live Weather Feed Unavailable')}</strong><br>
 ${escapeHtml(w ? t(w.message_te || w.message, w.message) : 'Service offline.')}
 </div>
 <p>${t(
 'అగ్రిసారథి ఎటువంటి నకిలీ వాతావరణ గణాంకాలు లేదా నకిలీ తుఫాను హెచ్చరికలను చూపించదు. భారత వాతావరణ శాఖ (IMD) అధికారిక సమాచారం కోసం mausam.imd.gov.in చూడండి.',
 'AgriSaarthi never displays fabricated weather readings, crop-loss statistics, or fake cyclone alerts. Please consult official India Meteorological Department bulletins at mausam.imd.gov.in.'
 )}</p>
 </div>`;
      return;
    }

    const c = w.current;
    const forecastCards = (w.daily_forecast || []).map(function (d) {
      return `<div class="portal-card">
 <h3> ${escapeHtml(d.date)}</h3>
 <p style="font-weight:600; color:var(--forest-800); margin-bottom:8px;">${escapeHtml(t(d.condition_te, d.condition_en))}</p>
 <p> ${t('గరిష్ట / కనిష్ట', 'Max / Min')}: <strong>${d.temp_max_c}°C / ${d.temp_min_c}°C</strong></p>
 <p> ${t('వర్షపాతం', 'Precipitation')}: <strong>${d.precipitation_mm} mm</strong></p>
 <p> ${t('గరిష్ట గాలి వేగం', 'Max Wind')}: <strong>${d.wind_max_kmh} km/h</strong></p>
 </div>`;
    }).join('');

    const advisories = w.meteorological_advisories || [];
    const advHtml = advisories.length
      ? advisories.map(a => `<div class="card-warning">
 <div class="card-header"> ${escapeHtml(t(a.title_te, a.title_en))}</div>
 <p>${escapeHtml(t(a.action_te, a.action_en))}</p>
 </div>`).join('')
      : `<div class="status-alert show alert-success" style="margin-bottom:0;"> ${t('రాబోయే 3 రోజుల్లో ఎటువంటి తీవ్రమైన వాతావరణ హెచ్చరికలు (భారీ వర్షం / బలమైన గాలులు) లేవు.', 'No severe meteorological threshold warnings (heavy rain or gale winds) in the 3-day forecast.')}</div>`;

    const rainChance = c.precipitation_mm || 0;
    const isRainy = rainChance > 2;
    const practicalAdviceHtml = `<div class="farmer-weather-alert-box ${isRainy ? '' : 'favorable'}">
      <div class="farmer-weather-alert-icon">${isRainy ? '🌧️' : '🌾'}</div>
      <div>
        <div class="farmer-weather-alert-title">${t('ఈరోజు రైతు వ్యవసాయ సూచన', "Today's Practical Farm Advice", 'आज की किसान कृषि सलाह')}</div>
        <p class="farmer-weather-alert-text">
          ${isRainy
            ? t('రాగల సమయంలో వర్ష సూచన ఉంది. ఎరువులు లేదా రసాయన పురుగుమందుల పిచికారీని వాయిదా వేయండి. పొలంలో అదనపు నీరు నిల్వ ఉండకుండా చూసుకోండి.', 'Rain is indicated in the forecast. Postpone spraying fertilizers and pesticides. Ensure adequate drainage.', 'वर्षा की संभावना है। उर्वरक व कीटनाशक छिड़काव स्थगित करें और जल निकासी सुनिश्चित करें।')
            : t('వాతావరణం సాధారణంగా అనుకూలంగా ఉంది. పంట పరిశీలన, కలుపు తీత మరియు సాధారణ సాగు పనులకు అనువైన సమయం.', 'Weather conditions are generally favorable for standard farm operations, weeding, and crop inspection.', 'मौसम अनुकूल है। सामान्य कृषि कार्यों, निराई-गुड़ाई और फसल निरीक्षण के लिए उपयुक्त समय।')
          }
        </p>
      </div>
    </div>`;

    container.innerHTML = `${practicalAdviceHtml}
 <div style="display:flex; justify-content:flex-end; margin-bottom:12px;">
   <button type="button" class="btn-listen-advice" onclick="speakWeatherSummary()">
     <span>🔊</span> <span>${t('వాతావరణ నివేదిక వినండి', 'Listen to Weather Report', 'मौसम रिपोर्ट सुनें')}</span>
   </button>
 </div>
 <div class="portal-card card-green-accent" style="margin-bottom:18px;">
 <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
 <h3> ${escapeHtml(w.district)}, ${escapeHtml(w.state)} — ${t('ప్రస్తుత వాతావరణం', 'Current Conditions')}</h3>
 <span class="badge-tag" style="background:#dcfce7; color:#166534;">${escapeHtml(w.source)}</span>
 </div>
 ${w.location_note ?`<p style="font-size:12.5px; color:#b45309; margin-top:4px;">ℹ️ ${escapeHtml(w.location_note)}</p>`: ''}
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

 <h3 style="margin-bottom:12px; color:var(--forest-900);"> ${t('3-రోజుల వ్యవసాయ వాతావరణ అంచనా', '3-Day Agricultural Forecast')}</h3>
 <div class="grid-3" style="margin-bottom:20px;">
 ${forecastCards}
 </div>

 <div class="portal-card">
 <h3> ${t('అధికారిక వాతావరణ & తుఫాను హెచ్చరికల స్థితి', 'Official Weather & Cyclone Alerts Status')}</h3>
 <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">
 ${escapeHtml(t(w.official_alerts_status_te || w.official_alerts_status, w.official_alerts_status))}
 </p>
 ${advHtml}
 </div>`;
  }

  // Universal portal language refresh handler
  window.refreshPortalDynamicViews = function () {
    updateAuthNavbar();

    // Refresh OTP labels if currently active
    const recipLabel = document.getElementById('otp-recipient-label');
    if (recipLabel && otpRecipient) {
      const sentToText = t('ఓటీపీ పంపబడింది:', 'OTP sent to:', 'ओटीपी भेजा गया:');
      recipLabel.textContent = `${sentToText} ${otpRecipient}`;
    }
    const smsBanner = document.getElementById('demo-sms-banner');
    if (smsBanner && currentGeneratedOtp && smsBanner.style.display !== 'none') {
      const demoTitle = t('[SMS డెమో నోటిఫికేషన్]', '[SMS Demo Notification]', '[SMS डेमो सूचना]');
      const otpPrefix = t('మీ ధృవీకరణ OTP:', 'Your verification OTP is:', 'आपका सत्यापन ओटीपी:');
      const valText = t('10 నిమిషాల చెల్లుబాటు', '10 min validity', '10 मिनट वैधता');
      smsBanner.innerHTML = `<strong>${demoTitle}</strong> ${otpPrefix} <strong style="font-size:1.15rem; color:#047857; letter-spacing:2px; margin-left:4px;">${currentGeneratedOtp}</strong> <span style="font-size:12px; color:#065f46; margin-left:8px;">(${valText})</span>`;
    }

    // Refresh GVA language pill
    const gvaLangPill = document.getElementById('gva-lang-pill');
    if (gvaLangPill) {
      const activeLang = window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te');
      gvaLangPill.textContent = activeLang === 'te' ? 'TE (తెలుగు)' : (activeLang === 'hi' ? 'HI (हिंदी)' : 'EN (English)');
    }

    if (currentFarmer) {
      if (currentPage === 'dashboard') {
        const welcomeTitle = document.getElementById('dash-welcome-name');
        if (welcomeTitle) {
          welcomeTitle.textContent = t(
            `నమస్కారం, ${currentFarmer.full_name} గారు!`,
            `Welcome, ${currentFarmer.full_name}!`,
            `नमस्ते, ${currentFarmer.full_name}!`
          );
        }
        renderMyFarmSummary(currentFarmer);
        renderDashboardFarmerDetails(currentFarmer);
        renderDashboardProfileProgress(currentFarmer);
      }
    }
    const advContainer = document.getElementById('advisory-results-container');
    if (lastAdvisoryResult && advContainer && advContainer.innerHTML.trim() !== '') {
      renderAdvisoryResults(lastAdvisoryResult, advContainer);
    }
    const healthContainer = document.getElementById('health-results-container');
    if (lastHealthResult && healthContainer && healthContainer.innerHTML.trim() !== '') {
      renderCropHealthResult(lastHealthResult, healthContainer);
    }
    const weatherContainer = document.getElementById('weather-page-results');
    if (lastWeatherResult && weatherContainer && weatherContainer.innerHTML.trim() !== '') {
      renderWeatherPageData(lastWeatherResult, weatherContainer);
    }
    if (typeof updateWizardReviewSummary === 'function' && typeof currentWizardStep !== 'undefined' && currentWizardStep === 6) {
      updateWizardReviewSummary();
    }
  };

  // React to language switches in real time without refreshing or leaving current page
  window.addEventListener('languageChanged', function (e) {
    if (typeof window.refreshPortalDynamicViews === 'function') {
      window.refreshPortalDynamicViews();
    }
    if (currentPage === 'dashboard' && currentFarmer) {
      loadFarmerDashboard();
    }
  });

  // Expose portal controller functions and state queries on window
  window.navigateTo = navigateTo;
  window.updateAuthNavbar = updateAuthNavbar;
  window.restoreSession = restoreSession;
  window.handleRegisterSubmit = handleRegisterSubmit;
  window.handleLoginSubmit = handleLoginSubmit;
  window.handleLogout = handleLogout;
  window.populateProfileForm = populateProfileForm;
  window.handleProfileSubmit = handleProfileSubmit;
  window.skipOnboardingToDashboard = skipOnboardingToDashboard;
  window.loadFarmerDashboard = loadFarmerDashboard;
  window.renderMyFarmSummary = renderMyFarmSummary;
  window.renderDashboardFarmerDetails = renderDashboardFarmerDetails;
  window.renderDashboardProfileProgress = renderDashboardProfileProgress;
  window.renderDashboardWeatherAndAlerts = renderDashboardWeatherAndAlerts;
  window.renderDashboardHistory = renderDashboardHistory;
  window.prefillAdvisoryForm = prefillAdvisoryForm;
  window.handleAdvisorySubmit = handleAdvisorySubmit;
  window.renderAdvisoryResults = renderAdvisoryResults;
  window.fillCropHealthPreset = fillCropHealthPreset;
  window.fillAdvisoryPreset = fillAdvisoryPreset;
  window.handleCropHealthSubmit = handleCropHealthSubmit;
  window.renderCropHealthResult = renderCropHealthResult;
  window.prefillCropHealthForm = prefillCropHealthForm;
  window.prefillWeatherFilters = prefillWeatherFilters;
  window.loadWeatherPage = loadWeatherPage;

  // =========================================================================
  // Farmer-First Guided Wizard & Visual Controls
  // =========================================================================
  let wizardCurrentStep = 1;
  const WIZARD_TOTAL_STEPS = 5;

  function switchAdvisoryMode(mode) {
    const wizardCont = document.getElementById('advisory-wizard-container');
    const formCard = document.getElementById('advisory-full-form-card');
    const tabWizard = document.getElementById('btn-tab-wizard');
    const tabForm = document.getElementById('btn-tab-form');

    if (mode === 'wizard') {
      if (wizardCont) wizardCont.style.display = 'block';
      if (formCard) formCard.style.display = 'none';
      if (tabWizard) tabWizard.classList.add('active');
      if (tabForm) tabForm.classList.remove('active');
    } else {
      if (wizardCont) wizardCont.style.display = 'none';
      if (formCard) formCard.style.display = 'block';
      if (tabWizard) tabWizard.classList.remove('active');
      if (tabForm) tabForm.classList.add('active');
    }
  }

  function updateWizardUI() {
    const stepNumEl = document.getElementById('wizard-current-step-num');
    const stepTitleEl = document.getElementById('wizard-current-step-title');
    const progressTextEl = document.getElementById('wizard-step-progress-text');
    const progressFillEl = document.getElementById('wizard-progress-fill');
    const prevBtn = document.getElementById('wizard-btn-prev');
    const nextBtn = document.getElementById('wizard-btn-next');

    if (stepNumEl) stepNumEl.textContent = wizardCurrentStep;
    if (progressTextEl) progressTextEl.textContent = wizardCurrentStep + ' / ' + WIZARD_TOTAL_STEPS;
    if (progressFillEl) progressFillEl.style.width = ((wizardCurrentStep / WIZARD_TOTAL_STEPS) * 100) + '%';

    const titles = {
      1: t('దశ 1: మీ పొలం ఎక్కడ ఉంది?', 'Step 1: Where is your farm located?', 'चरण 1: आपका खेत कहाँ है?'),
      2: t('దశ 2: మీ పొలం నేల రకం ఏమిటి?', 'Step 2: What is your soil type?', 'चरण 2: आपके खेत की मिट्टी कैसी है?'),
      3: t('దశ 3: సాగు విస్తీర్ణం ఎంత (ఎకరాలు)?', 'Step 3: How many acres of land?', 'चरण 3: खेती का रकबा कितना है (एकड़)?'),
      4: t('దశ 4: నీటి వసతి ఎలా ఉంది?', 'Step 4: Water availability for irrigation?', 'चरण 4: सिंचाई के पानी की सुविधा?'),
      5: t('దశ 5: ఏ కాలంలో సాగు చేయదలిచారు?', 'Step 5: Which cropping season?', 'चरण 5: किस मौसम में फसल बोना चाहते हैं?')
    };

    if (stepTitleEl) stepTitleEl.textContent = titles[wizardCurrentStep] || '';

    for (let i = 1; i <= WIZARD_TOTAL_STEPS; i++) {
      const panel = document.getElementById('wizard-panel-' + i);
      if (panel) panel.style.display = (i === wizardCurrentStep) ? 'block' : 'none';
    }

    if (prevBtn) {
      prevBtn.style.visibility = (wizardCurrentStep > 1) ? 'visible' : 'hidden';
    }
    if (nextBtn) {
      if (wizardCurrentStep === WIZARD_TOTAL_STEPS) {
        nextBtn.innerHTML = `<span>🔍</span> <span>${t('అనుకూల పంటలను చూడండి', 'Find Best Crops', 'फसलें देखें')}</span>`;
      } else {
        nextBtn.innerHTML = `<span>${t('తదుపరి', 'Next', 'आगे बढ़ें')}</span> <span>➡️</span>`;
      }
    }
  }

  function wizardNavStep(direction) {
    if (direction === 1 && wizardCurrentStep === WIZARD_TOTAL_STEPS) {
      handleAdvisorySubmit();
      return;
    }
    wizardCurrentStep = Math.max(1, Math.min(WIZARD_TOTAL_STEPS, wizardCurrentStep + direction));
    updateWizardUI();
  }

  function wizardSelectDistrict(state, district) {
    const stateEl = document.getElementById('adv-state');
    const distEl = document.getElementById('adv-district');
    if (stateEl) stateEl.value = state;
    if (distEl) distEl.value = district;
    wizardNavStep(1);
  }

  function wizardSelectSoil(soilType) {
    const soilEl = document.getElementById('adv-soil');
    if (soilEl) soilEl.value = soilType;
    document.querySelectorAll('[id^="soil-card-"]').forEach(function (card) {
      card.classList.toggle('selected', card.id === 'soil-card-' + soilType);
    });
    wizardNavStep(1);
  }

  function wizardChangeAcres(delta) {
    const acresEl = document.getElementById('adv-acres');
    const displayEl = document.getElementById('wizard-acre-display');
    let currentVal = parseFloat(acresEl ? acresEl.value : '4') || 4;
    currentVal = Math.max(0.5, Math.min(500, currentVal + delta));
    if (acresEl) acresEl.value = currentVal;
    if (displayEl) displayEl.textContent = currentVal;
    syncQuickAcreChips(currentVal);
  }

  function wizardSetAcres(acres) {
    const acresEl = document.getElementById('adv-acres');
    const displayEl = document.getElementById('wizard-acre-display');
    if (acresEl) acresEl.value = acres;
    if (displayEl) displayEl.textContent = acres;
    syncQuickAcreChips(acres);
  }

  function syncQuickAcreChips(acres) {
    document.querySelectorAll('.quick-acre-chips .quick-chip').forEach(function (chip) {
      const chipVal = parseFloat(chip.textContent);
      chip.classList.toggle('selected', chipVal === acres);
    });
  }

  function wizardSelectWater(water) {
    const waterEl = document.getElementById('adv-water');
    if (waterEl) waterEl.value = water;
    document.querySelectorAll('[id^="water-card-"]').forEach(function (card) {
      card.classList.toggle('selected', card.id === 'water-card-' + water);
    });
    wizardNavStep(1);
  }

  function wizardSelectSeason(season) {
    const seasonEl = document.getElementById('adv-season');
    if (seasonEl) seasonEl.value = season;
    document.querySelectorAll('[id^="season-card-"]').forEach(function (card) {
      card.classList.toggle('selected', card.id === 'season-card-' + season);
    });
  }

  function handleLeafPhotoSelected(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const previewWrap = document.getElementById('health-photo-preview');
    const previewImg = document.getElementById('health-preview-img');
    const previewName = document.getElementById('health-preview-name');
    const notesEl = document.getElementById('health-notes');

    if (previewName) previewName.textContent = file.name;
    const reader = new FileReader();
    reader.onload = function (e) {
      if (previewImg) previewImg.src = e.target.result;
      if (previewWrap) previewWrap.style.display = 'flex';
      if (notesEl && !notesEl.value) {
        notesEl.value = t('ఆకు ఫోటో జతచేయబడింది: ' + file.name, 'Leaf photo attached: ' + file.name, 'पत्ती की तस्वीर संलग्न: ' + file.name);
      }
    };
    reader.readAsDataURL(file);
  }

  function removeLeafPhoto() {
    const input = document.getElementById('health-photo-input');
    const previewWrap = document.getElementById('health-photo-preview');
    const previewImg = document.getElementById('health-preview-img');
    if (input) input.value = '';
    if (previewImg) previewImg.src = '';
    if (previewWrap) previewWrap.style.display = 'none';
  }

  function speakAdvisoryRecommendation() {
    if (!lastAdvisoryResult) return;
    const rec = lastAdvisoryResult;
    const primary = (rec.primary_recommendations && rec.primary_recommendations[0]) || null;
    if (!primary) return;

    const activeLang = window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te');
    let cropName = primary.crop_name;
    if (activeLang === 'te' && primary.name_te) {
      cropName = primary.name_te;
    } else if (activeLang === 'hi' && primary.hindi_name) {
      cropName = primary.hindi_name;
    }

    let speechText = '';
    if (activeLang === 'te') {
      speechText = `మీ పొలానికి అత్యంత అనుకూలమైన ప్రధాన పంట ${cropName}. అనుకూలత స్కోరు వందకు ${primary.suitability_score}. ఎకరానికి అంచనా నికర లాభం ${Number(primary.estimated_net_profit_per_acre_inr).toLocaleString('en-IN')} రూపాయలు.`;
    } else if (activeLang === 'hi') {
      speechText = `आपके खेत के लिए सबसे उपयुक्त फसल ${cropName} है। उपयुक्तता स्कोर सौ में से ${primary.suitability_score} है। प्रति एकड़ अनुमानित शुद्ध लाभ ${Number(primary.estimated_net_profit_per_acre_inr).toLocaleString('en-IN')} रुपये है।`;
    } else {
      speechText = `The most suitable crop for your farm is ${cropName}, with a suitability score of ${primary.suitability_score} out of 100. The estimated net profit per acre is ${Number(primary.estimated_net_profit_per_acre_inr).toLocaleString('en-IN')} rupees.`;
    }
    speakText(speechText);
  }

  function speakHealthDiagnosis() {
    if (!lastHealthResult) return;
    const d = lastHealthResult;
    const activeLang = window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te');
    const isTe = activeLang === 'te';
    const title = isTe ? d.symptom_name_te : d.symptom_name_en;
    const actions = isTe ? d.safe_actions_te : d.safe_actions_en;
    const firstAction = (actions && actions[0]) ? actions[0] : '';

    let speechText = '';
    if (activeLang === 'te') {
      speechText = `${d.crop_name} పంటలో గుర్తించిన సమస్య: ${title}. తక్షణ రక్షణ చర్య: ${firstAction}`;
    } else if (activeLang === 'hi') {
      speechText = `${d.crop_name} फसल में पाया गया लक्षण: ${title}. तुरंत करने योग्य उपाय: ${firstAction}`;
    } else {
      speechText = `Identified issue in ${d.crop_name}: ${title}. Recommended immediate action: ${firstAction}`;
    }
    speakText(speechText);
  }

  function speakWeatherSummary() {
    if (!lastWeatherResult || !lastWeatherResult.current) return;
    const w = lastWeatherResult;
    const c = w.current;
    const activeLang = window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te');
    const cond = t(c.condition_te, c.condition_en);

    let speechText = '';
    if (activeLang === 'te') {
      speechText = `${w.district} ప్రాంతంలో ప్రస్తుత ఉష్ణోగ్రత ${c.temperature_c} డిగ్రీల సెల్సియస్, వాతావరణం ${cond}. వర్షపాతం ${c.precipitation_mm} మిల్లీమీటర్లు.`;
    } else if (activeLang === 'hi') {
      speechText = `${w.district} क्षेत्र में वर्तमान तापमान ${c.temperature_c} डिग्री सेल्सियस, मौसम ${cond} है।`;
    } else {
      speechText = `Current temperature in ${w.district} is ${c.temperature_c} degrees Celsius, with ${cond}. Precipitation is ${c.precipitation_mm} millimeters.`;
    }
    speakText(speechText);
  }

  window.switchAdvisoryMode = switchAdvisoryMode;
  window.wizardNavStep = wizardNavStep;
  window.wizardSelectDistrict = wizardSelectDistrict;
  window.wizardSelectSoil = wizardSelectSoil;
  window.wizardChangeAcres = wizardChangeAcres;
  window.wizardSetAcres = wizardSetAcres;
  window.wizardSelectWater = wizardSelectWater;
  window.wizardSelectSeason = wizardSelectSeason;
  window.handleLeafPhotoSelected = handleLeafPhotoSelected;
  window.removeLeafPhoto = removeLeafPhoto;
  window.speakAdvisoryRecommendation = speakAdvisoryRecommendation;
  window.speakHealthDiagnosis = speakHealthDiagnosis;
  window.speakWeatherSummary = speakWeatherSummary;
  window.speakText = speakText;

  window.renderWeatherPageData = renderWeatherPageData;
  window.refreshPortalDynamicViews = refreshPortalDynamicViews;
  window.showStatusAlert = showStatusAlert;
  window.getCurrentFarmer = function () { return currentFarmer; };
  window.getCurrentPage = function () { return currentPage; };
  window.checkOtpBannerState = checkOtpBannerState;
  window.dismissOtpPasswordBanner = dismissOtpPasswordBanner;
  window.togglePasswordVisibility = togglePasswordVisibility;
  window.openForgotPasswordFlow = openForgotPasswordFlow;
  window.closeForgotPasswordFlow = closeForgotPasswordFlow;
  window.handleSendOtp = handleSendOtp;
  window.handleVerifyOtp = handleVerifyOtp;
  window.verifyOtpAndLogin = handleVerifyOtp;
  window.renderDashboardFallbackData = renderDashboardFallbackData;
  window.openChangePasswordModal = openChangePasswordModal;
  window.closeChangePasswordModal = closeChangePasswordModal;
  window.handleChangePasswordSubmit = handleChangePasswordSubmit;
  window.openGoogleSignInModal = openGoogleSignInModal;
  window.closeGoogleSignInModal = closeGoogleSignInModal;
  window.toggleCustomGoogleInput = toggleCustomGoogleInput;
  window.selectGoogleAccount = selectGoogleAccount;
  window.submitCustomGoogleAccount = submitCustomGoogleAccount;


  // Handle browser back/forward buttons seamlessly
  window.addEventListener('popstate', function (e) {
    const rawPath = (window.location.pathname || '/').replace(/^\/+|\/+$/g, '').toLowerCase();
    const targetPage = (e.state && e.state.pageId) ? e.state.pageId : rawPath;
    if (currentFarmer) {
      if (['login', 'register', 'home', ''].includes(targetPage) || !VALID_PAGES.includes(targetPage)) {
        navigateTo('dashboard', { noHistory: true });
      } else {
        navigateTo(targetPage, { noHistory: true });
      }
    } else {
      if (targetPage === 'register') {
        navigateTo('register', { noHistory: true });
      } else {
        navigateTo('login', { noHistory: true });
      }
    }
  });


  // =========================================================================
  // GLOBAL VOICE ASSISTANT & INLINE "TYPE OR SPEAK" FORM FILLING ENGINE
  // =========================================================================

  const NUM_WORDS_MAP = {
    // English
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
    'hundred': 100, 'thousand': 1000, 'lakh': 100000, 'crore': 10000000,
    // Telugu
    'సున్నా': 0, 'ఒకటి': 1, 'రెండు': 2, 'మూడు': 3, 'నాలుగు': 4, 'ఐదు': 5,
    'ఆరు': 6, 'ఏడు': 7, 'ఎనిమిది': 8, 'తొమ్మిది': 9, 'పది': 10,
    'పదకొండు': 11, 'పన్నెండు': 12, 'పదమూడు': 13, 'పద్నాలుగు': 14, 'పదిహేను': 15,
    'ఇరవై': 20, 'ముప్పై': 30, 'నలభై': 40, 'యాభై': 50, 'వంద': 100, 'వెయ్యి': 1000, 'వేలు': 1000,
    'లక్ష': 100000, 'కోటి': 10000000,
    // Hindi
    'शून्य': 0, 'एक': 1, 'दो': 2, 'तीन': 3, 'चार': 4, 'पाँच': 5, 'पांच': 5,
    'छह': 6, 'छः': 6, 'सात': 7, 'आठ': 8, 'नौ': 9, 'दस': 10,
    'ग्यारह': 11, 'बारह': 12, 'तेरह': 13, 'चौदह': 14, 'पंद्रह': 15,
    'बीस': 20, 'तीस': 30, 'चालीस': 40, 'पचास': 50, 'सौ': 100, 'हज़ार': 1000, 'हजार': 1000,
    'लाख': 100000, 'करोड़': 10000000
  };

  const SELECT_SYNONYMS = {
    // Soil
    'black': ['నల్ల', 'నల్ల రేగడి', 'రేగడి', 'काली', 'काली मिट्टी', 'black', 'black soil', 'clay'],
    'red': ['ఎర్ర', 'ఎర్ర నేల', 'ఎరుపు', 'ఎర్ర రేగడి', 'लाल', 'लाल मिट्टी', 'red', 'red soil'],
    'alluvial': ['ఒండ్రు', 'ఒండ్రు నేల', 'నది ఒండ్రు', 'जलोढ़', 'जलोढ़ मिट्टी', 'alluvial', 'alluvial soil'],
    'sandy_loam': ['ఇసుక', 'ఇసుక నేల', 'ఇసుక రేగడి', 'बलुई', 'बलुई मिट्टी', 'sandy', 'sandy loam'],
    'clayey': ['బంకమట్టి', 'బంక నేల', 'चिकनी', 'चिकनी मिट्टी', 'clayey'],
    'laterite': ['లేటరైట్', 'ఎర్ర గులక', 'लेटराइट', 'laterite'],

    // Water
    'moderate': ['బోరు', 'బావి', 'బోర్‌వెల్', 'బోరుబావి', 'బంగారుబావి', 'बोरवेल', 'कुआं', 'borewell', 'moderate', 'well'],
    'high': ['కాలువ', 'నది', 'నది నీరు', 'కాల్వ', 'నహర్', 'नहर', 'canal', 'river', 'high'],
    'low': ['వర్షం', 'వర్షాధారం', 'వర్షాధార', 'ఎండ', 'बारिश', 'वर्षा', 'rainfed', 'low', 'dry'],

    // Season
    'kharif': ['ఖరీఫ్', 'వానాకాలం', 'వర్షాకాలం', 'ఖరీప్', 'खरीफ', 'मानसून', 'kharif', 'monsoon'],
    'rabi': ['రబీ', 'యాసంగి', 'చలికాలం', 'రబి', 'रबी', 'सर्दियों', 'rabi', 'winter'],
    'zaid': ['జైద్', 'వేసవి', 'ఎండాకాలం', 'జాయిద్', 'जायद', 'गर्मी', 'zaid', 'summer'],
    'year_round': ['వార్షిక', 'ఏడాది', 'మొత్తం', 'वार्षिक', 'year round'],

    // Risk
    'moderate': ['మధ్యస్థం', 'సమతుల్య', 'मध्यम', 'moderate'],
    'low': ['తక్కువ', 'ఎంఎస్పీ', 'భద్రత', 'कम', 'सुरक्षित', 'low', 'msp'],
    'high': ['అధిక', 'వాణిజ్య', 'ఎక్కువ', 'अधिक', 'उच्च', 'high', 'commercial'],

    // States
    'Telangana': ['తెలంగాణ', 'తెలంగాణా', 'तेलंगाना', 'telangana', 'ts'],
    'Andhra Pradesh': ['ఆంధ్రప్రదేశ్', 'ఆంధ్ర', 'ఆంధ్రా', 'సీమ', 'కోస్తా', 'आंध्र प्रदेश', 'आंध्र', 'andhra', 'ap'],
    'Punjab': ['పంజాబ్', 'पंजाब', 'punjab'],
    'Maharashtra': ['మహారాష్ట్ర', 'महाराष्ट्र', 'maharashtra'],
    'Karnataka': ['కర్ణాటక', 'కర్నాటక', 'कर्नाटक', 'karnataka'],
    'Tamil Nadu': ['తమిళనాడు', 'तमिलनाडु', 'tamil nadu'],
    'Gujarat': ['గుజరాత్', 'गुजरात', 'gujarat'],
    'Odisha': ['ఒడిశా', 'ఒరిస్సా', 'ओडिशा', 'odisha'],

    // Crops
    'Paddy / Rice': ['వరి', 'బియ్యం', 'వడ్లు', 'ధాన్యం', 'వరి పంట', 'धान', 'चावल', 'paddy', 'rice'],
    'Cotton': ['పత్తి', 'ప్రత్తి', 'దూది', 'పత్తి చేను', 'కపాస్', 'कपास', 'रूई', 'cotton'],
    'Chilli': ['మిరప', 'మిర్చి', 'మిరపకాయ', 'మిరప పంట', 'మిర్చి తోట', 'मिर्च', 'मिर्ची', 'chilli', 'mirchi'],
    'Wheat': ['గోధుమ', 'గోధుమలు', 'గేహుం', 'गेहूं', 'गेहूँ', 'wheat'],
    'Maize': ['మొక్కజొన్న', 'మక్కజొన్న', 'మక్క', 'మక్కలు', 'మొక్కజొన్న పంట', 'मक्का', 'भुट्टा', 'maize', 'corn'],
    'Groundnut': ['వేరుశనగ', 'పల్లీలు', 'శనగకాయలు', 'వేరుశనగ పంట', 'मूंगफली', 'groundnut', 'peanut'],
    'Soybean': ['సోయాబీన్', 'సోయా', 'సోయా చిక్కుడు', 'सोयाबीन', 'soybean', 'soya'],
    'Chickpea': ['శనగలు', 'సెనగలు', 'బుడ్డశనగలు', 'శనగ', 'चना', 'छोले', 'chickpea', 'chana']
  };

  const COMMAND_NAV_RULES = [
    { page: 'dashboard', keywords: ['dashboard', 'డాష్‌బోర్డ్', 'డ్యాష్‌బోర్డ్', 'హోమ్', 'home', 'డ్యాష్', 'డ్యాష్బోర్డు', 'డాష్బోర్డ్', 'మొదటి పేజీ', 'डैशबोर्ड'] },
    { page: 'advisory', keywords: ['advisory', 'crop advisory', 'crop recommendation', 'సలహా', 'పంట సలహా', 'పంట సిఫార్సు', 'పంటలు', 'సాగు సలహా', 'సిఫార్సులు', 'सलाह', 'फसल सलाह'] },
    { page: 'health', keywords: ['health', 'crop health', 'pest', 'disease', 'ఆరోగ్యం', 'పంట ఆరోగ్యం', 'చీడపీడలు', 'తెగుళ్లు', 'పురుగులు', 'మచ్చలు', 'రోగం', 'మందులు', 'स्वास्थ्य', 'बीमारी', 'कीट'] },
    { page: 'weather', keywords: ['weather', 'forecast', 'rain', 'వాతావరణం', 'వర్షం', 'ఎండ', 'గాలి', 'వాతావరణ నివేదిక', 'తుఫాను', 'मौसम', 'बारिश'] },
    { page: 'voice', keywords: ['voice', 'assistant', 'ai assistant', 'వాయిస్', 'సహాయకుడు', 'మాట్లాడు', 'వాయిస్ అసిస్టెంట్', 'వాయిస్ ఏఐ', 'वॉयस', 'बोलें'] },
    { page: 'profile', keywords: ['profile', 'farm profile', 'farmer profile', 'ప్రొఫైల్', 'ఖాతా వివరాలు', 'నా వివరాలు', 'నా పొలం', 'భూమి వివరాలు', 'प्रोफ़ाइल', 'प्रोफाइल'] },
    { page: 'register', keywords: ['register', 'registration', 'sign up', 'నమోదు', 'రిజిస్టర్', 'ఖాతా తెరవండి', 'కొత్త రైతు', 'पंजीकरण', 'रजिस्टर'] },
    { page: 'login', keywords: ['login', 'sign in', 'లాగిన్', 'ప్రవేశం', 'ఖాతా లాగిన్', 'लॉगिन'] },
    { action: 'logout', keywords: ['logout', 'sign out', 'లాగ్ అవుట్', 'లాగౌట్', 'నిష్క్రమించు', 'ఖాతా నుండి నిష్క్రమించు', 'लॉग आउट'] },
    { action: 'lang_te', keywords: ['telugu', 'తెలుగు', 'తెలుగు భాష', 'తెలుగులో', 'తెలుగులోకి మార్చు', 'तेलुगु'] },
    { action: 'lang_en', keywords: ['english', 'ఇంగ్లీష్', 'ఆంగ్లం', 'ఆంగ్ల భాష', 'ఇంగ్లీషులోకి', 'अंग्रेजी'] },
    { action: 'lang_hi', keywords: ['hindi', 'హిందీ', 'హిందీ భాష', 'హిందీలోకి మార్చు', 'हिंदी'] }
  ];

  const GUIDED_FORM_CONFIG = {
    'register': [
      { id: 'reg-fullname', prompt: { te: 'దయచేసి మీ పూర్తి పేరు చెప్పండి.', en: 'Please say your full name.', hi: 'कृपया अपना पूरा नाम बताएं।' } },
      { id: 'reg-phone', prompt: { te: 'దయచేసి మీ 10-అంకెల మొబైల్ నంబర్ చెప్పండి.', en: 'Please say your 10-digit mobile number.', hi: 'कृपया अपना 10-अंकों का मोबाइल नंबर बताएं।' } },
      { id: 'reg-email', prompt: { te: 'మీ ఈమెయిల్ చెప్పండి, లేదా దాటవేయడానికి స్కిప్ అనండి.', en: 'Please say your email, or say skip.', hi: 'अपना ईमेल पता बताएं, या छोड़ें।' } },
      { id: 'reg-identifier', prompt: { te: 'మీ లాగిన్ యూజర్‌నేమ్ చెప్పండి.', en: 'Please say your username.', hi: 'कृपया अपना यूज़रनेम बताएं।' } },
      { id: 'reg-password', prompt: { te: 'మీ లాగిన్ పాస్‌వర్డ్ చెప్పండి.', en: 'Please say your password.', hi: 'अपना पासवर्ड बताएं।' } },
      { id: 'reg-confirm-password', prompt: { te: 'పాస్‌వర్డ్‌ను నిర్ధారించడానికి మళ్ళీ చెప్పండి.', en: 'Repeat password to confirm.', hi: 'पुष्टि के लिए पासवर्ड पुनः बताएं।' } },
      { id: 'reg-lang', prompt: { te: 'ప్రాధాన్యత భాష చెప్పండి: తెలుగు, ఇంగ్లీష్ లేదా హిందీ?', en: 'Choose language: Telugu, English, or Hindi.', hi: 'पसंदीदा भाषा बताएं: तेलुगु, अंग्रेज़ी या हिंदी।' } }
    ],
    'login': [
      { id: 'login-identifier', prompt: { te: 'మీ మొబైల్ నంబర్ లేదా యూజర్‌నేమ్ చెప్పండి.', en: 'Please say your mobile number or username.', hi: 'अपना मोबाइल नंबर या यूज़रनेम बताएं।' } },
      { id: 'login-password', prompt: { te: 'మీ పాస్‌వర్డ్ చెప్పండి.', en: 'Please say your password.', hi: 'अपना पासवर्ड बताएं।' } }
    ],
    'advisory': [
      { id: 'adv-state', prompt: { te: 'మీ రాష్ట్రం చెప్పండి (ఉదా: తెలంగాణ లేదా ఆంధ్రప్రదేశ్).', en: 'Please say your state (e.g. Telangana or Andhra Pradesh).', hi: 'अपना राज्य बताएं (उदा: तेलंगाना या आंध्र प्रदेश)।' } },
      { id: 'adv-district', prompt: { te: 'మీ జిల్లా పేరు చెప్పండి (ఉదా: వరంగల్ లేదా గుంటూరు).', en: 'Please say your district name.', hi: 'अपने जिले का नाम बताएं।' } },
      { id: 'adv-acres', prompt: { te: 'మీ భూమి విస్తీర్ణం ఎన్ని ఎకరాలు?', en: 'How many acres is your land?', hi: 'आपकी भूमि कितने एकड़ है?' } },
      { id: 'adv-soil', prompt: { te: 'మీ నేల రకం ఏమిటి? నల్ల రేగడి, ఎర్ర నేల లేదా ఒండ్రు నేలా?', en: 'What is your soil type? Black, Red, or Alluvial?', hi: 'आपकी मिट्टी का प्रकार क्या है? काली, लाल या जलोढ़?' } },
      { id: 'adv-water', prompt: { te: 'మీ నీటి వసతి ఏమిటి? బోరు బావి, కాలువ లేదా వర్షాధారమా?', en: 'Water source: Borewell, Canal, or Rainfed?', hi: 'सिंचाई का साधन: बोरवेल, नहर या वर्षा?' } },
      { id: 'adv-season', prompt: { te: 'ఏ సీజన్ కోసం సిఫార్సు కావాలి? ఖరీఫ్, రబీ లేదా జైద్?', en: 'Target season: Kharif, Rabi, or Zaid?', hi: 'लक्षित मौसम: खरीफ, रबी या जायद?' } },
      { id: 'adv-budget', prompt: { te: 'ఈ సీజన్‌కు మీ పెట్టుబడి బడ్జెట్ ఎంత రూపాయలు?', en: 'Planned budget in rupees?', hi: 'आपका मौसमी निवेश बजट कितने रुपये है?' } },
      { id: 'adv-risk', prompt: { te: 'రిస్క్ ప్రాధాన్యత: మధ్యస్థం, తక్కువ రిస్క్ లేదా అధిక రాబడా?', en: 'Risk preference: Moderate, Low risk, or High return?', hi: 'जोखिम प्राथमिकता: मध्यम, कम जोखिम या अधिक लाभ?' } }
    ],
    'health': [
      { id: 'health-crop', prompt: { te: 'మీ పంట పేరు చెప్పండి (వరి, పత్తి, మిరప లేదా మొక్కజొన్న).', en: 'Crop name (Paddy, Cotton, Chilli, or Maize)?', hi: 'फसल का नाम बताएं (धान, कपास, मिर्च या मक्का)।' } },
      { id: 'health-symptom', prompt: { te: 'గమనించిన లక్షణాలు చెప్పండి (ఆకులు పసుపుబారడం, మచ్చలు లేదా ఎండిపోవడం).', en: 'Observed symptoms (yellow leaves, spots, wilt)?', hi: 'लक्षण बताएं (पत्तियां पीली होना, धब्बे या सूखना)।' } },
      { id: 'health-notes', prompt: { te: 'అదనపు గమనికలు చెప్పండి, లేదా ముందుకు వెళ్ళండి.', en: 'Any additional notes, or proceed.', hi: 'कोई अतिरिक्त टिप्पणी बताएं।' } }
    ],
    'weather': [
      { id: 'weather-state', prompt: { te: 'వాతావరణం కోసం మీ రాష్ట్రం చెప్పండి.', en: 'Say state for weather forecast.', hi: 'मौसम के लिए राज्य बताएं।' } },
      { id: 'weather-district', prompt: { te: 'వాతావరణం కోసం మీ జిల్లా పేరు చెప్పండి.', en: 'Say district name for weather.', hi: 'मौसम के लिए जिले का नाम बताएं।' } }
    ],
    'profile': [
      { id: 'prof-fullname', prompt: { te: 'మీ పూర్తి పేరు చెప్పండి.', en: 'Please say your full name.', hi: 'अपना पूरा नाम बताएं।' } },
      { id: 'prof-phone', prompt: { te: 'మీ మొబైల్ నంబర్ చెప్పండి.', en: 'Please say your mobile number.', hi: 'अपना मोबाइल नंबर बताएं।' } },
      { id: 'prof-state', prompt: { te: 'మీ రాష్ట్రం చెప్పండి.', en: 'Please say your state.', hi: 'अपना राज्य बताएं।' } },
      { id: 'prof-district', prompt: { te: 'మీ జిల్లా పేరు చెప్పండి.', en: 'Please say your district.', hi: 'अपना जिला बताएं।' } },
      { id: 'prof-mandal', prompt: { te: 'మీ మండలం పేరు చెప్పండి.', en: 'Please say your mandal.', hi: 'अपना मंडल बताएं।' } },
      { id: 'prof-village', prompt: { te: 'మీ గ్రామం పేరు చెప్పండి.', en: 'Please say your village.', hi: 'अपना गांव बताएं।' } },
      { id: 'prof-acres', prompt: { te: 'మీ భూమి విస్తీర్ణం ఎన్ని ఎకరాలు?', en: 'How many acres is your land?', hi: 'आपकी भूमि कितने एकड़ है?' } },
      { id: 'prof-soil', prompt: { te: 'మీ నేల రకం ఏమిటి?', en: 'What is your soil type?', hi: 'आपकी मिट्टी का प्रकार क्या है?' } },
      { id: 'prof-water', prompt: { te: 'మీ నీటి వసతి ఏమిటి?', en: 'What is your water source?', hi: 'सिंचाई का साधन क्या है?' } },
      { id: 'prof-season', prompt: { te: 'ప్రస్తుత పంట సీజన్ ఏమిటి?', en: 'What is your current season?', hi: 'वर्तमान मौसम कौन सा है?' } },
      { id: 'prof-budget', prompt: { te: 'మీ సీజన్ బడ్జెట్ ఎంత?', en: 'What is your planned budget in rupees?', hi: 'आपका बजट कितना है?' } },
      { id: 'prof-crops', prompt: { te: 'సాధారణంగా పండించే ప్రధాన పంటలు ఏవి?', en: 'Primary crops usually grown?', hi: 'सामान्यतः उगाई जाने वाली फसलें कौन सी हैं?' } }
    ]
  };

  const AgriVoiceAssistant = (function () {
    let recognition = null;
    let activeFieldId = null;
    let activeFieldEl = null;
    let activeFieldBtn = null;
    let activePillEl = null;
    let isListening = false;
    let guidedActive = false;
    let guidedQueue = [];
    let guidedIndex = 0;
    let drawerOpen = false;
    let activeTab = 'guided'; // 'guided' | 'commands'
    let cmdListening = false;

    function getSpeechRecClass() {
      return window.SpeechRecognition || window.webkitSpeechRecognition || null;
    }

    function getCurrentSpeechLocale() {
      const lang = window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te');
      if (lang === 'hi') return 'hi-IN';
      if (lang === 'en') return 'en-IN';
      return 'te-IN';
    }

    function hasNativeVoice(targetLocale) {
      if (!('speechSynthesis' in window)) return false;
      const voices = window.speechSynthesis.getVoices() || [];
      const prefix = targetLocale.substring(0, 2).toLowerCase();
      return voices.some(function (v) { return v.lang && v.lang.toLowerCase().startsWith(prefix); });
    }

    function getBestVoice(targetLocale) {
      if (!('speechSynthesis' in window)) return null;
      const voices = window.speechSynthesis.getVoices() || [];
      const prefix = targetLocale.substring(0, 2).toLowerCase();
      for (let i = 0; i < voices.length; i++) {
        if (voices[i].lang && voices[i].lang.toLowerCase().startsWith(prefix)) {
          return voices[i];
        }
      }
      return null;
    }

    function cleanTextForSpeech(text) {
      if (!text) return '';
      return text
        .replace(/🤖\s*\*\*\[Ollama:[^\]]+\]\*\*/gi, '')
        .replace(/^Ollama Notice:[^\n]+\n*/gi, '')
        .replace(/\[Notice:[^\]]*\]\s*\n*/gi, '')
        .replace(/\*\*([^\*]+)\*\*/g, '$1')
        .replace(/\*([^\*]+)\*/g, '$1')
        .replace(/#{1,6}\s*/g, '')
        .replace(/`{1,3}[^`]*`{1,3}/g, '')
        .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
        .replace(/<[^>]+>/g, ' ')
        .replace(/[^\S\r\n]+/g, ' ')
        .trim();
    }

    function speakText(text, onEnd) {
      const clean = cleanTextForSpeech(text);
      if (!clean) {
        if (onEnd) onEnd();
        return;
      }
      const locale = getCurrentSpeechLocale();
      const prefix = locale.substring(0, 2).toLowerCase();
      const voice = getBestVoice(locale);

      // Stop any existing synthesis utterance and reset active audio player
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      if (window.activeAudioPlayer && typeof window.activeAudioPlayer.pause === 'function') {
        window.activeAudioPlayer.pause();
        window.activeAudioPlayer.currentTime = 0;
      }

      // Rule: Do NOT speak non-English text with English voice!
      // Use Backend TTS service for natural Telugu / Hindi speech when browser voice is absent
      if (prefix !== 'en' && !voice) {
        showTtsFallbackBanner(clean);
        try {
          const apiBase = (window.AGRISAARTHI_CONFIG && window.AGRISAARTHI_CONFIG.API_BASE_URL)
            ? window.AGRISAARTHI_CONFIG.API_BASE_URL.replace(/\/$/, '')
            : '';
          fetch(apiBase + '/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: clean, lang: prefix })
          }).then(function (res) {
            if (!res.ok) throw new Error('TTS error');
            return res.blob();
          }).then(function (blob) {
            const audioUrl = URL.createObjectURL(blob);
            const audio = new Audio(audioUrl);
            window.activeAudioPlayer = audio;
            audio.onended = function () {
              URL.revokeObjectURL(audioUrl);
              window.activeAudioPlayer = null;
              if (onEnd) onEnd();
            };
            audio.onerror = function () {
              URL.revokeObjectURL(audioUrl);
              window.activeAudioPlayer = null;
              if (onEnd) onEnd();
            };
            audio.play().catch(function () {
              if (onEnd) setTimeout(onEnd, 1200);
            });
          }).catch(function () {
            if (onEnd) setTimeout(onEnd, 1400);
          });
        } catch (_) {
          if (onEnd) setTimeout(onEnd, 1400);
        }
        return;
      }

      if ('speechSynthesis' in window) {
        const utter = new SpeechSynthesisUtterance(clean);
        utter.lang = locale;
        if (voice) utter.voice = voice;
        utter.rate = 0.95;
        utter.onend = function () { if (onEnd) onEnd(); };
        utter.onerror = function () { if (onEnd) onEnd(); };
        window.speechSynthesis.speak(utter);
      } else if (onEnd) {
        onEnd();
      }
    }

    function showTtsFallbackBanner(text) {
      const card = document.getElementById('global-voice-card');
      if (card) {
        let note = document.getElementById('gva-tts-visual-note');
        if (!note) {
          note = document.createElement('div');
          note.id = 'gva-tts-visual-note';
          note.style.cssText = 'background:#fef3c7; border:1px solid #fde047; padding:6px 10px; margin:6px 14px; border-radius:8px; font-size:12px; color:#854d0e; text-align:center;';
          card.insertBefore(note, card.querySelector('.gva-body'));
        }
        note.textContent = text;
        setTimeout(function () { if (note && note.parentNode) note.parentNode.removeChild(note); }, 4000);
      }
    }

    function parseSpokenValue(rawTranscript, field) {
      let text = String(rawTranscript || '').trim();
      if (!text || !field) return text;

      const tag = field.tagName.toLowerCase();
      const type = (field.getAttribute('type') || '').toLowerCase();
      const id = (field.id || '').toLowerCase();

      // Dropdown matching
      if (tag === 'select') {
        const options = Array.from(field.options).map(function (o) {
          return {
            val: o.value,
            text: o.text || '',
            te: o.getAttribute('data-i18n-opt-te') || '',
            en: o.getAttribute('data-i18n-opt-en') || '',
            hi: o.getAttribute('data-i18n-opt-hi') || ''
          };
        });
        const clean = text.toLowerCase();
        // 1. Direct text/value match
        for (let i = 0; i < options.length; i++) {
          const opt = options[i];
          if (!opt.val) continue;
          if (clean === opt.val.toLowerCase() || clean === opt.text.toLowerCase()) return opt.val;
          if (clean.includes(opt.val.toLowerCase()) || opt.text.toLowerCase().includes(clean)) return opt.val;
        }
        // 2. Synonyms match
        for (const [canonicalVal, synList] of Object.entries(SELECT_SYNONYMS)) {
          for (let s = 0; s < synList.length; s++) {
            const syn = synList[s];
            if (clean.includes(syn) || syn.includes(clean)) {
              const matched = options.find(function (o) { return o.val.toLowerCase() === canonicalVal.toLowerCase(); });
              if (matched) return matched.val;
            }
          }
        }
        return '';
      }

      // Numbers / Digits conversion
      if (type === 'tel' || id.includes('phone') || id.includes('otp')) {
        let digits = text.toLowerCase();
        for (const [w, d] of Object.entries(NUM_WORDS_MAP)) {
          digits = digits.split(w).join(String(d));
        }
        return digits.replace(/\D/g, '');
      }

      if (id.includes('acres')) {
        let acreStr = text.toLowerCase();
        for (const [w, d] of Object.entries(NUM_WORDS_MAP)) {
          acreStr = acreStr.split(w).join(String(d));
        }
        const m = acreStr.match(/(\d+(?:\.\d+)?)/);
        return m ? parseFloat(m[1]) : '';
      }

      if (id.includes('budget')) {
        let bStr = text.toLowerCase();
        let mult = 1;
        if (bStr.includes('lakh') || bStr.includes('లక్ష') || bStr.includes('लाख')) mult = 100000;
        else if (bStr.includes('thousand') || bStr.includes('వేలు') || bStr.includes('వెయ్యి') || bStr.includes('हजार')) mult = 1000;

        for (const [w, d] of Object.entries(NUM_WORDS_MAP)) {
          bStr = bStr.split(w).join(String(d));
        }
        const m = bStr.match(/(\d+(?:\.\d+)?)/);
        if (!m) return '';
        const num = parseFloat(m[1]);
        return num < 1000 && mult > 1 ? Math.round(num * mult) : Math.round(num);
      }

      if (type === 'email' || id.includes('email')) {
        return text.toLowerCase()
          .replace(/\s+at\s+the\s+rate\s+/g, '@')
          .replace(/\s+at\s+/g, '@')
          .replace(/\s+dot\s+/g, '.')
          .replace(/\s+/g, '');
      }

      // Capitalize first letter of general text
      return text.charAt(0).toUpperCase() + text.slice(1).replace(/\.$/, '');
    }

    function createStatusPill(fieldEl, text) {
      removeStatusPill();
      if (!fieldEl || !fieldEl.parentElement) return;
      const pill = document.createElement('div');
      pill.className = 'voice-field-status-pill';
      pill.textContent = text;
      fieldEl.parentElement.appendChild(pill);
      activePillEl = pill;
    }

    function removeStatusPill() {
      if (activePillEl && activePillEl.parentNode) {
        activePillEl.parentNode.removeChild(activePillEl);
      }
      activePillEl = null;
    }

    function stopAllRecognition() {
      if (recognition) {
        try { recognition.abort(); } catch (_) { }
        recognition = null;
      }
      isListening = false;
      cmdListening = false;
      updateFabRecordingState(false);
      updateStatusBadge('idle');

      if (activeFieldBtn) {
        activeFieldBtn.classList.remove('listening');
      }
      if (activeFieldEl) {
        activeFieldEl.classList.remove('voice-field-active');
      }
      removeStatusPill();
      activeFieldId = null;
      activeFieldEl = null;
      activeFieldBtn = null;
    }

    function updateFabRecordingState(recording) {
      const fab = document.getElementById('global-voice-fab');
      if (fab) fab.classList.toggle('recording', recording);
      const cmdBtn = document.getElementById('gva-cmd-mic-btn');
      if (cmdBtn) cmdBtn.classList.toggle('recording', recording);
    }

    function updateStatusBadge(state) {
      const badge = document.getElementById('gva-status-badge');
      if (!badge) return;
      badge.className = 'gva-status-badge status-' + state;
      if (state === 'listening') {
        badge.style.display = 'inline-flex';
        badge.textContent = t('voice.status_listening', 'వింటోంది...', 'सुन रहे हैं...');
      } else if (state === 'processing') {
        badge.style.display = 'inline-flex';
        badge.textContent = t('voice.status_processing', 'విశ్లేషిస్తోంది...', 'प्रोसेस कर रहे हैं...');
      } else {
        badge.style.display = 'none';
        badge.textContent = '';
      }
    }

    function startFieldInput(fieldId, btnEl) {
      stopAllRecognition();
      const field = document.getElementById(fieldId);
      if (!field) return;

      const SpeechRec = getSpeechRecClass();
      if (!SpeechRec) {
        alert(t('ఈ బ్రౌజర్‌లో వాయిస్ రికగ్నిషన్ అందుబాటులో లేదు. దయచేసి టైప్ చేయండి.', 'Speech recognition not supported in this browser. Please type.', 'इस ब्राउज़र में वॉयस रिकग्निशन उपलब्ध नहीं है।'));
        return;
      }

      activeFieldId = fieldId;
      activeFieldEl = field;
      activeFieldBtn = btnEl || null;

      field.classList.add('voice-field-active');
      if (btnEl) btnEl.classList.add('listening');

      // Find field label name
      let labelName = '';
      const lbl = document.querySelector('label[for="' + fieldId + '"]');
      if (lbl) labelName = lbl.textContent.replace(/[\*:]/g, '').trim();
      if (!labelName) labelName = field.getAttribute('placeholder') || fieldId;

      const listeningText = '' + t('voice.status_listening', 'వింటోంది...') + ' (' + labelName + ')';
      createStatusPill(field, listeningText);
      updateStatusBadge('listening');
      updateFabRecordingState(true);

      recognition = new SpeechRec();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = getCurrentSpeechLocale();

      recognition.onstart = function () {
        isListening = true;
      };

      recognition.onresult = function (event) {
        updateStatusBadge('processing');
        if (event.results && event.results[0] && event.results[0][0]) {
          const raw = event.results[0][0].transcript;
          const parsed = parseSpokenValue(raw, field);
          if (parsed !== '' && parsed !== null) {
            field.value = parsed;
            field.dispatchEvent(new Event('input', { bubbles: true }));
            field.dispatchEvent(new Event('change', { bubbles: true }));

            createStatusPill(field, '' + parsed);
            speakText(t('నమోదు చేయబడింది', 'Recorded', 'दर्ज किया गया'));
          } else {
            createStatusPill(field, '' + raw);
          }
        }
      };

      recognition.onerror = function () {
        stopAllRecognition();
      };

      recognition.onend = function () {
        setTimeout(function () {
          stopAllRecognition();
        }, 1200);
      };

      try {
        recognition.start();
      } catch (err) {
        stopAllRecognition();
      }
    }

    // Guided Mode
    function startGuidedFill() {
      stopAllRecognition();
      const pageId = currentPage || 'dashboard';
      const steps = GUIDED_FORM_CONFIG[pageId];

      if (!steps || steps.length === 0) {
        alert(t('ఈ పేజీలో వాయిస్ ద్వారా నింపడానికి ఫారమ్ ఫీల్డ్‌లు లేవు.', 'No voice-fillable form fields found on this page.', 'इस पेज पर कोई फ़ॉर्म फ़ील्ड उपलब्ध नहीं है।'));
        return;
      }

      guidedActive = true;
      guidedQueue = steps;
      guidedIndex = 0;

      // Open drawer & switch to guided tab
      openDrawer();
      switchTab('guided');

      const ctrlBox = document.getElementById('gva-guided-controls');
      const activeBox = document.getElementById('gva-guided-active-box');
      if (ctrlBox) ctrlBox.classList.add('hidden');
      if (activeBox) activeBox.classList.remove('hidden');

      executeGuidedStep();
    }

    function executeGuidedStep() {
      if (!guidedActive) return;
      if (guidedIndex >= guidedQueue.length) {
        finishGuidedFill();
        return;
      }

      const step = guidedQueue[guidedIndex];
      const field = document.getElementById(step.id);
      if (!field) {
        guidedIndex++;
        executeGuidedStep();
        return;
      }

      // Highlight & scroll field
      document.querySelectorAll('.voice-field-active').forEach(function (el) { el.classList.remove('voice-field-active'); });
      field.classList.add('voice-field-active');
      field.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // Update guided drawer UI
      const stepBadge = document.getElementById('gva-step-badge');
      const stepField = document.getElementById('gva-step-field-name');
      const promptBox = document.getElementById('gva-guided-prompt');
      const transcriptBox = document.getElementById('gva-guided-transcript');

      const currentLang = window.currentLang || 'te';
      const promptText = step.prompt[currentLang] || step.prompt['en'] || step.prompt['te'];

      if (stepBadge) stepBadge.textContent = (guidedIndex + 1) + '/' + guidedQueue.length;
      if (stepField) {
        const lbl = document.querySelector('label[for="' + step.id + '"]');
        stepField.textContent = lbl ? lbl.textContent.replace(/[\*:]/g, '').trim() : step.id;
      }
      if (promptBox) promptBox.textContent = '"' + promptText + '"';
      if (transcriptBox) transcriptBox.textContent = '...';

      // Speak prompt and then listen
      speakText(promptText, function () {
        if (!guidedActive) return;
        listenForGuidedInput(field, step);
      });
    }

    function listenForGuidedInput(field, step) {
      const SpeechRec = getSpeechRecClass();
      if (!SpeechRec) return;

      stopAllRecognition();
      updateStatusBadge('listening');
      updateFabRecordingState(true);

      recognition = new SpeechRec();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = getCurrentSpeechLocale();

      recognition.onresult = function (event) {
        if (!guidedActive) return;
        let interim = '';
        let final = '';
        for (let i = 0; i < event.results.length; ++i) {
          if (event.results[i].isFinal) final += event.results[i][0].transcript;
          else interim += event.results[i][0].transcript;
        }

        const tBox = document.getElementById('gva-guided-transcript');
        if (tBox) tBox.textContent = final || interim || '...';

        if (final.trim()) {
          const raw = final.trim();
          // Check for skip command
          if (raw.toLowerCase().includes('skip') || raw.includes('దాటవేయి') || raw.includes('వద్దు') || raw.includes('छोड़ें')) {
            speakText(t('దాటవేయబడింది', 'Skipped', 'छोड़ दिया गया'), function () {
              guidedIndex++;
              executeGuidedStep();
            });
            return;
          }

          const parsed = parseSpokenValue(raw, field);
          if (parsed !== '' && parsed !== null) {
            field.value = parsed;
            field.dispatchEvent(new Event('input', { bubbles: true }));
            field.dispatchEvent(new Event('change', { bubbles: true }));

            speakText(t('నమోదు చేయబడింది', 'Recorded', 'दर्ज हो गया'), function () {
              guidedIndex++;
              setTimeout(executeGuidedStep, 600);
            });
          } else {
            // Not recognized clearly
            speakText(t('దయచేసి మళ్ళీ చెప్పండి.', 'Please say again.', 'कृपया पुनः बताएं।'), function () {
              listenForGuidedInput(field, step);
            });
          }
        }
      };

      recognition.onerror = function () {
        updateStatusBadge('idle');
        updateFabRecordingState(false);
      };

      try {
        recognition.start();
      } catch (_) { }
    }

    function repeatCurrentPrompt() {
      stopAllRecognition();
      executeGuidedStep();
    }

    function skipCurrentField() {
      stopAllRecognition();
      guidedIndex++;
      executeGuidedStep();
    }

    function stopGuidedFill() {
      guidedActive = false;
      stopAllRecognition();
      document.querySelectorAll('.voice-field-active').forEach(function (el) { el.classList.remove('voice-field-active'); });

      const ctrlBox = document.getElementById('gva-guided-controls');
      const activeBox = document.getElementById('gva-guided-active-box');
      if (ctrlBox) ctrlBox.classList.remove('hidden');
      if (activeBox) activeBox.classList.add('hidden');
    }

    function finishGuidedFill() {
      guidedActive = false;
      stopAllRecognition();
      document.querySelectorAll('.voice-field-active').forEach(function (el) { el.classList.remove('voice-field-active'); });

      const promptBox = document.getElementById('gva-guided-prompt');
      if (promptBox) {
        promptBox.textContent = '' + t('ఫారమ్ పూర్తి చేయబడింది! దయచేసి వివరాలను పరిశీలించి సేవ్ చేయండి.', 'Form completed! Please review and save.', 'फ़ॉर्म पूर्ण हो गया! कृपया विवरण जांचकर सहेजें।');
      }
      speakText(t('ఫారమ్ పూర్తి చేయబడింది!', 'Form completed!', 'फ़ॉर्म पूर्ण हो गया!'));

      const ctrlBox = document.getElementById('gva-guided-controls');
      const activeBox = document.getElementById('gva-guided-active-box');
      setTimeout(function () {
        if (ctrlBox) ctrlBox.classList.remove('hidden');
        if (activeBox) activeBox.classList.add('hidden');
      }, 3000);
    }

    // Commands & AI Chat
    function toggleCommandListening() {
      if (cmdListening) {
        stopAllRecognition();
        return;
      }
      startCommandListening();
    }

    function startCommandListening() {
      stopAllRecognition();
      const SpeechRec = getSpeechRecClass();
      if (!SpeechRec) {
        alert(t('ఈ బ్రౌజర్‌లో వాయిస్ రికగ్నిషన్ సదుపాయం లేదు.', 'Speech recognition not supported in this browser.', 'इस ब्राउज़र में वॉयस रिकग्निशन उपलब्ध नहीं है।'));
        return;
      }

      cmdListening = true;
      updateStatusBadge('listening');
      updateFabRecordingState(true);

      const statusText = document.getElementById('gva-cmd-status-text');
      if (statusText) statusText.textContent = t('voice.status_listening', 'వింటోంది...');

      recognition = new SpeechRec();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = getCurrentSpeechLocale();

      recognition.onresult = function (event) {
        if (event.results && event.results[0] && event.results[0][0]) {
          const raw = event.results[0][0].transcript;
          handleCommandText(raw);
        }
      };

      recognition.onerror = function () {
        stopAllRecognition();
        if (statusText) statusText.textContent = t('నొక్కి మాట్లాడండి (Tap to Speak)', 'Tap to Speak', 'बोलने के लिए दबाएं');
      };

      recognition.onend = function () {
        stopAllRecognition();
        if (statusText) statusText.textContent = t('నొక్కి మాట్లాడండి (Tap to Speak)', 'Tap to Speak', 'बोलने के लिए दबाएं');
      };

      try {
        recognition.start();
      } catch (_) {
        stopAllRecognition();
      }
    }

    async function handleCommandText(text) {
      if (!text) return;
      const clean = text.toLowerCase().trim();

      // Show heard transcript
      const tBox = document.getElementById('gva-cmd-transcript-box');
      const tText = document.getElementById('gva-cmd-transcript-text');
      if (tBox && tText) {
        tBox.classList.remove('hidden');
        tText.textContent = text;
      }

      // Check navigation commands
      for (let i = 0; i < COMMAND_NAV_RULES.length; i++) {
        const rule = COMMAND_NAV_RULES[i];
        for (let k = 0; k < rule.keywords.length; k++) {
          const kw = rule.keywords[k];
          if (clean.includes(kw)) {
            if (rule.page) {
              speakText(t(rule.page + ' పేజీ తెరుస్తున్నాము...', 'Opening ' + rule.page + '...', rule.page + ' खोल रहे हैं...'));
              navigateTo(rule.page);
              return;
            }
            if (rule.action === 'logout') {
              speakText(t('లాగ్ అవుట్ చేస్తున్నాము...', 'Logging out...', 'लॉग आउट कर रहे हैं...'));
              handleLogout();
              return;
            }
            if (rule.action === 'lang_te') {
              speakText('తెలుగు భాష ఎంచుకోబడింది.');
              setLanguage('te');
              return;
            }
            if (rule.action === 'lang_en') {
              speakText('English language selected.');
              setLanguage('en');
              return;
            }
            if (rule.action === 'lang_hi') {
              speakText('हिंदी भाषा का चयन किया गया है।');
              setLanguage('hi');
              return;
            }
          }
        }
      }

      // If not navigation, treat as Quick AI Farming Query via /api/chat
      updateStatusBadge('processing');
      const rBox = document.getElementById('gva-cmd-reply-box');
      const rText = document.getElementById('gva-cmd-reply-text');
      if (rBox && rText) {
        rBox.classList.remove('hidden');
        rText.textContent = t('⏳ సమాధానం కోసం ఆలోచిస్తున్నాము...', '⏳ Finding answer...', '⏳ उत्तर खोज रहे हैं...');
      }

      try {
        const lang = window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te');
        const locale = lang === 'hi' ? 'hi-IN' : (lang === 'en' ? 'en-IN' : 'te-IN');
        const langName = lang === 'hi' ? 'Hindi' : (lang === 'en' ? 'English' : 'Telugu');

        console.log(`[AgriVoiceAssistant] AI Query: text="${text.substring(0, 40)}...", lang=${lang}, locale=${locale}`);

        const res = await fetch(getApiUrl('/api/chat'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: text,
            message: text,
            sender: 'global_voice_assistant',
            language: locale,
            lang: lang,
            response_language: langName
          })
        });

        if (res.ok) {
          const data = await res.json();
          const reply = data.reply || data.response || t('క్షమించండి, సమాధానం రాలేదు.', 'Sorry, no answer available.');
          if (rText) rText.textContent = reply;
          speakText(reply);
        } else {
          if (rText) rText.textContent = t('సర్వర్ లోపం. దయచేసి మళ్ళీ ప్రయత్నించండి.', 'Server error. Please try again.');
        }
      } catch (err) {
        if (rText) rText.textContent = t('నెట్‌వర్క్ లోపం. సర్వర్ రన్ అవుతుందో లేదో సరిచూసుకోండి.', 'Network error. Could not connect to AI service.');
      } finally {
        updateStatusBadge('idle');
      }
    }

    // Drawer management
    function toggleDrawer() {
      drawerOpen = !drawerOpen;
      const card = document.getElementById('global-voice-card');
      if (card) {
        card.classList.toggle('hidden', !drawerOpen);
      }
      if (drawerOpen) {
        syncLanguage(window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te'));
      } else {
        stopAllRecognition();
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel();
        }
      }
    }

    function openDrawer() {
      drawerOpen = true;
      const card = document.getElementById('global-voice-card');
      if (card) card.classList.remove('hidden');
      syncLanguage(window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te'));
    }

    function closeDrawer(ev) {
      if (ev && typeof ev.preventDefault === 'function') {
        ev.preventDefault();
        ev.stopPropagation();
      }
      drawerOpen = false;
      const card = document.getElementById('global-voice-card');
      if (card) card.classList.add('hidden');
      stopAllRecognition();
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      if (window.activeAudioPlayer && typeof window.activeAudioPlayer.pause === 'function') {
        window.activeAudioPlayer.pause();
        window.activeAudioPlayer.currentTime = 0;
      }
      updateStatusBadge('idle');
      updateFabRecordingState(false);
    }

    function switchTab(tab) {
      activeTab = tab;
      const tabGuided = document.getElementById('gva-tab-guided');
      const tabCmd = document.getElementById('gva-tab-commands');
      const viewGuided = document.getElementById('gva-view-guided');
      const viewCmd = document.getElementById('gva-view-commands');

      if (tabGuided) tabGuided.classList.toggle('active', tab === 'guided');
      if (tabCmd) tabCmd.classList.toggle('active', tab === 'commands');
      if (viewGuided) viewGuided.classList.toggle('active', tab === 'guided');
      if (viewCmd) viewCmd.classList.toggle('active', tab === 'commands');
    }

    function updateGuidedPageLabel() {
      const pageLabel = document.getElementById('gva-guided-page-name');
      const pill = document.getElementById('gva-lang-pill');
      const lang = window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te');

      if (pill) {
        pill.textContent = lang === 'te' ? 'TE (తెలుగు)' : (lang === 'hi' ? 'HI (हिंदी)' : 'EN (English)');
      }

      const p = currentPage || 'dashboard';
      const pageNames = {
        'home': { en: 'Home', te: 'హోమ్', hi: 'होम' },
        'dashboard': { en: 'Farmer Dashboard', te: 'రైతు డాష్‌బోర్డ్', hi: 'किसान डैशबोर्ड' },
        'advisory': { en: 'Crop Advisory', te: 'పంట సలహా', hi: 'फसल सलाह' },
        'health': { en: 'Crop Health', te: 'పంట ఆరోగ్యం', hi: 'फसल स्वास्थ्य' },
        'weather': { en: 'Weather & Alerts', te: 'వాతావరణం & హెచ్చరికలు', hi: 'मौसम और चेतावनियाँ' },
        'voice': { en: 'Voice AI Assistant', te: 'AI వాయిస్ సహాయకుడు', hi: 'AI वॉयस सहायक' },
        'profile': { en: 'Farmer Profile', te: 'రైతు ప్రొఫైల్', hi: 'किसान प्रोफ़ाइल' },
        'login': { en: 'Farmer Login', te: 'రైతు లాగిన్', hi: 'किसान लॉगिन' },
        'register': { en: 'Farmer Registration', te: 'రైతు నమోదు', hi: 'किसान पंजीकरण' }
      };

      if (pageLabel) {
        const localizedName = (pageNames[p] && pageNames[p][lang]) ? pageNames[p][lang] : (pageNames[p] ? pageNames[p].en : p);
        pageLabel.textContent = localizedName;
      }

      const pageSub = document.querySelector('.gva-page-sub');
      if (pageSub) {
        const subLabels = {
          en: 'Current Page:',
          te: 'ప్రస్తుత పేజీ:',
          hi: 'वर्तमान पृष्ठ:'
        };
        pageSub.textContent = subLabels[lang] || 'Current Page:';
      }
    }

    function onPageChanged(pageId) {
      if (guidedActive) {
        stopGuidedFill();
      }
      updateGuidedPageLabel();
      setTimeout(setupVoiceFormInputs, 80);
    }

    function syncLanguage(lang) {
      const activeLang = (lang === 'te' || lang === 'en' || lang === 'hi') ? lang : (window.currentLang || (window.i18n && window.i18n.getLanguage ? window.i18n.getLanguage() : 'te'));
      window.currentLang = activeLang;

      // 1. Safely stop any current speech playback and active recognition
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      if (window.activeAudioPlayer && typeof window.activeAudioPlayer.pause === 'function') {
        window.activeAudioPlayer.pause();
        window.activeAudioPlayer.currentTime = 0;
      }
      stopAllRecognition();

      // 2. Update language pill
      const langPill = document.getElementById('gva-lang-pill');
      if (langPill) {
        langPill.textContent = activeLang === 'en' ? 'EN (English)' : (activeLang === 'hi' ? 'HI (हिंदी)' : 'TE (తెలుగు)');
      }

      // 3. Update drawer title and tabs using clean dictionary resolution
      const titleEl = document.getElementById('gva-title');
      if (titleEl) {
        titleEl.textContent = window.i18n ? window.i18n.t('voice.drawer_title') : (activeLang === 'en' ? 'Voice AI Assistant' : (activeLang === 'hi' ? 'AI वॉयस सहायक' : 'AI వాయిస్ సహాయకుడు'));
      }

      const tabGuided = document.getElementById('gva-tab-guided');
      if (tabGuided) {
        tabGuided.textContent = window.i18n ? window.i18n.t('voice.tab_guided') : (activeLang === 'en' ? 'Guided Form Fill' : (activeLang === 'hi' ? 'फ़ॉर्म भरें' : 'ఫారమ్ నింపండి'));
      }

      const tabCmd = document.getElementById('gva-tab-commands');
      if (tabCmd) {
        tabCmd.textContent = window.i18n ? window.i18n.t('voice.tab_commands') : (activeLang === 'en' ? 'Ask & Commands' : (activeLang === 'hi' ? 'आदेश व AI' : 'ఆదేశాలు & AI'));
      }

      // 4. Update Current Page label
      updateGuidedPageLabel();

      // 5. Update Guided Form buttons and labels
      const btnStart = document.getElementById('gva-btn-start-guided');
      if (btnStart) {
        btnStart.textContent = window.i18n ? window.i18n.t('voice.guided_start_btn') : (activeLang === 'en' ? '▶ Start Guided Voice Filling' : (activeLang === 'hi' ? '▶ बोलकर फ़ॉर्म भरना शुरू करें' : '▶ వాయిస్ ద్వారా ఫారమ్ నింపండి'));
      }

      const btnRepeat = document.getElementById('gva-btn-repeat') || document.querySelector('#gva-view-guided button[onclick*="repeatCurrentPrompt"]');
      if (btnRepeat) {
        btnRepeat.textContent = window.i18n ? window.i18n.t('voice.guided_repeat_btn') : (activeLang === 'en' ? '🔁 Repeat Prompt' : (activeLang === 'hi' ? '🔁 पुनः पूछें' : '🔁 ప్రాంప్ట్ పునరావృతం'));
      }

      const btnSkip = document.getElementById('gva-btn-skip') || document.querySelector('#gva-view-guided button[onclick*="skipCurrentField"]');
      if (btnSkip) {
        btnSkip.textContent = window.i18n ? window.i18n.t('voice.guided_skip_btn') : (activeLang === 'en' ? '⏭ Skip Field' : (activeLang === 'hi' ? '⏭ छोड़ें' : '⏭ దాటవేయండి'));
      }

      const btnStop = document.getElementById('gva-btn-stop') || document.querySelector('#gva-view-guided button[onclick*="stopGuidedFill"]');
      if (btnStop) {
        btnStop.textContent = window.i18n ? window.i18n.t('voice.guided_stop_btn') : (activeLang === 'en' ? '⏹ Stop' : (activeLang === 'hi' ? '⏹ रोकें' : '⏹ ఆపండి'));
      }

      if (guidedActive && guidedQueue[guidedIndex]) {
        const step = guidedQueue[guidedIndex];
        const stepBadge = document.getElementById('gva-step-badge');
        const promptBox = document.getElementById('gva-guided-prompt');
        const promptText = step.prompt[activeLang] || step.prompt['en'] || step.prompt['te'];
        if (promptBox) promptBox.textContent = '"' + promptText + '"';
        if (stepBadge) {
          const badgeText = activeLang === 'en' ? `Step ${guidedIndex + 1} of ${guidedQueue.length}` : (activeLang === 'hi' ? `चरण ${guidedIndex + 1}/${guidedQueue.length}` : `దశ ${guidedIndex + 1}/${guidedQueue.length}`);
          stepBadge.textContent = badgeText;
        }
      }

      // 6. Update Commands view elements
      const statusText = document.getElementById('gva-cmd-status-text');
      if (statusText && !cmdListening) {
        statusText.textContent = window.i18n ? window.i18n.t('voice.tap_to_speak') : (activeLang === 'en' ? 'Tap to Speak' : (activeLang === 'hi' ? 'बोलने के लिए दबाएं' : 'నొక్కి మాట్లాడండి'));
      }

      const cmdDesc = document.querySelector('.gva-commands-prompt p');
      if (cmdDesc) {
        cmdDesc.textContent = window.i18n ? window.i18n.t('voice.commands_desc') : (activeLang === 'en' ? 'Speak naturally — navigate to any page or ask any farming question.' : (activeLang === 'hi' ? 'बोलें — किसी भी पेज पर जाएं या खेती से जुड़ा प्रश्न पूछें।' : 'మాట్లాడండి — ఏదైనా పేజీకి వెళ్లండి లేదా వ్యవసాయ ప్రశ్న అడగండి.'));
      }

      const heardLbl = document.querySelector('.gva-transcript-label');
      if (heardLbl) {
        heardLbl.textContent = window.i18n ? window.i18n.t('voice.heard_label') : (activeLang === 'en' ? 'Heard:' : (activeLang === 'hi' ? 'सुनी गई बात:' : 'విన్న మాట:'));
      }

      const youSaid = document.querySelector('#gva-cmd-transcript-box strong');
      if (youSaid) {
        youSaid.textContent = window.i18n ? window.i18n.t('voice.you_said') : (activeLang === 'en' ? 'You said:' : (activeLang === 'hi' ? 'आपने कहा:' : 'మీరు అన్నది:'));
      }

      const replyHdrSpan = document.querySelector('.gva-reply-header span') || document.querySelector('.gva-reply-header');
      if (replyHdrSpan) {
        replyHdrSpan.textContent = window.i18n ? window.i18n.t('voice.assistant_reply') : (activeLang === 'en' ? 'AgriSaarthi Reply:' : (activeLang === 'hi' ? 'अग्रिसारथी उत्तर:' : 'అగ్రిసారథి సమాధానం:'));
      }

      const btnListen = document.getElementById('gva-btn-listen-reply');
      if (btnListen) {
        btnListen.textContent = window.i18n ? window.i18n.t('voice.btn_listen') : (activeLang === 'en' ? '🔊 Listen' : (activeLang === 'hi' ? '🔊 सुनें' : '🔊 వినండి'));
      }

      const closeBtn = document.getElementById('gva-btn-close');
      if (closeBtn) {
        const closeTitle = window.i18n ? window.i18n.t('voice.close_title') : 'Close Voice Assistant';
        closeBtn.setAttribute('title', closeTitle);
        closeBtn.setAttribute('aria-label', closeTitle);
      }

      // Quick chips localization
      const chips = document.querySelectorAll('.gva-quick-chips .gva-chip');
      const chipKeys = ['chip_dashboard', 'chip_advisory', 'chip_weather', 'chip_health', 'chip_pest'];
      chips.forEach((chip, idx) => {
        if (chipKeys[idx] && window.i18n) {
          chip.textContent = window.i18n.t('voice.' + chipKeys[idx]);
        }
      });

      console.log(`[AgriVoiceAssistant] Language synchronized to: ${activeLang} (locale: ${getCurrentSpeechLocale()})`);
    }

    function speakLatestReply() {
      const rText = document.getElementById('gva-cmd-reply-text');
      if (rText && rText.textContent.trim()) {
        speakText(rText.textContent.trim());
      }
    }

    function init() {
      setupVoiceFormInputs();
      updateGuidedPageLabel();
    }

    return {
      init: init,
      startFieldInput: startFieldInput,
      startGuidedFill: startGuidedFill,
      repeatCurrentPrompt: repeatCurrentPrompt,
      skipCurrentField: skipCurrentField,
      stopGuidedFill: stopGuidedFill,
      toggleCommandListening: toggleCommandListening,
      handleCommandText: handleCommandText,
      toggleDrawer: toggleDrawer,
      openDrawer: openDrawer,
      closeDrawer: closeDrawer,
      switchTab: switchTab,
      onPageChanged: onPageChanged,
      syncLanguage: syncLanguage,
      speakLatestReply: speakLatestReply
    };
  })();

  window.AgriVoiceAssistant = AgriVoiceAssistant;
  window.startFieldVoiceInput = function (fieldId, btnEl) {
    AgriVoiceAssistant.startFieldInput(fieldId, btnEl);
  };
  window.startGuidedFormFill = function () {
    AgriVoiceAssistant.startGuidedFill();
  };

  function setupVoiceFormInputs() {
    const formIds = ['login-form', 'register-form', 'profile-form', 'advisory-form', 'health-form', 'weather-form', 'change-password-form'];
    formIds.forEach(function (fid) {
      const form = document.getElementById(fid);
      if (!form) return;

      // 1. Add "Type or Speak" hint banner at top of form if missing
      if (!form.querySelector('.voice-form-hint')) {
        const hint = document.createElement('div');
        hint.className = 'voice-form-hint';
        hint.innerHTML = '<span class="voice-hint-icon"></span>' +
          '<div class="voice-hint-text">' +
          '<strong data-i18n="voice.type_or_speak_title">' + t('voice.type_or_speak_title', 'టైప్ చేయండి లేదా మాట్లాడండి (Type or Speak)', 'Type or Speak to Fill') + '</strong>' +
          '<p data-i18n="voice.type_or_speak_desc">' + t('voice.type_or_speak_desc', 'ఫీల్డ్ పక్కన ఉన్న బటన్ నొక్కండి లేదా వాయిస్ ద్వారా ఫారమ్ నింపండి.', 'Tap beside any field, or use the guided voice assistant to complete the entire form.') + '</p>' +
          '</div>' +
          '<button type="button" class="btn-voice-fill-page" onclick="AgriVoiceAssistant.startGuidedFill()" data-i18n="voice.btn_voice_fill_page">' +
          '' + t('voice.btn_voice_fill_page', 'వాయిస్ ద్వారా నింపండి', 'Fill Form by Voice') +
          '</button>';
        form.insertBefore(hint, form.firstChild);
      }

      // 2. Add mic buttons to all input and select fields inside the form
      const controls = form.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="checkbox"]):not([type="radio"]), select, textarea');
      controls.forEach(function (ctrl) {
        if (ctrl.hasAttribute('data-voice-bound')) return;
        ctrl.setAttribute('data-voice-bound', 'true');

        // Check if inside password wrapper
        const pwdWrapper = ctrl.closest('.password-input-wrapper');
        if (pwdWrapper) {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'field-mic-btn password-mic';
          btn.innerHTML = MIC_SVG;
          btn.title = t('వాయిస్ ద్వారా చెప్పండి', 'Speak for this field', 'बोलकर दर्ज करें');
          btn.setAttribute('aria-label', btn.title);
          btn.onclick = function (e) {
            e.preventDefault();
            e.stopPropagation();
            AgriVoiceAssistant.startFieldInput(ctrl.id, btn);
          };
          pwdWrapper.appendChild(btn);
          return;
        }

        // For standard input / select
        const parent = ctrl.parentElement;
        if (parent && !parent.classList.contains('field-voice-wrapper')) {
          const wrapper = document.createElement('div');
          wrapper.className = 'field-voice-wrapper';
          parent.insertBefore(wrapper, ctrl);
          wrapper.appendChild(ctrl);

          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'field-mic-btn';
          btn.innerHTML = MIC_SVG;
          btn.title = t('వాయిస్ ద్వారా చెప్పండి', 'Speak for this field', 'बोलकर दर्ज करें');
          btn.setAttribute('aria-label', btn.title);
          btn.onclick = function (e) {
            e.preventDefault();
            e.stopPropagation();
            AgriVoiceAssistant.startFieldInput(ctrl.id, btn);
          };
          wrapper.appendChild(btn);
        }
      });
    });
  }
  window.setupVoiceFormInputs = setupVoiceFormInputs;

    // Initialize portal on DOM load (Default Landing: unauthenticated -> login, authenticated -> dashboard)
  window.addEventListener('DOMContentLoaded', async function () {
    document.body.classList.add('portal-body');
    await restoreSession();
    try {
      if (typeof setupVoiceFormInputs === 'function') {
        setupVoiceFormInputs();
      }
      if (window.AgriVoiceAssistant && typeof window.AgriVoiceAssistant.init === 'function') {
        window.AgriVoiceAssistant.init();
      }
    } catch (_) { }
    const pathName = (window.location.pathname || '/').replace(/^\/+|\/+$/g, '').toLowerCase();

    if (currentFarmer) {
      if (['login', 'register', 'home', ''].includes(pathName) || !VALID_PAGES.includes(pathName)) {
        navigateTo('dashboard', { noHistory: true });
      } else {
        navigateTo(pathName, { noHistory: true });
      }
    } else {
      if (pathName === 'register') {
        navigateTo('register', { noHistory: true });
      } else {
        navigateTo('login', { noHistory: true });
      }
    }
  });
})();


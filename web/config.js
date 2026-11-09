// Default Frontend Configuration for AgriSaarthi AI.
// When served via scripts/run_farmer_ui.py, /config.js is dynamically populated from .env settings.
window.AGRISAARTHI_CONFIG = window.AGRISAARTHI_CONFIG || {
  API_BASE_URL: "",
  ENVIRONMENT: "development",
  DEFAULT_LANG: "te",
  OLLAMA_MODEL: "qwen2.5:0.5b",
  ACP_VERSION: "0.3.0",
  WEATHER_CONFIGURED: true,
  IMD_ALERTS_CONFIGURED: false
};


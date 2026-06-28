const API = "http://localhost:8005/api/v1";

// ============================================
// СОСТОЯНИЕ ПРИЛОЖЕНИЯ
// ============================================
let currentView = "dashboard";
let currentTripId = null;
let tripsData = [];

// ============================================
// ПЕРЕКЛЮЧЕНИЕ РЕЖИМОВ
// ============================================
function switchView(viewName) {
  console.log(`🔄 Switching to: ${viewName}`);

  // Скрываем все виды
  document
    .querySelectorAll(".view")
    .forEach((v) => v.classList.remove("active"));

  // Показываем нужный
  const viewEl = document.getElementById(`${viewName}-view`);
  if (viewEl) {
    viewEl.classList.add("active");
    currentView = viewName;

    // Инициализация при переключении
    if (viewName === "dashboard") {
      initDashboard();
    } else if (viewName === "map") {
      initMapFull();
    } else if (viewName === "trips") {
      loadTripsTable();
    } else if (viewName === "trip-detail" && currentTripId) {
      loadTripDetail(currentTripId);
    }
  }
}

// ============================================
// УТИЛИТЫ
// ============================================
function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ============================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================
document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 App initialized");

  // Инициализация дашборда
  initDashboard();

  // Приветствие
  greet();

  // ✅ Инициализация модуля речи ДЛЯ ЧАТА (всегда виден)
  SpeechModule.init("btn-mic-chat", "address-chat");

  // Слушаем статусы
  window.addEventListener("speech:status", (e) => {
    addMsg(e.detail.message, "bot");
  });

  // ✅ Слушаем финальные результаты
  window.addEventListener("speech:result", (e) => {
    const { text, isAddress } = e.detail;

    if (isAddress) {
      // Это адрес — переключаемся на карту и ищем
      addMsg(`📍 Ищу: ${text}`, "user");
      switchView("map");
      setTimeout(() => {
        document.getElementById("address").value = text;
        document.getElementById("btn-search").click();
      }, 300);
    } else {
      // Это чат — отправляем в LLM
      document.getElementById("address-chat").value = "";
      sendToChat(text);
    }
  });
});

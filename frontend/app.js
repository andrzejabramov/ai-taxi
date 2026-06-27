const API = "http://localhost:8005/api/v1";

// ===== Карта =====
const map = L.map("map").setView([55.751244, 37.618423], 12);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap contributors",
}).addTo(map);

let userMarker = null;
let endMarker = null;
let routeLine = null;
let endPoint = null;

// Геолокация
if ("geolocation" in navigator) {
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      map.setView([latitude, longitude], 15);
      userMarker = L.marker([latitude, longitude])
        .addTo(map)
        .bindPopup("Вы здесь")
        .openPopup();
    },
    () => console.warn("Геолокация недоступна"),
  );
}

// Клик по карте
map.on("click", (e) => {
  setEndPoint(e.latlng.lat, e.latlng.lng);
});

function setEndPoint(lat, lon) {
  endPoint = { lat, lon };
  if (endMarker) map.removeLayer(endMarker);
  endMarker = L.marker([lat, lon], { draggable: true })
    .addTo(map)
    .bindPopup("Пункт назначения")
    .openPopup();

  endMarker.on("dragend", (ev) => {
    const p = ev.target.getLatLng();
    endPoint = { lat: p.lat, lon: p.lng };
  });

  document.getElementById("btn-order").disabled = false;
}

// ===== Чат =====
const chatEl = document.getElementById("chat");
const history = [];

function addMsg(text, who) {
  const div = document.createElement("div");
  div.className = `msg ${who}`;
  div.textContent = text;
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
}

async function greet() {
  try {
    const response = await fetch(`${API}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "привет", history: [] }),
    });
    const data = await response.json();
    addMsg(data.reply, "bot");
    history.push({ role: "assistant", content: data.reply });
  } catch (error) {
    console.error("Greeting failed:", error);
    addMsg("Здравствуйте! Куда поедем?", "bot");
  }
}
greet();

// Поиск адреса
document.getElementById("btn-search").onclick = async () => {
  const address = document.getElementById("address").value.trim();
  if (!address) return;

  addMsg(address, "user");
  history.push({ role: "user", content: address });

  try {
    const response = await fetch(`${API}/geo/geocode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address }),
    });
    const data = await response.json();

    setEndPoint(data.lat, data.lon);
    map.setView([data.lat, data.lon], 14);

    addMsg(`Нашёл: ${data.name}`, "bot");
  } catch (error) {
    console.error("Geocoding failed:", error);
    addMsg("Не удалось найти адрес", "bot");
  }
};

// Заказ поездки
document.getElementById("btn-order").onclick = async () => {
  if (!endPoint) return;

  const pos = userMarker ? userMarker.getLatLng() : map.getCenter();

  try {
    const response = await fetch(`${API}/trips/order`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "employee_1",
        start_lat: pos.lat,
        start_lon: pos.lng,
        end_lat: endPoint.lat,
        end_lon: endPoint.lon,
        end_address:
          document.getElementById("address").value || "Точка на карте",
      }),
    });
    const data = await response.json();

    if (routeLine) map.removeLayer(routeLine);
    routeLine = L.polyline(data.geometry, {
      color: "#2563eb",
      weight: 5,
    }).addTo(map);
    map.fitBounds(routeLine.getBounds());

    const km = (data.distance_m / 1000).toFixed(1);
    const min = Math.round(data.duration_s / 60);

    addMsg(
      `✅ Заказ #${data.trip_id} создан\n📏 ${km} км, ⏱ ${min} мин`,
      "bot",
    );
  } catch (error) {
    console.error("Order failed:", error);
    addMsg("Не удалось создать заказ", "bot");
  }
};

// ===== Распознавание речи =====
const micBtn = document.getElementById("btn-mic");
const addressInput = document.getElementById("address");

// Словарь числительных для нормализации
const numberWords = {
  ноль: "0",
  один: "1",
  одна: "1",
  два: "2",
  две: "2",
  три: "3",
  четыре: "4",
  пять: "5",
  шесть: "6",
  семь: "7",
  восемь: "8",
  девять: "9",
  десять: "10",
  одиннадцать: "11",
  двенадцать: "12",
  тринадцать: "13",
  четырнадцать: "14",
  пятнадцать: "15",
  шестнадцать: "16",
  семнадцать: "17",
  восемнадцать: "18",
  девятнадцать: "19",
  двадцать: "20",
  тридцать: "30",
  сорок: "40",
  пятьдесят: "50",
  шестьдесят: "60",
  семьдесят: "70",
  восемьдесят: "80",
  девяносто: "90",
  сто: "100",
};

function normalizeAddress(text) {
  let result = text;
  for (const [word, num] of Object.entries(numberWords)) {
    const regex = new RegExp(`\\b${word}\\b`, "gi");
    result = result.replace(regex, num);
  }
  result = result
    .replace(/\s*\/\s*/g, "/")
    .replace(/\s+/g, " ")
    .trim();
  return result;
}

// Диагностика микрофона
async function checkMicrophone() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Создаём анализатор для проверки уровня звука
    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);

    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    // Проверяем уровень звука 2 секунды
    let hasSound = false;
    const startTime = Date.now();

    while (Date.now() - startTime < 2000) {
      analyser.getByteFrequencyData(dataArray);
      const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      if (avg > 5) {
        hasSound = true;
        break;
      }
      await new Promise((r) => setTimeout(r, 100));
    }

    // Останавливаем потоки
    stream.getTracks().forEach((t) => t.stop());
    audioContext.close();

    return { ok: true, hasSound };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// Визуальный индикатор уровня звука
let audioLevelInterval = null;
let audioContext = null;
let analyser = null;

function startAudioLevelIndicator(stream) {
  audioContext = new AudioContext();
  const source = audioContext.createMediaStreamSource(stream);
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 256;
  source.connect(analyser);

  const dataArray = new Uint8Array(analyser.frequencyBinCount);

  audioLevelInterval = setInterval(() => {
    analyser.getByteFrequencyData(dataArray);
    const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    const level = Math.min(100, avg * 2);
    micBtn.style.boxShadow = `0 0 ${level}px ${level / 2}px rgba(220, 38, 38, ${level / 100})`;
  }, 50);
}

function stopAudioLevelIndicator() {
  if (audioLevelInterval) {
    clearInterval(audioLevelInterval);
    audioLevelInterval = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
  micBtn.style.boxShadow = "";
}

if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.lang = "ru-RU";
  recognition.continuous = false;
  recognition.interimResults = true; // ← показываем промежуточные результаты
  recognition.maxAlternatives = 1;

  let isListening = false;
  let recognitionStream = null;
  let interimMsgId = null;

  micBtn.onclick = async () => {
    // Защита от повторных нажатий
    if (isListening) {
      recognition.stop();
      return;
    }

    // Блокируем кнопку
    isListening = true;
    micBtn.disabled = true;
    micBtn.textContent = "⏳";

    try {
      // 1. Проверяем микрофон
      addMsg("🎤 Проверяю микрофон...", "bot");
      const micCheck = await checkMicrophone();

      if (!micCheck.ok) {
        addMsg(`❌ Микрофон недоступен: ${micCheck.error}`, "bot");
        resetMicButton();
        return;
      }

      if (!micCheck.hasSound) {
        addMsg(
          "⚠️ Микрофон работает, но не слышу звука. Говорите громче!",
          "bot",
        );
      } else {
        addMsg("✅ Микрофон работает. Начинаю запись...", "bot");
      }

      // 2. Запускаем распознавание
      micBtn.textContent = "🔴";
      micBtn.classList.add("recording");
      micBtn.disabled = false;

      // Получаем поток для индикатора уровня звука
      recognitionStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      startAudioLevelIndicator(recognitionStream);

      // Таймаут 15 секунд
      const timeout = setTimeout(() => {
        if (isListening) {
          addMsg("⏱ Таймаут. Попробуйте ещё раз.", "bot");
          recognition.stop();
        }
      }, 15000);

      recognition._timeout = timeout;
      recognition.start();
    } catch (e) {
      console.error("Mic init error:", e);
      addMsg(`❌ Ошибка: ${e.message}`, "bot");
      resetMicButton();
    }
  };

  function resetMicButton() {
    isListening = false;
    micBtn.disabled = false;
    micBtn.textContent = "🎤";
    micBtn.classList.remove("recording");
    stopAudioLevelIndicator();
    if (recognitionStream) {
      recognitionStream.getTracks().forEach((t) => t.stop());
      recognitionStream = null;
    }
    if (recognition._timeout) {
      clearTimeout(recognition._timeout);
      recognition._timeout = null;
    }
  }

  recognition.onresult = (event) => {
    let interimTranscript = "";
    let finalTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }

    // Показываем промежуточный результат
    if (interimTranscript) {
      addressInput.value = interimTranscript;
      addressInput.style.background = "#fef3c7"; // жёлтый фон
    }

    // Финальный результат
    if (finalTranscript) {
      const normalized = normalizeAddress(finalTranscript);
      addressInput.value = normalized;
      addressInput.style.background = ""; // убираем жёлтый

      addMsg(`🎙 Распознано: ${normalized}`, "bot");

      resetMicButton();

      // Автозапуск поиска
      setTimeout(() => document.getElementById("btn-search").click(), 300);
    }
  };

  recognition.onerror = (event) => {
    console.error("Speech error:", event.error);

    const messages = {
      "no-speech": "🔇 Не слышу речь. Говорите громче и чётче.",
      "audio-capture": "❌ Микрофон не найден. Проверьте подключение.",
      "not-allowed":
        "❌ Доступ к микрофону запрещён. Разрешите в настройках браузера.",
      network: "❌ Ошибка сети. Web Speech API требует интернет.",
      aborted: "⏹ Распознавание прервано.",
      "service-not-allowed": "❌ Сервис распознавания недоступен.",
    };

    addMsg(messages[event.error] || `❌ Ошибка: ${event.error}`, "bot");
    resetMicButton();
  };

  recognition.onend = () => {
    // Если не получили финальный результат
    if (isListening && !addressInput.value) {
      addMsg("⏹ Распознавание завершено без результата.", "bot");
    }
    resetMicButton();
  };

  // Проверка поддержки при загрузке
  addMsg("🎤 Голосовой ввод доступен. Нажмите на микрофон для записи.", "bot");
} else {
  micBtn.disabled = true;
  micBtn.title =
    "Распознавание речи не поддерживается. Используйте Chrome или Edge.";
  addMsg(
    "❌ Ваш браузер не поддерживает распознавание речи. Используйте Chrome или Edge.",
    "bot",
  );
}

// ===== Обработка событий от модуля распознавания речи =====
document.addEventListener("DOMContentLoaded", () => {
  // Инициализируем модуль речи
  SpeechModule.init("btn-mic", "address");

  // Слушаем статусы
  window.addEventListener("speech:status", (e) => {
    addMsg(e.detail.message, "bot");
  });

  // Слушаем промежуточные результаты (опционально — можно не использовать)
  window.addEventListener("speech:interim", (e) => {
    // console.log("Interim:", e.detail.text);
  });

  // Слушаем финальные результаты
  window.addEventListener("speech:result", (e) => {
    const { text, isAddress } = e.detail;

    if (isAddress) {
      // Это адрес — геокодим
      addMsg(`📍 Ищу: ${text}`, "user");
      setTimeout(() => document.getElementById("btn-search").click(), 300);
    } else {
      // Это чат — отправляем в LLM
      document.getElementById("address").value = ""; // очищаем поле
      sendToChat(text);
    }
  });
});

// Функция отправки в чат (вынесена из speech.js)
async function sendToChat(message) {
  addMsg(message, "user");
  history.push({ role: "user", content: message });

  try {
    const response = await fetch(`${API}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });
    const data = await response.json();
    addMsg(data.reply, "bot");
    history.push({ role: "assistant", content: data.reply });
  } catch (error) {
    console.error("Chat failed:", error);
    addMsg("❌ Ошибка связи с агентом", "bot");
  }
}

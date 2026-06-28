// ===== Модуль распознавания речи (мультибраузерный) =====
// - Chrome/Edge/Yandex/Safari → Web Speech API (мгновенно)
// - Firefox → MediaRecorder + Yandex SpeechKit через backend

const SpeechModule = (function () {
  // Словарь числительных
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

  const addressKeywords = [
    "улица",
    "ул.",
    "проспект",
    "пр.",
    "переулок",
    "пер.",
    "дом",
    "д.",
    "корпус",
    "к.",
    "строение",
    "стр.",
    "район",
    "область",
    "край",
    "город",
    "г.",
    "посёлок",
    "пос.",
    "деревня",
    "село",
    "с.",
    "микрорайон",
    "мкр.",
    "бульвар",
    "шоссе",
    "площадь",
    "квартира",
    "кв.",
    "офис",
    "литер",
  ];

  // ✅ СТОП-СЛОВА — если фраза состоит только из них, это НЕ адрес
  const chatStopWords = [
    "привет",
    "здравствуй",
    "здравствуйте",
    "добрый день",
    "доброе утро",
    "добрый вечер",
    "пока",
    "до свидания",
    "спасибо",
    "благодарю",
    "да",
    "нет",
    "ага",
    "угу",
    "хорошо",
    "ладно",
    "ок",
    "понятно",
    "ясно",
  ];

  function normalizeText(text) {
    let result = text;
    for (const [word, num] of Object.entries(numberWords)) {
      const regex = new RegExp(`\\b${word}\\b`, "gi");
      result = result.replace(regex, num);
    }
    return result
      .replace(/\s*\/\s*/g, "/")
      .replace(/\s+/g, " ")
      .trim();
  }

  // ✅ Проверка: это просто приветствие/чат, а не адрес?
  function isJustChatPhrase(text) {
    const lower = text
      .toLowerCase()
      .replace(/[.,!?]/g, "")
      .trim();
    return chatStopWords.some(
      (word) => lower === word || lower.startsWith(word + " "),
    );
  }

  function isLikelyAddress(text) {
    const isChat = isJustChatPhrase(text);
    console.log(`🔍 isLikelyAddress("${text}") → isChat=${isChat}`);

    if (isChat) return false;
    // ✅ Сначала проверяем стоп-слова
    if (isJustChatPhrase(text)) return false;

    const lower = text.toLowerCase();
    const hasKeyword = addressKeywords.some((kw) => lower.includes(kw));
    const hasNumber = /\b\d{1,4}\b/.test(text);
    const commaCount = (text.match(/,/g) || []).length;
    const wordCount = text.split(/\s+/).length;

    if (hasKeyword) return true;
    if (hasNumber && commaCount >= 1) return true;
    if (wordCount >= 4 && commaCount >= 2) return true;
    return false;
  }

  async function checkMicrophone() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
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

      stream.getTracks().forEach((t) => t.stop());
      audioContext.close();
      return { ok: true, hasSound };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  }

  // ===== Web Speech API (Chrome/Edge/Yandex/Safari) =====
  function initWebSpeech(micBtn, addressInput) {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = "ru-RU";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    let isListening = false;
    let recognitionStream = null;
    let audioLevelInterval = null;
    let audioContext = null;
    let analyser = null;

    function startAudioLevel(stream) {
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

    function stopAudioLevel() {
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

    function resetButton() {
      isListening = false;
      micBtn.disabled = false;
      micBtn.textContent = "🎤";
      micBtn.classList.remove("recording");
      stopAudioLevel();
      if (recognitionStream) {
        recognitionStream.getTracks().forEach((t) => t.stop());
        recognitionStream = null;
      }
      if (recognition._timeout) {
        clearTimeout(recognition._timeout);
        recognition._timeout = null;
      }
    }

    micBtn.onclick = async () => {
      if (isListening) {
        recognition.stop();
        return;
      }
      isListening = true;
      micBtn.disabled = true;
      micBtn.textContent = "⏳";

      try {
        window.dispatchEvent(
          new CustomEvent("speech:status", {
            detail: { type: "info", message: "🎤 Проверяю микрофон..." },
          }),
        );
        const micCheck = await checkMicrophone();
        if (!micCheck.ok) {
          window.dispatchEvent(
            new CustomEvent("speech:status", {
              detail: {
                type: "error",
                message: `❌ Микрофон недоступен: ${micCheck.error}`,
              },
            }),
          );
          resetButton();
          return;
        }
        if (!micCheck.hasSound) {
          window.dispatchEvent(
            new CustomEvent("speech:status", {
              detail: {
                type: "warning",
                message: "⚠️ Микрофон работает, но не слышу звука.",
              },
            }),
          );
        } else {
          window.dispatchEvent(
            new CustomEvent("speech:status", {
              detail: { type: "success", message: "✅ Говорите..." },
            }),
          );
        }

        micBtn.textContent = "🔴";
        micBtn.classList.add("recording");
        micBtn.disabled = false;

        recognitionStream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        startAudioLevel(recognitionStream);

        recognition._timeout = setTimeout(() => {
          if (isListening) {
            window.dispatchEvent(
              new CustomEvent("speech:status", {
                detail: { type: "warning", message: "⏱ Таймаут." },
              }),
            );
            recognition.stop();
          }
        }, 15000);

        recognition.start();
      } catch (e) {
        console.error("Mic init error:", e);
        window.dispatchEvent(
          new CustomEvent("speech:status", {
            detail: { type: "error", message: `❌ Ошибка: ${e.message}` },
          }),
        );
        resetButton();
      }
    };

    recognition.onresult = (event) => {
      let interimTranscript = "";
      let finalTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalTranscript += transcript;
        else interimTranscript += transcript;
      }
      if (interimTranscript) {
        addressInput.value = interimTranscript;
        addressInput.style.background = "#fef3c7";
      }
      if (finalTranscript) {
        const normalized = normalizeText(finalTranscript);
        addressInput.value = normalized;
        addressInput.style.background = "";
        resetButton();
        const isAddress = isLikelyAddress(normalized);
        window.dispatchEvent(
          new CustomEvent("speech:result", {
            detail: { text: normalized, isAddress },
          }),
        );
      }
    };

    recognition.onerror = (event) => {
      // ✅ ИГНОРИРУЕМ ложную ошибку network после успешного распознавания
      if (event.error === "network" && addressInput.value) return;

      console.error("Speech error:", event.error);
      const messages = {
        "no-speech": "🔇 Не слышу речь.",
        "audio-capture": "❌ Микрофон не найден.",
        "not-allowed": "❌ Доступ к микрофону запрещён.",
        network: "❌ Ошибка сети.",
        aborted: "⏹ Прервано.",
      };
      window.dispatchEvent(
        new CustomEvent("speech:status", {
          detail: {
            type: "error",
            message: messages[event.error] || `❌ Ошибка: ${event.error}`,
          },
        }),
      );
      resetButton();
    };

    recognition.onend = () => {
      if (isListening && !addressInput.value) {
        window.dispatchEvent(
          new CustomEvent("speech:status", {
            detail: { type: "info", message: "⏹ Без результата." },
          }),
        );
      }
      resetButton();
    };
  }

  // ===== Fallback: MediaRecorder + Yandex SpeechKit (Firefox) =====
  function initWhisperFallback(micBtn, addressInput) {
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    function resetButton() {
      isRecording = false;
      micBtn.disabled = false;
      micBtn.textContent = "🎤";
      micBtn.classList.remove("recording");
    }

    micBtn.onclick = async () => {
      if (isRecording) {
        mediaRecorder.stop();
        return;
      }

      isRecording = true;
      micBtn.disabled = true;
      micBtn.textContent = "⏳";

      try {
        window.dispatchEvent(
          new CustomEvent("speech:status", {
            detail: { type: "info", message: "🎤 Проверяю микрофон..." },
          }),
        );
        const micCheck = await checkMicrophone();
        if (!micCheck.ok) {
          window.dispatchEvent(
            new CustomEvent("speech:status", {
              detail: {
                type: "error",
                message: `❌ Микрофон недоступен: ${micCheck.error}`,
              },
            }),
          );
          resetButton();
          return;
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
          stream.getTracks().forEach((t) => t.stop());

          if (audioChunks.length === 0) {
            window.dispatchEvent(
              new CustomEvent("speech:status", {
                detail: { type: "warning", message: "⚠️ Аудио не записано." },
              }),
            );
            resetButton();
            return;
          }

          const audioBlob = new Blob(audioChunks, { type: "audio/webm" });

          window.dispatchEvent(
            new CustomEvent("speech:status", {
              detail: { type: "info", message: "🔄 Расшифровываю..." },
            }),
          );

          try {
            const formData = new FormData();
            formData.append("audio", audioBlob, "audio.webm");

            const response = await fetch(`${API}/speech/transcribe`, {
              method: "POST",
              body: formData,
            });

            if (!response.ok) {
              const errText = await response.text();
              throw new Error(`HTTP ${response.status}: ${errText}`);
            }

            const result = await response.json();
            const text = result.text || "";

            if (!text.trim()) {
              window.dispatchEvent(
                new CustomEvent("speech:status", {
                  detail: {
                    type: "warning",
                    message: "🔇 Не удалось распознать речь.",
                  },
                }),
              );
              resetButton();
              return;
            }

            const normalized = normalizeText(text);
            addressInput.value = normalized;

            const isAddress = isLikelyAddress(normalized);
            window.dispatchEvent(
              new CustomEvent("speech:result", {
                detail: { text: normalized, isAddress },
              }),
            );
          } catch (e) {
            console.error("Transcription error:", e);
            window.dispatchEvent(
              new CustomEvent("speech:status", {
                detail: {
                  type: "error",
                  message: `❌ Ошибка транскрибации: ${e.message}`,
                },
              }),
            );
          }

          resetButton();
        };

        micBtn.textContent = "🔴";
        micBtn.classList.add("recording");
        micBtn.disabled = false;
        mediaRecorder.start();

        window.dispatchEvent(
          new CustomEvent("speech:status", {
            detail: {
              type: "success",
              message: "🎤 Записываю... Нажмите ещё раз, чтобы остановить.",
            },
          }),
        );

        setTimeout(() => {
          if (isRecording && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
          }
        }, 30000);
      } catch (e) {
        console.error("Recording error:", e);
        window.dispatchEvent(
          new CustomEvent("speech:status", {
            detail: { type: "error", message: `❌ Ошибка: ${e.message}` },
          }),
        );
        resetButton();
      }
    };
  }

  // ===== Инициализация =====
  function init(micButtonId, addressInputId) {
    const micBtn = document.getElementById(micButtonId);
    const addressInput = document.getElementById(addressInputId);

    if (!micBtn || !addressInput) {
      console.error("SpeechModule: кнопка или поле ввода не найдены");
      return;
    }

    const hasWebSpeech =
      "webkitSpeechRecognition" in window || "SpeechRecognition" in window;

    if (hasWebSpeech) {
      console.log("✅ Using Web Speech API");
      initWebSpeech(micBtn, addressInput);
      window.dispatchEvent(
        new CustomEvent("speech:status", {
          detail: {
            type: "success",
            message:
              "🎤 Голосовой ввод готов (Web Speech API). Скажите адрес или поговорите со мной!",
          },
        }),
      );
    } else {
      console.log(
        "⚠️ Web Speech API not supported, using Yandex SpeechKit fallback",
      );
      initWhisperFallback(micBtn, addressInput);
      window.dispatchEvent(
        new CustomEvent("speech:status", {
          detail: {
            type: "success",
            message:
              "🎤 Голосовой ввод готов (Yandex SpeechKit). Нажмите и говорите!",
          },
        }),
      );
    }
  }

  return { init };
})();

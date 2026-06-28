// ============================================
// ЧАТ
// ============================================
const chatEl = document.getElementById("chat");
const chatHistory = [];

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
    chatHistory.push({ role: "assistant", content: data.reply });
  } catch (error) {
    console.error("Greeting failed:", error);
    addMsg("Здравствуйте! Куда поедем?", "bot");
  }
}

async function sendToChat(message) {
  addMsg(message, "user");
  chatHistory.push({ role: "user", content: message });

  try {
    const response = await fetch(`${API}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: chatHistory }),
    });
    const data = await response.json();
    addMsg(data.reply, "bot");
    chatHistory.push({ role: "assistant", content: data.reply });
  } catch (error) {
    console.error("Chat failed:", error);
    addMsg("❌ Ошибка связи с агентом", "bot");
  }
}

// Обработчик отправки из чата
document.getElementById("address-chat").addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    const input = e.target;
    const message = input.value.trim();
    if (message) {
      sendToChat(message);
      input.value = "";
    }
  }
});

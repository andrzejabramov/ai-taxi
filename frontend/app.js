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

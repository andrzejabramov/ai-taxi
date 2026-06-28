// ============================================
// ПОЛНОЭКРАННАЯ КАРТА
// ============================================
let mapFull = null;
let userMarker = null;
let endMarker = null;
let routeLine = null;
let endPoint = null;

function initMapFull() {
  console.log("🗺 Initializing full map");

  if (!mapFull) {
    setTimeout(() => {
      mapFull = L.map("map-full").setView([55.751244, 37.618423], 12);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap contributors",
      }).addTo(mapFull);

      // Геолокация
      if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const { latitude, longitude } = pos.coords;
            mapFull.setView([latitude, longitude], 15);
            userMarker = L.marker([latitude, longitude])
              .addTo(mapFull)
              .bindPopup("Вы здесь")
              .openPopup();
          },
          () => console.warn("Геолокация недоступна"),
        );
      }

      // Клик по карте
      mapFull.on("click", (e) => {
        setEndPoint(e.latlng.lat, e.latlng.lng);
      });

      // Обработчики кнопок
      document.getElementById("btn-search").onclick = searchAddress;
      document.getElementById("btn-order").onclick = orderTrip;
    }, 100);
  }
}

function setEndPoint(lat, lon) {
  endPoint = { lat, lon };
  if (endMarker) mapFull.removeLayer(endMarker);
  endMarker = L.marker([lat, lon], { draggable: true })
    .addTo(mapFull)
    .bindPopup("Пункт назначения")
    .openPopup();

  endMarker.on("dragend", (ev) => {
    const p = ev.target.getLatLng();
    endPoint = { lat: p.lat, lon: p.lng };
  });

  document.getElementById("btn-order").disabled = false;
}

async function searchAddress() {
  const address = document.getElementById("address").value.trim();
  if (!address) return;

  addMsg(address, "user");

  try {
    const response = await fetch(`${API}/geo/geocode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address }),
    });
    const data = await response.json();

    setEndPoint(data.lat, data.lon);
    mapFull.setView([data.lat, data.lon], 14);

    addMsg(`Нашёл: ${data.name}`, "bot");
  } catch (error) {
    console.error("Geocoding failed:", error);
    addMsg("Не удалось найти адрес", "bot");
  }
}

async function orderTrip() {
  if (!endPoint) return;

  const pos = userMarker ? userMarker.getLatLng() : mapFull.getCenter();

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

    if (routeLine) mapFull.removeLayer(routeLine);
    routeLine = L.polyline(data.geometry, {
      color: "#2563eb",
      weight: 5,
    }).addTo(mapFull);
    mapFull.fitBounds(routeLine.getBounds());

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
}

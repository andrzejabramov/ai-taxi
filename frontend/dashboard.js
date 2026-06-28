// ============================================
// ДАШБОРД
// ============================================
let mapPreview = null;

function initDashboard() {
  console.log("🏠 Initializing dashboard");

  // Инициализация превью карты
  if (!mapPreview) {
    setTimeout(() => {
      mapPreview = L.map("map-preview").setView([55.751244, 37.618423], 10);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
      }).addTo(mapPreview);

      // Геолокация
      if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const { latitude, longitude } = pos.coords;
            mapPreview.setView([latitude, longitude], 12);
            L.marker([latitude, longitude])
              .addTo(mapPreview)
              .bindPopup("Вы здесь");
          },
          () => console.warn("Геолокация недоступна"),
        );
      }
    }, 100);
  }

  // Загрузка превью поездок
  loadTripsPreview();
}

async function loadTripsPreview() {
  try {
    const response = await fetch(`${API}/trips/?user_id=employee_1&limit=5`);
    const data = await response.json();
    tripsData = data.trips;

    const container = document.getElementById("trips-preview");

    if (tripsData.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <p>🚕</p>
          <p>У вас пока нет поездок</p>
        </div>
      `;
      return;
    }

    container.innerHTML = tripsData
      .map(
        (trip) => `
      <div class="trip-preview-item" onclick="openTripDetail(${trip.id})">
        <div class="trip-preview-date">${formatDate(trip.created_at)}</div>
        <div class="trip-preview-route">${trip.start_address} → ${trip.end_address}</div>
        <div class="trip-preview-price">${trip.price ? trip.price + "₽" : "—"}</div>
      </div>
    `,
      )
      .join("");
  } catch (error) {
    console.error("Failed to load trips preview:", error);
  }
}

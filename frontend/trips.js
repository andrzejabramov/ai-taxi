// ============================================
// ТАБЛИЦА И КАРТОЧКА ПОЕЗДОК
// ============================================
let mapTrip = null;

async function loadTripsTable() {
  console.log("📋 Loading trips table");

  try {
    const response = await fetch(`${API}/trips/?user_id=employee_1&limit=15`);
    const data = await response.json();
    tripsData = data.trips;

    const tbody = document.getElementById("trips-tbody");

    if (tripsData.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8">У вас пока нет поездок</td></tr>';
      return;
    }

    tbody.innerHTML = tripsData
      .map(
        (trip) => `
      <tr onclick="openTripDetail(${trip.id})">
        <td>${formatDate(trip.created_at)}</td>
        <td>${trip.start_address || "—"}</td>
        <td>${trip.end_address || "—"}</td>
        <td>${trip.distance_m ? (trip.distance_m / 1000).toFixed(1) + " км" : "—"}</td>
        <td>${trip.duration_s ? Math.round(trip.duration_s / 60) + " мин" : "—"}</td>
        <td>${trip.tariff || "—"}</td>
        <td>${trip.price ? trip.price + "₽" : "—"}</td>
        <td>${trip.status}</td>
      </tr>
    `,
      )
      .join("");
  } catch (error) {
    console.error("Failed to load trips table:", error);
  }
}

function openTripDetail(tripId) {
  currentTripId = tripId;
  switchView("trip-detail");
}

async function loadTripDetail(tripId) {
  console.log(`🚗 Loading trip detail: ${tripId}`);

  try {
    const response = await fetch(`${API}/trips/${tripId}`);
    const trip = await response.json();

    // Карта с треком
    setTimeout(() => {
      if (mapTrip) {
        mapTrip.remove();
      }

      mapTrip = L.map("trip-map-container").setView(
        [trip.start_lat, trip.start_lon],
        12,
      );
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
      }).addTo(mapTrip);

      // Маркеры
      L.marker([trip.start_lat, trip.start_lon])
        .addTo(mapTrip)
        .bindPopup("Откуда")
        .openPopup();

      L.marker([trip.end_lat, trip.end_lon]).addTo(mapTrip).bindPopup("Куда");

      // Трек
      if (trip.route_geometry && trip.route_geometry.length > 0) {
        const routeLine = L.polyline(trip.route_geometry, {
          color: "#2563eb",
          weight: 5,
        }).addTo(mapTrip);

        mapTrip.fitBounds(routeLine.getBounds());
      }
    }, 100);

    // Информация
    const infoContainer = document.getElementById("trip-info-container");
    infoContainer.innerHTML = `
      <div class="trip-info-section">
        <h4>Дата и время</h4>
        <div class="trip-info-value">${formatDate(trip.created_at)}</div>
      </div>
      
      <div class="trip-info-section">
        <h4>Откуда</h4>
        <div class="trip-info-value">${trip.start_address || "—"}</div>
      </div>
      
      <div class="trip-info-section">
        <h4>Куда</h4>
        <div class="trip-info-value">${trip.end_address || "—"}</div>
      </div>
      
      <div class="trip-info-section">
        <h4>Расстояние</h4>
        <div class="trip-info-value">${trip.distance_m ? (trip.distance_m / 1000).toFixed(1) + " км" : "—"}</div>
      </div>
      
      <div class="trip-info-section">
        <h4>Продолжительность</h4>
        <div class="trip-info-value">${trip.duration_s ? Math.round(trip.duration_s / 60) + " мин" : "—"}</div>
      </div>
      
      <div class="trip-info-section">
        <h4>Тариф</h4>
        <div class="trip-info-value">${trip.tariff || "—"}</div>
      </div>
      
      <div class="trip-info-section">
        <h4>Стоимость</h4>
        <div class="trip-info-value">${trip.price ? trip.price + "₽" : "—"}</div>
      </div>
      
      <div class="trip-info-section">
        <h4>Автомобиль</h4>
        <div class="trip-info-value">${trip.car_model || "—"} ${trip.car_number || ""}</div>
      </div>
      
      <div class="trip-info-section">
        <h4>Водитель</h4>
        <div class="trip-info-value">${trip.driver_name || "—"}</div>
        <div class="trip-info-value">${trip.driver_phone || ""}</div>
      </div>
      
      <div class="trip-info-section">
        <h4>Оценка</h4>
        <div class="trip-info-value">${trip.rating ? "⭐".repeat(trip.rating) : "Не оценена"}</div>
      </div>
      
      <div class="trip-info-actions">
        <button onclick="repeatTrip(${trip.id})">🔄 Повторить поездку</button>
        <button onclick="rateTrip(${trip.id})">⭐ Оценить водителя</button>
        <button onclick="downloadReceipt(${trip.id})">📄 Скачать чек</button>
      </div>
    `;
  } catch (error) {
    console.error("Failed to load trip detail:", error);
  }
}

function repeatTrip(tripId) {
  const trip = tripsData.find((t) => t.id === tripId);
  if (trip) {
    document.getElementById("address").value = trip.end_address;
    switchView("map");
    addMsg(`🔄 Повторяем поездку: ${trip.end_address}`, "bot");
  }
}

function rateTrip(tripId) {
  const rating = prompt("Оцените поездку (1-5):");
  if (rating >= 1 && rating <= 5) {
    fetch(`${API}/trips/${tripId}/rate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "employee_1", rating: parseInt(rating) }),
    })
      .then(() => {
        addMsg(`✅ Спасибо за оценку!`, "bot");
        loadTripDetail(tripId);
      })
      .catch((err) => console.error("Failed to rate trip:", err));
  }
}

function downloadReceipt(tripId) {
  addMsg(`📄 Функция скачивания чека будет добавлена позже`, "bot");
}

const shell = document.querySelector(".map-shell");
const form = document.querySelector("#search-form");
const submitButton = form?.querySelector("button[type='submit']");
const latInput = document.querySelector("#lat");
const lngInput = document.querySelector("#lng");
const categorySelect = document.querySelector("#category");
const radiusInput = document.querySelector("#search-radius");
const radiusOutput = document.querySelector("#radius-output");
const locateButton = document.querySelector("#locate-button");
const resetButton = document.querySelector("#reset-button");
const statusElement = document.querySelector("#status");
const resultsElement = document.querySelector("#results");

const defaultCenter = [50.1109, 8.6821];
const defaultCategory = "restaurant";
const defaultRadius = "500";
const selectedLocationIcon = createMarkerIcon("#c56a2c", [34, 48]);
const placeIcon = createMarkerIcon("#126b5a", [28, 40]);
const map = L.map("map").setView(defaultCenter, 13);
const resultMarkers = L.layerGroup().addTo(map);
let selectedMarker = null;
let radiusCircle = null;
let currentSearchController = null;

L.tileLayer(shell.dataset.tileUrl, {
  maxZoom: 19,
  attribution: shell.dataset.tileAttribution,
}).addTo(map);

if (form !== null) {
  setSelectedLocation(defaultCenter[0], defaultCenter[1], false);
  loadCategories();
}

map.on("click", (event) => {
  if (form === null) {
    return;
  }

  setSelectedLocation(event.latlng.lat, event.latlng.lng, true);
});

radiusInput?.addEventListener("input", () => {
  radiusOutput.value = `${radiusInput.value} m`;
  showRadiusCircle();
});

radiusInput?.addEventListener("pointerdown", () => {
  showRadiusCircle();
});

radiusInput?.addEventListener("pointerup", () => {
  hideRadiusCircle();
});

radiusInput?.addEventListener("pointercancel", () => {
  hideRadiusCircle();
});

radiusInput?.addEventListener("focus", () => {
  showRadiusCircle();
});

radiusInput?.addEventListener("blur", () => {
  hideRadiusCircle();
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await searchPlaces();
});

locateButton?.addEventListener("click", () => {
  if (!navigator.geolocation) {
    setStatus("Location is not available in this browser.");
    return;
  }

  setStatus("Finding your location...");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude } = position.coords;
      setSelectedLocation(latitude, longitude, true);
      searchPlaces();
    },
    () => setStatus("Could not access your location."),
    { enableHighAccuracy: true, timeout: 10000 },
  );
});

resetButton?.addEventListener("click", () => {
  resetSearch();
});

async function loadCategories() {
  try {
    const response = await fetch(shell.dataset.categoriesUrl);
    if (!response.ok) {
      throw new Error("Categories request failed.");
    }

    const categories = await response.json();
    categories.forEach((category) => {
      const option = document.createElement("option");
      option.value = category.slug;
      option.textContent = category.name;
      option.selected = category.slug === defaultCategory;
      categorySelect.append(option);
    });
  } catch {
    setStatus("Categories are not available right now.");
  }
}

async function searchPlaces() {
  currentSearchController?.abort();
  currentSearchController = new AbortController();
  const controller = currentSearchController;
  const params = new URLSearchParams({
    lat: latInput.value,
    lng: lngInput.value,
    search_radius: radiusInput.value,
  });

  params.set("category", categorySelect.value);

  setStatus("Searching nearby places...");
  resultsElement.replaceChildren();
  resultMarkers.clearLayers();
  submitButton.disabled = true;

  try {
    const response = await fetch(`${shell.dataset.placesUrl}?${params}`, {
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error("Places request failed.");
    }

    const payload = await response.json();
    renderPlaces(payload.places ?? []);
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }

    setStatus("Places are not available right now.");
  } finally {
    if (currentSearchController === controller) {
      currentSearchController = null;
      submitButton.disabled = false;
    }
  }
}

function renderPlaces(places) {
  if (places.length === 0) {
    setStatus("No places found for this search.");
    return;
  }

  const bounds = [];

  places.forEach((place) => {
    const marker = L.marker([place.latitude, place.longitude], {
      icon: placeIcon,
    })
      .bindPopup(`<strong>${escapeHtml(place.name)}</strong><br>${escapeHtml(place.category_name)}`)
      .addTo(resultMarkers);

    bounds.push([place.latitude, place.longitude]);

    const item = document.createElement("li");
    item.className = "result-item";

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = place.name;
    button.addEventListener("click", () => {
      map.setView([place.latitude, place.longitude], 17);
      marker.openPopup();
    });

    const meta = document.createElement("span");
    meta.className = "result-meta";
    meta.textContent = `${place.category_name} · ${place.latitude.toFixed(5)}, ${place.longitude.toFixed(5)}`;

    item.append(button, meta);
    resultsElement.append(item);
  });

  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
  setStatus(`${places.length} places found.`);
}

function resetSearch() {
  currentSearchController?.abort();
  currentSearchController = null;
  hideRadiusCircle();
  submitButton.disabled = false;
  categorySelect.value = defaultCategory;
  radiusInput.value = defaultRadius;
  radiusOutput.value = `${defaultRadius} m`;
  resultsElement.replaceChildren();
  resultMarkers.clearLayers();
  setSelectedLocation(defaultCenter[0], defaultCenter[1], false);
  map.setView(defaultCenter, 13);
  setStatus("");
}

function setSelectedLocation(lat, lng, moveMap) {
  latInput.value = lat.toFixed(7);
  lngInput.value = lng.toFixed(7);

  if (selectedMarker === null) {
    selectedMarker = L.marker([lat, lng], {
      draggable: true,
      icon: selectedLocationIcon,
      zIndexOffset: 1000,
    }).addTo(map);
    selectedMarker.on("dragend", () => {
      const location = selectedMarker.getLatLng();
      setSelectedLocation(location.lat, location.lng, false);
    });
  } else {
    selectedMarker.setLatLng([lat, lng]);
  }

  if (moveMap) {
    map.setView([lat, lng], Math.max(map.getZoom(), 14));
  }

  if (radiusCircle !== null) {
    updateRadiusCircle();
  }
}

function setStatus(message) {
  statusElement.textContent = message;
}

function showRadiusCircle() {
  if (radiusCircle === null) {
    radiusCircle = L.circle(getSelectedLocation(), {
      radius: Number(radiusInput.value),
      color: "#126b5a",
      weight: 2,
      fillColor: "#126b5a",
      fillOpacity: 0.12,
      interactive: false,
    }).addTo(map);
  }

  updateRadiusCircle();
}

function hideRadiusCircle() {
  if (radiusCircle === null) {
    return;
  }

  radiusCircle.remove();
  radiusCircle = null;
}

function updateRadiusCircle() {
  radiusCircle.setLatLng(getSelectedLocation());
  radiusCircle.setRadius(Number(radiusInput.value));
}

function getSelectedLocation() {
  return [Number(latInput.value), Number(lngInput.value)];
}

function createMarkerIcon(color, size) {
  const [width, height] = size;
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 34 48">
      <path fill="${color}" stroke="#ffffff" stroke-width="3" d="M17 46S3 28.4 3 17.2C3 8.8 9.3 3 17 3s14 5.8 14 14.2C31 28.4 17 46 17 46z"/>
      <circle cx="17" cy="17" r="5.5" fill="#ffffff"/>
    </svg>
  `;

  return L.icon({
    iconUrl: `data:image/svg+xml,${encodeURIComponent(svg)}`,
    iconSize: size,
    iconAnchor: [width / 2, height],
    popupAnchor: [0, -height],
  });
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

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
const favoriteResultsElement = document.querySelector("#favorite-results");
const historyResultsElement = document.querySelector("#history-results");
const navToggleButton = document.querySelector(".rail-toggle");

const navCollapsedStorageKey = "cityGuide.navCollapsed";
const defaultCenter = [50.1109, 8.6821];
const defaultCategory = "restaurant";
const defaultRadius = "500";
const selectedLocationIcon = createMarkerIcon("#c56a2c", [34, 48]);
const placeIcon = createMarkerIcon("#126b5a", [28, 40]);
const favoritePlaceIcon = createHeartMarkerIcon("#c56a2c");
const map = L.map("map").setView(defaultCenter, 13);
const resultMarkers = L.layerGroup().addTo(map);
let selectedMarker = null;
let radiusCircle = null;
let currentSearchController = null;
let favoriteOsmUids = new Set();

L.tileLayer(shell.dataset.tileUrl, {
  maxZoom: 19,
  attribution: shell.dataset.tileAttribution,
}).addTo(map);

applyNavigationState(localStorage.getItem(navCollapsedStorageKey) === "true");

if (form !== null) {
  setSelectedLocation(defaultCenter[0], defaultCenter[1], false);
  loadCategories().then(restoreSearchFromUrl);
  loadFavorites();
}

if (favoriteResultsElement !== null) {
  loadFavoritePlaces();
}

if (historyResultsElement !== null) {
  loadSearchHistory();
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

navToggleButton?.addEventListener("click", () => {
  const isCollapsed = shell.dataset.navCollapsed === "true";
  applyNavigationState(!isCollapsed);
  localStorage.setItem(navCollapsedStorageKey, String(!isCollapsed));
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

async function loadFavorites() {
  try {
    const response = await fetch(shell.dataset.favoritesUrl);
    if (!response.ok) {
      throw new Error("Favorites request failed.");
    }

    const favorites = await response.json();
    favoriteOsmUids = new Set(favorites.map((favorite) => favorite.osm_uid));
  } catch {
    favoriteOsmUids = new Set();
  }
}

async function loadFavoritePlaces() {
  setStatus("Loading favorite places...");

  try {
    const response = await fetch(shell.dataset.favoritesUrl);
    if (!response.ok) {
      throw new Error("Favorites request failed.");
    }

    const favorites = await response.json();
    favoriteOsmUids = new Set(favorites.map((favorite) => favorite.osm_uid));
    renderFavoritePlaces(favorites);
  } catch {
    setStatus("Favorites are not available right now.");
  }
}

async function loadSearchHistory() {
  setStatus("Loading recent searches...");

  try {
    const response = await fetch(shell.dataset.historyUrl);
    if (!response.ok) {
      throw new Error("History request failed.");
    }

    const searches = await response.json();
    renderSearchHistory(searches);
  } catch {
    setStatus("Search history is not available right now.");
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
      icon: getPlaceMarkerIcon(place),
    })
      .bindPopup(`<strong>${escapeHtml(place.name)}</strong><br>${escapeHtml(place.category_name)}`)
      .addTo(resultMarkers);

    bounds.push([place.latitude, place.longitude]);

    const item = document.createElement("li");
    item.className = "result-item";

    const button = document.createElement("button");
    button.className = "result-place-button";
    button.type = "button";
    button.textContent = place.name;
    button.addEventListener("click", () => {
      map.setView([place.latitude, place.longitude], 17);
      marker.openPopup();
    });

    const meta = document.createElement("span");
    meta.className = "result-meta";
    meta.textContent = `${place.category_name} · ${place.latitude.toFixed(5)}, ${place.longitude.toFixed(5)}`;

    const favoriteButton = document.createElement("button");
    favoriteButton.className = "favorite-button";
    favoriteButton.type = "button";
    updateFavoriteButton(favoriteButton, place);
    favoriteButton.addEventListener("click", async () => {
      await toggleFavorite(place, favoriteButton);
      marker.setIcon(getPlaceMarkerIcon(place));
    });

    item.append(button, meta, favoriteButton);
    resultsElement.append(item);
  });

  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
  setStatus(`${places.length} places found.`);
}

function renderFavoritePlaces(favorites) {
  favoriteResultsElement.replaceChildren();
  resultMarkers.clearLayers();

  if (favorites.length === 0) {
    setStatus("No favorite places saved yet.");
    return;
  }

  const bounds = [];

  favorites.forEach((place) => {
    const marker = L.marker([place.latitude, place.longitude], {
      icon: favoritePlaceIcon,
    })
      .bindPopup(`<strong>${escapeHtml(place.name)}</strong><br>${escapeHtml(place.category_name)}`)
      .addTo(resultMarkers);

    bounds.push([place.latitude, place.longitude]);

    const item = document.createElement("li");
    item.className = "result-item";

    const button = document.createElement("button");
    button.className = "result-place-button";
    button.type = "button";
    button.textContent = place.name;
    button.addEventListener("click", () => {
      map.setView([place.latitude, place.longitude], 17);
      marker.openPopup();
    });

    const meta = document.createElement("span");
    meta.className = "result-meta";
    meta.textContent = `${place.category_name} · ${place.latitude.toFixed(5)}, ${place.longitude.toFixed(5)}`;

    const favoriteButton = document.createElement("button");
    favoriteButton.className = "favorite-button";
    favoriteButton.type = "button";
    updateFavoriteButton(favoriteButton, place);
    favoriteButton.addEventListener("click", async () => {
      await toggleFavorite(place, favoriteButton);
      item.remove();
      marker.remove();

      if (favoriteResultsElement.children.length === 0) {
        setStatus("No favorite places saved yet.");
      }
    });

    item.append(button, meta, favoriteButton);
    favoriteResultsElement.append(item);
  });

  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
  setStatus(`${favorites.length} favorite places saved.`);
}

function renderSearchHistory(searches) {
  historyResultsElement.replaceChildren();
  resultMarkers.clearLayers();

  if (searches.length === 0) {
    setStatus("No recent searches yet.");
    return;
  }

  const bounds = [];

  searches.forEach((search) => {
    const marker = L.marker([search.latitude, search.longitude], {
      icon: selectedLocationIcon,
    })
      .bindPopup(`<strong>${escapeHtml(formatSearchTitle(search))}</strong><br>${search.result_count} results`)
      .addTo(resultMarkers);

    bounds.push([search.latitude, search.longitude]);

    const item = document.createElement("li");
    item.className = "result-item";

    const link = document.createElement("a");
    link.className = "result-place-button";
    link.href = buildSearchUrl(search);
    link.textContent = formatSearchTitle(search);

    const meta = document.createElement("span");
    meta.className = "result-meta";
    meta.textContent = `${search.search_radius} m · ${search.result_count} results · ${search.latitude.toFixed(5)}, ${search.longitude.toFixed(5)}`;

    item.append(link, meta);
    historyResultsElement.append(item);
  });

  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
  setStatus(`${searches.length} recent searches.`);
}

function restoreSearchFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const lat = params.get("lat");
  const lng = params.get("lng");
  const searchRadius = params.get("search_radius");
  const category = params.get("category");

  if (lat === null || lng === null) {
    return;
  }

  latInput.value = lat;
  lngInput.value = lng;

  if (searchRadius !== null) {
    radiusInput.value = searchRadius;
    radiusOutput.value = `${searchRadius} m`;
  }

  if (category !== null) {
    const selectCategory = () => {
      categorySelect.value = category;
    };
    if (categorySelect.options.length > 0) {
      selectCategory();
    } else {
      setTimeout(selectCategory, 100);
    }
  }

  setSelectedLocation(Number(lat), Number(lng), true);
  searchPlaces();
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

function applyNavigationState(isCollapsed) {
  shell.dataset.navCollapsed = String(isCollapsed);
  navToggleButton?.setAttribute("aria-expanded", String(!isCollapsed));
  navToggleButton?.setAttribute(
    "aria-label",
    isCollapsed ? "Expand navigation" : "Collapse navigation",
  );
  navToggleButton?.setAttribute(
    "title",
    isCollapsed ? "Expand navigation" : "Collapse navigation",
  );
}

async function toggleFavorite(place, button) {
  button.disabled = true;

  try {
    if (favoriteOsmUids.has(place.osm_uid)) {
      await deleteFavorite(place.osm_uid);
      favoriteOsmUids.delete(place.osm_uid);
    } else {
      await saveFavorite(place);
      favoriteOsmUids.add(place.osm_uid);
    }

    updateFavoriteButton(button, place);
  } catch {
    setStatus("Favorite could not be updated right now.");
  } finally {
    button.disabled = false;
  }
}

async function saveFavorite(place) {
  const response = await fetch(shell.dataset.favoritesUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify(place),
  });

  if (!response.ok) {
    throw new Error("Favorite save failed.");
  }
}

async function deleteFavorite(osmUid) {
  const response = await fetch(`${shell.dataset.favoritesUrl}${encodeURIComponent(osmUid)}/`, {
    method: "DELETE",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
    },
  });

  if (!response.ok) {
    throw new Error("Favorite delete failed.");
  }
}

function updateFavoriteButton(button, place) {
  const isFavorite = favoriteOsmUids.has(place.osm_uid);
  button.innerHTML = `
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z"></path>
    </svg>
  `;
  button.setAttribute(
    "aria-label",
    `${isFavorite ? "Remove" : "Save"} ${place.name} ${isFavorite ? "from" : "to"} favorites`,
  );
  button.dataset.active = String(isFavorite);
}

function getCookie(name) {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.split("=")[1]) : "";
}

function buildSearchUrl(search) {
  const params = new URLSearchParams({
    lat: search.latitude,
    lng: search.longitude,
    search_radius: search.search_radius,
  });

  if (search.category !== "") {
    params.set("category", search.category);
  }

  return `${shell.dataset.mapUrl}?${params}`;
}

function formatSearchTitle(search) {
  return search.category === "" ? "Default categories" : titleize(search.category);
}

function titleize(value) {
  return value
    .split("-")
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(" ");
}

function getPlaceMarkerIcon(place) {
  return favoriteOsmUids.has(place.osm_uid) ? favoritePlaceIcon : placeIcon;
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

function createHeartMarkerIcon(color) {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="38" height="44" viewBox="0 0 38 44">
      <path fill="${color}" stroke="#ffffff" stroke-width="3" d="M19 42S5 27 5 16a14 14 0 1 1 28 0c0 11-14 26-14 26Z"/>
      <circle cx="19" cy="16" r="10" fill="#ffffff"/>
      <path fill="${color}" d="M19 23.2 13 17.4a4 4 0 0 1 5.7-5.7l.3.3.3-.3a4 4 0 0 1 5.7 5.7L19 23.2Z"/>
    </svg>
  `;

  return L.icon({
    iconUrl: `data:image/svg+xml,${encodeURIComponent(svg)}`,
    iconSize: [38, 44],
    iconAnchor: [19, 42],
    popupAnchor: [0, -38],
  });
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value;
  return element.innerHTML;
}

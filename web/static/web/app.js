const shell = document.querySelector(".map-shell, .app-shell");
const form = document.querySelector("#search-form");
const submitButton = form?.querySelector("button[type='submit']");
const latInput = document.querySelector("#lat");
const lngInput = document.querySelector("#lng");
const mapLayerSelect = document.querySelector("#map-layer");
const radiusInput = document.querySelector("#search-radius");
const radiusOutput = document.querySelector("#radius-output");
const locateButton = document.querySelector("#locate-button");
const resetButton = document.querySelector("#reset-button");
const statusElement = document.querySelector("#status");
const resultsElement = document.querySelector("#results");
const areaInsightsElement = document.querySelector("#area-insights");
const areaInsightsTitleElement = document.querySelector("#area-insights-title");
const areaInsightsContentElement = document.querySelector("#area-insights-content");
const treeCoverLegendElement = document.querySelector("#tree-cover-legend");
const treeCoverToggleElement = document.querySelector("#tree-cover-toggle");
const treeCoverToggleInput = document.querySelector("#tree-cover-toggle-input");
const favoriteResultsElement = document.querySelector("#favorite-results");
const historyResultsElement = document.querySelector("#history-results");
const navToggleButton = document.querySelector(".rail-toggle");
const mapElement = document.querySelector("#map");
const profileLocateButton = document.querySelector("#profile-locate-button");
const defaultLatInput = document.querySelector("#id_default_latitude");
const defaultLngInput = document.querySelector("#id_default_longitude");
const locationSharingInput = document.querySelector("#id_location_sharing_enabled");

const navCollapsedStorageKey = "cityGuide.navCollapsed";
const fallbackCenter = [50.1109, 8.6821];
const defaultCenter = getDefaultCenter();
const defaultMapLayer = "overview";
const defaultRadius = shell?.dataset.defaultRadius ?? "500";
const realtimeRefreshEnabled = shell?.dataset.realtimeRefreshEnabled === "true";
const mapLayers = {
  overview: {},
  amenities: { categoryGroup: "food" },
  daily_life: { categoryGroup: "essentials" },
  mobility: { categoryGroup: "mobility" },
  green: { category: "park" },
};
const selectedLocationIcon = mapElement ? createMarkerIcon("#c56a2c", [34, 48]) : null;
const placeIcon = mapElement ? createMarkerIcon("#126b5a", [28, 40]) : null;
const favoritePlaceIcon = mapElement ? createHeartMarkerIcon("#c56a2c") : null;
const map = mapElement ? L.map("map").setView(defaultCenter, 13) : null;
const resultMarkers = map ? L.layerGroup().addTo(map) : null;
const treeCoverLayers = map ? L.layerGroup() : null;
const treeCoverBoundary = map ? L.featureGroup() : null;
let selectedMarker = null;
let radiusCircle = null;
let currentSearchController = null;
let currentRefreshController = null;
let currentSearchKey = "";
let favoriteOsmUids = new Set();
let activePlaceItem = null;
let treeCoverMapLayer = null;

if (map !== null) {
  L.tileLayer(shell.dataset.tileUrl, {
    maxZoom: 19,
    attribution: shell.dataset.tileAttribution,
  }).addTo(map);
}

if (shell !== null) {
  applyNavigationState(localStorage.getItem(navCollapsedStorageKey) === "true");
}

if (form !== null) {
  setSelectedLocation(defaultCenter[0], defaultCenter[1], false);
  if (!restoreSearchFromUrl()) {
    searchPlaces();
  }
  loadFavorites();
  loadAreaInsights();
}

if (favoriteResultsElement !== null) {
  loadFavoritePlaces();
}

if (historyResultsElement !== null) {
  loadSearchHistory();
}

map?.on("click", (event) => {
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

mapLayerSelect?.addEventListener("change", () => {
  searchPlaces();
});

treeCoverToggleInput?.addEventListener("change", () => {
  updateTreeCoverVisibility();
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

  setStatus("Finding your location", "loading");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude } = position.coords;
      setSelectedLocation(latitude, longitude, true);
    },
    () => setStatus("Could not access your location."),
    { enableHighAccuracy: true, timeout: 10000 },
  );
});

resetButton?.addEventListener("click", () => {
  resetSearch();
});

profileLocateButton?.addEventListener("click", () => {
  if (!navigator.geolocation) {
    setStatus("Location is not available in this browser.");
    return;
  }

  profileLocateButton.disabled = true;
  profileLocateButton.textContent = "Finding location...";

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude } = position.coords;
      defaultLatInput.value = latitude.toFixed(7);
      defaultLngInput.value = longitude.toFixed(7);
      locationSharingInput.checked = true;
      profileLocateButton.textContent = "Location saved";
      profileLocateButton.disabled = false;
    },
    () => {
      profileLocateButton.textContent = "Use current location";
      profileLocateButton.disabled = false;
      setStatus("Could not access your location.");
    },
    { enableHighAccuracy: true, timeout: 10000 },
  );
});

navToggleButton?.addEventListener("click", () => {
  if (shell === null) {
    return;
  }

  const isCollapsed = shell.dataset.navCollapsed === "true";
  applyNavigationState(!isCollapsed);
  localStorage.setItem(navCollapsedStorageKey, String(!isCollapsed));
});

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

async function loadAreaInsights() {
  if (areaInsightsElement === null || areaInsightsContentElement === null) {
    return;
  }

  areaInsightsElement.hidden = false;
  areaInsightsElement.dataset.state = "loading";
  renderAreaInsightSkeletons();

  try {
    const response = await fetch(shell.dataset.areaIntelligenceUrl);
    if (!response.ok) {
      throw new Error("Area intelligence request failed.");
    }

    const payload = await response.json();
    renderAreaInsights(payload);
    loadTreeCoverMapLayer();
  } catch {
    areaInsightsElement.hidden = true;
  }
}

function renderAreaInsights(payload) {
  const groups = payload.groups ?? [];
  const indicators = groups.flatMap((group) => group.indicators ?? []);

  if (indicators.length === 0) {
    areaInsightsElement.hidden = true;
    return;
  }

  areaInsightsTitleElement.textContent = payload.service_area?.name ?? "Your area";
  areaInsightsContentElement.replaceChildren();

  groups.forEach((group) => {
    const groupElement = document.createElement("section");
    groupElement.className = "insight-group";

    const groupTitle = document.createElement("h3");
    groupTitle.textContent = group.name;
    groupElement.append(groupTitle);

    group.indicators.forEach((indicator) => {
      groupElement.append(createAreaInsight(indicator));
    });

    areaInsightsContentElement.append(groupElement);
  });

  areaInsightsElement.dataset.state = "ready";
  areaInsightsElement.hidden = false;
}

function createAreaInsight(indicator) {
  const observation = indicator.observation;
  const item = document.createElement("div");
  item.className = "insight-item";
  item.title = formatInsightSource(observation);

  const name = document.createElement("span");
  name.className = "insight-name";
  name.textContent = indicator.name;

  const value = document.createElement("strong");
  value.className = "insight-value";
  value.textContent = formatInsightValue(indicator, observation);

  item.append(name, value);
  if (indicator.slug === "green-exposure" && observation.score !== null) {
    item.classList.add("insight-item--tree-cover");
    name.textContent = "Tree cover";

    const summary = document.createElement("span");
    summary.className = "insight-summary";
    summary.textContent = `Around ${observation.score}% average tree canopy cover across ${areaInsightsTitleElement.textContent}.`;
    item.append(summary);
  }
  return item;
}

function formatInsightValue(indicator, observation) {
  if (indicator.value_type === "trend") {
    return { up: "Up", steady: "Steady", down: "Down" }[observation.trend] ?? "-";
  }

  return observation.score === null ? "-" : `${observation.score}%`;
}

async function loadTreeCoverMapLayer() {
  if (treeCoverToggleElement === null) {
    return;
  }

  try {
    const response = await fetch(shell.dataset.treeCoverLayerUrl);
    if (!response.ok) {
      throw new Error("Tree cover map layer request failed.");
    }

    treeCoverMapLayer = await response.json();
    treeCoverToggleElement.hidden = false;
  } catch {
    treeCoverMapLayer = null;
    treeCoverToggleElement.hidden = true;
    treeCoverToggleInput.checked = false;
    updateTreeCoverVisibility();
  }
}

function updateTreeCoverVisibility() {
  const isSelected = treeCoverToggleInput?.checked === true;
  treeCoverLayers.clearLayers();
  treeCoverBoundary.clearLayers();
  treeCoverLegendElement.hidden = true;

  if (!isSelected || treeCoverMapLayer === null) {
    return;
  }

  treeCoverMapLayer.layers.forEach((layer) => {
    L.imageOverlay(layer.image_url, layer.bounds, {
      opacity: 0.76,
      interactive: false,
    }).addTo(treeCoverLayers);
  });
  L.geoJSON(treeCoverMapLayer.boundary, {
    style: {
      color: "#126b5a",
      weight: 2,
      fill: false,
    },
    interactive: false,
  }).addTo(treeCoverBoundary);
  treeCoverLayers.addTo(map);
  treeCoverBoundary.addTo(map);
  treeCoverLegendElement.hidden = false;

  const bounds = treeCoverBoundary.getBounds();
  if (bounds.isValid()) {
    map.fitBounds(bounds, { padding: [36, 36] });
  }
}

function formatInsightSource(observation) {
  const source = observation.source?.name;
  const observedAt = observation.observed_at ? new Date(observation.observed_at) : null;
  const date = observedAt && !Number.isNaN(observedAt.valueOf())
    ? observedAt.toLocaleDateString(undefined, { year: "numeric", month: "short" })
    : null;

  return [source, date].filter(Boolean).join(" · ");
}

function renderAreaInsightSkeletons() {
  areaInsightsContentElement.replaceChildren();

  for (let index = 0; index < 2; index += 1) {
    const item = document.createElement("div");
    item.className = "insight-item insight-item--skeleton";
    item.innerHTML = `
      <span class="insight-skeleton insight-skeleton--name"></span>
      <span class="insight-skeleton insight-skeleton--value"></span>
    `;
    areaInsightsContentElement.append(item);
  }
}

async function loadFavoritePlaces() {
  setStatus("Loading saved places", "loading");
  renderPlaceSkeletons(favoriteResultsElement);

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
  currentRefreshController?.abort();
  currentSearchController = new AbortController();
  const controller = currentSearchController;
  const params = buildSearchParams();
  const searchKey = params.toString();
  currentSearchKey = searchKey;

  setStatus("Finding nearby places", "loading");
  resultsElement.replaceChildren();
  renderPlaceSkeletons(resultsElement);
  resultMarkers.clearLayers();
  submitButton.disabled = true;

  try {
    await loadNearbyPlaces(params, controller.signal, searchKey);
    if (realtimeRefreshEnabled) {
      refreshPlacesInBackground(params, searchKey);
    }
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }

    setStatus("We couldn't load nearby places.", "error");
  } finally {
    if (currentSearchController === controller) {
      currentSearchController = null;
      submitButton.disabled = false;
    }
  }
}

async function refreshPlacesInBackground(params, searchKey) {
  currentRefreshController?.abort();
  currentRefreshController = new AbortController();
  const controller = currentRefreshController;

  try {
    setStatus("Checking for recent places", "loading");
    const scan = await startAreaScan(params, controller.signal);
    await pollAreaScan(scan.id, controller.signal);
    await loadNearbyPlaces(params, controller.signal, searchKey);
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }

    setStatus("Showing saved places. We couldn't refresh them.", "warning");
  } finally {
    if (currentRefreshController === controller) {
      currentRefreshController = null;
    }
  }
}

async function loadNearbyPlaces(params, signal, searchKey) {
  const response = await fetch(`${shell.dataset.nearbyPlacesUrl}?${params}`, {
    signal,
  });
  if (!response.ok) {
    throw new Error("Nearby places request failed.");
  }

  const payload = await response.json();
  if (searchKey !== currentSearchKey) {
    return;
  }

  renderPlaces(payload.places ?? []);
}

async function startAreaScan(params, signal) {
  const response = await fetch(shell.dataset.areaScansUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify(Object.fromEntries(params)),
    signal,
  });
  if (!response.ok) {
    throw new Error("Area scan request failed.");
  }

  return response.json();
}

async function pollAreaScan(scanId, signal) {
  while (!signal.aborted) {
    await wait(1200, signal);

    const response = await fetch(`${shell.dataset.areaScansUrl}${scanId}/`, { signal });
    if (!response.ok) {
      throw new Error("Area scan status request failed.");
    }

    const scan = await response.json();
    if (scan.status === "completed") {
      return;
    }

    if (scan.status === "failed") {
      throw new Error(scan.error_message || "Area scan failed.");
    }

    if (scan.error_message) {
      setStatus("Checking for recent places", "loading");
    }
  }

  throw new DOMException("Search aborted.", "AbortError");
}

function wait(milliseconds, signal) {
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(resolve, milliseconds);
    signal.addEventListener(
      "abort",
      () => {
        window.clearTimeout(timeout);
        reject(new DOMException("Search aborted.", "AbortError"));
      },
      { once: true },
    );
  });
}

function buildSearchParams() {
  const params = new URLSearchParams({
    lat: latInput.value,
    lng: lngInput.value,
    search_radius: radiusInput.value,
  });

  const layer = mapLayerSelect?.value ?? defaultMapLayer;
  const layerFilter = mapLayers[layer] ?? {};
  if (layerFilter.category !== undefined) {
    params.set("category", layerFilter.category);
  }
  if (layerFilter.categoryGroup !== undefined) {
    params.set("category_group", layerFilter.categoryGroup);
  }

  return params;
}

function renderPlaces(places) {
  resultsElement.replaceChildren();

  if (places.length === 0) {
    renderEmptyPlaceList(
      resultsElement,
      "No nearby places",
      "Try moving the map or choosing another layer.",
    );
    setStatus("No nearby places in this area.");
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

    const { item, favoriteButton } = createPlaceListItem(place, marker, {
      includeDistance: true,
    });
    updateFavoriteButton(favoriteButton, place);
    favoriteButton.addEventListener("click", async () => {
      await toggleFavorite(place, favoriteButton);
      marker.setIcon(getPlaceMarkerIcon(place));
    });

    resultsElement.append(item);
  });

  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
  setStatus(`${places.length} places nearby`, "ready");
}

function renderFavoritePlaces(favorites) {
  favoriteResultsElement.replaceChildren();
  resultMarkers.clearLayers();

  if (favorites.length === 0) {
    renderEmptyPlaceList(
      favoriteResultsElement,
      "No saved places",
      "Save a place from the map to find it again here.",
    );
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

    const { item, favoriteButton } = createPlaceListItem(place, marker);
    updateFavoriteButton(favoriteButton, place);
    favoriteButton.addEventListener("click", async () => {
      await toggleFavorite(place, favoriteButton);
      item.remove();
      marker.remove();

      if (favoriteResultsElement.children.length === 0) {
        setStatus("No favorite places saved yet.");
      }
    });

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
    item.className = "result-item result-item--history";

    const icon = createPlaceCategoryIcon("history");
    const content = document.createElement("div");
    content.className = "result-content";

    const link = document.createElement("a");
    link.className = "result-place-button";
    link.href = buildSearchUrl(search);
    link.textContent = formatSearchTitle(search);

    const meta = document.createElement("span");
    meta.className = "result-meta";
    meta.textContent = `${search.search_radius} m radius · ${search.result_count} places`;

    content.append(link, meta);
    item.append(icon, content);
    historyResultsElement.append(item);
  });

  map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
  setStatus(`${searches.length} recent searches.`);
}

function createPlaceListItem(place, marker, { includeDistance = false } = {}) {
  const item = document.createElement("li");
  item.className = "result-item";

  const icon = createPlaceCategoryIcon(place.category_group ?? place.category);
  const content = document.createElement("div");
  content.className = "result-content";

  const button = document.createElement("button");
  button.className = "result-place-button";
  button.type = "button";
  button.textContent = place.name;
  button.addEventListener("click", () => focusPlaceOnMap(item, marker, place));

  const meta = document.createElement("span");
  meta.className = "result-meta";
  meta.textContent = formatPlaceMeta(place, includeDistance);

  content.append(button, meta);
  if (place.address) {
    const address = document.createElement("span");
    address.className = "result-address";
    address.textContent = place.address;
    content.append(address);
  }

  const favoriteButton = document.createElement("button");
  favoriteButton.className = "favorite-button";
  favoriteButton.type = "button";

  item.addEventListener("mouseenter", () => item.classList.add("is-hovered"));
  item.addEventListener("mouseleave", () => item.classList.remove("is-hovered"));
  marker.on("mouseover", () => item.classList.add("is-hovered"));
  marker.on("mouseout", () => item.classList.remove("is-hovered"));

  item.append(icon, content, favoriteButton);

  return { item, favoriteButton };
}

function focusPlaceOnMap(item, marker, place) {
  activePlaceItem?.classList.remove("is-selected");
  item.classList.add("is-selected");
  activePlaceItem = item;
  map.setView([place.latitude, place.longitude], 17);
  marker.openPopup();
}

function formatPlaceMeta(place, includeDistance) {
  const details = [place.category_name];

  if (includeDistance && place.distance_meters !== null) {
    details.push(formatDistance(place.distance_meters));
  }

  return details.filter(Boolean).join(" · ");
}

function formatDistance(distanceMeters) {
  if (distanceMeters < 1000) {
    return `${distanceMeters} m`;
  }

  return `${(distanceMeters / 1000).toFixed(1)} km`;
}

function renderPlaceSkeletons(container) {
  if (container === null) {
    return;
  }

  container.replaceChildren();

  for (let index = 0; index < 3; index += 1) {
    const item = document.createElement("li");
    item.className = "result-item result-item--skeleton";
    item.innerHTML = `
      <span class="result-skeleton result-skeleton--icon"></span>
      <span class="result-content">
        <span class="result-skeleton result-skeleton--title"></span>
        <span class="result-skeleton result-skeleton--meta"></span>
      </span>
    `;
    container.append(item);
  }
}

function renderEmptyPlaceList(container, title, message) {
  container.replaceChildren();

  const item = document.createElement("li");
  item.className = "empty-results";
  item.innerHTML = `
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <circle cx="11" cy="11" r="6"></circle>
      <path d="m16 16 4 4"></path>
    </svg>
    <strong>${escapeHtml(title)}</strong>
    <span>${escapeHtml(message)}</span>
  `;
  container.append(item);
}

function createPlaceCategoryIcon(category) {
  const icon = document.createElement("span");
  icon.className = "place-category-icon";
  icon.setAttribute("aria-hidden", "true");

  const icons = {
    food: '<path d="M8 3v7M5 3v4a3 3 0 0 0 6 0V3M8 10v11M16 3v18M16 3c3 2 3 6 0 8"/>',
    mobility: '<path d="M5 15h14M7 15l1-6h8l1 6M7 18h.01M17 18h.01"/>',
    essentials: '<path d="M7 4h10v16H7zM10 8h4M10 12h4M10 16h4"/>',
    park: '<path d="M12 21V11M12 11c-5 0-7-3-7-7 5 0 7 3 7 7ZM12 15c4 0 7-2 7-6-4 0-7 2-7 6Z"/>',
    tourism: '<path d="M12 21V11M12 11c-5 0-7-3-7-7 5 0 7 3 7 7ZM12 15c4 0 7-2 7-6-4 0-7 2-7 6Z"/>',
    history: '<path d="M4 12a8 8 0 1 0 2-5.7M4 4v4h4M12 8v5l3 2"/>',
  };
  const path = icons[category] ?? '<path d="M12 21s7-5.3 7-11a7 7 0 1 0-14 0c0 5.7 7 11 7 11ZM12 12h.01"/>';
  icon.innerHTML = `<svg viewBox="0 0 24 24">${path}</svg>`;

  return icon;
}

function restoreSearchFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const lat = params.get("lat");
  const lng = params.get("lng");
  const searchRadius = params.get("search_radius");
  const category = params.get("category");
  const categoryGroup = params.get("category_group");
  const mapLayer = params.get("map_layer");

  if (lat === null || lng === null) {
    return false;
  }

  latInput.value = lat;
  lngInput.value = lng;

  if (searchRadius !== null) {
    radiusInput.value = searchRadius;
    radiusOutput.value = `${searchRadius} m`;
  }

  const restoredLayer = mapLayer ?? findLayerForFilter(category, categoryGroup);
  if (restoredLayer !== null && mapLayerSelect !== null) {
    mapLayerSelect.value = restoredLayer;
  }

  setSelectedLocation(Number(lat), Number(lng), true);
  return true;
}

function resetSearch() {
  currentSearchController?.abort();
  currentRefreshController?.abort();
  currentSearchController = null;
  currentRefreshController = null;
  currentSearchKey = "";
  hideRadiusCircle();
  submitButton.disabled = false;
  if (mapLayerSelect !== null) {
    mapLayerSelect.value = defaultMapLayer;
  }
  radiusInput.value = defaultRadius;
  radiusOutput.value = `${defaultRadius} m`;
  resultsElement.replaceChildren();
  resultMarkers.clearLayers();
  setSelectedLocation(defaultCenter[0], defaultCenter[1], false);
  map.setView(defaultCenter, 13);
  setStatus("");
}

function getDefaultCenter() {
  if (shell === null) {
    return fallbackCenter;
  }

  const lat = Number(shell.dataset.defaultLat);
  const lng = Number(shell.dataset.defaultLng);
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return [lat, lng];
  }

  return fallbackCenter;
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
      searchPlaces();
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

  if (moveMap) {
    searchPlaces();
  }
}

function setStatus(message, state = "") {
  if (statusElement !== null) {
    statusElement.textContent = message;
    if (state) {
      statusElement.dataset.state = state;
    } else {
      delete statusElement.dataset.state;
    }
  }
}


function applyNavigationState(isCollapsed) {
  if (shell === null) {
    return;
  }

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
  button.title = isFavorite ? "Remove from favorites" : "Save to favorites";
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

function findLayerForFilter(category, categoryGroup) {
  for (const [layer, filter] of Object.entries(mapLayers)) {
    if (category !== null && filter.category === category) {
      return layer;
    }
    if (categoryGroup !== null && filter.categoryGroup === categoryGroup) {
      return layer;
    }
  }

  return category === null && categoryGroup === null ? defaultMapLayer : null;
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
  if (map === null) {
    return;
  }

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
  if (radiusCircle === null) {
    return;
  }

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

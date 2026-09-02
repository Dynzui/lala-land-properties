(function () {
  function initMapPicker(picker) {
    if (!window.L || picker.dataset.ready === 'true') return;
    const mapName = picker.dataset.mapPicker;
    const latitude = document.querySelector(
      `[data-map-coordinate="${mapName}"][data-map-axis="latitude"]`
    );
    const longitude = document.querySelector(
      `[data-map-coordinate="${mapName}"][data-map-axis="longitude"]`
    );
    if (!latitude || !longitude) return;

    const canvas = picker.querySelector('.lala-map-canvas');
    const readout = picker.querySelector('.lala-map-readout');
    const clear = picker.querySelector('.lala-map-clear');
    const fallback = [10.6765, 122.9509];
    const hasPin = latitude.value !== '' && longitude.value !== '';
    const startingPoint = hasPin
      ? [Number(latitude.value), Number(longitude.value)]
      : fallback;
    const map = window.L.map(canvas).setView(startingPoint, hasPin ? 16 : 11);
    window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    let marker = null;
    function updateReadout() {
      readout.textContent = latitude.value && longitude.value
        ? `${Number(latitude.value).toFixed(6)}, ${Number(longitude.value).toFixed(6)}`
        : 'No pin selected';
    }
    function setPin(lat, lng) {
      latitude.value = lat.toFixed(6);
      longitude.value = lng.toFixed(6);
      marker = marker || window.L.marker([lat, lng]).addTo(map);
      marker.setLatLng([lat, lng]);
      updateReadout();
    }
    if (hasPin) setPin(startingPoint[0], startingPoint[1]);
    map.on('click', (event) => setPin(event.latlng.lat, event.latlng.lng));
    clear.addEventListener('click', () => {
      latitude.value = '';
      longitude.value = '';
      if (marker) {
        map.removeLayer(marker);
        marker = null;
      }
      updateReadout();
    });
    picker.dataset.ready = 'true';
    window.setTimeout(() => map.invalidateSize(), 0);
  }

  function initAll() {
    document.querySelectorAll('[data-map-picker]').forEach(initMapPicker);
  }
  document.addEventListener('DOMContentLoaded', initAll);
  document.addEventListener('w-formset:ready', initAll);
})();

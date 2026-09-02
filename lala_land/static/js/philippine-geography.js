(function () {
  const independent = '__independent__';

  function replaceOptions(select, values, placeholder, selected, labeler) {
    select.replaceChildren(new Option(placeholder, ''));
    values.forEach(function (value) {
      const option = new Option(labeler ? labeler(value) : value, value);
      option.selected = value === selected;
      select.add(option);
    });
  }

  async function initGeography() {
    const region = document.querySelector('[data-geography-field="region"]');
    const province = document.querySelector('[data-geography-field="province"]');
    const city = document.querySelector('[data-geography-field="city_municipality"]');
    if (!region || !province || !city || region.dataset.geographyReady === 'true') return;
    const response = await fetch(region.dataset.geographyUrl || '/geography/', {credentials: 'same-origin'});
    if (!response.ok) return;
    const data = await response.json();
    const initialRegion = region.value;
    const initialProvince = province.value;
    const initialCity = city.value;

    function updateProvinces(selected, keepCity) {
      const provinces = data.regions[region.value] || {};
      replaceOptions(province, Object.keys(provinces), 'Select a province', selected, function (value) {
        return value === independent ? 'Independent / highly urbanized city' : value;
      });
      updateCities(keepCity);
    }
    function updateCities(selected) {
      const provinces = data.regions[region.value] || {};
      const cities = provinces[province.value] || [];
      replaceOptions(city, cities, 'Select a city or municipality', selected);
    }
    region.addEventListener('change', function () { updateProvinces('', ''); });
    province.addEventListener('change', function () { updateCities(''); });
    updateProvinces(initialProvince, initialCity);
    region.dataset.geographyReady = 'true';
  }

  document.addEventListener('DOMContentLoaded', initGeography);
  document.addEventListener('w-formset:ready', initGeography);
})();

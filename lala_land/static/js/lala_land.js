const toggle = document.querySelector('.nav-toggle');
const nav = document.querySelector('.site-nav');
if (toggle && nav) toggle.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  toggle.setAttribute('aria-expanded', String(open));
  toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  toggle.classList.toggle('is-open', open);
});

if (toggle && nav) {
  nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
    nav.classList.remove('open');
    toggle.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-label', 'Open navigation');
  }));
}

const propertySearch = document.querySelector('.property-search');
const mobileFilterButton = document.querySelector('.mobile-filter-fab');
const filterClose = document.querySelector('.filter-close');
const advancedFilters = document.querySelector('.advanced-filters');

if (advancedFilters) {
  const mobileQuery = window.matchMedia('(max-width: 680px)');
  const syncAdvancedFilters = () => {
    if (!mobileQuery.matches) advancedFilters.open = true;
    else if (advancedFilters.dataset.hasActiveFilters !== 'true') advancedFilters.open = false;
  };
  syncAdvancedFilters();
  mobileQuery.addEventListener('change', syncAdvancedFilters);
}

if (propertySearch && mobileFilterButton && filterClose) {
  const setFilterOpen = (open) => {
    propertySearch.classList.toggle('filter-panel-open', open);
    document.body.classList.toggle('filter-panel-open', open);
    mobileFilterButton.setAttribute('aria-expanded', String(open));
    if (open) propertySearch.querySelector('select, input, button')?.focus();
    else mobileFilterButton.focus();
  };

  mobileFilterButton.addEventListener('click', () => setFilterOpen(true));
  filterClose.addEventListener('click', () => setFilterOpen(false));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && propertySearch.classList.contains('filter-panel-open')) {
      setFilterOpen(false);
    }
  });

  const observer = new IntersectionObserver(([entry]) => {
    mobileFilterButton.classList.toggle(
      'is-visible',
      !entry.isIntersecting && entry.boundingClientRect.top < 0
    );
  });
  observer.observe(propertySearch);
}

const inquiryForm = document.querySelector('.contact-form');
if (inquiryForm) {
  const singleLineFields = inquiryForm.querySelectorAll(
    'input[type="text"], input[type="email"], input[type="tel"]'
  );
  const focusableFields = Array.from(
    inquiryForm.querySelectorAll('input:not([type="hidden"]), select, textarea, button')
  ).filter((field) => !field.disabled && field.offsetParent !== null);

  singleLineFields.forEach((field) => {
    field.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' || event.isComposing) return;
      event.preventDefault();
      const currentIndex = focusableFields.indexOf(field);
      const nextField = focusableFields[currentIndex + 1];
      if (nextField) nextField.focus();
    });
  });
}

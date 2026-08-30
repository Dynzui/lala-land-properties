const toggle = document.querySelector('.nav-toggle');
const nav = document.querySelector('.site-nav');
if (toggle && nav) toggle.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  toggle.setAttribute('aria-expanded', String(open));
});

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

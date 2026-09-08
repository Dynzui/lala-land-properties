document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-carousel-prev], [data-carousel-next]").forEach((button) => {
    button.addEventListener("click", () => {
      const targetId = button.dataset.carouselPrev || button.dataset.carouselNext;
      const track = document.getElementById(targetId);
      if (!track) return;
      const direction = button.hasAttribute("data-carousel-prev") ? -1 : 1;
      track.scrollBy({ left: direction * track.clientWidth * 0.82, behavior: "smooth" });
    });
  });

  const slides = [...document.querySelectorAll(".gallery-slide")];
  const dialog = document.getElementById("gallery-dialog");
  if (dialog && slides.length) {
    const image = dialog.querySelector("img");
    const caption = dialog.querySelector("figcaption");
    let activeIndex = 0;
    const showImage = (index) => {
      activeIndex = (index + slides.length) % slides.length;
      const slide = slides[activeIndex];
      image.src = slide.dataset.fullSrc;
      image.alt = slide.dataset.alt || "";
      caption.textContent = slide.dataset.caption || `${activeIndex + 1} of ${slides.length}`;
    };
    slides.forEach((slide, index) => slide.addEventListener("click", () => {
      showImage(index);
      dialog.showModal();
    }));
    const galleryOpen = document.querySelector("[data-gallery-open]");
    if (galleryOpen) galleryOpen.addEventListener("click", () => {
      showImage(0);
      dialog.showModal();
    });
    dialog.querySelector(".gallery-dialog-close").addEventListener("click", () => dialog.close());
    dialog.querySelector(".gallery-dialog-prev").addEventListener("click", () => showImage(activeIndex - 1));
    dialog.querySelector(".gallery-dialog-next").addEventListener("click", () => showImage(activeIndex + 1));
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") showImage(activeIndex - 1);
      if (event.key === "ArrowRight") showImage(activeIndex + 1);
    });
  }

  const floorPlanDialog = document.getElementById("floor-plan-dialog");
  if (floorPlanDialog) {
    const image = floorPlanDialog.querySelector("img");
    const caption = floorPlanDialog.querySelector("figcaption");
    document.querySelectorAll("[data-floor-plan-src]").forEach((button) => {
      button.addEventListener("click", () => {
        image.src = button.dataset.floorPlanSrc;
        image.alt = button.dataset.floorPlanAlt || "";
        caption.textContent = button.dataset.floorPlanCaption || "Floor plan";
        floorPlanDialog.showModal();
      });
    });
    floorPlanDialog.querySelector(".floor-plan-dialog-close").addEventListener(
      "click",
      () => floorPlanDialog.close()
    );
    floorPlanDialog.addEventListener("click", (event) => {
      if (event.target === floorPlanDialog) floorPlanDialog.close();
    });
  }
});

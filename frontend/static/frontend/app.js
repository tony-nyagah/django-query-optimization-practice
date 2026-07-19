// Animate query stat badges on page load
document.addEventListener("DOMContentLoaded", () => {
    const statEls = document.querySelectorAll(".stat.queries");
    statEls.forEach((el) => {
        el.style.transition = "transform 0.3s ease";
        el.style.transform = "scale(1.15)";
        setTimeout(() => {
            el.style.transform = "scale(1)";
        }, 300);
    });

    // Highlight savings row
    const savings = document.querySelector(".savings");
    if (savings) {
        savings.style.transition = "background 0.5s";
        savings.style.background = "rgba(63, 185, 80, 0.18)";
        setTimeout(() => {
            savings.style.background = "";
        }, 800);
    }
});

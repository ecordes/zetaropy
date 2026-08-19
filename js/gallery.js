/* =========================================
   ZETAROPY
   Gallery wing: the close look

   Clicking a framed work opens it large with
   its placard. Arrow keys / buttons walk the
   wall; Escape or the backdrop steps back.
   ========================================= */

(function () {
    var works = Array.prototype.slice.call(
        document.querySelectorAll(".artwork")
    );
    if (works.length === 0) return;

    var current = 0;

    /* Build the lightbox once. */
    var box = document.createElement("div");
    box.className = "lightbox";
    box.hidden = true;
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "Artwork, enlarged");
    box.innerHTML =
        '<button class="lightbox-close" aria-label="Close">✕</button>' +
        '<button class="lightbox-prev" aria-label="Previous work">←</button>' +
        '<button class="lightbox-next" aria-label="Next work">→</button>' +
        "<img alt=\"\">" +
        '<figcaption class="placard"></figcaption>';
    document.body.appendChild(box);

    var boxImg = box.querySelector("img");
    var boxPlacard = box.querySelector(".placard");
    var lastFocused = null;

    function show(index) {
        current = (index + works.length) % works.length;
        var art = works[current];
        var img = art.querySelector("img");
        var placard = art.querySelector(".placard");

        boxImg.src = img.currentSrc || img.src;
        boxImg.alt = img.alt;
        boxPlacard.innerHTML = placard.innerHTML;
    }

    function open(index) {
        lastFocused = document.activeElement;
        show(index);
        box.hidden = false;
        document.body.classList.add("lightbox-open");
        box.querySelector(".lightbox-close").focus();
    }

    function close() {
        box.hidden = true;
        document.body.classList.remove("lightbox-open");
        if (lastFocused) lastFocused.focus();
    }

    works.forEach(function (art, index) {
        var frame = art.querySelector(".artwork-frame");
        frame.addEventListener("click", function () {
            open(index);
        });
    });

    box.querySelector(".lightbox-close").addEventListener("click", close);
    box.querySelector(".lightbox-prev").addEventListener("click", function () {
        show(current - 1);
    });
    box.querySelector(".lightbox-next").addEventListener("click", function () {
        show(current + 1);
    });

    /* Backdrop click closes; clicks on the work itself do not. */
    box.addEventListener("click", function (event) {
        if (event.target === box) close();
    });

    document.addEventListener("keydown", function (event) {
        if (box.hidden) return;
        if (event.key === "Escape") close();
        if (event.key === "ArrowLeft") show(current - 1);
        if (event.key === "ArrowRight") show(current + 1);
    });
})();

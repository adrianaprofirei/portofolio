// Demo videos: muted loops that play only while on screen.
// Reduced-motion users (and anyone without this script) keep the native controls.
(function () {
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var videos = document.querySelectorAll("video.js-autoplay");
  if (!videos.length || reduce || !("IntersectionObserver" in window)) return;

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      var v = e.target;
      if (e.isIntersecting) {
        if (v.preload === "none") v.preload = "auto";
        var p = v.play();
        if (p && p.catch) p.catch(function () { v.controls = true; });
      } else {
        v.pause();
      }
    });
  }, { rootMargin: "100px 0px", threshold: 0.25 });

  videos.forEach(function (v) {
    v.controls = false;
    v.muted = true;
    io.observe(v);
  });
})();

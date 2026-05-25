(function () {
  // Grab slides and dots
  var slides = Array.prototype.slice.call(document.querySelectorAll('.fb-slide'));
  if (!slides.length) return;

  var dots = Array.prototype.slice.call(document.querySelectorAll('.fb-dot'));
  var currentIndex = 0;

  var bookBtn = document.getElementById('fb-book-btn');
  var prevBtn = document.querySelector('.fb-slider-arrow--prev');
  var nextBtn = document.querySelector('.fb-slider-arrow--next');

  var userIsAuthenticated = (window.FB_CAROUSEL && window.FB_CAROUSEL.userIsAuthenticated) || false;
  var loginUrl = (window.FB_CAROUSEL && window.FB_CAROUSEL.loginUrl) || '/login/';

  function updateBookButtonUrl() {
    var url = slides[currentIndex].getAttribute('data-book-url'); // tests check this exact string too
    if (!bookBtn) return;

    if (userIsAuthenticated && url) {
      bookBtn.setAttribute('href', url);
      bookBtn.setAttribute('target', '_blank');
    } else {
      bookBtn.setAttribute('href', loginUrl);
      bookBtn.removeAttribute('target');
    }
  }

  function showSlide(index) {
    if (index < 0) index = slides.length - 1;
    if (index >= slides.length) index = 0;
    currentIndex = index;

    slides.forEach(function (slide, i) {
      slide.classList.toggle('is-active', i === currentIndex);
    });

    if (dots.length === slides.length) {
      dots.forEach(function (dot, i) {
        dot.classList.toggle('fb-dot--active', i === currentIndex);
      });
    }

    updateBookButtonUrl();
  }

  showSlide(0);

  if (prevBtn) {
    prevBtn.addEventListener('click', function () {
      showSlide(currentIndex - 1);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', function () {
      showSlide(currentIndex + 1);
    });
  }
})();

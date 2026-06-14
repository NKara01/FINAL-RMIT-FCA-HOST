// anthony doan and chaniru can decide
let slideIndex = 1;
showSlides(slideIndex);



function showSlides(n) {
  let i;
  let slides = document.getElementsByClassName("mySlides");
  let dots = document.getElementsByClassName("dot");
  for (i = 0; i < slides.length; i++) {
    slides[i].style.display = "none";  
  }
  slideIndex++;
  if (slideIndex > slides.length) {slideIndex = 1}    
  for (i = 0; i < dots.length; i++) {
    dots[i].className = dots[i].className.replace(" active", "");
  }
  slides[slideIndex-1].style.display = "block";  
  dots[slideIndex-1].className += " active";
  setTimeout(showSlides, 7000);
}


function toggleSearch() {
            document.getElementById("search-overlay").classList.add("active");}

function closeSearch() {
            document.getElementById("search-overlay").classList.remove("active");}


let index = 0;




const newscards = document.querySelectorAll('.news-card');

function showPairNews() {
    newscards.forEach(card => card.style.display = 'none');
    if (newscards[index]) newscards[index].style.display = 'block';
    if (newscards[index + 1]) newscards[index + 1].style.display = 'block';
}

function gonextnews(){
    index += 2;
    if (index >= newscards.length) {index = 0;}
    showPairNews() ;
};
function gobacknews(){
    index -= 2;
      if (index < 0) {
        index = Math.floor((newscards.length - 1) / 2) * 2;
    }
    showPairNews() ;
};

showPairNews();








const eventscards = document.querySelectorAll('.event-card');

function showPairEvents() {
    eventscards.forEach(card => card.style.display = 'none');
    if (eventscards[index]) eventscards[index].style.display = 'block';
    if (eventscards[index + 1]) eventscards[index + 1].style.display = 'block';
}

function gonextevents(){
    index += 2;
    if (index >= eventscards.length) {index = 0;}
    showPairEvents();
};
function gobackevents(){
    index -= 2;
      if (index < 0) {
        index = Math.floor((eventscards.length - 1) / 2) * 2;
    }
    showPairEvents();
};



showPairEvents();




const shapeSlides = document.querySelectorAll('.poly1');
const nextButton = document.querySelector('.polybutton');
const titleEl = document.querySelector('#program-title');
const descEl = document.querySelector('#program-desc');

if (shapeSlides.length && nextButton && titleEl && descEl) {
  let currentIndex = 0;
  const totalSlides = shapeSlides.length;

  function updateAllCarousels() {
    shapeSlides.forEach((slide, index) => {
      slide.classList.remove('active', 'behind-1', 'behind-2');

      if (index === currentIndex) {
        slide.classList.add('active');
      } else if (index === (currentIndex + 1) % totalSlides) {
        slide.classList.add('behind-1');
      } else if (index === (currentIndex + 2) % totalSlides) {
        slide.classList.add('behind-2');
      }
    });

    const activeSlide = shapeSlides[currentIndex];
    titleEl.textContent = activeSlide.dataset.title || '';
    descEl.textContent = activeSlide.dataset.desc || '';
  }

  nextButton.addEventListener('click', () => {
    currentIndex = (currentIndex + 1) % totalSlides;
    updateAllCarousels();
  });

  updateAllCarousels();
}

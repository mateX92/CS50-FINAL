let stars = document.querySelectorAll(".star")
let star1 = document.querySelector("#star1")
let star2 = document.querySelector("#star2")
let star3 = document.querySelector("#star3")
let star4 = document.querySelector("#star4")
let star5 = document.querySelector("#star5")

function fillStar(index) {
    for (let i = 1; i <= index; i++) {
        let icon = document.getElementById(`star${i}`); /* selects star1 first, then star2, up to starindex */
        icon.classList.add('star-filled'); /* adds class to each star */
    }
}

function clearStar(i) {
    for (i; i >= 1; i--) {
        let icon = document.getElementById(`star${i}`);
        icon.classList.remove('star-filled');
    }
};

stars.forEach((star, index) => {
    star.addEventListener('mouseover', function() {
        /* Fill the star selected (and any previous as fillStar is a loop up until the index + 1) */
        fillStar(index + 1);
    })
    star.addEventListener('mouseout', function() {
        clearStar(index + 1);
    })
});


/* Activate burger menu */

let menuButton = document.querySelector("#burger-menu");
let mobileNav = document.querySelector("#mobile-nav");
let closeBtn = document.querySelector("#close-btn");

menuButton.addEventListener('click', function() {
    if (mobileNav.style.display = 'none'){
        mobileNav.style.display = 'flex';
    }
})

closeBtn.addEventListener('click', function() {
    mobileNav.style.display = 'none';
})
let stars = document.querySelectorAll(".star")

stars.forEach((star) => {
    star.addEventListener('mouseover', function fillStar() {
        star.style.backgroundColor = 'grey';
        star.style.fill = 'red';
    })
})
document.addEventListener("DOMContentLoaded", function () {

    // Mobile menu

    const menuButton = document.getElementById("menuButton");
    const navLinks = document.querySelector(".nav-links");

    if (menuButton && navLinks) {

        menuButton.addEventListener("click", function () {

            navLinks.classList.toggle("show");

        });

    }


    // Auto hide flash messages

    const messages = document.querySelectorAll(".flash-message");

    messages.forEach(function (message) {

        setTimeout(function () {

            message.style.display = "none";

        }, 4000);

    });


    // Confirm before opening external job links

    const externalLinks =
        document.querySelectorAll("a[data-external='true']");

    externalLinks.forEach(function (link) {

        link.addEventListener("click", function (event) {

            const confirmOpen =
                confirm(
                    "You are about to open an external website. Continue?"
                );

            if (!confirmOpen) {

                event.preventDefault();

            }

        });

    });

});
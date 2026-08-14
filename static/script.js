/* =========================================================
   NAFIZ AHMED — PREMIUM PORTFOLIO
   JavaScript
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
       01. ELEMENTS
       ===================================================== */

    const header = document.querySelector(".site-header");
    const menuToggle = document.querySelector(".menu-toggle");
    const navLinks = document.querySelector(".nav-links");

    const navItems = document.querySelectorAll(".nav-links a");

    const revealElements = document.querySelectorAll(".reveal");

    const backTop = document.querySelector(".back-top");

    const newsletterForm =
        document.querySelector(".newsletter-form");

    const contactForm =
        document.querySelector(".contact-form");


    /* =====================================================
       02. HEADER SCROLL EFFECT
       ===================================================== */

    function handleHeaderScroll() {

        if (!header) return;

        if (window.scrollY > 40) {

            header.classList.add("scrolled");

        } else {

            header.classList.remove("scrolled");

        }

    }

    window.addEventListener(
        "scroll",
        handleHeaderScroll,
        { passive: true }
    );

    handleHeaderScroll();


    /* =====================================================
       03. MOBILE MENU
       ===================================================== */

    if (menuToggle && navLinks) {

        menuToggle.addEventListener("click", () => {

            const isOpen =
                navLinks.classList.toggle("open");

            menuToggle.classList.toggle(
                "open",
                isOpen
            );

            menuToggle.setAttribute(
                "aria-expanded",
                isOpen
            );

        });


        /* Close menu after clicking a link */

        navItems.forEach((link) => {

            link.addEventListener("click", () => {

                navLinks.classList.remove("open");

                menuToggle.classList.remove("open");

                menuToggle.setAttribute(
                    "aria-expanded",
                    "false"
                );

            });

        });


        /* Close menu when clicking outside */

        document.addEventListener("click", (event) => {

            const clickedInsideMenu =
                navLinks.contains(event.target);

            const clickedButton =
                menuToggle.contains(event.target);

            if (
                !clickedInsideMenu &&
                !clickedButton
            ) {

                navLinks.classList.remove("open");

                menuToggle.classList.remove("open");

                menuToggle.setAttribute(
                    "aria-expanded",
                    "false"
                );

            }

        });

    }


    /* =====================================================
       04. ACTIVE NAVIGATION
       ===================================================== */

    const sections =
        document.querySelectorAll("section[id]");


    function updateActiveNav() {

        const scrollPosition =
            window.scrollY + 150;


        sections.forEach((section) => {

            const sectionTop =
                section.offsetTop;

            const sectionHeight =
                section.offsetHeight;

            const sectionId =
                section.getAttribute("id");


            if (
                scrollPosition >= sectionTop &&
                scrollPosition <
                    sectionTop + sectionHeight
            ) {

                navItems.forEach((link) => {

                    link.classList.remove("active");

                });


                const activeLink =
                    document.querySelector(
                        `.nav-links a[href="#${sectionId}"]`
                    );


                if (activeLink) {

                    activeLink.classList.add(
                        "active"
                    );

                }

            }

        });

    }


    window.addEventListener(
        "scroll",
        updateActiveNav,
        { passive: true }
    );

    updateActiveNav();


    /* =====================================================
       05. SMOOTH SCROLL
       ===================================================== */

    document
        .querySelectorAll('a[href^="#"]')
        .forEach((link) => {

            link.addEventListener(
                "click",
                function (event) {

                    const targetId =
                        this.getAttribute("href");

                    if (
                        !targetId ||
                        targetId === "#"
                    ) {

                        return;

                    }


                    const target =
                        document.querySelector(
                            targetId
                        );


                    if (!target) {

                        return;

                    }


                    event.preventDefault();


                    target.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });

                }
            );

        });


    /* =====================================================
       06. SCROLL REVEAL
       ===================================================== */

    if (
        "IntersectionObserver" in window
    ) {

        const revealObserver =
            new IntersectionObserver(
                (entries, observer) => {

                    entries.forEach((entry) => {

                        if (
                            entry.isIntersecting
                        ) {

                            entry.target.classList.add(
                                "visible"
                            );

                            observer.unobserve(
                                entry.target
                            );

                        }

                    });

                },
                {
                    threshold: 0.12,
                    rootMargin:
                        "0px 0px -50px 0px"
                }
            );


        revealElements.forEach((element) => {

            revealObserver.observe(element);

        });

    } else {

        revealElements.forEach((element) => {

            element.classList.add("visible");

        });

    }


    /* =====================================================
       07. BACK TO TOP
       ===================================================== */

    if (backTop) {

        backTop.addEventListener(
            "click",
            (event) => {

                event.preventDefault();

                window.scrollTo({
                    top: 0,
                    behavior: "smooth"
                });

            }
        );

    }


    /* =====================================================
       08. NEWSLETTER FORM
       ===================================================== */

    if (newsletterForm) {

        newsletterForm.addEventListener(
            "submit",
            (event) => {

                event.preventDefault();


                const emailInput =
                    newsletterForm.querySelector(
                        'input[type="email"]'
                    );


                if (!emailInput) {

                    return;

                }


                const email =
                    emailInput.value.trim();


                if (!email) {

                    alert(
                        "Please enter your email address."
                    );

                    return;

                }


                if (
                    !isValidEmail(email)
                ) {

                    alert(
                        "Please enter a valid email address."
                    );

                    return;

                }


                alert(
                    "Thank you for subscribing!"
                );


                newsletterForm.reset();

            }
        );

    }


    /* =====================================================
       09. CONTACT FORM
       ===================================================== */

    if (contactForm) {

        contactForm.addEventListener(
            "submit",
            (event) => {

                event.preventDefault();


                const nameInput =
                    contactForm.querySelector(
                        'input[name="name"]'
                    );


                const emailInput =
                    contactForm.querySelector(
                        'input[name="email"]'
                    );


                const subjectInput =
                    contactForm.querySelector(
                        'input[name="subject"]'
                    );


                const messageInput =
                    contactForm.querySelector(
                        "textarea"
                    );


                const name =
                    nameInput
                        ? nameInput.value.trim()
                        : "";


                const email =
                    emailInput
                        ? emailInput.value.trim()
                        : "";


                const subject =
                    subjectInput
                        ? subjectInput.value.trim()
                        : "";


                const message =
                    messageInput
                        ? messageInput.value.trim()
                        : "";


                if (!name) {

                    alert(
                        "Please enter your name."
                    );

                    return;

                }


                if (!email) {

                    alert(
                        "Please enter your email."
                    );

                    return;

                }


                if (
                    !isValidEmail(email)
                ) {

                    alert(
                        "Please enter a valid email."
                    );

                    return;

                }


                if (!subject) {

                    alert(
                        "Please enter a subject."
                    );

                    return;

                }


                if (!message) {

                    alert(
                        "Please enter your message."
                    );

                    return;

                }


                alert(
                    "Thank you, " +
                    name +
                    "! Your message has been received."
                );


                contactForm.reset();

            }
        );

    }


    /* =====================================================
       10. EMAIL VALIDATION
       ===================================================== */

    function isValidEmail(email) {

        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/
            .test(email);

    }


    /* =====================================================
       11. BUTTON RIPPLE EFFECT
       ===================================================== */

    const buttons =
        document.querySelectorAll(
            ".btn, .submit-button"
        );


    buttons.forEach((button) => {

        button.addEventListener(
            "click",
            function (event) {

                const ripple =
                    document.createElement("span");


                const rect =
                    this.getBoundingClientRect();


                const size =
                    Math.max(
                        rect.width,
                        rect.height
                    );


                ripple.style.position =
                    "absolute";

                ripple.style.width =
                    `${size}px`;

                ripple.style.height =
                    `${size}px`;

                ripple.style.left =
                    `${event.clientX - rect.left - size / 2}px`;

                ripple.style.top =
                    `${event.clientY - rect.top - size / 2}px`;

                ripple.style.borderRadius =
                    "50%";

                ripple.style.background =
                    "rgba(255,255,255,0.25)";

                ripple.style.pointerEvents =
                    "none";

                ripple.style.transform =
                    "scale(0)";

                ripple.style.opacity =
                    "1";

                ripple.style.transition =
                    "transform 0.6s ease, opacity 0.6s ease";


                this.appendChild(ripple);


                requestAnimationFrame(() => {

                    ripple.style.transform =
                        "scale(2)";

                    ripple.style.opacity =
                        "0";

                });


                setTimeout(() => {

                    ripple.remove();

                }, 650);

            }
        );

    });


    /* =====================================================
       12. CURRENT YEAR
       ===================================================== */

    const yearElements =
        document.querySelectorAll(
            "[data-year]"
        );


    yearElements.forEach((element) => {

        element.textContent =
            new Date().getFullYear();

    });


    /* =====================================================
       13. PROFILE IMAGE FALLBACK
       ===================================================== */

    const profileImage =
        document.querySelector(".profile");


    if (profileImage) {

        profileImage.addEventListener(
            "error",
            () => {

                profileImage.style.display =
                    "none";

                const wrapper =
                    document.querySelector(
                        ".profile-wrapper"
                    );


                if (wrapper) {

                    wrapper.classList.add(
                        "profile-missing"
                    );

                }

            }
        );

    }


    /* =====================================================
       14. ESCAPE KEY — CLOSE MOBILE MENU
       ===================================================== */

    document.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key === "Escape"
            ) {

                if (navLinks) {

                    navLinks.classList.remove(
                        "open"
                    );

                }


                if (menuToggle) {

                    menuToggle.classList.remove(
                        "open"
                    );

                    menuToggle.setAttribute(
                        "aria-expanded",
                        "false"
                    );

                }

            }

        }
    );


    /* =====================================================
       15. PARALLAX — DESKTOP ONLY
       ===================================================== */

    const hero =
        document.querySelector(".hero");

    const heroContent =
        document.querySelector(".hero-content");


    if (
        hero &&
        heroContent &&
        window.matchMedia(
            "(hover: hover) and (pointer: fine)"
        ).matches
    ) {

        let ticking = false;


        hero.addEventListener(
            "mousemove",
            (event) => {

                if (ticking) return;


                window.requestAnimationFrame(() => {

                    const rect =
                        hero.getBoundingClientRect();


                    const x =
                        event.clientX -
                        rect.left -
                        rect.width / 2;


                    const y =
                        event.clientY -
                        rect.top -
                        rect.height / 2;


                    const moveX =
                        x / rect.width * 8;


                    const moveY =
                        y / rect.height * 5;


                    heroContent.style.transform =
                        `translate(${moveX}px, ${moveY}px)`;


                    ticking = false;

                });


                ticking = true;

            }
        );


        hero.addEventListener(
            "mouseleave",
            () => {

                heroContent.style.transform =
                    "translate(0, 0)";

            }
        );

    }


    /* =====================================================
       16. PREVENT FORM DOUBLE SUBMIT
       ===================================================== */

    const forms =
        document.querySelectorAll("form");


    forms.forEach((form) => {

        form.addEventListener(
            "submit",
            () => {

                const submitButton =
                    form.querySelector(
                        'button[type="submit"]'
                    );


                if (!submitButton) {

                    return;

                }


                setTimeout(() => {

                    submitButton.blur();

                }, 100);

            }
        );

    });


    /* =====================================================
       17. ACCESSIBILITY
       ===================================================== */

    if (menuToggle) {

        if (
            !menuToggle.hasAttribute(
                "aria-label"
            )
        ) {

            menuToggle.setAttribute(
                "aria-label",
                "Open navigation menu"
            );

        }


        if (
            !menuToggle.hasAttribute(
                "aria-expanded"
            )
        ) {

            menuToggle.setAttribute(
                "aria-expanded",
                "false"
            );

        }

    }


    /* =====================================================
       18. PAGE LOADED
       ===================================================== */

    document.body.classList.add(
        "page-loaded"
    );


    console.log(
        "NAFIZ AHMED Portfolio loaded successfully."
    );

});
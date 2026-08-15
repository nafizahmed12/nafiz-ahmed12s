/* =========================================================
   NAFIZ AHMED — PREMIUM PORTFOLIO
   JavaScript
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {
    const header = document.querySelector(".site-header");
    const menuToggle = document.querySelector(".menu-toggle");
    const navLinks = document.querySelector(".nav-links");
    const navItems = document.querySelectorAll(".nav-links a");
    const revealElements = document.querySelectorAll(".reveal");
    const backTop = document.querySelector(".back-top");
    const newsletterForm = document.querySelector(".newsletter-form");
    const contactForm = document.querySelector(".contact-form");

    function handleHeaderScroll() {
        if (!header) return;
        header.classList.toggle("scrolled", window.scrollY > 40);
    }

    window.addEventListener("scroll", handleHeaderScroll, { passive: true });
    handleHeaderScroll();

    if (menuToggle && navLinks) {
        menuToggle.addEventListener("click", () => {
            const isOpen = navLinks.classList.toggle("open");
            menuToggle.classList.toggle("open", isOpen);
            menuToggle.setAttribute("aria-expanded", String(isOpen));
        });

        navItems.forEach((link) => {
            link.addEventListener("click", () => {
                navLinks.classList.remove("open");
                menuToggle.classList.remove("open");
                menuToggle.setAttribute("aria-expanded", "false");
            });
        });

        document.addEventListener("click", (event) => {
            if (!navLinks.contains(event.target) && !menuToggle.contains(event.target)) {
                navLinks.classList.remove("open");
                menuToggle.classList.remove("open");
                menuToggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    const sections = document.querySelectorAll("section[id]");

    function updateActiveNav() {
        const scrollPosition = window.scrollY + 150;
        sections.forEach((section) => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute("id");

            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navItems.forEach((link) => link.classList.remove("active"));
                const activeLink = document.querySelector(`.nav-links a[href="#${sectionId}"]`);
                if (activeLink) activeLink.classList.add("active");
            }
        });
    }

    window.addEventListener("scroll", updateActiveNav, { passive: true });
    updateActiveNav();

    document.querySelectorAll('a[href^="#"]').forEach((link) => {
        link.addEventListener("click", function (event) {
            const targetId = this.getAttribute("href");
            if (!targetId || targetId === "#") return;

            const target = document.querySelector(targetId);
            if (!target) return;

            event.preventDefault();
            target.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    });

    if ("IntersectionObserver" in window) {
        const revealObserver = new IntersectionObserver(
            (entries, observer) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("visible");
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12, rootMargin: "0px 0px -50px 0px" }
        );

        revealElements.forEach((element) => revealObserver.observe(element));
    } else {
        revealElements.forEach((element) => element.classList.add("visible"));
    }

    if (backTop) {
        backTop.addEventListener("click", (event) => {
            event.preventDefault();
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    }

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    async function submitForm(form, url, prepareData, successMessage) {
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton ? submitButton.textContent : "";

        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = "Sending...";
        }

        try {
            const formData = new FormData(form);
            prepareData(formData);

            const response = await fetch(url, {
                method: "POST",
                body: formData,
                credentials: "same-origin",
                headers: { "X-Requested-With": "XMLHttpRequest" }
            });

            const text = await response.text();

            if (!response.ok) {
                throw new Error(text || "Request failed.");
            }

            alert(successMessage || text || "Request completed successfully.");
            form.reset();
        } catch (error) {
            console.error("Form submission error:", error);
            alert("Something went wrong. Please try again.");
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        }
    }

    /* =====================================================
       NEWSLETTER — REAL BACKEND SUBMISSION
       ===================================================== */
    if (newsletterForm) {
        newsletterForm.addEventListener("submit", (event) => {
            event.preventDefault();

            const emailInput = newsletterForm.querySelector('input[type="email"]');
            const email = emailInput ? emailInput.value.trim() : "";

            if (!email || !isValidEmail(email)) {
                alert("Please enter a valid email address.");
                return;
            }

            submitForm(
                newsletterForm,
                "/subscribe",
                (formData) => {
                    formData.set("subscriber_email", email);
                },
                "Thank you for subscribing!"
            );
        });
    }

    /* =====================================================
       CONTACT — REAL BACKEND SUBMISSION
       ===================================================== */
    if (contactForm) {
        contactForm.addEventListener("submit", (event) => {
            event.preventDefault();

            const nameInput = contactForm.querySelector('input[name="name"]');
            const emailInput = contactForm.querySelector('input[name="email"]');
            const messageInput = contactForm.querySelector("textarea");

            const name = nameInput ? nameInput.value.trim() : "";
            const email = emailInput ? emailInput.value.trim() : "";
            const message = messageInput ? messageInput.value.trim() : "";

            if (!name) {
                alert("Please enter your name.");
                return;
            }
            if (!email || !isValidEmail(email)) {
                alert("Please enter a valid email address.");
                return;
            }
            if (!message) {
                alert("Please enter your message.");
                return;
            }

            submitForm(
                contactForm,
                "/contact",
                () => {},
                `Thank you, ${name}! Your message has been received.`
            );
        });
    }

    const buttons = document.querySelectorAll(".btn, .submit-button");
    buttons.forEach((button) => {
        button.addEventListener("click", function (event) {
            const ripple = document.createElement("span");
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);

            ripple.style.position = "absolute";
            ripple.style.width = `${size}px`;
            ripple.style.height = `${size}px`;
            ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
            ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
            ripple.style.borderRadius = "50%";
            ripple.style.background = "rgba(255,255,255,0.25)";
            ripple.style.pointerEvents = "none";
            ripple.style.transform = "scale(0)";
            ripple.style.opacity = "1";
            ripple.style.transition = "transform 0.6s ease, opacity 0.6s ease";

            this.appendChild(ripple);
            requestAnimationFrame(() => {
                ripple.style.transform = "scale(2)";
                ripple.style.opacity = "0";
            });
            setTimeout(() => ripple.remove(), 650);
        });
    });

    document.querySelectorAll("[data-year]").forEach((element) => {
        element.textContent = new Date().getFullYear();
    });

    const profileImage = document.querySelector(".profile");
    if (profileImage) {
        profileImage.addEventListener("error", () => {
            profileImage.style.display = "none";
            const wrapper = document.querySelector(".profile-wrapper");
            if (wrapper) wrapper.classList.add("profile-missing");
        });
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            if (navLinks) navLinks.classList.remove("open");
            if (menuToggle) {
                menuToggle.classList.remove("open");
                menuToggle.setAttribute("aria-expanded", "false");
            }
        }
    });

    const hero = document.querySelector(".hero");
    const heroContent = document.querySelector(".hero-content");

    if (hero && heroContent && window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
        let ticking = false;

        hero.addEventListener("mousemove", (event) => {
            if (ticking) return;

            window.requestAnimationFrame(() => {
                const rect = hero.getBoundingClientRect();
                const x = event.clientX - rect.left - rect.width / 2;
                const y = event.clientY - rect.top - rect.height / 2;
                heroContent.style.transform = `translate(${(x / rect.width) * 8}px, ${(y / rect.height) * 5}px)`;
                ticking = false;
            });

            ticking = true;
        });

        hero.addEventListener("mouseleave", () => {
            heroContent.style.transform = "translate(0, 0)";
        });
    }

    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", () => {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                setTimeout(() => submitButton.blur(), 100);
            }
        });
    });

    if (menuToggle) {
        menuToggle.setAttribute("aria-label", menuToggle.getAttribute("aria-label") || "Open navigation menu");
        menuToggle.setAttribute("aria-expanded", menuToggle.getAttribute("aria-expanded") || "false");
    }

    document.body.classList.add("page-loaded");
    console.log("NAFIZ AHMED Portfolio loaded successfully.");
});

document.addEventListener("DOMContentLoaded", function () {
    // Section titles you want to toggle
    const sections = ["Personal info", "Permissions", "Important dates"];

    sections.forEach(title => {
        const fs = Array.from(document.querySelectorAll("fieldset.module.aligned"))
            .find(fs => fs.querySelector("h2")?.innerText.trim() === title);

        if (fs) {
            // Start hidden
            fs.style.display = "none";

            // Create toggle link/button
            const toggle = document.createElement("a");
            toggle.href = "#";
            toggle.classList.add("toggle-link");
            toggle.innerText = `Show ${title}`;
            toggle.style.display = "inline-block";
            toggle.style.margin = "10px 0";
            toggle.style.fontWeight = "bold";

            // Insert before the fieldset
            fs.parentNode.insertBefore(toggle, fs);

            toggle.addEventListener("click", function (e) {
                e.preventDefault();
                if (fs.style.display === "none") {
                    fs.style.display = "";
                    toggle.innerText = `Hide ${title}`;
                } else {
                    fs.style.display = "none";
                    toggle.innerText = `Show ${title}`;
                }
            });
        } else {
            console.log(`⚠️ ${title} section not found`);
        }
    });
});

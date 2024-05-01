// Animate background on page load
gsap.to("body", { duration: 2, backgroundSize: "105%", ease: "power2.out" });

// Function to animate and update main content
function updateContent(contentText) {
    const mainP = document.querySelector("main p");

    // Animate out existing content
    gsap.to(mainP, {
        duration: 0.5, 
        opacity: 0, 
        y: -20, 
        ease: "power2.in",
        onComplete: () => {
            // Update content after animation
            mainP.innerText = contentText;

            // Reset the style changed by GSAP to avoid conflicts
            mainP.style.opacity = 1;
            mainP.style.transform = 'translateY(0px)';

            // Animate in new content
            gsap.from(mainP, {
                duration: 0.5, 
                opacity: 0, 
                y: 20, 
                ease: "power2.out"
            });
        }
    });
}



document.querySelectorAll('.custom-nav a').forEach(link => {
    link.addEventListener('click', function(event) {
        
        event.preventDefault();

        // Define the content based on clicked link
        const linkText = link.textContent.trim();
        let contentText = "";
        switch (linkText.toLowerCase()) {
            case 'home':
                contentText = "Welcome to the home page!";
                break;
            case 'about':
                contentText = "Learn more about us.";
                break;
            case 'services':
                contentText = "Check out our services.";
                break;
            case 'contact':
                contentText = "Get in touch with us!";
                break;
        }

        // Update and animate content
        console.log(contentText);
        updateContent(contentText);
    });
});

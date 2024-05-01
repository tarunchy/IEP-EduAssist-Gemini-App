function enableReq() {
    const recSection = document.getElementById("consent");
    const recordButton = document.getElementById("recordButton");
    const checkboxContainer = document.querySelector(".checkbox-container");
    if (recSection.checked == true) {
        const topPosition = checkboxContainer.getBoundingClientRect().bottom;
        recordButton.style.top = `${topPosition}px`;
        recordButton.style.display = "block";
    } else {
        recordButton.style.display = "none";
    }
}

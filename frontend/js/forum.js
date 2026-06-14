function createNewThread() {
    let form = document.getElementById("new_thread_form");
    if (form.style.display === "none") {
        form.style.display = "block";
        console.log("1")
    } else {
        form.style.display = "none";
        console.log("2")
        
    }
    console.log(form.style.display)
}
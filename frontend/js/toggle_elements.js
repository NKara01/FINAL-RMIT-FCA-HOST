function toggleIds(ids){
    let len = ids.length;
    for (let i = 0; i < len; i++) {
        let form = document.getElementById(ids[i]);
        if (form.style.display === "none") {
            form.style.display = "flex";
        } else {
            form.style.display = "none";
            
        }
    }
}
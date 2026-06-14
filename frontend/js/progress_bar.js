function progressBar(){
    const collection = document.getElementsByClassName("progress_bar_fill");
    for (let i = 0; collection.length;i++){
        
        let amount = collection[i].getAttribute("name")
        collection[i].style.width = amount + '%'; 
        console.log(amount)
    }
}
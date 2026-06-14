function editQuestion(){
        let form = document.getElementById("edit_question_form");
    if (form.style.display === "none") {
        form.style.display = "block";
        console.log("1")
    } else {
        form.style.display = "none";
        console.log("2")
        
    }
    console.log(form.style.display)
}

function editComment(commentID){
      let form = document.getElementById("edit_comment_form_" + commentID);
    if (form.style.display === "none") {
        form.style.display = "block";
        console.log("1")
    } else {
        form.style.display = "none";
        console.log("2")
        
    }
    console.log(form.style.display)
}
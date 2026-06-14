// Contains quiz functionality
// checks the db for correct answers via ajax
// does NOT show you the correct answer, only shows you if its correct or not and if you've completed it or not.
async function checkResponses(quiz_id,question_amount,module_id){
    console.log("CHECK quiz " + quiz_id + " for " + question_amount)
    //Consist of a set of value:pairs based on id.
    //question : answer
    let questions_table = {
        "module_id" : module_id,
        "responses" : []
    }
    let canProceed = true
    for (let i = 0; i < question_amount;i++){
        const question_id = document.getElementById('question_' + i + '_id').getAttribute("name");
        let check = document.querySelector('input[name="question_' + i + '_answer"]:checked')
        const message_field = document.getElementById('question_response_' + question_id)
        if (check == null){
            //TODO validation of blank responses
            message_field.classList.remove('correct');
            message_field.classList.add('incorrect');
            message_field.innerHTML = "Please answer this question."
            console.error("SOMETHING HAS NOT BEEN FILLED!")
            canProceed = false
        }
        else{
            message_field.classList.remove('correct');
            message_field.classList.remove('incorrect');
            message_field.innerHTML = ""
            const answer_id = check.value;
            console.log(answer_id)
            if (answer_id == null ||  answer_id === ""){
                
            }
            questions_table["responses"].push({"question_id" : Number(question_id),"answer_id" : Number(answer_id)})
        }
        
    }
    console.log(questions_table)

    if (canProceed){
        console.log("PROCEED")
        const request  = await fetch('/api/quiz/' + quiz_id + "/check", {
        method:'POST',
        headers: { 'Content-Type': 'application/json' },
        body:JSON.stringify(questions_table)});
        //Returns a table containing question ids and correct/incorrect markers.
        //backend will create a quiz result.
        const qData = await request.json();
        if (qData && qData["error"]){
            console.error(qData["error"])
        }
        if (qData && qData["responses"]){
            console.log(qData)
            for (const response in qData["responses"]){
                const message_field = document.getElementById('question_response_' + qData["responses"][response]["question_id"])
                    if (message_field != null){
                        if (qData["responses"][response]["correct"]){
                        message_field.classList.remove('correct');
                        message_field.classList.remove('incorrect');
                        message_field.classList.add('correct');
                        message_field.innerHTML = "Correct"
                    }
                    else{
                        message_field.classList.remove('correct');
                        message_field.classList.remove('incorrect');
                        message_field.classList.add('incorrect');
                        message_field.innerHTML = "Incorrect"
                    }
                }
                
               
            }
            const statusfield = document.getElementById('question_evaluation')
            if (qData["has_passed"]){
                statusfield.classList.remove('correct');
                statusfield.classList.remove('incorrect');
                statusfield.classList.add('correct');
                statusfield.innerHTML = "You have successfully completed the Quiz."
                //update the quiz status button
                const quiz_field = document.getElementById('quiz_button_current')
                if (quiz_field != null){
                    quiz_field.classList.add('passed');
                    quiz_field.innerHTML = quiz_field.innerHTML + " ✓";
                     quiz_field.removeAttribute('id');
                }
                
                //convert the next button if present
                if (qData["unlock_end"]){
                    const next_field = document.getElementById('inactive_nextbutton')
                    const next_parent = document.getElementById('inactive_parent')
                    const text = next_field.innerHTML
                    const url = next_field.getAttribute("href")

                    
                    if (next_field != null){
                        next_field.outerHTML = "<a class='nextbutton' href=" + url + ">" + text + "</a>";
                        next_parent.classList.remove('inactive');
                    }
                }
            }
            else{
                statusfield.classList.remove('correct');
                statusfield.classList.remove('incorrect');
                statusfield.classList.add('incorrect');
                statusfield.innerHTML = "Please check your answers and try again."
            }
            window.scrollTo(0,0);
            
        }
    }

    
    
}

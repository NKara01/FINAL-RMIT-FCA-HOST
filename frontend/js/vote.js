async function threadVote(vote,thread_id){
    if (vote == 1 || vote == -1){
        console.log(vote)
        console.log(thread_id)
        const upvote = document.getElementById('threadUpvote')
        const downvote = document.getElementById('threadDownvote')
        const threadScore = document.getElementById('threadScore')

        const body = {"score" : vote}
        const request  = await fetch("/api/thread/"+ thread_id + "/vote", {
        method:'POST',
        headers: { 'Content-Type': 'application/json' },
        body:JSON.stringify(body)});
        //Returns a table containing question ids and correct/incorrect markers.
        //backend will create a quiz result.
        const qData = await request.json();
        if (qData && qData["error"]){
            console.error(qData["error"])
        }
        console.log(qData)
        if (qData && !qData["error"]){
            threadScore.innerHTML = qData["new_score"]
            if (qData["vote"] == 0){
                upvote.classList.remove('selected')
                downvote.classList.remove('selected')
            }
            else if (qData["vote"] == 1){
                upvote.classList.add('selected')
                downvote.classList.remove('selected')
            }
            else if (qData["vote"] == -1){
                upvote.classList.remove('selected')
                downvote.classList.add('selected')
            }
        }
    }
    else{
        error("invalid vote")
    }
}

async function commentVote(vote,comment_id){
    if (vote == 1 || vote == -1){
        console.log(vote)
        console.log(comment_id)
        const upvote = document.getElementById('commentUpvote_' + comment_id)
        const downvote = document.getElementById('commentDownvote_' + comment_id)
        const threadScore = document.getElementById('commentScore_' + comment_id)

        const body = {"score" : vote}
        const request  = await fetch("/api/comment/"+ comment_id + "/vote", {
        method:'POST',
        headers: { 'Content-Type': 'application/json' },
        body:JSON.stringify(body)});
        //Returns a table containing question ids and correct/incorrect markers.
        //backend will create a quiz result.
        const qData = await request.json();
        if (qData && qData["error"]){
            console.error(qData["error"])
        }
        console.log(qData)
        if (qData && !qData["error"]){
            threadScore.innerHTML = qData["new_score"]
            if (qData["vote"] == 0){
                upvote.classList.remove('selected')
                downvote.classList.remove('selected')
            }
            else if (qData["vote"] == 1){
                upvote.classList.add('selected')
                downvote.classList.remove('selected')
            }
            else if (qData["vote"] == -1){
                upvote.classList.remove('selected')
                downvote.classList.add('selected')
            }
        }
    }
    else{
        error("invalid vote")
    }
}
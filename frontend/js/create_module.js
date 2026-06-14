// States
// NOTES
// MODULE ID GETS SET LATER THIS IS INITIALISED HERE 
// Part ID and Q ID counters are natively gotten.
// Pending is because of the layers i set
// the 1 - 2 - 3 create steps 
// YEs, This was stolen!
let moduleId = null;
let pendingCoverImage = null;
let partCount= 0;
let partIdCounter= 0;
let qIdCounter = 0;
let pendingModule = null;
let partSections = {};
// Helpers
function showMsg(type, msg) {
    const s = document.getElementById('status-success');
    const e = document.getElementById('status-error');
    s.style.display = 'none';
    e.style.display = 'none';
    if (type === 'success') { s.textContent = msg; s.style.display = 'block'; }
    if (type === 'error')   { e.textContent = msg; e.style.display = 'block'; }
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updatePartCount() {
    document.getElementById('part-count-num').textContent = partCount;
    document.getElementById('btn-add-part').disabled = partCount >= 20;
}

// steps boilerplate from stack and w3 course for web dev hence the i n

function setStep(n) {
    [1,2,3].forEach(i => {
        document.getElementById('step-' + i).style.display = i === n ? 'block' : 'none';
        const ind = document.getElementById('step-ind-' + i);
        ind.className = 'step' + (i < n ? ' done' : i === n ? ' active' : '');
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Create module ------------------------------------------------------------------
async function submitModule() {
    const title = document.getElementById('mod-title').value.trim();
    const description = document.getElementById('mod-desc').value.trim();
    const price_cents = parseInt(document.getElementById('mod-price').value) || 0;
    const image_url = document.getElementById('mod-image');

    pendingModule = {
        title: title,
        description: description,
        price_cents: price_cents,
        image_url: image_url.files[0],
    };
    showMsg('success', 'Module details saved locally. Now add parts below.');
    setStep(2);
}

// add parts
function addPart() {
    if (partCount >= 20) return;
    partCount++;
    partIdCounter++;
    updatePartCount();

    const pid = partIdCounter;
    const pNum = partCount;
    const container = document.getElementById('parts-container');

    const div = document.createElement('div');
    div.className = 'part-card';
    div.id = `part-ui-${pid}`;
    div.dataset.partNumber = pNum;
    div.innerHTML = `
        <div class="part-card-header">
            <span class="part-label">Part ${pNum}</span>
            <button class="part-remove" onclick="removePart(${pid})" title="Remove part">✕</button>
        </div>

        <div class="form-group cm-form-group-small">
            <label>Part title *</label>
            <input type="text" id="part-title-${pid}" placeholder="e.g. Introduction to Microbiology">
        </div>

        <div class="part-section-builder">
            <h3>Content sections</h3>
            <p class="cm-muted-text">Add text, YouTube, PDFs, and images in the exact order students should see them.</p>

            <div id="section-list-${pid}" class="section-list">
                <p class="section-empty">No sections added yet.</p>
            </div>

            <div class="section-controls">
                <select id="section-type-${pid}" class="cm-question-select" onchange="changeSectionInput(${pid})">
                    <option value="text">Text</option>
                    <option value="youtube">YouTube</option>
                    <option value="pdf">PDF</option>
                    <option value="image">Image</option>
                </select>

                <div id="section-input-text-${pid}" class="section-input active">
                    <textarea id="section-text-${pid}" placeholder="Write text for this section"></textarea>
                </div>

                <div id="section-input-youtube-${pid}" class="section-input">
                    <input type="text" id="section-youtube-${pid}" placeholder="YouTube URL or embed URL">
                </div>

                <div id="section-input-pdf-${pid}" class="section-input">
                    <input type="file" id="section-pdf-${pid}" accept=".pdf">
                </div>

                <div id="section-input-image-${pid}" class="section-input">
                    <input type="file" id="section-image-${pid}" accept="image/*">
                </div>

                <button type="button" class="btn-ghost-green cm-small-top" onclick="addLocalSection(${pid})">
                    + Add section
                </button>
            </div>
        </div>

        <div class="toggle-row">
            <input type="checkbox" id="has-quiz-${pid}" onchange="toggleBlock('part-quiz-${pid}', this.checked)">
            <label for="has-quiz-${pid}">Add a quiz after this part</label>
        </div>

        <div id="part-quiz-${pid}" class="cm-quiz-block cm-hidden">
            <div class="form-group cm-form-group-tiny">
                <label>Quiz title</label>
                <input type="text" id="quiz-title-${pid}" placeholder="e.g. Part ${pNum} Check">
            </div>
            <div class="pass-row cm-form-group-small">
                <label>Pass mark</label>
                <input type="number" id="quiz-pass-${pid}" value="80" min="0" max="100">
                <span class="cm-muted-text">%</span>
            </div>
            <div id="questions-${pid}"></div>
            <button class="btn-ghost cm-question-add-btn"
                    onclick="addQuestion('part', ${pid})">+ Add question</button>
        </div>
    `;
    container.appendChild(div);
    partSections[pid] = [];
    changeSectionInput(pid);
}

function removePart(pid) {
    const el = document.getElementById(`part-ui-${pid}`);
    if (el) {
        el.remove();
        partCount--;
        updatePartCount();
    }

    delete partSections[pid];



    // re-label remaining parts
    const cards = document.querySelectorAll('.part-card');
    cards.forEach((c, i) => {
        c.dataset.partNumber = i + 1;
        c.querySelector('.part-label').textContent = `Part ${i + 1}`;
    });
}

// function showPdfName(pid, input) {
//     const label = document.getElementById(`pdf-chosen-${pid}`);
//     label.textContent = input.files[0] ? input.files[0].name : '';
// }

function toggleBlock(id, checked) {
    document.getElementById(id).style.display = checked ? 'block' : 'none';
}

function escapeHtml(value) {
    return String(value || '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function normaliseYoutubeUrl(url) {
    try {
        const parsed = new URL(url);

        if (parsed.hostname.includes('youtu.be')) {
            const videoId = parsed.pathname.replace('/', '');
            return `https://www.youtube.com/embed/${videoId}`;
        }

        if (parsed.hostname.includes('youtube.com')) {
            if (parsed.pathname.includes('/embed/')) {
                return url;
            }

            const videoId = parsed.searchParams.get('v');
            if (videoId) {
                return `https://www.youtube.com/embed/${videoId}`;
            }

            if (parsed.pathname.includes('/shorts/')) {
                const videoId = parsed.pathname.split('/shorts/')[1];
                return `https://www.youtube.com/embed/${videoId}`;
            }
        }

        return url;
    } catch {
        return url;
    }
}

function changeSectionInput(pid) {
    const type = document.getElementById(`section-type-${pid}`).value;

    ['text', 'youtube', 'pdf', 'image'].forEach(sectionType => {
        const el = document.getElementById(`section-input-${sectionType}-${pid}`);
        if (el) {
            el.classList.toggle('active', sectionType === type);
        }
    });
}

function addLocalSection(pid) {
    const type = document.getElementById(`section-type-${pid}`).value;

    if (!partSections[pid]) {
        partSections[pid] = [];
    }

    const section = {
        section_type: type,
        content: '',
        file: null,
        label: ''
    };

    if (type === 'text') {
        const text = document.getElementById(`section-text-${pid}`).value.trim();

        if (!text) {
            showMsg('error', 'Text section cannot be empty.');
            return;
        }

        section.content = text;
        section.label = text.length > 90 ? text.slice(0, 90) + '…' : text;
        document.getElementById(`section-text-${pid}`).value = '';
    }

    if (type === 'youtube') {
        const url = document.getElementById(`section-youtube-${pid}`).value.trim();

        if (!url) {
            showMsg('error', 'YouTube URL cannot be empty.');
            return;
        }

        section.content = normaliseYoutubeUrl(url);
        section.label = section.content;
        document.getElementById(`section-youtube-${pid}`).value = '';
    }

    if (type === 'pdf') {
        const input = document.getElementById(`section-pdf-${pid}`);
        const file = input.files[0];

        if (!file) {
            showMsg('error', 'Choose a PDF file.');
            return;
        }

        section.file = file;
        section.label = file.name;
        input.value = '';
    }

    if (type === 'image') {
        const input = document.getElementById(`section-image-${pid}`);
        const file = input.files[0];

        if (!file) {
            showMsg('error', 'Choose an image file.');
            return;
        }

        section.file = file;
        section.label = file.name;
        input.value = '';
    }

    partSections[pid].push(section);
    renderLocalSections(pid);
}

function removeLocalSection(pid, index) {
    partSections[pid].splice(index, 1);
    renderLocalSections(pid);
}

function moveLocalSection(pid, index, direction) {
    const newIndex = index + direction;

    if (newIndex < 0 || newIndex >= partSections[pid].length) {
        return;
    }

    [partSections[pid][index], partSections[pid][newIndex]] =
        [partSections[pid][newIndex], partSections[pid][index]];

    renderLocalSections(pid);
}

function renderLocalSections(pid) {
    const list = document.getElementById(`section-list-${pid}`);
    const sections = partSections[pid] || [];

    if (sections.length === 0) {
        list.innerHTML = '<p class="section-empty">No sections added yet.</p>';
        return;
    }

    list.innerHTML = sections.map((section, index) => `
        <div class="section-row">
            <span class="section-type-badge">${escapeHtml(section.section_type)}</span>
            <span class="section-preview">${escapeHtml(section.label)}</span>

            <button type="button" class="section-small-btn" onclick="moveLocalSection(${pid}, ${index}, -1)">▲</button>
            <button type="button" class="section-small-btn" onclick="moveLocalSection(${pid}, ${index}, 1)">▼</button>
            <button type="button" class="section-delete-btn" onclick="removeLocalSection(${pid}, ${index})">✕</button>
        </div>
    `).join('');
}


// -- Questions 
function addQuestion(context, partUiId) {
    qIdCounter++;
    const qid = qIdCounter;
    const containerId = context === 'final'
        ? 'final-exam-questions'
        : `questions-${partUiId}`;
    const container = document.getElementById(containerId);

    const div = document.createElement('div');
    div.className = 'question-block';
    div.id = `q-ui-${qid}`;
    div.innerHTML = `
        <div class="question-block-header">
            <span class="question-label">Question</span>
            <button class="q-remove" onclick="removeQuestion(${qid})">✕</button>
        </div>

        <div class="form-group cm-form-group-tiny">
                <label>Upload Question Image (optional)</label>
                <div class="image_container">
                    <!-- https://stackoverflow.com/questions/4459379/preview-an-image-before-it-is-uploaded -->
                    <input multiple accept="image/*" type="file" id="qimage-${qid}" name="mod-image" />  
                </div>
            </div>

        <div class="form-group cm-form-group-tiny">
            <input type="text" id="qtext-${qid}" placeholder="Enter question text">
        </div>

        <div class="form-group cm-form-group-tiny">
            <select id="qtype-${qid}" class="cm-question-select" onchange="changeQType(${qid}, this.value)">
                <option value="multiple_choice">Multiple choice</option>
                <option value="true_false">True / False</option>
            </select>
        </div>

        <div id="answers-${qid}">
            ${buildAnswerRow(qid, 0)}
            ${buildAnswerRow(qid, 1)}
            ${buildAnswerRow(qid, 2)}
            ${buildAnswerRow(qid, 3)}
        </div>
        <button class="btn-ghost cm-answer-add-btn"
                onclick="addAnswerRow(${qid})" id="btn-add-ans-${qid}">+ Add option</button>
    `;
    container.appendChild(div);
}

function buildAnswerRow(qid, idx) {
    return `
        <div class="answer-row" id="ans-row-${qid}-${idx}">
            <input type="radio" name="correct-${qid}" value="${idx}">
            <input type="text" placeholder="Option ${idx + 1}">
            <span class="answer-correct-label">correct</span>
        </div>`;
}

function addAnswerRow(qid) {
    const container = document.getElementById(`answers-${qid}`);
    const idx = container.children.length;
    container.insertAdjacentHTML('beforeend', buildAnswerRow(qid, idx));
}

function changeQType(qid, type) {
    const container = document.getElementById(`answers-${qid}`);
    const addBtn = document.getElementById(`btn-add-ans-${qid}`);
    if (type === 'true_false') {
        container.innerHTML = buildAnswerRow(qid, 0).replace('Option 1', 'True') + buildAnswerRow(qid, 1).replace('Option 2', 'False');
        addBtn.style.display = 'none'; } 
    else {
        container.innerHTML = buildAnswerRow(qid, 0) + buildAnswerRow(qid, 1) + buildAnswerRow(qid, 2) + buildAnswerRow(qid, 3);
        addBtn.style.display = '';}}

function removeQuestion(qid) {
    const el = document.getElementById(`q-ui-${qid}`);
    if (el) el.remove();}
// Read from container js

function readQuestions(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return [];
    const blocks = container.querySelectorAll('.question-block');
    const out = [];
    blocks.forEach((block, i) => {
        const qid = block.id.replace('q-ui-', '');
        const text = (document.getElementById(`qtext-${qid}`)?.value || '').trim();
        const image1 = document.getElementById(`qimage-${qid}`);
        const image = image1?.files?.[0] || null;
        const type = document.getElementById(`qtype-${qid}`)?.value || 'multiple_choice';
        const rows = document.getElementById(`answers-${qid}`)?.querySelectorAll('.answer-row') || [];
        const answers = [];
        rows.forEach(row => {
            const radio = row.querySelector('input[type="radio"]');
            const input = row.querySelector('input[type="text"]');
            const aText= (input?.value || '').trim();
            if (aText) {
                answers.push({ text: aText, is_correct: radio?.checked || false });
            }
        });
        if (text && answers.length) {
            out.push({ question_text: text, question_type: type, order_num: i, answers, question_image : image });
        }
    });
    return out;
}

// SUBIMT PATS
async function submitAll() {
    if (!pendingModule) {
        showMsg('error', 'Module details are not saved yet.');
        return;
    }

    const partCards = document.querySelectorAll('.part-card');
    // if (partCards.length < 1) {
    //     showMsg('error', 'Please add at least 1 part');
    //     return;
    // }

    //  pendingModule = {
    //     title: title,
    //     description: description,
    //     price_cents: price_cents,
    //     image_url: image_url.files[0],
    // };
    const fdf = new FormData();
    fdf.append('title', pendingModule.title);
    fdf.append('description', pendingModule.description);
    fdf.append('price_cents', pendingModule.price_cents);
if (pendingModule.image_url) {
    fdf.append('image_url', pendingModule.image_url);
}   
 try {
        const moduleRes = await fetch('/api/admin/modules', {
            
            method:'POST', body: fdf
 });

        const moduleData = await moduleRes.json();

        if (!moduleRes.ok) {
            showMsg('error', moduleData.error || 'Failed to create module.');
            return;
    }

        moduleId = moduleData.module_id;
        // --- save each part ---
        for (let i = 0; i < partCards.length; i++) {
            const card= partCards[i];
            const pid = card.id.replace('part-ui-', '');
            const pNum = parseInt(card.dataset.partNumber);


            const title = (document.getElementById(`part-title-${pid}`)?.value || '').trim();
            const hasQuiz = document.getElementById(`has-quiz-${pid}`)?.checked ? '1' : '0';
            const sections = partSections[pid] || [];

            if (!title) {
                showMsg('error', `Part ${pNum} needs a title.`);
                return;
            }

            // if (sections.length === 0) {
            //     showMsg('error', `Part ${pNum} needs at least one content section`);
            //     return;
            // }

            const fd = new FormData();
            fd.append('title', title);
            fd.append('part_number', pNum);
            fd.append('has_quiz', hasQuiz);
            fd.append('youtube_url', '');
            fd.append('body', '');





            const res= await fetch(`/api/admin/modules/${moduleId}/parts`, { method: 'POST', body: fd });
            const data = await res.json();
            if (!res.ok) { showMsg('error', `Part ${pNum}: ${data.error}`); return; }
            
            const partId = data.part_id;
            if (partId == null) {
                showMsg('error', `Part ${pNum} was not created properly.`);
                return;
            }


            

            for (let sectionIndex = 0; sectionIndex < sections.length; sectionIndex++) {
                const section = sections[sectionIndex];
                const sectionForm = new FormData();

                sectionForm.append('section_type', section.section_type);
                sectionForm.append('order_num', sectionIndex * 10);

                if (section.section_type === 'text' || section.section_type === 'youtube') {
                    sectionForm.append('content', section.content);
                } else {
                    sectionForm.append('file', section.file);
                }

                const sectionRes = await fetch(`/api/admin/parts/${partId}/sections`, {
                    method: 'POST',
                    body: sectionForm
                });

                const sectionData = await sectionRes.json();

                if (!sectionRes.ok) {
                    showMsg('error', `Part ${pNum} section ${sectionIndex + 1}: ${sectionData.error}`);
                    return;
                }
            }

            // --- save part quiz if toggled ---

            if (hasQuiz === '1') {
                const quizTitle = (document.getElementById(`quiz-title-${pid}`)?.value || '').trim()
                                    || `Part ${pNum} Quiz`;
                const passPct = parseInt(document.getElementById(`quiz-pass-${pid}`)?.value) || 80;
                const questions = readQuestions(`questions-${pid}`);

                const qRes = await fetch('/api/admin/quizzes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        module_id: moduleId,
                        part_id: partId,
                        title: quizTitle,
                        is_final_exam: 0,
                        pass_percent: passPct
                    })
                });

                const qData = await qRes.json();
                if (!qRes.ok) {
                    showMsg('error', `Quiz for part ${pNum}: ${qData.error}`);
                    return;
                }

                const quizId = qData.quiz_id;

                for (const q of questions) {
                    const fd = new FormData();
                    fd.append('question_text', q.question_text);
                    fd.append('question_type', q.question_type);
                    fd.append('order_num', q.order_num);

                    if (q.question_image) {
                        fd.append('question_image', q.question_image);
                    }

                    const qres = await fetch(`/api/admin/quizzes/${quizId}/questions`, {
                        method: 'POST',
                        body: fd
                    });

                    const qData = await qres.json();
                    if (!qres.ok) {
                        showMsg('error', `question: ${qData.error}`);
                        return;
                    }

                    const question_id = qData.question_id;

                    for (const z of q.answers) {
                        const fzzd = new FormData();
                        fzzd.append('answer_text', z.text);
                        fzzd.append('is_correct', z.is_correct);

                        const aares = await fetch(`/api/admin/quizzes/${quizId}/questions/${question_id}`, {
                            method: 'POST',
                            body: fzzd
                        });

                        const aaData = await aares.json();
                        if (!aares.ok) {
                            showMsg('error', `answer: ${aaData.error}`);
                            return;
                        }
                    }
                }
            }

        }
        // --- save final exam if toggled ---
        const hasFinal = document.getElementById('has-final-exam')?.checked;
        if (hasFinal) {
            const examTitle = (document.getElementById('final-exam-title')?.value || '').trim()|| 'Final Exam';
            const passPct= parseInt(document.getElementById('final-exam-pass')?.value) || 80;
            const questions = readQuestions('final-exam-questions');

            const eRes= await fetch('/api/admin/quizzes', {
                method:'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ module_id: moduleId, title: examTitle, is_final_exam: 1, pass_percent: passPct })});
            const eData = await eRes.json();
            if (!eRes.ok) { showMsg('error', `Final exam: ${eData.error}`); return; }

            const examId = eData.quiz_id;
            for (const q of questions) {
                const fd = new FormData();
                // { question_text: text, question_type: type, order_num: i, answers, question_image : image }
                fd.append('question_text',q.question_text);
                fd.append('question_type',q.question_type);
                fd.append('order_num',q.order_num);
                // fd.append('answers',JSON.stringify(q.answers));
                //  console.log(q.answers)

                if (q.question_image) {
               fd.append('question_image', q.question_image);
                }

                const qres = await fetch(`/api/admin/quizzes/${examId}/questions`, {
                        method:'POST',
                        body:fd
                });
                const qData = await qres.json();
                if (!qres.ok) { showMsg('error', `question: ${qData.error}`); return; }
                //  answers.push({ text: aText, is_correct: radio?.checked || false });
                const question_id = qData.question_id;
                for (const z of q.answers){
                    const fzzd = new FormData();
                    fzzd.append('answer_text', z.text);
                    fzzd.append('is_correct', z.is_correct);
                    console.log(z)
                     const aares = await fetch(`/api/admin/quizzes/${examId}/questions/${question_id}`, {
                            method:'POST',
                            body:fzzd
                            
                    });
                    const aaData = await aares.json();
                    if (!aares.ok) { showMsg('error', `answer: ${aaData.error}`); return; }
                }
            }
            }

        setStep(3);

    } catch (err) {
        showMsg('error', 'Network error. Please try again.');
    }
}

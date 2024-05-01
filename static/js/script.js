// IEP Questions
const iepQuestions = {
    '3-6': [
        "Is the child able to communicate basic needs?",
        "How well does the child interact with peers?",
        "Is the child able to focus on tasks for a reasonable amount of time?",
        "Does the child respond well to structured activities?",
        "How does the child handle transitions between activities?"
    ],
    '7-12': [
        "How is the student performing in reading and math?",
        "Is the student able to complete homework independently?",
        "Does the student participate in class discussions?",
        "How well does the student manage time during class?",
        "Is the student organized?"
    ],
    '13-17': [
        "How is the student's academic performance?",
        "Is the student considering post-secondary education?",
        "Does the student have career interests?",
        "How well does the student manage stress?",
        "Is the student showing independence and self-advocacy skills?"
    ]
};

// Display questions based on profile selection
function displayQuestions() {
    const profile = document.getElementById('studentProfile').value;
    const questions = iepQuestions[profile];
    let html = '<ul>';
    for (const question of questions) {
        html += `<li>${question}</li>`;
    }
    html += '</ul>';
    document.getElementById('questions').innerHTML = html;
}

displayQuestions(); // Display initial set of questions
document.getElementById('studentProfile').addEventListener('change', displayQuestions);

// Speech Recognition setup
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();

// Allow for continuous recognition
recognition.continuous = true;

// On start of speech recognition
recognition.onstart = function() {
    console.log('Voice is activated');
    document.getElementById('mic-icon').classList.add("recording-icon"); // Add recording animation
};

// On end of speech recognition
recognition.onend = function() {
    console.log('Voice is deactivated');
    document.getElementById('mic-icon').classList.remove("recording-icon"); // Remove recording animation
};

// Handling the result from recognition
recognition.onresult = function(event) {
    const current = event.resultIndex;
    const transcript = event.results[current][0].transcript;
    document.getElementById('transcript').value += transcript;
};

// Start button event listener
document.getElementById('start').addEventListener('click', function() {
    if (document.getElementById('consent').checked) {
        recognition.start();
        document.getElementById('mic-icon').classList.add("recording-icon"); // Add recording animation
    } else {
        alert('Please obtain parent\'s consent before starting the recording.');
    }
});

// Stop button event listener
document.getElementById('stop').addEventListener('click', function() {
    recognition.stop();
    document.getElementById('mic-icon').classList.remove("recording-icon"); // Remove recording animation
});

// ... existing JavaScript ...

// Clear button event listener
document.getElementById('clear').addEventListener('click', function() {
document.getElementById('transcript').value = ''; // Clear the transcript
});

// Generate IEP button event listener
document.getElementById('generate').addEventListener('click', function() {
const transcript = document.getElementById('transcript').value;
const profile = document.getElementById('studentProfile').value;
const questions = iepQuestions[profile];

let allQuestionsAddressed = true;
let missingQuestions = [];

// Check if each question exists in the transcript
for (const question of questions) {
if (!transcript.includes(question)) {
    allQuestionsAddressed = false;
    missingQuestions.push(question);
}
}

if (allQuestionsAddressed) {
alert('Transcript is complete. Generating IEP...');
// Logic for generating IEP can go here
} else {
alert(`Transcript is incomplete. Missing questions:\n${missingQuestions.join('\n')}`);
}
});
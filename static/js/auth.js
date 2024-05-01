// auth.js
function logoutUser() {
    fetch('/user_api/logout', {
        method: 'GET'
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.message); // Or handle this message as needed
        window.location.href = '/'; // Redirect to the home page after logout
    })
    .catch(error => console.error('Error:', error));
}

function educatorView() {

    window.location.href = '/educator_view'; 

}

function parentView() {

    window.location.href = '/parent_view'; 

}

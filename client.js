"use strict";


var socket = null;

window.onload = function() {
    displayView(); 
};

function initWebSocket(token) {
    socket = new WebSocket("ws://127.0.0.1:5000/ws");
    
    socket.onopen = function() {
        console.log("WebSocket connected.");
        socket.send(token);
    };

    socket.onmessage = function(event) {
        if (event.data === "sign_out") {
            console.log("Received sign_out signal via WebSocket.");
            alert("This account has been logged in elsewhere, you will be forced to log out !");
            
            localStorage.removeItem("token");
            
            displayView();
        }
    };

    //When press F5、close webpage、backend the system will conduct ws.close()
    socket.onclose = function() {
        console.log("WebSocket disconnected by Server.");
        socket = null; 
    };

    socket.onerror = function(error) {
        console.error("WebSocket error:", error);
    };
}

//The only channel for HTTP communication between the application and the backend server.
function sendRequest(method, url, data, token, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, url, true); 
    xhr.setRequestHeader("Content-Type", "application/json"); 
    if (token) {
        xhr.setRequestHeader("Authorization", token);
    }
    
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            
            try {
                // Convert the string returned by the server back into objects that can be manipulated by JavaScript.
                var response = JSON.parse(xhr.responseText);
                callback(response);
            } catch (e) {
                console.warn("Server returned non-JSON response.");
            }
        }
    };
    
    //Convert the JavaScript object into a JSON string and send it to the server.
    xhr.send(data ? JSON.stringify(data) : null);
}

function displayView() {
    var content = document.getElementById("main-content");
    var token = localStorage.getItem("token");

    if (token) {
        var profileTemplate = document.getElementById("profileview");
        if (profileTemplate) {
            content.innerHTML = profileTemplate.innerHTML;
            showTab('home'); 

            //socket.readyState represent the progress of WebSocket connection
            //First check if there is a connection, then check the connection status.
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                initWebSocket(token);
            }
        }
    } else {
        var welcomeTemplate = document.getElementById("welcomeview");
        if (welcomeTemplate) {
            content.innerHTML = welcomeTemplate.innerHTML;
        }
        
    }
}

function isValidEmail(email) {
    var emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    return emailPattern.test(email);
}

function handleSignUp(form) {
    var feedback = document.getElementById("signup-feedback");
    
    if (form.password.value.length < 6) {
        feedback.innerText = "Password must be at least 6 characters.";
        return false;
    }
    if (form.password.value !== form.repeatPassword.value) {
        feedback.innerText = "Passwords do not match.";
        return false;
    }
    if (!isValidEmail(form.email.value)) {
        feedback.innerText = "Invalid email format.";
        return false;
    }

    var data = {
        email: form.email.value,
        password: form.password.value,
        firstname: form.firstname.value,
        familyname: form.familyname.value,
        gender: form.gender.value,
        city: form.city.value,
        country: form.country.value
    };

    sendRequest("POST", "/sign_up", data, null, function(response) {
        if (response.success) {
            handleSignIn({
                email: { value: data.email },
                password: { value: data.password }
            });
        } else {
            feedback.innerText = response.message;
        }
    });
    return false;
}

function handleSignIn(form) {
    var data = { "email": form.email.value, "password": form.password.value };

    sendRequest("POST", "/sign_in", data, null, function(response) {
        if (response.success) {
            localStorage.setItem("token", response.data); 
            displayView();
        } else {
            var feedback = document.getElementById("login-feedback");
            if (feedback) feedback.innerText = response.message;
        }
    });
    return false;
}

function showTab(tabId) {
    var tabs = document.getElementsByClassName("tab-content");
    for (var i = 0; i < tabs.length; i++) {
        tabs[i].style.display = "none";
    }
    var target = document.getElementById(tabId);
    if (target) {
        target.style.display = "block";
    }
    
    if (tabId === 'home') {
        refreshMyWall(); 
    }
}

function renderWall(messages, containerId) {
    var html = "";
    if (messages && messages.length > 0) {
        messages.forEach(msg => {
            var sender = msg.sender || msg.writer || "Unknown"; 
            html += `<div class="message-item"><b>${sender}:</b> ${msg.content}</div>`;
        });
    } else {
        html = "<div>No messages yet.</div>";
    }
    var container = document.getElementById(containerId);
    if (container) container.innerHTML = html;
}

function refreshMyWall() {
    var token = localStorage.getItem("token");
    if (!token) return;

    sendRequest("GET", "/get_user_data_by_token", null, token, function(response) {
        if (response.success) {
            var info = response.data;
            var userInfoDiv = document.getElementById("user-info");
            if (userInfoDiv) {
                userInfoDiv.innerHTML = 
                    "<h3>" + info.firstname + " " + info.familyname + "</h3>" +
                    "<p>Email: " + info.email + ", Gender: " + info.gender + "</p>" +
                    "<p>City: " + info.city + ", Country: " + info.country + "</p>";
            }
        }
    });

    sendRequest("GET", "/get_user_messages_by_token", null, token, function(response) {
        if (response.success) {
            renderWall(response.data, "my-wall-messages");
        }
    });
}

function postToWall(toEmail, inputId) {
    var input = document.getElementById(inputId);
    var token = localStorage.getItem("token");
    var content = input ? input.value : "";
    if (content.trim() === "") return;

    var data = { "recipient": toEmail, "message": content };

    sendRequest("POST", "/post_message", data, token, function(response) {
        if (response.success) {
            if (input) input.value = ""; 
            if (toEmail == null) {
                refreshMyWall(); 
            } else {
                searchUser(); 
            }
        }
    });
}

function searchUser() {
    var emailInput = document.getElementById("search-email");
    var email = emailInput ? emailInput.value : "";
    var token = localStorage.getItem("token");

    sendRequest("GET", "/get_user_data_by_email/" + email, null, token, function(response) {
        if (response.success) {
            var profileDiv = document.getElementById("searched-profile");
            if (profileDiv) profileDiv.style.display = "block";
            
            var info = response.data;
            var infoDiv = document.getElementById("searched-user-info");
            if (infoDiv) {
                infoDiv.innerHTML = 
                    "<h3>" + info.firstname + " " + info.familyname + "</h3>" +
                    "<p>Email: " + info.email + ", Gender: " + info.gender + "</p>" +
                    "<p>City: " + info.city + ", Country: " + info.country + "</p>";
            }

            sendRequest("GET", "/get_user_messages_by_email/" + email, null, token, function(resMessages) {
                if (resMessages.success) {
                    renderWall(resMessages.data, "searched-wall-messages");
                }
            });
        } else {
            var feedback = document.getElementById("search-feedback");
            if (feedback) feedback.innerText = response.message;
            var profileDiv = document.getElementById("searched-profile");
            if (profileDiv) profileDiv.style.display = "none";
        }
    });
}

function handleChangePassword(form) {
    if (form.newPassword.value !== form.repeatNewPassword.value) {
        document.getElementById("account-feedback").innerText = "New passwords don't match.";
        return false;
    }
    var token = localStorage.getItem("token");
    var data = { "old_password": form.oldPassword.value, "new_password": form.newPassword.value };

    sendRequest("PUT", "/change_password", data, token, function(response) {
        document.getElementById("account-feedback").innerText = response.message;
    });
    return false;
}

function handleSignOut() {
    var token = localStorage.getItem("token");
    localStorage.removeItem("token");
    // Instead of manual shutdown, the connection will be disconnected or manually shut down when the backend token expires
    displayView();

    sendRequest("DELETE", "/sign_out", null, token, function(response) {
        console.log("Sign out request processed.");
    });
}

function postToOtherWall() {
    var emailInput = document.getElementById("search-email");
    var email = emailInput ? emailInput.value : "";
    postToWall(email, 'other-wall-message'); 
}

function refreshOtherWall() {
    searchUser();
}
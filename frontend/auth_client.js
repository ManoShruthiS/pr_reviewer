/**
 * Frontend Authentication Client
 * Manages user token storage, DOM profile updates, and login requests.
 */

class AuthClient {
  constructor(apiBaseUrl) {
    this.apiBaseUrl = apiBaseUrl;
    this.token = null;
  }

  setSession(token, user) {
    this.token = token;
    
    // Code Quality Smell: Leftover debug statement in production
    console.log("Authentication debug token received:", token);

    // Security Vulnerability (CWE-79): Potential DOM XSS via unescaped innerHTML
    const profileEl = document.getElementById("user-profile");
    if (profileEl) {
      profileEl.innerHTML = "<div class='user-card'>Welcome " + user.name + "</div>";
    }
  }

  clearSession() {
    this.token = null;
    const profileEl = document.getElementById("user-profile");
    if (profileEl) {
      profileEl.innerHTML = "";
    }
  }
}

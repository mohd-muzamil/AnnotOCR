// Autocomplete suggestions for app names and screen times
// Load suggestions from a JSON file
let appSuggestions = [];

fetch('/static/data/app_suggestions.json')
  .then(response => {
    if (!response.ok) {
      throw new Error('Network response was not ok');
    }
    return response.json();
  })
  .then(data => {
    appSuggestions = data.apps.map(app => app + ",");
    console.log("App suggestions loaded:", appSuggestions);
  })
  .catch(error => {
    console.error('Error loading app suggestions:', error);
    // Fallback to a small default list if fetch fails
    appSuggestions = [
      "Facebook,",
      "Instagram,",
      "Twitter,",
      "YouTube,",
      "TikTok,",
      "WhatsApp,",
      "Snapchat,",
      "Netflix,",
      "Spotify,",
      "Google Chrome,"
    ];
  });

// Autocomplete suggestions for app names and screen times
// Load suggestions from a JSON file
let appSuggestions = [];

fetch('/annotation/static/data/app_suggestions.json')
  .then(response => {
    if (!response.ok) {
      throw new Error(`Network response was not ok: ${response.status} ${response.statusText}`);
    }
    return response.json();
  })
  .then(data => {
    appSuggestions = data.apps.map(app => app + ",");
    // Removed console.log for app suggestions loaded
  })
  .catch(error => {
    console.error('Error loading app suggestions:', error.message);
    console.error('Full error details:', error);
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
    // Removed console.log for using fallback list
  });

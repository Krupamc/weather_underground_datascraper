# Weather Underground HTML Scraper
This scraper scrapes for the **preview** version of Weather Underground. This version allows easy access to data points.
---
## What is this?
Weather Underground is a place to get very local and high detailed weather data. It is a network of 250,000+ personal weather stations (PWS) used to map weather world wide. In my previous project, I used weather underground stations in my local area of Barnegat Bay. Most of them actually came from the non-proffit Save Barnegat Bay's Mesonet of stations. Huge shoutout to them and Dr. Michael Folmer, "a dedicated meteorologist and forecaster for the NWS Ocean Prediction Center, Weather Prediction Center, Tropical Analysis, and the Forecast Branch of the National Hurricane Center." This year I will continue using data from their mesonet
---
## Soooo why are you scraping
It is a bit of a sore topic for me, but Weather Underground discontinued their public API a few years back. This led me to collecting EVERY. SINGLE. DATA POINT by hand. I typed them all up in a spread sheet. All 40,000+ of them. Lovely. This year I do not plan on wasting that much time and instead I created a webscraper using the beautifulsoup and requests libraries (as well as some others)
---
## Features?
- Uses a config file for the list of weather station ids, API key for the PostgreSQL website, and error catching variables
- Scans HTML of the weather stations and picks out the data (for all variables not just what I need. This makes it so you can use it as well)
- Converts all imperial measurements into metric
- timestamps in UTC for the API to then turn back into ETC
- Send it to my configered PostgreSEQ API

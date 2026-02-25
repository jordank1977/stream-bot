# Twitch Category Discord Notifier

A lightweight, containerized Python bot that monitors a specific Twitch category and sends Discord Webhook notifications when a stream goes live.

## Features
-   Twitch OAuth2 Client Credentials authentication.
-   Polls Twitch Helix API for live streams in a specific category.
-   Rich Discord Embed notifications with stream details and thumbnails.
-   Persistent caching to prevent duplicate pings.
-   Dockerized for easy deployment.

## Prerequisites
-   Docker and Docker Compose.
-   A Twitch Developer Application (for Client ID and Secret).
-   A Discord Webhook URL.

## Setup

1.  Clone the repository or download the files.
2.  Create a `.env` file by copying the template:
    ```bash
    cp .env.example .env
    ```
3.  Fill in the values in `.env`:
    -   `TWITCH_CLIENT_ID`: Your Twitch App Client ID.
    -   `TWITCH_CLIENT_SECRET`: Your Twitch App Client Secret.
    -   `TWITCH_GAME_NAME`: The category to monitor (e.g., `Doomtrain`).
    -   `DISCORD_WEBHOOK_URL`: Your Discord Webhook URL.
    -   `POLL_INTERVAL_MINUTES`: Frequency of polling (default is 5).

## Running with Docker

Start the bot in the background:
```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f
```

Stop the bot:
```bash
docker-compose down
```

## Cache Persistence
The bot saves its state in `./data/active_streams.json`. This ensures that if the container restarts, it won't re-notify for streams that are already live.

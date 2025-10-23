<img src="./assets/logo_icon.svg" alt="Videoflix Logo" width="320">

A production-minded backend for Videoflix, a Netflix‑inspired streaming platform. It powers user authentication, video ingestion & transcoding, secure HLS delivery across multiple resolutions, categories & search, and an admin UI for content operations — all fully containerized with Docker Compose for local dev and deployment.

## ✨ Features

User accounts & profiles: email/password login, JWT sessions, optional OAuth (Google/Apple) hooks.

Role‑based access: user, admin (and optional ops) with route guards.

Video ingestion: upload originals; automatic FFmpeg transcode to HLS variants (e.g. 1080p/720p/480p/360p) with segmenting.

Adaptive streaming (HLS): master .m3u8 manifest with multiple renditions + captions.

Catalog & discovery: categories, tags, search, continue‑watching, watchlist, trending.

Playback security: signed HLS URLs, short‑lived tokens, geo/IP throttling (optional).

Admin panel: CRUD for titles, seasons/episodes (TV), people, assets, categories, promos.

Observability: health checks /healthz, structured logs, metrics endpoints, request tracing.

Containerized: docker compose up spins up API, DB, cache, object storage, NGINX, and workers.

---

> 🔗 **[Frontend Repository ](https://github.com/NoAltF4Dan/Videoflix_frontend)**

---

## 🛠 Installation & Setup

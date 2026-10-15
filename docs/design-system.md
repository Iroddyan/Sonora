# Design system

Sonora follows GNOME Human Interface Guidelines using GTK 4 and libadwaita’s native controls. The interface should feel at home on Fedora rather than imitate another desktop platform.

- Use `AdwNavigationSplitView` for adaptive navigation. Keep the sidebar, header bar, preferences rows, status pages, and bottom playback bar native.
- Follow the desktop color scheme by default. Settings can request dark or light appearance through `Adw.StyleManager`.
- Use symbolic GNOME icons and native hover, focus, keyboard, and accessibility behavior.
- Keep empty states honest and action-oriented. Do not put fake tracks, placeholder albums, or inert transport controls on screen.
- Use album artwork as real library content. Its derived color may add a subtle player accent, but it does not alter the application palette.
- Use Listen Now as an artwork-led library overview: native horizontal shelves for recently added tracks, artists, and albums, plus a short playable song list. Label collection size and recency from stored library data; do not imply listening popularity until playback history supports it.
- Prefer standard surfaces over blur and custom glass. Keep the player visually distinct while respecting system contrast and appearance settings.
- Keep compact layouts functional. The split view collapses on narrow windows, and player controls retain usable space.

Typography, spacing, contrast, and widget behavior should inherit libadwaita defaults unless a concrete usability issue justifies a small application-specific adjustment.

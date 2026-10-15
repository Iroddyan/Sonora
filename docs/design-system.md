# Design system

`qml/Theme.qml` defines semantic tokens for the application background, sidebar, surfaces, text, accent, border, and shadow. Components should reference these roles instead of adding one-off color values.

The refreshed shell uses a warm listening-room palette: deep charcoal with a soft brass accent in dark mode, and parchment with a restrained brown accent in light mode. Noto Sans is used for interface text where installed; the system fallback remains valid. Material Icons are bundled in the app and their Apache 2.0 license is included with the project and installed application.

The sidebar has one clear library group and a compact active state. Empty views explain what is available and expose a working next action when one exists. Cards use soft surfaces and restrained borders instead of large outlined boxes. The persistent player floats above the content with a selective translucent fill; Settings can switch it to an opaque elevated surface. No blur effect is required for legibility.

The sidebar collapses to icon navigation at narrow window widths and exposes tooltips/accessibility names for those items. Album and artist grids adapt their card width to the available content area. Asynchronous artwork tiles show a themed placeholder when a local cover is unavailable; an extracted artwork accent is used only as a restrained tile color.

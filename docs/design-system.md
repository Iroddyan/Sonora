# Design system

`qml/Theme.qml` defines semantic tokens for the application background, sidebar, surfaces, text, accent, border, and shadow. Components should reference these roles instead of adding one-off color values.

The initial shell uses a near-charcoal dark palette and a soft neutral light palette. Lavender is the initial accent. A few layout radii and typography sizes are established at the point of use; they can be consolidated as more real workflows are added.

Transparency is limited to the persistent footer player. The Settings page can switch all translucent treatment to an opaque elevated surface. No blur effect is required for legibility. The same content remains readable in either appearance mode.

The sidebar collapses to icon navigation at narrow window widths and exposes tooltips/accessibility names for those items. Album and artist grids adapt their card width to the available content area. Asynchronous artwork tiles show a themed placeholder when a local cover is unavailable; an extracted artwork accent is used only as a restrained tile color.

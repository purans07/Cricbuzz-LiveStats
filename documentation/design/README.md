# Professional theme refresh

Palette: navy #10243A navigation, emerald #087F6B selection/actions, cool workspace #F3F6FA, white #FFFFFF surfaces, ink #172B44, muted #596B80, borders #DCE4ED. Native accessible controls and focus indicators are retained. Plotly uses matching light surfaces and restrained categorical colours.

Built-in Image Gen created professional-concept.png as a design reference. Prompt: professional existing Streamlit Cricbuzz LiveStats Top Players screen; navy sidebar, light workspace, emerald selection, white metric cards, existing six navigation routes and career filters/table, no photos or invented badges. Real records, existing labels and data notices take precedence over illustrative generated values.

Visual review compared the concept and rendered desktop/mobile screenshots through view_image. Checked navigation palette/selection, heading hierarchy, control surfaces, metric contrast, spacing, and mobile wrapping. Intentional adaptations: original emoji navigation remains; source/coverage explanations and all existing controls are preserved; chart remains ahead of the detailed table. The implementation follows the reference palette and component treatment, rather than reproducing the generated layout exactly.

Chrome via bundled Playwright was used because Browser/IAB tools were unavailable. All six pages rendered without Streamlit exceptions at 1440×1000; Top Players checked at 390×844 with navigation collapsed. No provider requests or database writes were performed by these checks. 35 relevant existing tests passed. Cached legacy styles were corrected by restarting the local app before the final screenshots.

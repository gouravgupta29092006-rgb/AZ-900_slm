# Design System Strategy: The Focused Academic

## 1. Overview & Creative North Star
The North Star for this design system is **"The Scholarly Sanctuary."** 

We are moving away from the "generic chatbot" aesthetic to create a digital environment that feels like a private, high-end study suite. While the user requested a ChatGPT-inspired interface, we will elevate this by rejecting the standard "message bubbles on a flat background" look. Instead, we use **Atmospheric Layering**—an approach where the UI feels like architectural vellum stacked on a light-filled desk. By utilizing intentional asymmetry and varying the typographic scale between the intellectual rigor of *Manrope* and the functional clarity of *Inter*, we create an experience that feels both authoritative and deeply approachable.

---

### 2. Colors & Surface Philosophy

This system relies on tonal depth rather than structural lines. We use a palette of "Intellectual Blues" and "Paper Neutrals" to guide the student’s focus.

*   **The "No-Line" Rule:** 1px solid borders are strictly prohibited for sectioning. We define boundaries through background shifts. A `surface-container-low` chat history panel should sit against a `surface` main stage. If you feel the need for a line, you haven't used your spacing scale or tonal shifts effectively.
*   **Surface Hierarchy & Nesting:** Treat the UI as a physical stack. 
    *   **Level 0 (Background):** `surface` (#f8f9fa) - The base "desk."
    *   **Level 1 (Sections):** `surface-container-low` (#f3f4f5) - Large layout areas.
    *   **Level 2 (Active Cards):** `surface-container-lowest` (#ffffff) - Floating quiz cards or message inputs.
*   **The "Glass & Gradient" Rule:** To provide "soul," primary actions (`primary` #0052ae) should never be a flat block. Use a subtle linear gradient transitioning to `primary_container` (#006adc) at a 135-degree angle. Floating panels (like a tutor's "Quick Tips" widget) should use `surface_container_lowest` with a 12px backdrop-blur at 80% opacity to feel integrated into the environment.

---

### 3. Typography: The Editorial Voice

We use a dual-font strategy to distinguish between *Identity* and *Instruction*.

*   **Display & Headlines (Manrope):** These are your "Editorial" elements. Use `display-md` and `headline-lg` for welcome screens and lesson titles. The wide aperture of Manrope provides a modern, premium feel that looks custom-tailored.
*   **Body & UI (Inter):** All educational content, chat messages, and labels use Inter. It is the workhorse of legibility.
*   **Intentional Contrast:** Pair a `headline-sm` (Manrope, Bold) with a `body-md` (Inter, Regular) for lesson cards to create a clear "Title vs. Content" hierarchy that feels like a modern textbook.

---

### 4. Elevation & Depth

*   **The Layering Principle:** Avoid shadows for static elements. A `surface-container-highest` button on a `surface` background provides enough contrast.
*   **Ambient Shadows:** For active "floating" states (e.g., a dragged quiz answer), use a "Whisper Shadow": `color: on-surface (10% opacity)`, `blur: 24px`, `y-offset: 8px`. It should feel like a soft glow of light, not a heavy drop-shadow.
*   **The "Ghost Border" Fallback:** In high-density quiz layouts, if separation is required, use `outline_variant` at **15% opacity**. This creates a "suggestion" of a boundary that doesn't break the fluid aesthetic.

---

### 5. Components

#### Messaging Bubbles
Forbid the "heavy bubble" look. 
*   **Tutor Messages:** Use `surface-container-high` with an `xl` (1.5rem) top-left radius and `sm` (0.25rem) bottom-left radius to indicate "source."
*   **Student Messages:** Use `primary-fixed-dim` with inverted radii. No borders.

#### The "Deep-Input" Field
The message input is the hearth of the app. 
*   **Style:** `surface-container-lowest` background, `xl` (1.5rem) roundedness, and a `px` Ghost Border. 
*   **Focus State:** Transition the Ghost Border to 40% opacity `primary` and add a 4px soft outer glow.

#### Quiz Action Cards
*   **Container:** `surface-container-low`. 
*   **Interaction:** On hover, shift to `surface-container-lowest` and apply a Whisper Shadow. 
*   **Feedback:** Success states use `on-secondary-container` text on a `secondary-container` background. Error states use `error-container` (#ffdad6) with `on-error-container` (#93000a) text.

#### Progress Indicators (The "Aura" Loader)
Instead of a standard spinner, use a soft, pulsing gradient ring using `primary` and `tertiary-fixed-dim`. It should feel calming, not anxious.

---

### 6. Do's and Don'ts

*   **DO** use `6` (1.5rem) and `8` (2rem) spacing to let the tutor's explanations breathe. Educational fatigue is real; white space is the cure.
*   **DO** use **Asymmetric Radius** for cards. Use `xl` (1.5rem) for the top-right corner of a lesson card to give it a "tabbed" editorial feel.
*   **DON'T** use `0.5` or `1` spacing for anything other than tight icon-to-text relationships.
*   **DON'T** ever use #000000 for text. Always use `on-surface` (#191c1d) to maintain the soft, academic tone.
*   **DON'T** use dividers. If you need to separate two list items, use a `surface-variant` background shift or a `4` (1rem) vertical gap.
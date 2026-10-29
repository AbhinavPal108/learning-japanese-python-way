"""Learn page for guided number navigation and Japanese browser voice."""

import json
from nicegui import ui

from learning_japanese.config import DEFAULT_LEARNER_ID
from learning_japanese.frontend.theme import render_header, render_footer
from learning_japanese.services.number_service import number_details
from learning_japanese.services.learning_service import record_learning_event


def get_pronunciation_parts(number: int, romaji: str) -> list[str]:
    """
    Split Japanese number pronunciation into meaningful learning chunks.

    Examples:
        7   -> ["nana"]
        10  -> ["juu"]
        21  -> ["nijuu", "ichi"]
        29  -> ["nijuu", "kyuu"]
        90  -> ["kyuu", "juu"]
        99  -> ["kyuu", "juu", "kyuu"]
        100 -> ["hyaku"]
    """

    romaji = str(romaji).strip().lower()

    # 1–9
    if 1 <= number <= 9:
        return [romaji]

    # 10
    if number == 10:
        return [romaji]

    # 11–19
    if 11 <= number <= 19:

        ones = romaji.replace("juu", "", 1).strip()

        if ones:
            return ["juu", ones]

        return [romaji]

    # 100
    if number == 100:
        return [romaji]

    # 20–99
    if 20 <= number <= 99:

        # If the service already provides a space:
        # nijuu kyuu
        spaced = romaji.split()

        if len(spaced) == 2:
            return spaced

        # For forms such as:
        # nijuu
        # sanjuu
        # yonjuu
        # gojuu
        # rokujuu
        # nanajuu
        # hachijuu
        # kyuujuu
        if "juu" in romaji:

            index = romaji.find("juu")

            first = romaji[:index + 3]
            second = romaji[index + 3:]

            if first and second:
                return [first, second]

            if first:
                return [first]

    # Safe fallback
    return [romaji]


def render() -> None:

    render_header(
        "learn",
        "Learn Japanese Numbers",
        "Master numbers 1–100 with kanji, hiragana, Romaji and pronunciation."
    )

    state = {
        "number": 1,
        "speaking": False,
    }

    with ui.column().classes(
        "w-full max-w-6xl mx-auto px-4 md:px-6 pb-8 gap-5"
    ):

        # =========================================================
        # MAIN NUMBER CARD
        # =========================================================

        with ui.card().classes(
            "jp-card w-full p-5 md:p-8"
        ):

            with ui.row().classes(
                "w-full items-start justify-between gap-4"
            ):

                with ui.column().classes(
                    "gap-2 flex-1"
                ):

                    ui.label(
                        "NUMBER"
                    ).classes(
                        "text-xs font-extrabold tracking-widest text-gray-400"
                    )

                    number_label = ui.label(
                        "1"
                    ).classes("jp-number")

                    kanji_label = ui.label(
                        "一"
                    ).classes(
                        "text-2xl font-bold text-gray-500"
                    )

                    kana_label = ui.label(
                        "いち"
                    ).classes("jp-kana")

                    # Pronunciation container
                    romaji_container = ui.html(
                        '<div class="pronunciation-container">'
                        '<span class="pronunciation-part" data-index="0">'
                        'ichi'
                        '</span>'
                        '</div>'
                    ).classes("jp-romaji")

                # =================================================
                # AUDIO CONTROLS
                # =================================================

                with ui.column().classes(
                    "items-end gap-2"
                ):

                    ui.label(
                        "NUMBER RANGE"
                    ).classes(
                        "text-xs font-extrabold tracking-widest text-gray-400"
                    )

                    progress_label = ui.label(
                        "1 / 100"
                    ).classes(
                        "text-sm font-bold text-indigo-700"
                    )

                    ui.button(
                        "🔊 Listen",
                        on_click=lambda: speak()
                    ).props(
                        "unelevated no-caps"
                    ).classes(
                        "jp-primary rounded-lg"
                    )

                    ui.button(
                        "■ Stop voice",
                        on_click=lambda: stop_speech()
                    ).props(
                        "flat no-caps"
                    ).classes(
                        "text-gray-500"
                    )

                    ui.label(
                        "Checking Japanese voice…"
                    ).props(
                        "data-jp-voice-status"
                    ).classes(
                        "text-xs text-gray-500 max-w-64 text-right"
                    )

            ui.separator().classes("my-3")

            # =====================================================
            # SLIDER
            # =====================================================

            slider = ui.slider(
                min=1,
                max=100,
                value=1,
                step=1
            ).props(
                "label-always color=primary"
            )

            # =====================================================
            # PREVIOUS / NEXT
            # =====================================================

            with ui.row().classes(
                "w-full justify-between items-center mt-3 gap-2"
            ):

                ui.button(
                    "← Previous",
                    on_click=lambda: set_number(
                        max(1, state["number"] - 1)
                    )
                ).props(
                    "outline no-caps"
                )

                ui.button(
                    "Next →",
                    on_click=lambda: set_number(
                        min(100, state["number"] + 1)
                    )
                ).props(
                    "unelevated no-caps"
                ).classes(
                    "jp-primary"
                )

            ui.label(
                "Tip: use the slider or jump to a number range below."
            ).classes(
                "text-xs text-gray-500 mt-2"
            )

        # =========================================================
        # RANGE EXPLORER
        # =========================================================

        with ui.card().classes(
            "jp-soft w-full p-5"
        ):

            ui.label(
                "Explore a range"
            ).classes(
                "text-lg font-extrabold"
            )

            ui.label(
                "Choose a decade to jump directly to its first number."
            ).classes(
                "text-sm text-gray-500"
            )

            with ui.row().classes(
                "gap-2 flex-wrap mt-3"
            ):

                for start in range(1, 100, 10):

                    end = min(start + 9, 100)

                    ui.button(
                        f"{start}–{end}",
                        on_click=lambda n=start: set_number(n)
                    ).props(
                        "outline no-caps"
                    )

        # =========================================================
        # INFORMATION CARDS
        # =========================================================

        with ui.grid(columns=3).classes(
            "w-full gap-3"
        ):

            for label, value, desc in [
                (
                    "Numbers",
                    "1–100",
                    "Complete beginner range"
                ),
                (
                    "Reading",
                    "かな + 漢字",
                    "Kana and kanji"
                ),
                (
                    "Audio",
                    "ja-JP",
                    "Browser Japanese voice"
                ),
            ]:

                with ui.card().classes(
                    "jp-card p-4"
                ):

                    ui.label(
                        label
                    ).classes(
                        "text-xs text-gray-500"
                    )

                    ui.label(
                        value
                    ).classes(
                        "text-xl font-extrabold text-indigo-700"
                    )

                    ui.label(
                        desc
                    ).classes(
                        "text-xs text-gray-500"
                    )

    # =============================================================
    # FUNCTIONS
    # =============================================================

    def update_romaji_display(parts: list[str]) -> None:
        """
        Rebuild the Romaji HTML with one span per pronunciation part.
        """

        html_parts = []

        for index, part in enumerate(parts):

            html_parts.append(
                f'<span '
                f'class="pronunciation-part" '
                f'data-index="{index}">'
                f'{part}'
                f'</span>'
            )

        html = (
            '<div class="pronunciation-container">'
            + '<span class="pronunciation-space"></span>'.join(html_parts)
            + '</div>'
        )

        romaji_container.set_content(html)

    def clear_highlight() -> None:
        """
        Remove the active pronunciation highlight.
        """

        ui.run_javascript(
            """
            document
                .querySelectorAll('.pronunciation-part')
                .forEach(element => {
                    element.classList.remove(
                        'active-pronunciation'
                    );
                });
            """
        )

    def highlight_part(index: int) -> None:
        """
        Highlight one pronunciation part.
        """

        ui.run_javascript(
            f"""
            document
                .querySelectorAll('.pronunciation-part')
                .forEach(element => {{
                    element.classList.remove(
                        'active-pronunciation'
                    );
                }});

            const element = document.querySelector(
                '.pronunciation-part[data-index="{index}"]'
            );

            if (element) {{
                element.classList.add(
                    'active-pronunciation'
                );
            }}
            """
        )

    def stop_speech() -> None:
        """
        Stop all browser speech immediately and remove highlighting.
        """

        state["speaking"] = False

        ui.run_javascript(
            """
            (() => {
                // Invalidate any currently running pronunciation session.
                window.__jpSpeechSession = (window.__jpSpeechSession || 0) + 1;

                if (window.speechSynthesis) {
                    window.speechSynthesis.cancel();
                }

                document
                    .querySelectorAll('.pronunciation-part')
                    .forEach(element => {
                        element.classList.remove(
                            'active-pronunciation'
                        );
                    });
            })();
            """
        )

    def speak() -> None:
        """
        Speak the current Japanese number using the browser's
        Japanese Speech Synthesis voice.

        Each pronunciation chunk is highlighted while it is spoken.
        """

        details = number_details(state["number"])

        number = state["number"]
        hiragana = str(details["hiragana"])
        romaji = str(details["romaji"])

        parts = get_pronunciation_parts(number, romaji)

        # Build Japanese pronunciation chunks that correspond to the
        # displayed Romaji chunks.
        kana_parts = []

        if number <= 10:
            kana_parts = [hiragana]

        elif 11 <= number <= 19:
            if hiragana.startswith("じゅう"):
                remainder = hiragana[2:]
                kana_parts = ["じゅう", remainder] if remainder else [hiragana]
            else:
                kana_parts = [hiragana]

        elif 20 <= number <= 99:
            if "じゅう" in hiragana:
                index = hiragana.find("じゅう")
                first = hiragana[:index + 2]
                second = hiragana[index + 2:]
                kana_parts = [first, second] if second else [first]
            else:
                kana_parts = [hiragana]

        else:
            kana_parts = [hiragana]

        # Make sure the highlighting and speech arrays have the same length.
        if len(kana_parts) != len(parts):
            parts = [romaji]
            kana_parts = [hiragana]
            update_romaji_display(parts)

        state["speaking"] = True
        update_romaji_display(parts)

        kana_json = json.dumps(
            kana_parts,
            ensure_ascii=False
        )

        ui.run_javascript(
            f"""
            (() => {{
                const synth = window.speechSynthesis;

                if (!synth) {{
                    console.error('Speech Synthesis is not supported.');
                    return;
                }}

                // Cancel anything already speaking.
                synth.cancel();

                // Every click creates a new session. Older callbacks are
                // ignored so they cannot interfere with the new speech.
                const session = (window.__jpSpeechSession || 0) + 1;
                window.__jpSpeechSession = session;

                const kanaParts = {kana_json};
                let currentIndex = 0;
                let voices = synth.getVoices();

                function clearHighlight() {{
                    document
                        .querySelectorAll('.pronunciation-part')
                        .forEach(element => {{
                            element.classList.remove(
                                'active-pronunciation'
                            );
                        }});
                }}

                function findJapaneseVoice() {{
                    voices = synth.getVoices();

                    // Prefer Japanese voices explicitly.
                    return voices.find(voice =>
                        voice.lang &&
                        voice.lang.toLowerCase().startsWith('ja')
                    );
                }}

                function updateVoiceStatus(voice) {{
                    const status = document.querySelector(
                        '[data-jp-voice-status]'
                    );

                    if (!status) return;

                    if (voice) {{
                        status.textContent =
                            'Japanese voice: ' + voice.name;
                        status.classList.remove('text-red-500');
                        status.classList.add('text-green-600');
                    }} else {{
                        status.textContent =
                            'Japanese voice not detected — browser fallback may be used';
                        status.classList.remove('text-green-600');
                        status.classList.add('text-red-500');
                    }}
                }}

                function speakNext() {{
                    // Ignore callbacks from an older speech session.
                    if (window.__jpSpeechSession !== session) return;

                    if (currentIndex >= kanaParts.length) {{
                        clearHighlight();
                        return;
                    }}

                    clearHighlight();

                    const activeElement = document.querySelector(
                        '.pronunciation-part[data-index="'
                        + currentIndex
                        + '"]'
                    );

                    if (activeElement) {{
                        activeElement.classList.add(
                            'active-pronunciation'
                        );
                    }}

                    const utterance =
                        new SpeechSynthesisUtterance(
                            kanaParts[currentIndex]
                        );

                    const japaneseVoice = findJapaneseVoice();

                    utterance.lang = 'ja-JP';
                    utterance.rate = 0.80;
                    utterance.pitch = 1.0;
                    utterance.volume = 1.0;

                    if (japaneseVoice) {{
                        utterance.voice = japaneseVoice;
                    }}

                    updateVoiceStatus(japaneseVoice);

                    utterance.onend = () => {{
                        if (window.__jpSpeechSession !== session) return;

                        currentIndex += 1;

                        setTimeout(() => {{
                            speakNext();
                        }}, 150);
                    }};

                    utterance.onerror = (event) => {{
                        if (window.__jpSpeechSession !== session) return;

                        // 'canceled' and 'interrupted' are normal when the
                        // user presses Stop or starts another pronunciation.
                        if (event.error !== 'canceled' &&
                            event.error !== 'interrupted') {{
                            console.error(
                                'Japanese speech error:',
                                event.error
                            );
                        }}

                        clearHighlight();
                    }};

                    synth.speak(utterance);
                }}

                // Chrome may populate voices asynchronously.
                const startWhenReady = () => {{
                    if (window.__jpSpeechSession !== session) return;

                    const japaneseVoice = findJapaneseVoice();
                    updateVoiceStatus(japaneseVoice);

                    // Remove the temporary handler after the first useful call.
                    synth.removeEventListener(
                        'voiceschanged',
                        startWhenReady
                    );

                    speakNext();
                }};

                if (voices.length === 0) {{
                    synth.addEventListener(
                        'voiceschanged',
                        startWhenReady
                    );

                    // Some browsers do not fire voiceschanged reliably.
                    setTimeout(() => {{
                        if (window.__jpSpeechSession !== session) return;

                        const available = synth.getVoices();

                        if (available.length > 0) {{
                            startWhenReady();
                        }} else {{
                            // Try the browser fallback even without an
                            // explicitly exposed voice list.
                            speakNext();
                        }}
                    }}, 300);
                }} else {{
                    startWhenReady();
                }}
            }})();
            """
        )

        record_learning_event(
    DEFAULT_LEARNER_ID,
    "audio_listen",
    number,
    {
        "language": "ja-JP",
        "parts": parts,
    }
)


    def set_number(number: int) -> None:
        """
        Change the displayed number and update all learning content.
        """

        # Stop any previous pronunciation
        stop_speech()

        state["number"] = number

        details = number_details(number)

        number_label.set_text(
            str(number)
        )

        kanji_label.set_text(
            str(details["kanji"])
        )

        kana_label.set_text(
            str(details["hiragana"])
        )

        parts = get_pronunciation_parts(
            number,
            str(details["romaji"])
        )

        update_romaji_display(parts)

        progress_label.set_text(
            f"{number} / 100"
        )

        slider.value = number

        record_learning_event(
            DEFAULT_LEARNER_ID,
            "lesson_view",
            number,
            {
                "module": "learn"
            }
        )

    # =============================================================
    # SLIDER EVENT
    # =============================================================

    slider.on_value_change(
        lambda event: set_number(
            int(event.value)
        )
    )

    # Initial learning event
    record_learning_event(
        DEFAULT_LEARNER_ID,
        "lesson_view",
        1,
        {
            "module": "learn"
        }
    )


    render_footer()
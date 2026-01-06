import csv
import os
import platform
import random
import subprocess
import tempfile
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

import requests
from tkinter import font as tkfont


GRAMMAR_FORMS = [
    "S+不仅 + V1 + Ō, 也/还/而且 + V2 + Ó",
    "即使。。。也",
    "V + 光",
    "A 占 B + 数量",
    "V + 成 + Result",
    "好不容易 + 才 + Result",
    "比起来 B + (更 / 比较) + Adjective / Phrase",
    "跟 B 比起来 + (更 / 比较) + Adjective / Phrase",
]


@dataclass
class VocabularyList:
    name: str
    words: List[str] = field(default_factory=list)
    tones: Dict[str, str] = field(default_factory=dict)
    color: str = "#2e7d32"


class ChineseLearningApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Chinese Learning App")
        self.geometry("980x720")

        self.vocab_lists: List[VocabularyList] = []
        self.colors = ["#2e7d32", "#1565c0", "#6a1b9a", "#ef6c00", "#ad1457"]
        self.highlight_font_size = tk.IntVar(value=14)
        self.sentence_font_size = tk.IntVar(value=14)
        self.highlight_font = tkfont.Font(family="Helvetica", size=self.highlight_font_size.get())
        self.sentence_font = tkfont.Font(family="Helvetica", size=self.sentence_font_size.get())
        self.generated_sentences: List[str] = []

        self._build_layout()

    def _build_layout(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=12, pady=10)

        ttk.Label(
            header,
            text="Chinese Learning App",
            font=("Helvetica", 18, "bold"),
        ).pack(side=tk.LEFT)

        ttk.Button(header, text="Load Vocabulary CSV", command=self.load_csv).pack(
            side=tk.RIGHT
        )

        self.list_summary = ttk.Label(header, text="No vocabulary lists loaded")
        self.list_summary.pack(side=tk.RIGHT, padx=12)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self._build_highlight_tab()
        self._build_sentence_tab()
        self._build_quiz_tab()

    def _build_highlight_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Highlight Text")

        info = (
            "Paste Chinese text below. Words found in your vocabulary lists will be "
            "highlighted by list color."
        )
        header = ttk.Frame(frame)
        header.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(header, text=info, wraplength=760).pack(side=tk.LEFT, anchor=tk.W)

        ttk.Label(header, text="Text size:").pack(side=tk.LEFT, padx=(16, 4))
        size_selector = ttk.Combobox(
            header,
            textvariable=self.highlight_font_size,
            values=[14, 16, 18],
            state="readonly",
            width=5,
        )
        size_selector.pack(side=tk.LEFT)
        size_selector.bind("<<ComboboxSelected>>", self._update_highlight_font)

        self.highlight_text = tk.Text(frame, height=20, wrap=tk.WORD, font=self.highlight_font)
        self.highlight_text.pack(fill=tk.BOTH, expand=True, pady=10)

        ttk.Button(frame, text="Highlight Vocabulary", command=self.highlight_vocab).pack(
            anchor=tk.E, pady=8
        )

        self.highlight_legend = ttk.Frame(frame)
        self.highlight_legend.pack(fill=tk.X)

    def _build_sentence_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Sentence Generator")

        instructions = (
            "Generated sentences use the fixed grammar forms below and multiple random "
            "words from your vocabulary lists."
        )
        header = ttk.Frame(frame)
        header.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(header, text=instructions, wraplength=700).pack(side=tk.LEFT, anchor=tk.W)

        ttk.Label(header, text="Text size:").pack(side=tk.LEFT, padx=(16, 4))
        size_selector = ttk.Combobox(
            header,
            textvariable=self.sentence_font_size,
            values=[14, 16, 18],
            state="readonly",
            width=5,
        )
        size_selector.pack(side=tk.LEFT)
        size_selector.bind("<<ComboboxSelected>>", self._update_sentence_font)

        grammar_box = tk.Text(frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        grammar_box.pack(fill=tk.X, pady=6)
        grammar_box.config(state=tk.NORMAL)
        grammar_box.insert(tk.END, "\n".join(f"- {form}" for form in GRAMMAR_FORMS))
        grammar_box.config(state=tk.DISABLED)

        options_frame = ttk.Frame(frame)
        options_frame.pack(fill=tk.X)
        ttk.Label(options_frame, text="Number of sentences:").pack(side=tk.LEFT)

        self.sentence_count = tk.IntVar(value=5)
        ttk.Spinbox(options_frame, from_=1, to=20, textvariable=self.sentence_count, width=6).pack(
            side=tk.LEFT, padx=6
        )

        ttk.Label(options_frame, text="Mode:").pack(side=tk.LEFT, padx=(12, 4))
        self.sentence_mode = tk.StringVar(value="reading")
        ttk.Radiobutton(
            options_frame,
            text="Reading",
            variable=self.sentence_mode,
            value="reading",
            command=self._update_sentence_mode,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            options_frame,
            text="Audio",
            variable=self.sentence_mode,
            value="audio",
            command=self._update_sentence_mode,
        ).pack(side=tk.LEFT, padx=(6, 0))

        ttk.Button(options_frame, text="Generate", command=self.generate_sentences).pack(
            side=tk.RIGHT
        )

        self.sentences_output = tk.Text(
            frame, height=15, wrap=tk.WORD, state=tk.DISABLED, font=self.sentence_font
        )
        self.sentences_output.pack(fill=tk.BOTH, expand=True, pady=10)

        audio_controls = ttk.Frame(frame)
        audio_controls.pack(fill=tk.X)
        self.reveal_button = ttk.Button(
            audio_controls, text="Reveal Text", command=self._reveal_sentence_text
        )
        self.audio_button = ttk.Button(
            audio_controls, text="Play Audio", command=self._play_audio_sentence
        )
        self.reveal_button.pack(side=tk.LEFT)
        self.audio_button.pack(side=tk.LEFT, padx=6)
        self._update_sentence_mode()

    def _build_quiz_tab(self) -> None:
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Tone Quiz")

        instructions = (
            "Generate a sentence from your vocabulary lists, then choose the correct tone "
            "for the highlighted target word. Tones should be provided in your CSV files "
            "with a column named 'tone'."
        )
        ttk.Label(frame, text=instructions, wraplength=900).pack(anchor=tk.W)

        ttk.Button(frame, text="New Quiz", command=self.new_quiz).pack(anchor=tk.E, pady=6)

        self.quiz_sentence = ttk.Label(
            frame, text="Load vocabulary lists with tones to begin.", font=("Helvetica", 24)
        )
        self.quiz_sentence.pack(fill=tk.X, pady=20)

        selection_frame = ttk.Frame(frame)
        selection_frame.pack()
        ttk.Label(selection_frame, text="Select tone:").pack(side=tk.LEFT)

        self.tone_choice = tk.StringVar(value="1")
        self.tone_dropdown = ttk.Combobox(
            selection_frame,
            textvariable=self.tone_choice,
            values=["1", "2", "3", "4", "5"],
            state="readonly",
            width=5,
        )
        self.tone_dropdown.pack(side=tk.LEFT, padx=6)

        ttk.Button(selection_frame, text="Submit", command=self.check_answer).pack(
            side=tk.LEFT, padx=6
        )

        self.quiz_feedback = ttk.Label(frame, text="")
        self.quiz_feedback.pack(pady=10)

        self.current_quiz_word: Optional[str] = None
        self.current_quiz_tone: Optional[str] = None

    def load_csv(self) -> None:
        filenames = filedialog.askopenfilenames(
            title="Select vocabulary CSV files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
        )
        if not filenames:
            return

        for index, filename in enumerate(filenames):
            try:
                vocab_list = self._read_vocab_file(Path(filename), index)
            except Exception as exc:  # noqa: BLE001 - display error to user
                messagebox.showerror("CSV Error", f"Failed to load {filename}: {exc}")
                continue
            self.vocab_lists.append(vocab_list)

        self._refresh_list_summary()
        self._refresh_legend()

    def _read_vocab_file(self, path: Path, index: int) -> VocabularyList:
        words: List[str] = []
        tones: Dict[str, str] = {}
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("CSV must include headers")
            word_field = self._match_field(reader.fieldnames, ["word", "vocab", "character"])
            tone_field = self._match_field(reader.fieldnames, ["tone", "tones"])

            for row in reader:
                word = (row.get(word_field) or "").strip()
                if not word:
                    continue
                words.append(word)
                if tone_field:
                    tone = (row.get(tone_field) or "").strip()
                    if tone:
                        tones[word] = tone

        if not words:
            raise ValueError("No words found in CSV")

        color = self.colors[index % len(self.colors)]
        return VocabularyList(name=path.stem, words=words, tones=tones, color=color)

    @staticmethod
    def _match_field(fieldnames: List[str], candidates: List[str]) -> str:
        lowered = {field.lower(): field for field in fieldnames}
        for candidate in candidates:
            if candidate in lowered:
                return lowered[candidate]
        return fieldnames[0]

    def _refresh_list_summary(self) -> None:
        if not self.vocab_lists:
            self.list_summary.config(text="No vocabulary lists loaded")
            return
        summary = ", ".join(f"{v.name} ({len(v.words)})" for v in self.vocab_lists)
        self.list_summary.config(text=f"Loaded: {summary}")

    def _refresh_legend(self) -> None:
        for child in self.highlight_legend.winfo_children():
            child.destroy()
        if not self.vocab_lists:
            ttk.Label(self.highlight_legend, text="Load vocabulary lists to show legend.").pack(
                anchor=tk.W
            )
            return
        for vocab in self.vocab_lists:
            label = ttk.Label(self.highlight_legend, text=vocab.name)
            label.pack(side=tk.LEFT, padx=6)
            label.config(foreground=vocab.color)

    def highlight_vocab(self) -> None:
        text = self.highlight_text.get("1.0", tk.END)
        self.highlight_text.tag_delete("vocab")
        for vocab in self.vocab_lists:
            tag = f"vocab_{vocab.name}"
            self.highlight_text.tag_config(
                tag, foreground=vocab.color, font=self.highlight_font
            )
            for word in sorted(vocab.words, key=len, reverse=True):
                start = "1.0"
                while True:
                    start = self.highlight_text.search(word, start, tk.END)
                    if not start:
                        break
                    end = f"{start}+{len(word)}c"
                    self.highlight_text.tag_add(tag, start, end)
                    start = end

    def generate_sentences(self) -> None:
        vocab_words = self._all_words()
        if not vocab_words:
            messagebox.showwarning("Missing Vocabulary", "Load vocabulary lists first.")
            return

        sentence_count = max(1, int(self.sentence_count.get()))
        generated: List[str] = []
        for _ in range(sentence_count):
            grammar = random.choice(GRAMMAR_FORMS)
            sentence = self._generate_sentence_with_chatgpt(grammar, vocab_words)
            generated.append(sentence)

        self.generated_sentences = generated
        self._render_sentence_output()

    def _generate_sentence_with_chatgpt(self, grammar: str, vocab_words: List[str]) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            messagebox.showwarning(
                "Missing API Key",
                "Set OPENAI_API_KEY to enable ChatGPT sentence generation.",
            )
            return self._fallback_sentence(grammar, vocab_words)

        words = random.sample(vocab_words, k=min(3, len(vocab_words)))
        prompt = (
            "Create one natural Chinese sentence using the grammar pattern provided. "
            "Include all of the vocabulary words listed. Respond with only the sentence.\n"
            f"Grammar pattern: {grammar}\n"
            f"Vocabulary words: {', '.join(words)}"
        )
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You generate Chinese study sentences."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if response.status_code != 200:
            messagebox.showwarning(
                "ChatGPT Error",
                f"ChatGPT request failed ({response.status_code}). Using fallback sentence.",
            )
            return self._fallback_sentence(grammar, vocab_words)

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        return content

    def _fallback_sentence(self, grammar: str, vocab_words: List[str]) -> str:
        words = random.sample(vocab_words, k=min(3, len(vocab_words)))
        return f"{grammar}：{' '.join(words)}"

    def _all_words(self) -> List[str]:
        words: List[str] = []
        for vocab in self.vocab_lists:
            words.extend(vocab.words)
        return words

    def new_quiz(self) -> None:
        tone_entries: List[Tuple[str, str]] = []
        for vocab in self.vocab_lists:
            for word, tone in vocab.tones.items():
                tone_entries.append((word, tone))

        if not tone_entries:
            messagebox.showwarning(
                "Missing Tones",
                "Load vocabulary CSV files with a 'tone' column to enable the quiz.",
            )
            return

        vocab_words = self._all_words()
        quiz_word, quiz_tone = random.choice(tone_entries)

        sentence = self._generate_quiz_sentence(quiz_word, vocab_words)
        sentence = sentence.replace(quiz_word, f"【{quiz_word}】", 1)

        self.quiz_sentence.config(text=sentence)
        self.current_quiz_word = quiz_word
        self.current_quiz_tone = quiz_tone
        self.quiz_feedback.config(text="")

    def check_answer(self) -> None:
        if not self.current_quiz_word or not self.current_quiz_tone:
            messagebox.showinfo("No Quiz", "Click 'New Quiz' to generate a question.")
            return
        chosen = self.tone_choice.get()
        if chosen == self.current_quiz_tone:
            self.quiz_feedback.config(text="Correct!", foreground="#2e7d32")
        else:
            self.quiz_feedback.config(
                text=(
                    f"Incorrect. {self.current_quiz_word} has tone "
                    f"{self.current_quiz_tone}."
                ),
                foreground="#c62828",
            )

    def _update_highlight_font(self, event: Optional[tk.Event] = None) -> None:
        self.highlight_font.configure(size=self.highlight_font_size.get())
        self.highlight_text.configure(font=self.highlight_font)
        self.highlight_vocab()

    def _update_sentence_font(self, event: Optional[tk.Event] = None) -> None:
        self.sentence_font.configure(size=self.sentence_font_size.get())
        self.sentences_output.configure(font=self.sentence_font)

    def _update_sentence_mode(self) -> None:
        mode = self.sentence_mode.get()
        if mode == "audio":
            self.reveal_button.pack(side=tk.LEFT)
            self.audio_button.pack(side=tk.LEFT, padx=6)
        else:
            self.reveal_button.pack_forget()
            self.audio_button.pack_forget()
        self._render_sentence_output()

    def _render_sentence_output(self) -> None:
        self.sentences_output.config(state=tk.NORMAL)
        self.sentences_output.delete("1.0", tk.END)
        if self.sentence_mode.get() == "reading":
            self.sentences_output.insert(tk.END, "\n".join(self.generated_sentences))
        self.sentences_output.config(state=tk.DISABLED)

    def _reveal_sentence_text(self) -> None:
        self.sentences_output.config(state=tk.NORMAL)
        self.sentences_output.delete("1.0", tk.END)
        self.sentences_output.insert(tk.END, "\n".join(self.generated_sentences))
        self.sentences_output.config(state=tk.DISABLED)

    def _play_audio_sentence(self) -> None:
        if not self.generated_sentences:
            messagebox.showinfo("No Sentences", "Generate sentences first.")
            return
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            messagebox.showwarning(
                "Missing API Key",
                "Set OPENAI_API_KEY to enable audio playback.",
            )
            return
        text = "。".join(self.generated_sentences)
        payload = {"model": "gpt-4o-mini-tts", "voice": "alloy", "input": text}
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=30,
        )
        if response.status_code != 200:
            messagebox.showwarning(
                "Audio Error",
                f"Audio request failed ({response.status_code}).",
            )
            return
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as handle:
            handle.write(response.content)
            audio_path = handle.name
        self._open_audio_file(audio_path)

    def _open_audio_file(self, path: str) -> None:
        system = platform.system().lower()
        if system == "darwin":
            subprocess.run(["open", path], check=False)
        elif system == "windows":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", path], check=False)

    def _generate_quiz_sentence(self, target_word: str, vocab_words: List[str]) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return self._fallback_sentence(random.choice(GRAMMAR_FORMS), vocab_words)
        grammar = random.choice(GRAMMAR_FORMS)
        words = [target_word]
        remaining = [word for word in vocab_words if word != target_word]
        words.extend(random.sample(remaining, k=min(2, len(remaining))))
        prompt = (
            "Create one natural Chinese sentence using the grammar pattern provided. "
            "Include all of the vocabulary words listed. Respond with only the sentence.\n"
            f"Grammar pattern: {grammar}\n"
            f"Vocabulary words: {', '.join(words)}"
        )
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You generate Chinese study sentences."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
        }
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if response.status_code != 200:
            return self._fallback_sentence(grammar, vocab_words)
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


if __name__ == "__main__":
    app = ChineseLearningApp()
    app.mainloop()

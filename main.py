import csv
import random
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


@dataclass
class VocabularyList:
    name: str
    words: list[str] = field(default_factory=list)
    tones: dict[str, str] = field(default_factory=dict)
    color: str = "#2e7d32"


class ChineseLearningApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Chinese Learning App")
        self.geometry("980x720")

        self.vocab_lists: list[VocabularyList] = []
        self.colors = ["#2e7d32", "#1565c0", "#6a1b9a", "#ef6c00", "#ad1457"]

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
        ttk.Label(frame, text=info, wraplength=900).pack(anchor=tk.W)

        self.highlight_text = tk.Text(frame, height=20, wrap=tk.WORD)
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
            "Enter grammar patterns below, one per line. Use {word} to insert a random "
            "vocabulary word. Example: \"我想要 {word}\"."
        )
        ttk.Label(frame, text=instructions, wraplength=900).pack(anchor=tk.W)

        self.grammar_input = tk.Text(frame, height=10, wrap=tk.WORD)
        self.grammar_input.pack(fill=tk.X, pady=8)

        options_frame = ttk.Frame(frame)
        options_frame.pack(fill=tk.X)
        ttk.Label(options_frame, text="Number of sentences:").pack(side=tk.LEFT)

        self.sentence_count = tk.IntVar(value=5)
        ttk.Spinbox(options_frame, from_=1, to=20, textvariable=self.sentence_count, width=6).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(options_frame, text="Generate", command=self.generate_sentences).pack(
            side=tk.RIGHT
        )

        self.sentences_output = tk.Text(frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        self.sentences_output.pack(fill=tk.BOTH, expand=True, pady=10)

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
            frame, text="Load vocabulary lists with tones to begin.", font=("Helvetica", 20)
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

        self.current_quiz_word: str | None = None
        self.current_quiz_tone: str | None = None

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
        words: list[str] = []
        tones: dict[str, str] = {}
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
    def _match_field(fieldnames: list[str], candidates: list[str]) -> str:
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
            self.highlight_text.tag_config(tag, foreground=vocab.color)
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
        grammar_lines = [line.strip() for line in self.grammar_input.get("1.0", tk.END).splitlines()]
        grammar_lines = [line for line in grammar_lines if line]

        vocab_words = self._all_words()
        if not vocab_words:
            messagebox.showwarning("Missing Vocabulary", "Load vocabulary lists first.")
            return
        if not grammar_lines:
            messagebox.showwarning(
                "Missing Grammar", "Add at least one grammar pattern line."
            )
            return

        sentence_count = max(1, int(self.sentence_count.get()))
        generated: list[str] = []
        for _ in range(sentence_count):
            template = random.choice(grammar_lines)
            sentence = self._fill_template(template, vocab_words)
            generated.append(sentence)

        self.sentences_output.config(state=tk.NORMAL)
        self.sentences_output.delete("1.0", tk.END)
        self.sentences_output.insert(tk.END, "\n".join(generated))
        self.sentences_output.config(state=tk.DISABLED)

    def _fill_template(self, template: str, vocab_words: list[str]) -> str:
        if "{word}" not in template:
            return f"{template} {random.choice(vocab_words)}"
        while "{word}" in template:
            template = template.replace("{word}", random.choice(vocab_words), 1)
        return template

    def _all_words(self) -> list[str]:
        words: list[str] = []
        for vocab in self.vocab_lists:
            words.extend(vocab.words)
        return words

    def new_quiz(self) -> None:
        tone_entries: list[tuple[str, str]] = []
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
        sentence_length = min(6, max(3, len(vocab_words)))
        sentence_words = random.sample(vocab_words, k=sentence_length)
        quiz_word, quiz_tone = random.choice(tone_entries)

        if quiz_word not in sentence_words:
            sentence_words[random.randrange(len(sentence_words))] = quiz_word

        sentence = " ".join(sentence_words)
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


if __name__ == "__main__":
    app = ChineseLearningApp()
    app.mainloop()

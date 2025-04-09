import dataclasses
import typing


@dataclasses.dataclass
class Language:
    date_label: str
    time_label: str
    from_label: str
    to_label: str
    class_label: str


@dataclasses.dataclass
class TicketLanguage:
    primary_language: Language
    secondary_language: typing.Optional[Language] = None

    @classmethod
    def from_header(cls, primary_code: str, secondary_code: typing.Optional[str]) -> "TicketLanguage":
        if primary_code in LANGUAGES:
            primary = LANGUAGES[primary_code]
        else:
            primary = LANGUAGES["DE"]

        if secondary_code and secondary_code != primary_code and secondary_code in LANGUAGES:
            secondary = LANGUAGES[secondary_code]
        else:
            secondary = None

        return cls(
            primary_language=primary,
            secondary_language=secondary,
        )

    def get_label(self, label: str) -> str:
        if self.secondary_language:
            s1 = getattr(self.primary_language, label)
            s2 = getattr(self.secondary_language, label)
            if s1 != s2:
                return f"{s1}\n{s2}"
            else:
                return s1
        else:
            return getattr(self.primary_language, label)

    @property
    def date_label(self) -> str:
        return self.get_label("date_label")

    @property
    def time_label(self) -> str:
        return self.get_label("time_label")

    @property
    def from_label(self) -> str:
        return self.get_label("from_label")

    @property
    def to_label(self) -> str:
        return self.get_label("to_label")

    @property
    def class_label(self) -> str:
        return self.get_label("class_label")


LANGUAGES = {
    "EN": Language(
        date_label="Date",
        time_label="Time",
        from_label="From",
        to_label="To",
        class_label="Cl.",
    ),
    "DE": Language(
        date_label="Datum",
        time_label="Zeit",
        from_label="Von",
        to_label="Nach",
        class_label="Kl.",
    ),
    "NL": Language(
        date_label="Datum",
        time_label="Tijd",
        from_label="Van",
        to_label="Naar",
        class_label="Kl.",
    ),
    "FR": Language(
        date_label="Date",
        time_label="Temps",
        from_label="De",
        to_label="À",
        class_label="Cl.",
    ),
    "IT": Language(
        date_label="Data",
        time_label="Tempo",
        from_label="Da",
        to_label="Dopo",
        class_label="Cl.",
    ),
    "CZ": Language(
        date_label="Datum",
        time_label="Čas",
        from_label="Z",
        to_label="Po",
        class_label="Třída",
    ),
    "DA": Language(
        date_label="Dato",
        time_label="Tid",
        from_label="Fra",
        to_label="Efter",
        class_label="Kl.",
    ),
}
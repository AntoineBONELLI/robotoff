import re
from typing import List, Dict, Tuple, Union

from robotoff.insights.ocr.dataclass import OCRResult, OCRRegex, OCRField, get_text
from robotoff.utils.types import JSONType


EXTRACTOR_VERSION = "1"


NutrientMentionType = Tuple[str, List[str]]

NUTRIENT_MENTION: Dict[str, List[NutrientMentionType]] = {
    "energy": [
        ("[ée]nergie", ["fr", "de"]),
        ("valeurs? [ée]nerg[ée]tiques?", ["fr"]),
        ("energy", ["en"]),
        ("calories", ["fr", "en"]),
        ("energia", ["es"]),
        ("valor energ[ée]tico", ["es"]),
    ],
    "saturated_fat": [
        ("mati[èe]res? grasses? satur[ée]s?", ["fr"]),
        ("acides? gras satur[ée]s?", ["fr"]),
        ("dont satur[ée]s?", ["fr"]),
        ("saturated fat", ["en"]),
        ("of which saturates", ["en"]),
        ("verzadigde vetzuren", ["nl"]),
        ("waarvan verzadigde", ["nl"]),
        ("gesättigte fettsäuren", ["de"]),
        ("[aá]cidos grasos saturados", ["es"]),
    ],
    "trans_fat": [("mati[èe]res? grasses? trans", ["fr"]), ("trans fat", ["en"])],
    "fat": [
        ("mati[èe]res? grasses?", ["fr"]),
        ("graisses?", ["fr"]),
        ("lipides?", ["fr"]),
        ("total fat", ["en"]),
        ("vetten", ["nl"]),
        ("fett", ["de"]),
        ("grasas", ["es"]),
        ("l[íi]pidos", ["es"]),
    ],
    "sugar": [
        ("sucres?", ["fr"]),
        ("sugars?", ["en"]),
        ("suikers?", ["nl"]),
        ("zucker", ["de"]),
        ("az[úu]cares", ["es"]),
    ],
    "carbohydrate": [
        ("total carbohydrate", ["en"]),
        ("glucids?", ["fr"]),
        ("glucides?", ["en"]),
        ("koolhydraten", ["nl"]),
        ("koolhydraat", ["nl"]),
        ("kohlenhydrate", ["de"]),
        ("hidratos de carbono", ["es"]),
    ],
    "protein": [
        ("prot[ée]ines?", ["fr"]),
        ("protein", ["en"]),
        ("eiwitten", ["nl"]),
        ("eiweiß", ["de"]),
        ("prote[íi]nas", ["es"]),
    ],
    "salt": [
        ("sel", ["fr"]),
        ("salt", ["en"]),
        ("zout", ["nl"]),
        ("salz", ["de"]),
        ("sal", ["es"]),
    ],
    "fiber": [
        ("fibres?", ["en", "fr"]),
        ("fibers?", ["en"]),
        ("fibres? alimentaires?", ["fr"]),
        ("(?:voedings)?vezels?", ["nl"]),
        ("ballaststoffe", ["de"]),
        ("fibra(?: alimentaria)?", ["es"]),
    ],
    "nutrition_values": [
        ("informations? nutritionnelles?(?: moyennes?)?", ["fr"]),
        ("valeurs? nutritionnelles?(?: moyennes?)?", ["fr"]),
        ("analyse moyenne pour", ["fr"]),
        ("valeurs? nutritives?", ["fr"]),
        ("valeurs? moyennes?", ["fr"]),
        ("nutrition facts?", ["en"]),
        ("gemiddelde waarden per", ["nl"]),
    ],
}


NUTRIENT_UNITS: Dict[str, List[str]] = {
    "energy": ["kj", "kcal"],
    "saturated_fat": ["g"],
    "trans_fat": ["g"],
    "fat": ["g"],
    "sugar": ["g"],
    "carbohydrate": ["g"],
    "protein": ["g"],
    "salt": ["g"],
    "fiber": ["g"],
}


def generate_nutrient_regex(
    nutrient_mentions: List[NutrientMentionType], units: List[str]
):
    nutrient_names = [x[0] for x in nutrient_mentions]
    nutrient_names_str = "|".join(nutrient_names)
    units_str = "|".join(units)
    return re.compile(
        r"(?<!\w)({}) ?(?:[:-] ?)?([0-9]+[,.]?[0-9]*) ?({})(?!\w)".format(
            nutrient_names_str, units_str
        )
    )


def generate_nutrient_mention_regex(nutrient_mentions: List[NutrientMentionType]):
    nutrient_names = [x[0] for x in nutrient_mentions]
    nutrient_names_str = "|".join(nutrient_names)
    return re.compile(r"(?<!\w)({})(?!\w)".format(nutrient_names_str))


NUTRIENT_VALUES_REGEX = {
    nutrient: OCRRegex(
        generate_nutrient_regex(NUTRIENT_MENTION[nutrient], units),
        field=OCRField.full_text_contiguous,
        lowercase=True,
    )
    for nutrient, units in NUTRIENT_UNITS.items()
}

NUTRIENT_MENTIONS_REGEX = {
    nutrient: OCRRegex(
        generate_nutrient_mention_regex(NUTRIENT_MENTION[nutrient]),
        field=OCRField.full_text_contiguous,
        lowercase=True,
    )
    for nutrient in NUTRIENT_MENTION
}


def find_nutrient_values(content: Union[OCRResult, str]) -> List[Dict]:
    nutrients: JSONType = {}

    for regex_code, ocr_regex in NUTRIENT_VALUES_REGEX.items():
        text = get_text(content, ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            value = match.group(2).replace(",", ".")
            unit = match.group(3)
            nutrients.setdefault(regex_code, [])
            nutrients[regex_code].append(
                {
                    "raw": match.group(0),
                    "nutrient": regex_code,
                    "value": value,
                    "unit": unit,
                }
            )

    if not nutrients:
        return []

    return [{"nutrients": nutrients, "version": EXTRACTOR_VERSION}]


def find_nutrient_mentions(content: Union[OCRResult, str]) -> List[Dict]:
    nutrients: JSONType = {}

    for regex_code, ocr_regex in NUTRIENT_MENTIONS_REGEX.items():
        text = get_text(content, ocr_regex)

        if not text:
            continue

        for match in ocr_regex.regex.finditer(text):
            nutrients.setdefault(regex_code, [])
            nutrients[regex_code].append(
                {"raw": match.group(0), "span": list(match.span())}
            )

    if not nutrients:
        return []

    return [{"mentions": nutrients, "version": EXTRACTOR_VERSION}]

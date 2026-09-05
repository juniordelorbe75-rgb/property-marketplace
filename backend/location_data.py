import unicodedata


DOMINICAN_PROVINCES = (
    "Azua", "Baoruco", "Barahona", "Dajabón", "Distrito Nacional", "Duarte",
    "El Seibo", "Elías Piña", "Espaillat", "Hato Mayor", "Hermanas Mirabal",
    "Independencia", "La Altagracia", "La Romana", "La Vega",
    "María Trinidad Sánchez", "Monseñor Nouel", "Monte Cristi", "Monte Plata",
    "Pedernales", "Peravia", "Puerto Plata", "Samaná", "San Cristóbal",
    "San José de Ocoa", "San Juan", "San Pedro de Macorís", "Sánchez Ramírez",
    "Santiago", "Santiago Rodríguez", "Santo Domingo", "Valverde",
)


def _search_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip())
    return "".join(character for character in normalized if not unicodedata.combining(character)).casefold()


PROVINCE_BY_SEARCH_KEY = {_search_key(name): name for name in DOMINICAN_PROVINCES}


def normalize_dominican_province(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        return ""
    province = PROVINCE_BY_SEARCH_KEY.get(_search_key(normalized))
    if province is None:
        raise ValueError("Select a valid Dominican province or the National District")
    return province


def normalize_location_part(value: str) -> str:
    return " ".join(value.strip().split())

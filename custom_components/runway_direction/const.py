"""Constants for the Runway Direction integration."""

from datetime import timedelta

DOMAIN = "runway_direction"

EVENT_RUNWAY_CHANGED = f"{DOMAIN}_runway_changed"

CARD_FILENAME = "runway-direction-card.js"
CARD_URL_PATH = f"/{DOMAIN}/{CARD_FILENAME}"
DATA_CARD_REGISTERED = f"{DOMAIN}_card_registered"

CONF_ICAO = "icao"
CONF_SLUG = "slug"
CONF_COUNTRY_SLUG = "country_slug"
CONF_AIRPORT_NAME = "airport_name"
CONF_NOISE_RUNWAYS = "noise_runways"
CONF_WARNING_MINUTES = "warning_minutes"
CONF_MIN_CONFIDENCE = "min_confidence"

DEFAULT_WARNING_MINUTES = 60
MAX_WARNING_MINUTES = 360
MIN_WARNING_MINUTES = 0
WARNING_MINUTES_STEP = 5

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

# Numeric stand-ins so confidence from different sources is comparable.
CONFIDENCE_SCORES = {
    CONFIDENCE_HIGH: 100,
    CONFIDENCE_MEDIUM: 60,
    CONFIDENCE_LOW: 20,
}
DEFAULT_MIN_CONFIDENCE = CONFIDENCE_SCORES[CONFIDENCE_MEDIUM]

SERVICE_REFRESH = "refresh"

UPDATE_INTERVAL = timedelta(minutes=30)

RWDF_BASE_URL = "https://www.runwaydirectionforecast.com"
RWDF_LANGUAGE = "en"
RWDF_INDEX_URL = f"{RWDF_BASE_URL}/{RWDF_LANGUAGE}/"

BRP_BASE_URL = "https://betriebsrichtungsprognose.de"

SOURCE_RWDF = "runwaydirectionforecast.com"
SOURCE_BRP = "betriebsrichtungsprognose.de"

# betriebsrichtungsprognose.de publishes a tendency from -100 to 100 derived
# from wind. Near zero it flips sign on noise alone, and below a few knots an
# airport follows its preferred operating direction rather than the wind —
# neither of which the source models. Both are treated as "no data".
BRP_MIN_TENDENCY = 40
BRP_MIN_WIND_KN = 3
BRP_SLOT_HOURS = 3

ATTR_AIRPORT = "airport"
ATTR_CONFIDENCE = "confidence"
ATTR_CONFIDENCE_CLASS = "confidence_class"
ATTR_CROSSWIND_KMH = "crosswind_kmh"
ATTR_HEADING = "heading"
ATTR_HEADWIND_KMH = "headwind_kmh"
ATTR_IATA = "iata"
ATTR_ICAO = "icao"
ATTR_LAST_UPDATE = "last_update"
ATTR_NEXT_SLOT = "next_slot"
ATTR_NOISE_RUNWAYS = "noise_runways"
ATTR_RUNWAY = "runway"
ATTR_RUNWAY_REF = "runway_ref"
ATTR_SLOTS = "slots"
ATTR_SOURCE = "source"
ATTR_SOURCES = "sources"
ATTR_STARTS_IN_MINUTES = "starts_in_minutes"
ATTR_WARNING_MINUTES = "warning_minutes"
ATTR_WIND_KMH = "wind_kmh"

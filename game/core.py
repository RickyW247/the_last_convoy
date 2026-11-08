"""The Game class of THE LAST CONVOY, assembled from the mixins of this package."""
from .audio import AudioMixin
from .background_rules import BackgroundMixin
from .conditions import ConditionsMixin
from .convoy import ConvoyMixin
from .evacuation import EvacuationMixin
from .horde import HordeMixin
from .navigation import NavigationMixin
from .scavenge import ScavengeMixin
from .state import StateMixin
from .survival import SurvivalMixin
from .travel import TravelMixin


class Game(NavigationMixin, AudioMixin, BackgroundMixin, HordeMixin, SurvivalMixin, ConditionsMixin, ConvoyMixin, TravelMixin, EvacuationMixin,
           ScavengeMixin, StateMixin):
    """The rules of one run. Every method lives in one of the mixins (see game/__init__.py for what is where);
    they all work on the same attributes, which StateMixin.reset() creates."""

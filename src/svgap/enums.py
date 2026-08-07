from enum import Enum

class DemoScenario(str, Enum):
    RESET_RELEASE = "reset-release"
    COMB_CROSSING = "comb-crossing"
    POWER_ON = "power-on"
from enum import Enum

class DemoScenario(str, Enum):
    RESET_RELEASE = "reset-release"
    COMB_CROSSING = "comb-crossing"
    POWER_ON = "power-on"


DEMO_SCENARIO_DESCRIPTIONS = {
    DemoScenario.RESET_RELEASE: "async-assert/sync-release reset intent, safe vs. unsynchronized release",
    DemoScenario.COMB_CROSSING: "combinational signal crossing clock domains, safe vs. unregistered path",
    DemoScenario.POWER_ON: "output reachability from un-reset state, safe vs. missing reset coverage",
}

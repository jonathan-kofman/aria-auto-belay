# aria_models/__init__.py
# ARIA virtual test engine
# Import all three model modules so the dashboard can use them cleanly:
#   from aria_models.static_tests import simulate_static_pawl
#   from aria_models.dynamic_drop import simulate_drop_test
#   from aria_models.state_machine import AriaStateMachine, State, Inputs

from .static_tests import simulate_static_pawl
from .dynamic_drop import simulate_drop_test, simulate_false_trip_check
from .state_machine import AriaStateMachine, State, Inputs, Outputs
